#!/usr/bin/env python3
"""
최적의 세그먼트 크기 탐색 실험

MIDTP와 TCP의 청크(세그먼트) 크기에 따른 처리율을 측정하여
최적의 세그먼트 크기를 찾는 실험 스크립트입니다.
논문의 그래프 1을 재현합니다.
"""

import socket
import argparse
import os
import struct
import time
import math
import threading
import matplotlib.pyplot as plt
from typing import List, Tuple

# --- 실험 환경 설정 ---
DEFAULT_FILE_SIZE_MB = 50
DEFAULT_RECEIVER_HOST = '127.0.0.1'  # 로컬 테스트용. 원격 테스트 시 수신자 IP로 변경
DEFAULT_TCP_PORT = 9998
DEFAULT_MIDTP_PORT = 9999
CHUNK_SIZE_RANGE = range(1400, 15401, 1400)  # 1400부터 15400까지 1400씩 증가 (약 10구간)

# --- MIDTP 프로토콜 상수 ---
PACKET_HEADER_FORMAT = "!IIHB"
PACKET_HEADER_SIZE = struct.calcsize(PACKET_HEADER_FORMAT)
FLAG_DATA = 0x01
FLAG_NACK = 0x02
FLAG_INIT = 0x04
FLAG_FIN = 0x08

# --- 수신자 스레드 관리 ---
stop_receiver = threading.Event()


# --- 수신자 로직 (백그라운드 스레드에서 실행) ---
def receiver_thread_func(host: str, tcp_port: int, midtp_port: int):
    """TCP와 MIDTP 수신을 모두 처리하는 스레드 함수"""
    
    # TCP 소켓 설정
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_sock.bind((host, tcp_port))
    tcp_sock.listen(1)
    tcp_sock.settimeout(0.5)  # 루프 종료를 위해 타임아웃 설정

    # MIDTP 소켓 설정
    midtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    midtp_sock.bind((host, midtp_port))
    midtp_sock.settimeout(0.5)

    print(f"🔧 TCP 포트 {tcp_port}, MIDTP 포트 {midtp_port}에서 수신 대기 중...")

    while not stop_receiver.is_set():
        # TCP 연결 처리
        try:
            conn, addr = tcp_sock.accept()
            print(f"  📡 TCP 연결 수신: {addr}")
            with conn:
                # 파일 크기 수신
                file_size_data = conn.recv(8)
                if not file_size_data:
                    continue
                file_size = struct.unpack("!Q", file_size_data)[0]
                
                bytes_received = 0
                while bytes_received < file_size:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    bytes_received += len(chunk)
                
                print(f"  ✅ TCP 수신 완료: {bytes_received / (1024*1024):.2f} MB")
        except socket.timeout:
            pass  # 타임아웃은 정상, 루프 계속
        except Exception as e:
            if not stop_receiver.is_set():
                print(f"  ⚠️ TCP 오류: {e}")

        # MIDTP 패킷 처리
        try:
            # MIDTP는 상태를 유지해야 하므로 간단한 상태 머신으로 구현
            # 이 실험에서는 송신자가 전송을 완료하면 수신자는 자동으로 리셋됨
            # 실제 구현에서는 세션 관리가 필요함
            packet, sender_addr = midtp_sock.recvfrom(65535)
            if len(packet) >= PACKET_HEADER_SIZE:
                seq_num, total_packets, payload_len, flags = struct.unpack(
                    PACKET_HEADER_FORMAT, 
                    packet[:PACKET_HEADER_SIZE]
                )
                
                # INIT 패킷 처리
                if flags & FLAG_INIT:
                    print(f"  📡 MIDTP 세션 시작: {sender_addr}, 총 {total_packets}개 패킷")
                
                # FIN 패킷 처리
                if flags & FLAG_FIN:
                    print(f"  ✅ MIDTP 수신 완료")
                    
        except socket.timeout:
            pass
        except Exception as e:
            if not stop_receiver.is_set():
                print(f"  ⚠️ MIDTP 오류: {e}")

    tcp_sock.close()
    midtp_sock.close()
    print("🔧 수신자 스레드 종료.")


