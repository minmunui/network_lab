#!/usr/bin/env python3
"""
네트워크 프로토콜 성능 측정 - Receiver (수신자)

다양한 프로토콜을 통해 데이터를 수신하고 성능을 측정합니다.
지원 프로토콜: MIDTP, TCP, TCP-BBR, QUIC, UDT(stub), SCTP(stub)
"""

import argparse
import socket
import struct
import random
import time
import asyncio
import os
from typing import Set, Dict

# QUIC 관련 임포트 (선택적)
try:
    from aioquic.asyncio import serve
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.asyncio.protocol import QuicConnectionProtocol
    from aioquic.quic.events import StreamDataReceived
    QUIC_AVAILABLE = True
except ImportError:
    QUIC_AVAILABLE = False


# ============================================================================
# MIDTP 프로토콜 구현 (알고리즘 2: 수신자)
# ============================================================================

# MIDTP 패킷 헤더 형식: 시퀀스 번호(4바이트) + 플래그(1바이트)
MIDTP_HEADER_FORMAT = '!IB'  # unsigned int (4), unsigned char (1)
MIDTP_HEADER_SIZE = struct.calcsize(MIDTP_HEADER_FORMAT)

# MIDTP 플래그
FLAG_DATA = 0x01
FLAG_FIN = 0x02
FLAG_NACK = 0x04

# MIDTP 설정
MIDTP_MAX_PACKET_SIZE = 8192
MIDTP_TIMEOUT = 5.0  # 초


