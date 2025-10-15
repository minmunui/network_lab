# 로깅 기능 가이드

## 개요

sender.py와 receiver.py에 상세한 로깅 기능이 추가되었습니다. 이제 다음과 같은 정보를 실시간으로 확인할 수 있습니다:

## 로깅 아이콘 설명

- 📦 패킷/데이터 수신/전송
- 📤 데이터 전송
- 📨 응답 수신 (ACK/NACK)
- 🏁 FIN 패킷 (전송 완료 신호)
- ✅ 성공 상태
- ⚠️  경고/재전송 필요
- ❌ 오류 발생
- 📉 패킷 손실 (시뮬레이션)
- 🔍 상세 정보 (누락 패킷 ID 등)
- 📊 통계 정보
- ⏳ 대기 중
- ⏱️  타임아웃
- 🔄 재전송

## MIDTP 프로토콜 로그 예시

### Sender (송신자) 로그

```
======================================================================
네트워크 프로토콜 성능 측정 - Sender
프로토콜: MIDTP
======================================================================

[Data] Generating 100 MB of random data...
[Data] Data generation complete

[MIDTP] Connecting to 127.0.0.1:5000
[MIDTP] Data size: 104857600 bytes, Chunk size: 8192 bytes
[MIDTP] 📦 Total packets to send: 12800

[MIDTP] 📤 Sending packets... 100/12800
[MIDTP] 📤 Sending packets... 200/12800
...
[MIDTP] 📤 Sent 12800 packets
[MIDTP] 🏁 FIN packet sent (signaling end of transmission)
[MIDTP] ⏳ Waiting for receiver response...
[MIDTP] 📨 NACK received: 640 packets requested
[MIDTP] ⚠️  NACK received: 640 packets need retransmission
[MIDTP] 🔍 Lost packet IDs: [5, 12, 23, 45, 67, 89, 123, 156, 189, 234, 267, 298, 345, 378, 412, 445, 478, 512, 545, 578]...
[MIDTP] 🔄 Starting retransmission round 1/10

[MIDTP] 📤 Sending packets... 100/640
...
[MIDTP] 📤 Sent 640 packets
[MIDTP] 🏁 FIN packet sent (signaling end of transmission)
[MIDTP] ⏳ Waiting for receiver response...
[MIDTP] 📨 ACK received from receiver
[MIDTP] ✅ Transfer complete (ACK received)
[MIDTP] 📊 Total packets sent (including retransmissions): 13440

[MIDTP] 📊 Transmission Statistics:
[MIDTP]   ✓ Original packets: 12800
[MIDTP]   ✓ Total packets sent: 13440
[MIDTP]   ✓ Retransmission rounds: 1
[MIDTP]   ✓ Retransmission overhead: 5.0%

======================================================================
=== 전송 완료 ===
프로토콜: MIDTP
파일 크기: 100.00 MB
총 소요 시간: 12.34 초
처리율: 8.10 MB/s
======================================================================
```

### Receiver (수신자) 로그

```
======================================================================
네트워크 프로토콜 성능 측정 - Receiver
프로토콜: MIDTP
======================================================================

[MIDTP] Receiver listening on 0.0.0.0:5000
[MIDTP] Packet loss simulation: 5.0%
[MIDTP] Connected to sender: ('127.0.0.1', 54321)

[MIDTP] 📦 Received 100 packets...
[MIDTP] 📉 Packet dropped (simulated loss)
[MIDTP] 📦 Received 200 packets...
[MIDTP] 📉 Packet dropped (simulated loss)
...
[MIDTP] 📉 ... (추가 손실 패킷은 로그 생략)
...
[MIDTP] 📦 Received 12800 packets...
[MIDTP] 🏁 FIN packet received (total packets expected: 12800)
[MIDTP] 📊 Statistics: 12160 received, 640 dropped
[MIDTP] ⚠️  Retransmission round 1: 640 packets missing
[MIDTP] 🔍 Missing packet IDs: [5, 12, 23, 45, 67, 89, 123, 156, 189, 234, 267, 298, 345, 378, 412, 445, 478, 512, 545, 578]...
[MIDTP] 📤 NACK sent: requesting 640 missing packets

[MIDTP] 📦 Received 12900 packets...
[MIDTP] 🏁 FIN packet received (total packets expected: 12800)
[MIDTP] 📊 Statistics: 12800 received, 640 dropped
[MIDTP] ✅ All packets received successfully
[MIDTP] 📤 ACK sent (transmission complete)

[MIDTP] 📊 Final Statistics:
[MIDTP]   ✓ Total data received: 104857600 bytes
[MIDTP]   ✓ Total packets: 12800
[MIDTP]   ✓ Packets dropped (simulated): 640
[MIDTP]   ✓ Retransmission rounds: 1

======================================================================
=== 수신 완료 ===
프로토콜: MIDTP
수신 크기: 100.00 MB
총 소요 시간: 12.35 초
처리율: 8.10 MB/s
======================================================================
```

