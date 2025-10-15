#!/usr/bin/env python3
"""
네트워크 프로토콜 성능 측정 - Sender (송신자)

다양한 프로토콜을 통해 대용량 데이터를 전송하고 성능을 측정합니다.
지원 프로토콜: MIDTP, TCP, TCP-BBR, QUIC, UDT(stub), SCTP(stub)
"""

import argparse
import socket
import struct
import time
import os
import asyncio
from typing import Set

# QUIC 관련 임포트 (선택적)
try:
    from aioquic.asyncio import connect
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.asyncio.protocol import QuicConnectionProtocol
    QUIC_AVAILABLE = True
except ImportError:
    QUIC_AVAILABLE = False


# ============================================================================
# MIDTP 프로토콜 구현 (알고리즘 1: 송신자)
# ============================================================================

# MIDTP 패킷 헤더 형식: 시퀀스 번호(4바이트) + 플래그(1바이트)
MIDTP_HEADER_FORMAT = '!IB'  # unsigned int (4), unsigned char (1)
MIDTP_HEADER_SIZE = struct.calcsize(MIDTP_HEADER_FORMAT)

# MIDTP 플래그
FLAG_DATA = 0x01
FLAG_FIN = 0x02
FLAG_NACK = 0x04

# MIDTP 설정
MIDTP_MAX_PAYLOAD_SIZE = 8192
MIDTP_TIMEOUT = 5.0  # 초
MIDTP_MAX_RETRIES = 10