# --- 송신자 로직 ---
def run_tcp_transfer(host: str, port: int, data: bytes, chunk_size: int) -> float:
    """TCP로 데이터를 전송하고 처리율을 반환"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        start_time = time.time()
        
        # 파일 크기 먼저 전송
        sock.sendall(struct.pack("!Q", len(data)))
        
        # 지정된 청크 크기로 데이터 전송
        total_sent = 0
        while total_sent < len(data):
            chunk = data[total_sent:total_sent + chunk_size]
            sock.sendall(chunk)
            total_sent += len(chunk)
        
        end_time = time.time()
        sock.close()
        
        total_time = end_time - start_time
        throughput = (len(data) / (1024*1024)) / total_time if total_time > 0 else 0
        return throughput
        
    except ConnectionRefusedError:
        print(f"  ❌ 연결 거부. 수신자가 실행 중인지 확인하세요.")
        return 0
    except Exception as e:
        print(f"  ❌ TCP 전송 오류: {e}")
        return 0


def run_midtp_transfer(host: str, port: int, data: bytes, chunk_size: int) -> float:
    """MIDTP로 데이터를 전송하고 처리율을 반환"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver_addr = (host, port)
        
        # 패킷 생성
        packets = []
        total_packets = math.ceil(len(data) / chunk_size)
        
        for i in range(total_packets):
            start = i * chunk_size
            end = start + chunk_size
            payload = data[start:end]
            header = struct.pack(
                PACKET_HEADER_FORMAT, 
                i, 
                total_packets, 
                len(payload), 
                FLAG_DATA
            )
            packets.append(header + payload)

        start_time = time.time()
        
        # INIT 패킷 전송 (수신자가 주소를 알 수 있도록)
        init_header = struct.pack(PACKET_HEADER_FORMAT, 0, total_packets, 0, FLAG_INIT)
        sock.sendto(init_header, receiver_addr)
        time.sleep(0.01)  # INIT 처리 대기

        # MIDTP는 재전송 로직이 복잡하므로, 이 실험에서는 손실이 거의 없는
        # 로컬 환경을 가정하고 재전송 없이 전송 시간만 측정하여
        # 버퍼 오버플로우 현상을 관찰하는 데 집중합니다.
        for packet in packets:
            sock.sendto(packet, receiver_addr)

        # FIN 패킷 전송
        fin_header = struct.pack(PACKET_HEADER_FORMAT, total_packets, total_packets, 0, FLAG_FIN)
        sock.sendto(fin_header, receiver_addr)
        
        # 모든 데이터가 전송되었다고 가정하고 시간 측정 종료
        end_time = time.time()
        sock.close()

        total_time = end_time - start_time
        throughput = (len(data) / (1024*1024)) / total_time if total_time > 0 else 0
        return throughput
        
    except Exception as e:
        print(f"  ❌ MIDTP 전송 오류: {e}")
        return 0


# --- 결과 시각화 ---
def plot_results(tcp_results: List[Tuple[int, float]], midtp_results: List[Tuple[int, float]], 
                 output_file: str = None):
    """실험 결과를 그래프로 시각화"""
    
    if not tcp_results or not midtp_results:
        print("❌ 결과 데이터가 충분하지 않습니다.")
        return
    
    tcp_x, tcp_y = zip(*tcp_results)
    midtp_x, midtp_y = zip(*midtp_results)

    plt.figure(figsize=(12, 7))
    plt.plot(tcp_x, tcp_y, 'o-', label='TCP', color='royalblue', linewidth=2, markersize=8)
    plt.plot(midtp_x, midtp_y, 's-', label='MIDTP', color='crimson', linewidth=2, markersize=8)

    # MIDTP 최적점 찾기 및 표시
    if midtp_y:
        max_throughput = max(midtp_y)
        optimal_chunk_size = midtp_x[midtp_y.index(max_throughput)]
        
        plt.axvline(x=optimal_chunk_size, color='gray', linestyle='--', linewidth=1)
        plt.annotate(
            f'Optimal Point\n{optimal_chunk_size} Bytes\n{max_throughput:.2f} MB/s',
            xy=(optimal_chunk_size, max_throughput),
            xytext=(optimal_chunk_size + 1500, max_throughput * 0.85),
            arrowprops=dict(facecolor='black', shrink=0.05, width=2, headwidth=8),
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.5", fc="yellow", ec="black", lw=2, alpha=0.8)
        )
        
        print(f"\n📊 MIDTP 최적 세그먼트 크기: {optimal_chunk_size} Bytes")
        print(f"📊 최대 처리율: {max_throughput:.2f} MB/s")

    # TCP 평균 처리율
    tcp_avg = sum(tcp_y) / len(tcp_y) if tcp_y else 0
    print(f"📊 TCP 평균 처리율: {tcp_avg:.2f} MB/s")

    plt.title('Chunk Size vs. Throughput (논문 그래프 1 재현)', fontsize=16, fontweight='bold')
    plt.xlabel('Chunk (Segment) Size (Bytes)', fontsize=13)
    plt.ylabel('Throughput (MB/s)', fontsize=13)
    plt.legend(fontsize=11)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5, alpha=0.7)
    plt.xticks(list(CHUNK_SIZE_RANGE), rotation=45)
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"📊 그래프 저장: {output_file}")
    
    plt.show()