class MIDTPReceiver:
    """MIDTP 프로토콜 수신자 구현"""
    
    def __init__(self, host: str, port: int, loss_rate: float = 0.0):
        self.host = host
        self.port = port
        self.loss_rate = loss_rate
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.settimeout(MIDTP_TIMEOUT)
        
        self.received_packets: Dict[int, bytes] = {}
        self.sender_addr = None
        self.total_packets = 0
        self.fin_received = False
        
    def receive_data(self) -> bytes:
        """데이터 수신 및 MIDTP 프로토콜 처리"""
        print(f"[MIDTP] Receiver listening on {self.host}:{self.port}")
        print(f"[MIDTP] Packet loss simulation: {self.loss_rate * 100:.1f}%")
        
        retransmission_round = 0
        packets_received = 0
        packets_dropped = 0
        
        while not self.fin_received:
            try:
                # 패킷 수신
                data, addr = self.sock.recvfrom(MIDTP_MAX_PACKET_SIZE + MIDTP_HEADER_SIZE)
                
                if self.sender_addr is None:
                    self.sender_addr = addr
                    print(f"[MIDTP] Connected to sender: {addr}")
                
                # 패킷 손실 시뮬레이션
                if random.random() < self.loss_rate:
                    packets_dropped += 1
                    if packets_dropped <= 10:  # 처음 10개만 출력
                        print(f"[MIDTP] 📉 Packet dropped (simulated loss)")
                    elif packets_dropped == 11:
                        print(f"[MIDTP] 📉 ... (추가 손실 패킷은 로그 생략)")
                    continue  # 패킷 드롭
                
                # 헤더 파싱
                if len(data) < MIDTP_HEADER_SIZE:
                    continue
                
                seq_num, flags = struct.unpack(MIDTP_HEADER_FORMAT, data[:MIDTP_HEADER_SIZE])
                payload = data[MIDTP_HEADER_SIZE:]
                
                # FIN 패킷 처리
                if flags & FLAG_FIN:
                    print(f"[MIDTP] 🏁 FIN packet received (total packets expected: {seq_num})")
                    print(f"[MIDTP] 📊 Statistics: {packets_received} received, {packets_dropped} dropped")
                    self.total_packets = seq_num
                    self.fin_received = True
                    
                    # 누락된 패킷 확인 및 NACK 전송
                    missing = self._find_missing_packets()
                    if missing:
                        retransmission_round += 1
                        print(f"[MIDTP] ⚠️  Retransmission round {retransmission_round}: {len(missing)} packets missing")
                        print(f"[MIDTP] 🔍 Missing packet IDs: {sorted(list(missing))[:20]}{'...' if len(missing) > 20 else ''}")
                        self._send_nack(missing)
                        self.fin_received = False  # 재전송 대기
                    else:
                        print(f"[MIDTP] ✅ All packets received successfully")
                        self._send_ack()
                        break
                
                # 데이터 패킷 처리
                elif flags & FLAG_DATA:
                    if seq_num not in self.received_packets:
                        self.received_packets[seq_num] = payload
                        packets_received += 1
                        
                        # 진행 상황 표시 (매 100개 패킷마다)
                        if packets_received % 100 == 0:
                            print(f"[MIDTP] 📦 Received {packets_received} packets...")
                
            except socket.timeout:
                if self.fin_received:
                    # FIN 수신 후 타임아웃 발생 시 누락 패킷 확인
                    missing = self._find_missing_packets()
                    if missing:
                        retransmission_round += 1
                        print(f"[MIDTP] ⏱️  Timeout - Retransmission round {retransmission_round}: {len(missing)} packets missing")
                        print(f"[MIDTP] 🔍 Missing packet IDs: {sorted(list(missing))[:20]}{'...' if len(missing) > 20 else ''}")
                        self._send_nack(missing)
                        self.fin_received = False
                    else:
                        print(f"[MIDTP] ✅ All packets received after timeout")
                        break
                else:
                    # FIN 수신 전 타임아웃
                    if len(self.received_packets) > 0:
                        print(f"[MIDTP] ⏱️  Timeout waiting for more packets ({len(self.received_packets)} received)")
                    continue
        
        # 수신된 데이터를 시퀀스 순서대로 재조립
        result = bytearray()
        for seq in sorted(self.received_packets.keys()):
            result.extend(self.received_packets[seq])
        
        print(f"\n[MIDTP] 📊 Final Statistics:")
        print(f"[MIDTP]   ✓ Total data received: {len(result)} bytes")
        print(f"[MIDTP]   ✓ Total packets: {len(self.received_packets)}")
        print(f"[MIDTP]   ✓ Packets dropped (simulated): {packets_dropped}")
        print(f"[MIDTP]   ✓ Retransmission rounds: {retransmission_round}")
        return bytes(result)
    
    def _find_missing_packets(self) -> Set[int]:
        """누락된 패킷 시퀀스 번호 찾기"""
        if self.total_packets == 0:
            return set()
        
        expected = set(range(self.total_packets))
        received = set(self.received_packets.keys())
        return expected - received
    
    def _send_nack(self, missing_seq_nums: Set[int]):
        """NACK 패킷 전송 (누락된 패킷 목록 포함)"""
        if not self.sender_addr:
            return
        
        # NACK 패킷: 헤더(누락 개수) + 시퀀스 번호 리스트
        count = len(missing_seq_nums)
        nack_data = struct.pack(MIDTP_HEADER_FORMAT, count, FLAG_NACK)
        
        # 누락된 시퀀스 번호들을 패킷에 추가
        for seq in sorted(missing_seq_nums):
            nack_data += struct.pack('!I', seq)
        
        self.sock.sendto(nack_data, self.sender_addr)
        print(f"[MIDTP] 📤 NACK sent: requesting {count} missing packets")
    
    def _send_ack(self):
        """ACK 패킷 전송 (전송 완료 확인)"""
        if not self.sender_addr:
            return
        
        ack_data = struct.pack(MIDTP_HEADER_FORMAT, 0, FLAG_FIN | FLAG_DATA)
        self.sock.sendto(ack_data, self.sender_addr)
        print(f"[MIDTP] 📤 ACK sent (transmission complete)")
    
    def close(self):
        """소켓 종료"""
        self.sock.close()


# ============================================================================
# TCP 프로토콜 구현 (Baseline 및 BBR)
# ============================================================================

class TCPReceiver:
    """TCP 프로토콜 수신자 구현"""
    
    def __init__(self, host: str, port: int, protocol_name: str = "TCP"):
        self.host = host
        self.port = port
        self.protocol_name = protocol_name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(1)
        
    def receive_data(self) -> bytes:
        """TCP 연결을 통해 데이터 수신"""
        print(f"[{self.protocol_name}] Receiver listening on {self.host}:{self.port}")
        
        # 클라이언트 연결 대기
        conn, addr = self.sock.accept()
        print(f"[{self.protocol_name}] ✅ Connected to sender: {addr}")
        
        # 데이터 수신
        received_data = bytearray()
        chunks_received = 0
        try:
            while True:
                chunk = conn.recv(65536)  # 큰 버퍼 크기 사용
                if not chunk:
                    break
                received_data.extend(chunk)
                chunks_received += 1
                
                # 진행 상황 표시 (매 100개 청크마다)
                if chunks_received % 100 == 0:
                    print(f"[{self.protocol_name}] 📦 Received {len(received_data) / (1024*1024):.2f} MB...")
        except Exception as e:
            print(f"[{self.protocol_name}] ❌ Error during reception: {e}")
        finally:
            conn.close()
        
        print(f"[{self.protocol_name}] 📊 Total received: {len(received_data)} bytes in {chunks_received} chunks")
        return bytes(received_data)
    
    def close(self):
        """소켓 종료"""
        self.sock.close()


