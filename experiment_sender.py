#!/usr/bin/env python3
"""
최적의 세그먼트 크기 탐색 실험 - 송신자 (Sender)

실험을 위한 전용 송신자 프로그램입니다.
다양한 청크 크기로 TCP와 MIDTP 프로토콜을 테스트합니다.

사용법:
    python3 experiment_sender.py --host 192.168.1.100 --file-size 100
"""

import socket
import argparse
import os
import struct
import time
import math
import matplotlib.pyplot as plt
from typing import List, Tuple

# --- MIDTP 프로토콜 상수 ---
PACKET_HEADER_FORMAT = "!IIHB"
PACKET_HEADER_SIZE = struct.calcsize(PACKET_HEADER_FORMAT)
FLAG_DATA = 0x01
FLAG_NACK = 0x02
FLAG_INIT = 0x04
FLAG_FIN = 0x08

# --- 기본 설정 ---
DEFAULT_FILE_SIZE_MB = 50
DEFAULT_RECEIVER_HOST = "127.0.0.1"
DEFAULT_TCP_PORT = 9998
DEFAULT_MIDTP_PORT = 9999
CHUNK_SIZE_RANGE = range(1400, 15401, 1400)  # 1400~15400, 1400씩 증가


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
            chunk = data[total_sent : total_sent + chunk_size]
            sock.sendall(chunk)
            total_sent += len(chunk)

        end_time = time.time()
        sock.close()

        total_time = end_time - start_time
        throughput = (len(data) / (1024 * 1024)) / total_time if total_time > 0 else 0
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
                PACKET_HEADER_FORMAT, i, total_packets, len(payload), FLAG_DATA
            )
            packets.append(header + payload)

        start_time = time.time()

        # INIT 패킷 전송 (수신자가 세션을 시작할 수 있도록)
        init_header = struct.pack(PACKET_HEADER_FORMAT, 0, total_packets, 0, FLAG_INIT)
        sock.sendto(init_header, receiver_addr)
        time.sleep(0.01)  # INIT 처리 대기

        # 데이터 패킷 전송
        for packet in packets:
            sock.sendto(packet, receiver_addr)

        # FIN 패킷 전송
        fin_header = struct.pack(
            PACKET_HEADER_FORMAT, total_packets, total_packets, 0, FLAG_FIN
        )
        sock.sendto(fin_header, receiver_addr)

        end_time = time.time()
        sock.close()

        # 수신자가 처리할 시간 대기
        time.sleep(0.1)

        total_time = end_time - start_time
        throughput = (len(data) / (1024 * 1024)) / total_time if total_time > 0 else 0
        return throughput

    except Exception as e:
        print(f"  ❌ MIDTP 전송 오류: {e}")
        return 0