# --- 메인 실행 로직 ---
def main():
    parser = argparse.ArgumentParser(
        description="최적의 세그먼트 크기 탐색 실험",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 실행 (50MB, 로컬호스트)
  python3 find_optimal_segment.py

  # 100MB 파일로 테스트
  python3 find_optimal_segment.py --file-size 100

  # 결과를 이미지 파일로 저장
  python3 find_optimal_segment.py --output results.png

  # 원격 수신자 테스트
  python3 find_optimal_segment.py --host 192.168.1.100
        """
    )
    
    parser.add_argument(
        "--host", 
        type=str, 
        default=DEFAULT_RECEIVER_HOST, 
        help="수신자 IP 주소 (기본값: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--file-size", 
        type=int, 
        default=DEFAULT_FILE_SIZE_MB, 
        help="전송할 파일 크기 (MB, 기본값: 50)"
    )
    
    parser.add_argument(
        "--tcp-port", 
        type=int, 
        default=DEFAULT_TCP_PORT, 
        help="TCP 포트 번호 (기본값: 9998)"
    )
    
    parser.add_argument(
        "--midtp-port", 
        type=int, 
        default=DEFAULT_MIDTP_PORT, 
        help="MIDTP 포트 번호 (기본값: 9999)"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        default=None, 
        help="결과 그래프 저장 파일명 (예: results.png)"
    )
    
    args = parser.parse_args()

    print("="*70)
    print("최적의 세그먼트 크기 탐색 실험")
    print("="*70)
    print(f"📋 파일 크기: {args.file_size} MB")
    print(f"📋 수신자 주소: {args.host}")
    print(f"📋 TCP 포트: {args.tcp_port}")
    print(f"📋 MIDTP 포트: {args.midtp_port}")
    print(f"📋 청크 크기 범위: {list(CHUNK_SIZE_RANGE)}")
    print("="*70)

    # 1. 수신자 스레드 시작
    print("\n🚀 수신자 스레드 시작 중...")
    receiver_thread = threading.Thread(
        target=receiver_thread_func, 
        args=(args.host, args.tcp_port, args.midtp_port),
        daemon=True
    )
    receiver_thread.start()
    time.sleep(1)  # 수신자가 준비될 때까지 잠시 대기

    # 2. 더미 데이터 생성
    file_size_bytes = args.file_size * 1024 * 1024
    print(f"\n📦 {args.file_size}MB 크기의 더미 데이터 생성 중...")
    dummy_data = os.urandom(file_size_bytes)
    print("✅ 데이터 생성 완료.")

    tcp_results = []
    midtp_results = []

    # 3. 청크 크기를 변경하며 실험 진행
    print("\n🧪 청크 크기별 성능 측정을 시작합니다...\n")
    
    for idx, size in enumerate(CHUNK_SIZE_RANGE, 1):
        print(f"[{idx}/{len(list(CHUNK_SIZE_RANGE))}] 청크 크기: {size} Bytes 테스트 중")
        print("-" * 50)
        
        # TCP 테스트
        print("  🔵 TCP 테스트 중...")
        tcp_throughput = run_tcp_transfer(args.host, args.tcp_port, dummy_data, size)
        tcp_results.append((size, tcp_throughput))
        print(f"  ✅ TCP 처리율: {tcp_throughput:.2f} MB/s")
        time.sleep(0.5)  # 포트 정리 대기

        # MIDTP 테스트
        print("  🔴 MIDTP 테스트 중...")
        midtp_throughput = run_midtp_transfer(args.host, args.midtp_port, dummy_data, size)
        midtp_results.append((size, midtp_throughput))
        print(f"  ✅ MIDTP 처리율: {midtp_throughput:.2f} MB/s")
        print()
        time.sleep(1)  # 다음 테스트 전 잠시 대기

    # 4. 수신자 스레드 종료
    print("="*70)
    print("🏁 실험 완료. 수신자 스레드 종료 중...")
    stop_receiver.set()
    receiver_thread.join(timeout=2)

    # 5. 결과 출력
    print("\n📊 실험 결과 요약:")
    print("="*70)
    print(f"{'청크 크기 (Bytes)':<20} {'TCP (MB/s)':<15} {'MIDTP (MB/s)':<15}")
    print("-"*70)
    for (tcp_size, tcp_tp), (midtp_size, midtp_tp) in zip(tcp_results, midtp_results):
        print(f"{tcp_size:<20} {tcp_tp:<15.2f} {midtp_tp:<15.2f}")
    print("="*70)

    # 6. 결과 시각화
    print("\n📈 결과 그래프를 생성합니다...")
    plot_results(tcp_results, midtp_results, args.output)
    print("\n✅ 모든 작업 완료!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        stop_receiver.set()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        stop_receiver.set()