# ============================================================================
# QUIC 프로토콜 구현
# ============================================================================

if QUIC_AVAILABLE:
    class QuicServerProtocol(QuicConnectionProtocol):
        """QUIC 서버 프로토콜 핸들러"""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.received_data = bytearray()
            self.transfer_complete = asyncio.Event()
        
        def quic_event_received(self, event):
            """QUIC 이벤트 처리"""
            if isinstance(event, StreamDataReceived):
                # 스트림 데이터 수신
                data_len_before = len(self.received_data)
                self.received_data.extend(event.data)
                
                # 진행 상황 표시 (매 10MB마다)
                if len(self.received_data) % (10 * 1024 * 1024) < len(event.data):
                    print(f"[QUIC] 📦 Received {len(self.received_data) / (1024*1024):.2f} MB...")
                
                # 스트림 종료 확인
                if event.end_stream:
                    print(f"[QUIC] ✅ Stream {event.stream_id} complete: {len(self.received_data)} bytes")
                    self.transfer_complete.set()


class QUICReceiver:
    """QUIC 프로토콜 수신자 구현"""
    
    def __init__(self, host: str, port: int):
        if not QUIC_AVAILABLE:
            raise ImportError("aioquic 라이브러리가 설치되지 않았습니다. 'pip install aioquic'를 실행하세요.")
        
        self.host = host
        self.port = port
        self.protocol_instance = None
        
    async def receive_data_async(self) -> bytes:
        """QUIC 연결을 통해 데이터 수신 (비동기)"""
        print(f"[QUIC] Receiver listening on {self.host}:{self.port}")
        
        # QUIC 설정
        configuration = QuicConfiguration(
            is_client=False,
            max_datagram_frame_size=65536,
        )
        
        # TLS 인증서 로드
        if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
            raise FileNotFoundError(
                "QUIC 인증서 파일(cert.pem, key.pem)이 없습니다.\n"
                "다음 명령어로 생성하세요:\n"
                "openssl req -x509 -newkey rsa:2048 -nodes "
                "-keyout key.pem -out cert.pem -days 365 "
                "-subj '/C=KR/ST=Seoul/L=Seoul/O=NetworkLab/CN=localhost'"
            )
        
        configuration.load_cert_chain("cert.pem", "key.pem")
        print(f"[QUIC] ✅ TLS certificates loaded")
        
        # QUIC 서버 시작
        def create_protocol(*args, **kwargs):
            self.protocol_instance = QuicServerProtocol(*args, **kwargs)
            return self.protocol_instance
        
        server = await serve(
            self.host,
            self.port,
            configuration=configuration,
            create_protocol=create_protocol,
        )
        
        print(f"[QUIC] ⏳ Server started, waiting for connection...")
        
        # 데이터 전송 완료 대기
        if self.protocol_instance:
            await self.protocol_instance.transfer_complete.wait()
        
        # 서버 종료
        server.close()
        
        received_data = self.protocol_instance.received_data if self.protocol_instance else bytearray()
        print(f"[QUIC] 📊 Total received: {len(received_data)} bytes")
        return bytes(received_data)
    
    def receive_data(self) -> bytes:
        """동기 인터페이스를 위한 래퍼"""
        return asyncio.run(self.receive_data_async())


# ============================================================================
# UDT 프로토콜 (스텁)
# ============================================================================