## TCP/BBR 프로토콜 로그 예시

### Sender

```
[TCP] Connecting to 127.0.0.1:5001
[TCP] Data size: 100.00 MB
[TCP] ✅ Connected to receiver
[TCP] 📤 Sent 10.00 MB / 100.00 MB
[TCP] 📤 Sent 20.00 MB / 100.00 MB
...
[TCP] 📤 Sent 100.00 MB / 100.00 MB
[TCP] ✅ Transfer complete
```

### Receiver

```
[TCP] Receiver listening on 0.0.0.0:5001
[TCP] ✅ Connected to sender: ('127.0.0.1', 54322)
[TCP] 📦 Received 10.00 MB...
[TCP] 📦 Received 20.00 MB...
...
[TCP] 📦 Received 100.00 MB...
[TCP] 📊 Total received: 104857600 bytes in 1600 chunks
```

## QUIC 프로토콜 로그 예시

### Sender

```
[QUIC] Connecting to 127.0.0.1:5003
[QUIC] Data size: 100.00 MB
[QUIC] ✅ Configuration set (self-signed cert mode)
[QUIC] ✅ Connected to receiver
[QUIC] 📤 Opened stream 0 for data transfer
[QUIC] 📤 Sent 10.00 MB / 100.00 MB
[QUIC] 📤 Sent 20.00 MB / 100.00 MB
...
[QUIC] 📤 Sent 100.00 MB / 100.00 MB
[QUIC] ✅ All data sent on stream 0
[QUIC] ✅ Transfer complete
```

### Receiver

```
[QUIC] Receiver listening on 0.0.0.0:5003
[QUIC] ✅ TLS certificates loaded
[QUIC] ⏳ Server started, waiting for connection...
[QUIC] 📦 Received 10.00 MB...
[QUIC] 📦 Received 20.00 MB...
...
[QUIC] 📦 Received 100.00 MB...
[QUIC] ✅ Stream 0 complete: 104857600 bytes
[QUIC] 📊 Total received: 104857600 bytes
```

## 로그 분석 팁

### 1. 패킷 손실 추적 (MIDTP)

누락된 패킷 ID를 확인하여 손실 패턴을 분석할 수 있습니다:
```
[MIDTP] 🔍 Missing packet IDs: [5, 12, 23, 45, 67, ...]
```

### 2. 재전송 오버헤드 계산 (MIDTP)

전송 통계에서 재전송으로 인한 추가 비용을 확인:
```
[MIDTP]   ✓ Retransmission overhead: 5.0%
```

### 3. 진행 상황 모니터링

- MIDTP: 매 100개 패킷마다 진행 상황 표시
- TCP/QUIC: 매 10MB마다 진행 상황 표시

### 4. 성능 비교

각 프로토콜의 처리율(MB/s)을 비교하여 성능 차이를 분석:
```
처리율: 8.10 MB/s
```

## 테스트 시나리오

### 시나리오 1: 낮은 손실률 (1%)

```bash
# Receiver
python3 receiver.py --protocol midtp --host 0.0.0.0 --port 5000 --loss-rate 0.01

# Sender
python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 100
```

**예상 결과**: 재전송 1-2회, 오버헤드 1-2%

### 시나리오 2: 높은 손실률 (10%)

```bash
# Receiver
python3 receiver.py --protocol midtp --host 0.0.0.0 --port 5000 --loss-rate 0.10

# Sender
python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 100
```

**예상 결과**: 재전송 2-4회, 오버헤드 10-15%

### 시나리오 3: 프로토콜 성능 비교

동일한 파일 크기로 각 프로토콜을 테스트하여 처리율 비교:

```bash
# MIDTP
python3 receiver.py --protocol midtp --host 0.0.0.0 --port 5000 --loss-rate 0.05
python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 500

# TCP
python3 receiver.py --protocol tcp --host 0.0.0.0 --port 5001
python3 sender.py --protocol tcp --host 127.0.0.1 --port 5001 --file-size 500

# QUIC
python3 receiver.py --protocol quic --host 0.0.0.0 --port 5003
python3 sender.py --protocol quic --host 127.0.0.1 --port 5003 --file-size 500
```

## 로그 저장

로그를 파일로 저장하려면 리다이렉션을 사용하세요:

```bash
# Receiver 로그 저장
python3 receiver.py --protocol midtp --host 0.0.0.0 --port 5000 --loss-rate 0.05 2>&1 | tee receiver_midtp.log

# Sender 로그 저장
python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 100 2>&1 | tee sender_midtp.log
```

## 로그 분석 스크립트

저장된 로그에서 주요 정보 추출:

```bash
# 처리율 추출
grep "처리율" sender_midtp.log

# 재전송 횟수 확인
grep "Retransmission rounds" sender_midtp.log

# 손실 패킷 수 확인
grep "packets missing" receiver_midtp.log
```