class MIDTPSender:
    """MIDTP 프로토콜 송신자 구현"""
    
    def __init__(self, host: str, port: int, chunk_size: int = MIDTP_MAX_PAYLOAD_SIZE):
        self.host = host
        self.port = port
        self.chunk_size = min(chunk_size, MIDTP_MAX_PAYLOAD_SIZE)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(MIDTP_TIMEOUT)
        
    def send_data(self, data: bytes) -> float:
        """데이터 전송 및 MIDTP 프로토콜 처리"""
        print(f"[MIDTP] Connecting to {self.host}:{self.port}")
        print(f"[MIDTP] Data size: {len(data)} bytes, Chunk size: {self.chunk_size} bytes")
        
        start_time = time.time()
        
        # 데이터를 청크로 분할
        chunks = []
        for i in range(0, len(data), self.chunk_size):
            chunks.append(data[i:i + self.chunk_size])
        
        total_packets = len(chunks)
        print(f"[MIDTP] 📦 Total packets to send: {total_packets}")
        
        # 패킷 전송 사이클
        retry_count = 0
        packets_to_send = set(range(total_packets))  # 전송할 패킷 시퀀스 번호
        total_packets_sent = 0
        
        while retry_count < MIDTP_MAX_RETRIES:
            # 1. 데이터 패킷 전송
            sent_count = self._send_packets(chunks, packets_to_send)
            total_packets_sent += sent_count
            
            # 2. FIN 패킷 전송
            self._send_fin(total_packets)
            
            # 3. NACK 또는 ACK 대기
            response = self._wait_for_response()
            
            if response is None:
                # 타임아웃 - 재전송
                retry_count += 1
                print(f"[MIDTP] ⏱️  Timeout waiting for response (retry {retry_count}/{MIDTP_MAX_RETRIES})")
                continue
            
            if response == 'ACK':
                # 전송 완료
                print(f"[MIDTP] ✅ Transfer complete (ACK received)")
                print(f"[MIDTP] 📊 Total packets sent (including retransmissions): {total_packets_sent}")
                break
            
            elif isinstance(response, set):
                # NACK 수신 - 손실된 패킷만 재전송
                packets_to_send = response
                retry_count += 1
                print(f"[MIDTP] ⚠️  NACK received: {len(packets_to_send)} packets need retransmission")
                print(f"[MIDTP] 🔍 Lost packet IDs: {sorted(list(packets_to_send))[:20]}{'...' if len(packets_to_send) > 20 else ''}")
                print(f"[MIDTP] 🔄 Starting retransmission round {retry_count}/{MIDTP_MAX_RETRIES}")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        if retry_count >= MIDTP_MAX_RETRIES:
            print(f"[MIDTP] ⚠️  Warning: Max retries reached, transmission may be incomplete")
        
        print(f"\n[MIDTP] 📊 Transmission Statistics:")
        print(f"[MIDTP]   ✓ Original packets: {total_packets}")
        print(f"[MIDTP]   ✓ Total packets sent: {total_packets_sent}")
        print(f"[MIDTP]   ✓ Retransmission rounds: {retry_count}")
        print(f"[MIDTP]   ✓ Retransmission overhead: {((total_packets_sent - total_packets) / total_packets * 100):.1f}%")
        
        return elapsed_time
    
    def _send_packets(self, chunks: list, packet_indices: Set[int]) -> int:
        """지정된 패킷들을 전송"""
        sent_count = 0
        for seq_num in sorted(packet_indices):
            if seq_num >= len(chunks):
                continue
            
            # 패킷 생성: 헤더 + 페이로드
            header = struct.pack(MIDTP_HEADER_FORMAT, seq_num, FLAG_DATA)
            packet = header + chunks[seq_num]
            
            # 패킷 전송
            self.sock.sendto(packet, (self.host, self.port))
            sent_count += 1
            
            # 진행 상황 표시 (매 100개 패킷마다)
            if sent_count % 100 == 0:
                print(f"[MIDTP] 📤 Sending packets... {sent_count}/{len(packet_indices)}")
        
        print(f"[MIDTP] 📤 Sent {sent_count} packets")
        return sent_count
    
    def _send_fin(self, total_packets: int):
        """FIN 패킷 전송 (전송 완료 알림)"""
        fin_packet = struct.pack(MIDTP_HEADER_FORMAT, total_packets, FLAG_FIN)
        self.sock.sendto(fin_packet, (self.host, self.port))
        print(f"[MIDTP] 🏁 FIN packet sent (signaling end of transmission)")
    
    def _wait_for_response(self):
        """NACK 또는 ACK 대기"""
        try:
            print(f"[MIDTP] ⏳ Waiting for receiver response...")
            data, _ = self.sock.recvfrom(65536)
            
            if len(data) < MIDTP_HEADER_SIZE:
                return None
            
            count, flags = struct.unpack(MIDTP_HEADER_FORMAT, data[:MIDTP_HEADER_SIZE])
            
            # ACK 확인
            if (flags & FLAG_FIN) and (flags & FLAG_DATA):
                print(f"[MIDTP] 📨 ACK received from receiver")
                return 'ACK'
            
            # NACK 처리
            if flags & FLAG_NACK:
                # NACK 패킷에서 누락된 시퀀스 번호 추출
                missing = set()
                offset = MIDTP_HEADER_SIZE
                for _ in range(count):
                    if offset + 4 <= len(data):
                        seq_num = struct.unpack('!I', data[offset:offset+4])[0]
                        missing.add(seq_num)
                        offset += 4
                
                print(f"[MIDTP] 📨 NACK received: {len(missing)} packets requested")
                return missing
            
            return None
            
        except socket.timeout:
            return None
    
    def close(self):
        """소켓 종료"""
        self.sock.close()


# ============================================================================
# TCP 프로토콜 구현 (Baseline 및 BBR)
# ============================================================================

