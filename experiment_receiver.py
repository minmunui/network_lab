#!/usr/bin/env python3
"""
최적의 세그먼트 크기 탐색 실험 - 수신자 (Receiver)

실험을 위한 전용 수신자 프로그램입니다.
TCP와 MIDTP 프로토콜을 모두 수신할 수 있습니다.

사용법:
    python3 experiment_receiver.py --host 0.0.0.0 --tcp-port 9998 --midtp-port 9999
"""

import socket
import argparse
import struct
import time
import signal
import sys

# --- MIDTP 프로토콜 상수 ---
PACKET_HEADER_FORMAT = "!IIHB"
PACKET_HEADER_SIZE = struct.calcsize(PACKET_HEADER_FORMAT)
FLAG_DATA = 0x01
FLAG_NACK = 0x02
FLAG_INIT = 0x04
FLAG_FIN = 0x08

# --- 전역 변수 ---
running = True
tcp_sock = None
midtp_sock = None


def signal_handler(sig, frame):
    """Ctrl+C 처리"""
    global running
    print("\n\n⚠️  종료 신호 수신. 수신자를 종료합니다...")
    running = False


def handle_tcp_connection(tcp_port: int, host: str):
    """TCP 연결을 처리하는 함수"""
    global tcp_sock, running

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_sock.bind((host, tcp_port))
    tcp_sock.listen(5)
    tcp_sock.settimeout(1.0)  # 1초 타임아웃

    print(f"🔵 TCP 수신자 시작: {host}:{tcp_port}")

    connection_count = 0

    while running:
        try:
            conn, addr = tcp_sock.accept()
            connection_count += 1
            print(f"\n[TCP #{connection_count}] 연결 수신: {addr}")

            with conn:
                # 파일 크기 수신
                file_size_data = conn.recv(8)
                if not file_size_data:
                    print(f"[TCP #{connection_count}] ⚠️  파일 크기 수신 실패")
                    continue

                file_size = struct.unpack("!Q", file_size_data)[0]
                print(
                    f"[TCP #{connection_count}] 📦 예상 크기: {file_size / (1024*1024):.2f} MB"
                )

                # 데이터 수신
                bytes_received = 0
                start_time = time.time()
                last_report = start_time

                while bytes_received < file_size:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    bytes_received += len(chunk)

                    # 진행 상황 표시 (매 1초마다)
                    current_time = time.time()
                    if current_time - last_report >= 1.0:
                        progress = (bytes_received / file_size) * 100
                        speed = (
                            bytes_received / (current_time - start_time) / (1024 * 1024)
                        )
                        print(
                            f"[TCP #{connection_count}] 📊 진행: {progress:.1f}% ({speed:.2f} MB/s)"
                        )
                        last_report = current_time

                end_time = time.time()
                elapsed = end_time - start_time
                throughput = (
                    (bytes_received / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                )

                print(
                    f"[TCP #{connection_count}] ✅ 수신 완료: {bytes_received / (1024*1024):.2f} MB"
                )
                print(f"[TCP #{connection_count}] ⏱️  소요 시간: {elapsed:.2f}초")
                print(f"[TCP #{connection_count}] 📈 처리율: {throughput:.2f} MB/s")

        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"[TCP] ❌ 오류: {e}")

    tcp_sock.close()
    print("🔵 TCP 수신자 종료")