class UDTReceiver:
    """UDT 프로토콜 수신자 (스텁 구현)"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
    
    def receive_data(self) -> bytes:
        """UDT는 스텁으로만 구현됨"""
        print("\n" + "="*70)
        print("[UDT] 이 프로토콜은 현재 스텁(stub)으로만 구현되었습니다.")
        print("="*70)
        print("\n실제 UDT 구현을 위해서는 다음이 필요합니다:")
        print("  1. pyudt 라이브러리 (pip install pyudt)")
        print("  2. UDT4 C++ 라이브러리")
        print("  3. C++ 컴파일러 및 빌드 도구")
        print("\nUDT는 대용량 데이터 전송에 최적화된 고성능 프로토콜로,")
        print("특히 높은 대역폭-지연 곱(BDP) 환경에서 뛰어난 성능을 보입니다.")
        print("\n자세한 정보: https://udt.sourceforge.io/")
        print("="*70 + "\n")
        raise NotImplementedError("UDT 프로토콜은 스텁으로만 구현되었습니다.")
    
    def close(self):
        pass


# ============================================================================
# SCTP 프로토콜 (스텁)
# ============================================================================

class SCTPReceiver:
    """SCTP 프로토콜 수신자 (스텁 구현)"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
    
    def receive_data(self) -> bytes:
        """SCTP는 스텁으로만 구현됨"""
        print("\n" + "="*70)
        print("[SCTP] 이 프로토콜은 현재 스텁(stub)으로만 구현되었습니다.")
        print("="*70)
        print("\n실제 SCTP 구현을 위해서는 다음이 필요합니다:")
        print("  1. pysctp 라이브러리 (pip install pysctp)")
        print("  2. Linux 커널의 SCTP 모듈 지원")
        print("  3. lksctp-tools 패키지")
        print("\nSCTP는 TCP와 UDP의 장점을 결합한 프로토콜로,")
        print("멀티스트리밍과 멀티호밍을 지원합니다.")
        print("\n주의: macOS는 SCTP를 제한적으로만 지원합니다.")
        print("\n자세한 정보: https://en.wikipedia.org/wiki/Stream_Control_Transmission_Protocol")
        print("="*70 + "\n")
        raise NotImplementedError("SCTP 프로토콜은 스텁으로만 구현되었습니다.")
    
    def close(self):
        pass


# ============================================================================
# 메인 함수
# ============================================================================

def main():
    """메인 함수: 명령줄 인자 파싱 및 수신자 실행"""
    parser = argparse.ArgumentParser(
        description='네트워크 프로토콜 성능 측정 - Receiver (수신자)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python3 receiver.py --protocol midtp --host 0.0.0.0 --port 5000 --loss-rate 0.05
  python3 receiver.py --protocol tcp --host 0.0.0.0 --port 5001
  python3 receiver.py --protocol bbr --host 0.0.0.0 --port 5002
  python3 receiver.py --protocol quic --host 0.0.0.0 --port 5003
        """
    )
    
    parser.add_argument(
        '--protocol',
        type=str,
        required=True,
        choices=['midtp', 'tcp', 'bbr', 'quic', 'udt', 'sctp'],
        help='사용할 프로토콜 선택'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='바인딩할 IP 주소 (기본값: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='포트 번호 (기본값: 5000)'
    )
    
    parser.add_argument(
        '--loss-rate',
        type=float,
        default=0.0,
        help='패킷 손실률 시뮬레이션 (0.0~1.0, MIDTP 전용, 기본값: 0.0)'
    )
    
    args = parser.parse_args()
    
    # 프로토콜에 따라 적절한 수신자 인스턴스 생성
    receiver = None
    
    try:
        print(f"\n{'='*70}")
        print(f"네트워크 프로토콜 성능 측정 - Receiver")
        print(f"프로토콜: {args.protocol.upper()}")
        print(f"{'='*70}\n")
        
        if args.protocol == 'midtp':
            receiver = MIDTPReceiver(args.host, args.port, args.loss_rate)
        
        elif args.protocol == 'tcp':
            receiver = TCPReceiver(args.host, args.port, "TCP")
        
        elif args.protocol == 'bbr':
            print("[TCP-BBR] 주의: Sender 측에서 BBR 혼잡 제어 알고리즘을 활성화해야 합니다.")
            print("[TCP-BBR] Linux 커널 설정: sudo sysctl -w net.ipv4.tcp_congestion_control=bbr")
            print()
            receiver = TCPReceiver(args.host, args.port, "TCP-BBR")
        
        elif args.protocol == 'quic':
            receiver = QUICReceiver(args.host, args.port)
        
        elif args.protocol == 'udt':
            receiver = UDTReceiver(args.host, args.port)
        
        elif args.protocol == 'sctp':
            receiver = SCTPReceiver(args.host, args.port)
        
        # 데이터 수신
        start_time = time.time()
        data = receiver.receive_data()
        end_time = time.time()
        
        # 결과 출력
        elapsed_time = end_time - start_time
        data_size_mb = len(data) / (1024 * 1024)
        
        print(f"\n{'='*70}")
        print(f"=== 수신 완료 ===")
        print(f"프로토콜: {args.protocol.upper()}")
        print(f"수신 크기: {data_size_mb:.2f} MB")
        print(f"총 소요 시간: {elapsed_time:.2f} 초")
        if elapsed_time > 0:
            print(f"처리율: {data_size_mb / elapsed_time:.2f} MB/s")
        print(f"{'='*70}\n")
        
    except KeyboardInterrupt:
        print("\n\n[중단] 사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        print(f"\n[오류] {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if receiver:
            receiver.close()


if __name__ == '__main__':
    main()