class TCPSender:
    """TCP 프로토콜 송신자 구현"""
    
    def __init__(self, host: str, port: int, protocol_name: str = "TCP"):
        self.host = host
        self.port = port
        self.protocol_name = protocol_name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # TCP 성능 최적화
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
    def send_data(self, data: bytes) -> float:
        """TCP 연결을 통해 데이터 전송"""
        print(f"[{self.protocol_name}] Connecting to {self.host}:{self.port}")
        print(f"[{self.protocol_name}] Data size: {len(data) / (1024*1024):.2f} MB")
        
        # 서버에 연결
        self.sock.connect((self.host, self.port))
        print(f"[{self.protocol_name}] ✅ Connected to receiver")
        
        # 데이터 전송
        start_time = time.time()
        
        # 진행 상황을 위해 청크로 전송
        chunk_size = 1024 * 1024  # 1MB 청크
        total_sent = 0
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            self.sock.sendall(chunk)
            total_sent += len(chunk)
            
            # 진행 상황 표시 (매 10MB마다)
            if total_sent % (10 * 1024 * 1024) == 0 or total_sent == len(data):
                print(f"[{self.protocol_name}] 📤 Sent {total_sent / (1024*1024):.2f} MB / {len(data) / (1024*1024):.2f} MB")
        
        # 우아한 종료
        self.sock.shutdown(socket.SHUT_WR)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        print(f"[{self.protocol_name}] ✅ Transfer complete")
        
        return elapsed_time
    
    def close(self):
        """소켓 종료"""
        self.sock.close()


# ============================================================================
# QUIC 프로토콜 구현
# ============================================================================

if QUIC_AVAILABLE:
    class QuicClientProtocol(QuicConnectionProtocol):
        """QUIC 클라이언트 프로토콜 핸들러"""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.data_sent = asyncio.Event()
        
        async def send_data_on_stream(self, data: bytes):
            """스트림을 통해 데이터 전송"""
            stream_id = self._quic.get_next_available_stream_id()
            print(f"[QUIC] 📤 Opened stream {stream_id} for data transfer")
            
            # 큰 데이터를 청크로 분할하여 전송
            chunk_size = 1024 * 1024  # 1MB 청크
            total_sent = 0
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                end_stream = (i + chunk_size >= len(data))
                
                self._quic.send_stream_data(stream_id, chunk, end_stream=end_stream)
                self.transmit()
                total_sent += len(chunk)
                
                # 진행 상황 표시 (매 10MB마다)
                if total_sent % (10 * 1024 * 1024) == 0 or end_stream:
                    print(f"[QUIC] 📤 Sent {total_sent / (1024*1024):.2f} MB / {len(data) / (1024*1024):.2f} MB")
                
                # 백프레셔 방지를 위한 짧은 대기
                await asyncio.sleep(0.001)
            
            print(f"[QUIC] ✅ All data sent on stream {stream_id}")
            self.data_sent.set()


class QUICServer:
    """QUIC 프로토콜 송신자 구현"""
    
    def __init__(self, host: str, port: int):
        if not QUIC_AVAILABLE:
            raise ImportError("aioquic 라이브러리가 설치되지 않았습니다. 'pip install aioquic'를 실행하세요.")
        
        self.host = host
        self.port = port
        
    async def send_data_async(self, data: bytes) -> float:
        """QUIC 연결을 통해 데이터 전송 (비동기)"""
        print(f"[QUIC] Connecting to {self.host}:{self.port}")
        print(f"[QUIC] Data size: {len(data) / (1024*1024):.2f} MB")
        
        # QUIC 클라이언트 설정
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["file-transfer"],
        )
        # 자체 서명 인증서 검증 비활성화 (테스트 목적)
        configuration.verify_mode = False
        print(f"[QUIC] ✅ Configuration set (self-signed cert mode)")
        
        start_time = time.time()
        
        # QUIC 연결 설정
        async with connect(
            self.host,
            self.port,
            configuration=configuration,
            create_protocol=QuicClientProtocol,
        ) as client:
            client = client  # type: QuicClientProtocol
            print(f"[QUIC] ✅ Connected to receiver")
            
            # 데이터 전송
            await client.send_data_on_stream(data)
            
            # 전송 완료 대기
            await client.data_sent.wait()
            
            # 연결 종료 대기
            await asyncio.sleep(0.5)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"[QUIC] ✅ Transfer complete")
        return elapsed_time
    
    def send_data(self, data: bytes) -> float:
        """동기 인터페이스를 위한 래퍼"""
        return asyncio.run(self.send_data_async(data))


# ============================================================================
# UDT 프로토콜 (스텁)
# ============================================================================