def handle_midtp_packets(midtp_port: int, host: str):
    """MIDTP 패킷을 처리하는 함수"""
    global midtp_sock, running

    midtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    midtp_sock.bind((host, midtp_port))
    midtp_sock.settimeout(1.0)  # 1초 타임아웃

    print(f"🔴 MIDTP 수신자 시작: {host}:{midtp_port}")

    # 세션 상태 관리
    current_session = {
        "active": False,
        "sender_addr": None,
        "total_packets": 0,
        "received_packets": set(),
        "start_time": 0,
        "last_packet_time": 0,
        "bytes_received": 0,
        "session_num": 0,
    }

    session_timeout = 3.0  # 3초 동안 패킷이 없으면 세션 종료

    while running:
        try:
            packet, sender_addr = midtp_sock.recvfrom(65535)

            if len(packet) < PACKET_HEADER_SIZE:
                continue

            # 헤더 파싱
            seq_num, total_packets, payload_len, flags = struct.unpack(
                PACKET_HEADER_FORMAT, packet[:PACKET_HEADER_SIZE]
            )
            payload = packet[PACKET_HEADER_SIZE:]

            current_time = time.time()

            # INIT 패킷: 새 세션 시작
            if flags & FLAG_INIT:
                if current_session["active"]:
                    # 이전 세션 종료
                    print(
                        f"[MIDTP #{current_session['session_num']}] ⚠️  새 세션 시작으로 이전 세션 종료"
                    )

                current_session["session_num"] += 1
                current_session["active"] = True
                current_session["sender_addr"] = sender_addr
                current_session["total_packets"] = total_packets
                current_session["received_packets"] = set()
                current_session["start_time"] = current_time
                current_session["last_packet_time"] = current_time
                current_session["bytes_received"] = 0

                print(
                    f"\n[MIDTP #{current_session['session_num']}] 📡 세션 시작: {sender_addr}"
                )
                print(
                    f"[MIDTP #{current_session['session_num']}] 📦 예상 패킷 수: {total_packets}"
                )
                continue

            # 세션이 활성화되어 있지 않으면 무시
            if not current_session["active"]:
                continue

            # 데이터 패킷
            if flags & FLAG_DATA:
                if seq_num not in current_session["received_packets"]:
                    current_session["received_packets"].add(seq_num)
                    current_session["bytes_received"] += payload_len
                    current_session["last_packet_time"] = current_time

                    # 진행 상황 표시 (매 1000개 패킷마다)
                    if len(current_session["received_packets"]) % 1000 == 0:
                        progress = (
                            len(current_session["received_packets"])
                            / current_session["total_packets"]
                        ) * 100
                        elapsed = current_time - current_session["start_time"]
                        speed = (
                            (current_session["bytes_received"] / (1024 * 1024))
                            / elapsed
                            if elapsed > 0
                            else 0
                        )
                        print(
                            f"[MIDTP #{current_session['session_num']}] 📊 진행: {progress:.1f}% "
                            f"({len(current_session['received_packets'])}/{current_session['total_packets']} 패킷, {speed:.2f} MB/s)"
                        )

            # FIN 패킷: 세션 종료
            if flags & FLAG_FIN:
                elapsed = current_time - current_session["start_time"]
                throughput = (
                    (current_session["bytes_received"] / (1024 * 1024)) / elapsed
                    if elapsed > 0
                    else 0
                )

                missing = current_session["total_packets"] - len(
                    current_session["received_packets"]
                )

                print(f"[MIDTP #{current_session['session_num']}] 🏁 FIN 수신")
                print(
                    f"[MIDTP #{current_session['session_num']}] ✅ 수신 완료: {current_session['bytes_received'] / (1024*1024):.2f} MB"
                )
                print(
                    f"[MIDTP #{current_session['session_num']}] 📦 수신 패킷: {len(current_session['received_packets'])}/{current_session['total_packets']}"
                )
                if missing > 0:
                    print(
                        f"[MIDTP #{current_session['session_num']}] ⚠️  누락 패킷: {missing}개"
                    )
                print(
                    f"[MIDTP #{current_session['session_num']}] ⏱️  소요 시간: {elapsed:.2f}초"
                )
                print(
                    f"[MIDTP #{current_session['session_num']}] 📈 처리율: {throughput:.2f} MB/s"
                )

                # 세션 초기화
                current_session["active"] = False

            # 세션 타임아웃 체크
            if current_session["active"]:
                if current_time - current_session["last_packet_time"] > session_timeout:
                    print(
                        f"[MIDTP #{current_session['session_num']}] ⏱️  세션 타임아웃 (마지막 패킷으로부터 {session_timeout}초 경과)"
                    )
                    elapsed = current_time - current_session["start_time"]
                    throughput = (
                        (current_session["bytes_received"] / (1024 * 1024)) / elapsed
                        if elapsed > 0
                        else 0
                    )
                    print(
                        f"[MIDTP #{current_session['session_num']}] 📊 부분 수신: {current_session['bytes_received'] / (1024*1024):.2f} MB ({throughput:.2f} MB/s)"
                    )
                    current_session["active"] = False

        except socket.timeout:
            # 타임아웃은 정상, 세션 타임아웃만 체크
            if current_session["active"]:
                current_time = time.time()
                if current_time - current_session["last_packet_time"] > session_timeout:
                    print(f"[MIDTP #{current_session['session_num']}] ⏱️  세션 타임아웃")
                    current_session["active"] = False
            continue
        except Exception as e:
            if running:
                print(f"[MIDTP] ❌ 오류: {e}")

    midtp_sock.close()
    print("🔴 MIDTP 수신자 종료")


def main():
    parser = argparse.ArgumentParser(
        description="최적 세그먼트 크기 실험 - 수신자",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 모든 인터페이스에서 수신 (권장)
  python3 experiment_receiver.py --host 0.0.0.0

  # 특정 IP에서만 수신
  python3 experiment_receiver.py --host 192.168.1.100

  # 포트 변경
  python3 experiment_receiver.py --tcp-port 8000 --midtp-port 8001
        """,
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="바인딩할 IP 주소 (기본값: 0.0.0.0 - 모든 인터페이스)",
    )

    parser.add_argument(
        "--tcp-port", type=int, default=9998, help="TCP 포트 번호 (기본값: 9998)"
    )

    parser.add_argument(
        "--midtp-port", type=int, default=9999, help="MIDTP 포트 번호 (기본값: 9999)"
    )

    args = parser.parse_args()

    # Ctrl+C 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 70)
    print("최적 세그먼트 크기 실험 - 수신자 (Receiver)")
    print("=" * 70)
    print(f"📋 바인딩 주소: {args.host}")
    print(f"📋 TCP 포트: {args.tcp_port}")
    print(f"📋 MIDTP 포트: {args.midtp_port}")
    print("=" * 70)
    print("\n⏳ 송신자의 연결을 기다리고 있습니다...")
    print("💡 종료하려면 Ctrl+C를 누르세요.\n")

    # TCP와 MIDTP를 별도 스레드에서 실행
    import threading

    tcp_thread = threading.Thread(
        target=handle_tcp_connection, args=(args.tcp_port, args.host), daemon=True
    )

    midtp_thread = threading.Thread(
        target=handle_midtp_packets, args=(args.midtp_port, args.host), daemon=True
    )

    tcp_thread.start()
    midtp_thread.start()

    # 메인 스레드는 종료 신호를 기다림
    try:
        tcp_thread.join()
        midtp_thread.join()
    except KeyboardInterrupt:
        pass

    print("\n✅ 수신자 종료 완료")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