def plot_results(
    tcp_results: List[Tuple[int, float]],
    midtp_results: List[Tuple[int, float]],
    output_file: str = None,
):
    """실험 결과를 그래프로 시각화"""

    if not tcp_results or not midtp_results:
        print("❌ 결과 데이터가 충분하지 않습니다.")
        return

    tcp_x, tcp_y = zip(*tcp_results)
    midtp_x, midtp_y = zip(*midtp_results)

    plt.figure(figsize=(12, 7))
    plt.plot(
        tcp_x, tcp_y, "o-", label="TCP", color="royalblue", linewidth=2, markersize=8
    )
    plt.plot(
        midtp_x,
        midtp_y,
        "s-",
        label="MIDTP",
        color="crimson",
        linewidth=2,
        markersize=8,
    )

    # MIDTP 최적점 찾기 및 표시
    if midtp_y:
        max_throughput = max(midtp_y)
        optimal_chunk_size = midtp_x[midtp_y.index(max_throughput)]

        plt.axvline(x=optimal_chunk_size, color="gray", linestyle="--", linewidth=1)
        plt.annotate(
            f"Optimal Point\n{optimal_chunk_size} Bytes\n{max_throughput:.2f} MB/s",
            xy=(optimal_chunk_size, max_throughput),
            xytext=(optimal_chunk_size + 1500, max_throughput * 0.85),
            arrowprops=dict(facecolor="black", shrink=0.05, width=2, headwidth=8),
            fontsize=11,
            bbox=dict(
                boxstyle="round,pad=0.5", fc="yellow", ec="black", lw=2, alpha=0.8
            ),
        )

        print(f"\n📊 MIDTP 최적 세그먼트 크기: {optimal_chunk_size} Bytes")
        print(f"📊 최대 처리율: {max_throughput:.2f} MB/s")

    # TCP 평균 처리율
    tcp_avg = sum(tcp_y) / len(tcp_y) if tcp_y else 0
    print(f"📊 TCP 평균 처리율: {tcp_avg:.2f} MB/s")

    plt.title(
        "Chunk Size vs. Throughput (논문 그래프 1 재현)", fontsize=16, fontweight="bold"
    )
    plt.xlabel("Chunk (Segment) Size (Bytes)", fontsize=13)
    plt.ylabel("Throughput (MB/s)", fontsize=13)
    plt.legend(fontsize=11)
    plt.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)
    plt.xticks(list(CHUNK_SIZE_RANGE), rotation=45)
    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"📊 그래프 저장: {output_file}")

    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="최적 세그먼트 크기 실험 - 송신자",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 로컬 테스트
  python3 experiment_sender.py --host 127.0.0.1 --file-size 50

  # 원격 수신자로 테스트
  python3 experiment_sender.py --host 192.168.1.100 --file-size 100

  # 결과를 이미지로 저장
  python3 experiment_sender.py --host 192.168.1.100 --file-size 200 --output results.png
        """,
    )

    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_RECEIVER_HOST,
        help="수신자 IP 주소 (기본값: 127.0.0.1)",
    )

    parser.add_argument(
        "--file-size",
        type=int,
        default=DEFAULT_FILE_SIZE_MB,
        help="전송할 파일 크기 (MB, 기본값: 50)",
    )

    parser.add_argument(
        "--tcp-port",
        type=int,
        default=DEFAULT_TCP_PORT,
        help="TCP 포트 번호 (기본값: 9998)",
    )

    parser.add_argument(
        "--midtp-port",
        type=int,
        default=DEFAULT_MIDTP_PORT,
        help="MIDTP 포트 번호 (기본값: 9999)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과 그래프 저장 파일명 (예: results.png)",
    )

    parser.add_argument(
        "--chunk-sizes",
        type=str,
        default=None,
        help="청크 크기 범위 (예: '1400-15400-1400' = 1400부터 15400까지 1400씩)",
    )

    args = parser.parse_args()

    # 청크 크기 범위 파싱
    chunk_sizes = CHUNK_SIZE_RANGE
    if args.chunk_sizes:
        try:
            parts = args.chunk_sizes.split("-")
            if len(parts) == 3:
                start, end, step = map(int, parts)
                chunk_sizes = range(start, end + 1, step)
        except:
            print("⚠️  잘못된 청크 크기 형식. 기본값 사용")

    print("=" * 70)
    print("최적 세그먼트 크기 실험 - 송신자 (Sender)")
    print("=" * 70)
    print(
        f"📋 수신자 주소: {args.host}:{args.tcp_port} (TCP), {args.host}:{args.midtp_port} (MIDTP)"
    )
    print(f"📋 파일 크기: {args.file_size} MB")
    print(f"📋 청크 크기 범위: {list(chunk_sizes)}")
    print("=" * 70)

    # 더미 데이터 생성
    file_size_bytes = args.file_size * 1024 * 1024
    print(f"\n📦 {args.file_size}MB 크기의 더미 데이터 생성 중...")
    dummy_data = os.urandom(file_size_bytes)
    print("✅ 데이터 생성 완료.")

    tcp_results = []
    midtp_results = []

    # 청크 크기별 실험
    print(f"\n🧪 청크 크기별 성능 측정 시작 (총 {len(list(chunk_sizes))}회)\n")

    for idx, size in enumerate(chunk_sizes, 1):
        print(f"[{idx}/{len(list(chunk_sizes))}] 청크 크기: {size} Bytes")
        print("-" * 50)

        # TCP 테스트
        print("  🔵 TCP 전송 중...")
        tcp_throughput = run_tcp_transfer(args.host, args.tcp_port, dummy_data, size)
        tcp_results.append((size, tcp_throughput))
        print(f"  ✅ TCP 처리율: {tcp_throughput:.2f} MB/s")
        time.sleep(0.5)

        # MIDTP 테스트
        print("  🔴 MIDTP 전송 중...")
        midtp_throughput = run_midtp_transfer(
            args.host, args.midtp_port, dummy_data, size
        )
        midtp_results.append((size, midtp_throughput))
        print(f"  ✅ MIDTP 처리율: {midtp_throughput:.2f} MB/s")
        print()
        time.sleep(1.0)

    # 결과 요약
    print("=" * 70)
    print("📊 실험 결과 요약")
    print("=" * 70)
    print(f"{'청크 크기 (Bytes)':<20} {'TCP (MB/s)':<15} {'MIDTP (MB/s)':<15}")
    print("-" * 70)
    for (tcp_size, tcp_tp), (midtp_size, midtp_tp) in zip(tcp_results, midtp_results):
        print(f"{tcp_size:<20} {tcp_tp:<15.2f} {midtp_tp:<15.2f}")
    print("=" * 70)

    # 그래프 생성
    print("\n📈 결과 그래프 생성 중...")
    plot_results(tcp_results, midtp_results, args.output)

    print("\n✅ 모든 실험 완료!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