class UDTSender:
    """UDT 프로토콜 송신자 (스텁 구현)"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
    
    def send_data(self, data: bytes) -> float:
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

class SCTPSender:
    """SCTP 프로토콜 송신자 (스텁 구현)"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
    
    def send_data(self, data: bytes) -> float:
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
# 유틸리티 함수
# ============================================================================

def generate_dummy_data(size_mb: int) -> bytes:
    """지정된 크기의 더미 데이터 생성"""
    size_bytes = size_mb * 1024 * 1024
    print(f"[Data] Generating {size_mb} MB of random data...")
    data = os.urandom(size_bytes)
    print(f"[Data] Data generation complete")
    return data


# ============================================================================
# 메인 함수
# ============================================================================

def main():
    """메인 함수: 명령줄 인자 파싱 및 송신자 실행"""
    parser = argparse.ArgumentParser(
        description='네트워크 프로토콜 성능 측정 - Sender (송신자)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 100
  python3 sender.py --protocol tcp --host 192.168.1.100 --port 5001 --file-size 500
  python3 sender.py --protocol bbr --host 127.0.0.1 --port 5002 --file-size 1024
  python3 sender.py --protocol quic --host 127.0.0.1 --port 5003 --file-size 100
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
        default='127.0.0.1',
        help='수신자 IP 주소 (기본값: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='포트 번호 (기본값: 5000)'
    )
    
    parser.add_argument(
        '--file-size',
        type=int,
        default=100,
        help='전송할 파일 크기 (MB 단위, 기본값: 100)'
    )
    
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=8192,
        help='한 번에 전송할 데이터 청크 크기 (바이트, 기본값: 8192)'
    )
    
    args = parser.parse_args()
    
    # 입력 검증
    if args.file_size <= 0:
        print("[오류] 파일 크기는 양수여야 합니다.")
        return
    
    if args.chunk_size <= 0:
        print("[오류] 청크 크기는 양수여야 합니다.")
        return
    
    # 프로토콜에 따라 적절한 송신자 인스턴스 생성
    sender = None
    
    try:
        print(f"\n{'='*70}")
        print(f"네트워크 프로토콜 성능 측정 - Sender")
        print(f"프로토콜: {args.protocol.upper()}")
        print(f"{'='*70}\n")
        
        # 더미 데이터 생성
        data = generate_dummy_data(args.file_size)
        
        # 프로토콜별 송신자 생성
        if args.protocol == 'midtp':
            sender = MIDTPSender(args.host, args.port, args.chunk_size)
        
        elif args.protocol == 'tcp':
            sender = TCPSender(args.host, args.port, "TCP")
        
        elif args.protocol == 'bbr':
            print("[TCP-BBR] 주의: BBR 혼잡 제어 알고리즘이 활성화되어 있는지 확인하세요.")
            print("[TCP-BBR] Linux 커널 설정: sudo sysctl -w net.ipv4.tcp_congestion_control=bbr")
            print("[TCP-BBR] 확인: sysctl net.ipv4.tcp_congestion_control")
            print()
            sender = TCPSender(args.host, args.port, "TCP-BBR")
        
        elif args.protocol == 'quic':
            sender = QUICServer(args.host, args.port)
        
        elif args.protocol == 'udt':
            sender = UDTSender(args.host, args.port)
        
        elif args.protocol == 'sctp':
            sender = SCTPSender(args.host, args.port)
        
        # 데이터 전송
        print()
        elapsed_time = sender.send_data(data)
        
        # 결과 출력
        data_size_mb = len(data) / (1024 * 1024)
        throughput = data_size_mb / elapsed_time if elapsed_time > 0 else 0
        
        print(f"\n{'='*70}")
        print(f"=== 전송 완료 ===")
        print(f"프로토콜: {args.protocol.upper()}")
        print(f"파일 크기: {data_size_mb:.2f} MB")
        print(f"총 소요 시간: {elapsed_time:.2f} 초")
        print(f"처리율: {throughput:.2f} MB/s")
        print(f"{'='*70}\n")
        
    except KeyboardInterrupt:
        print("\n\n[중단] 사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        print(f"\n[오류] {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if sender:
            sender.close()


if __name__ == '__main__':
    main()
