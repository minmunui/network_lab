# 네트워크 프로토콜 성능 측정 프로젝트

## 프로젝트 개요

이 프로젝트는 **MIDTP 프로토콜 성능 심층 분석** 연구를 위해 설계되었습니다. 실제 로컬 네트워크 환경에서 다음 6가지 네트워크 전송 프로토콜의 성능을 측정하고 비교합니다:

1. **MIDTP** - 논문 기반 UDP 위 경량 커스텀 프로토콜
2. **TCP (Baseline)** - OS 기본 혼잡 제어 알고리즘 (예: CUBIC) 사용
3. **TCP-BBR** - Google의 최신 혼잡 제어 알고리즘
4. **QUIC** - UDP 기반 최신 프로토콜 (aioquic 라이브러리 활용)
5. **UDT** - 대용량 파일 전송 특화 프로토콜 (스텁 구현)
6. **SCTP** - 멀티스트리밍 지원 프로토콜 (스텁 구현)

## 사전 준비 사항

### 1. Python 환경

- **Python 3.7 이상** 필요
- Python 버전 확인:
  ```bash
  python3 --version
  ```

### 2. 필수 라이브러리 설치

프로젝트 디렉토리에서 다음 명령어를 실행하여 필요한 라이브러리를 설치합니다:

```bash
pip3 install -r requirements.txt
```

### 3. 프로토콜별 특별 설정

#### 3.1 QUIC 프로토콜 설정

QUIC은 TLS 암호화를 필수로 사용하므로 자체 서명 인증서를 생성해야 합니다.

**인증서 생성 (프로젝트 디렉토리에서 실행):**

```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=NetworkLab/CN=localhost"
```

**생성되는 파일:**
- `cert.pem` - 공개 인증서
- `key.pem` - 개인 키

**이유:** QUIC 프로토콜은 보안을 위해 TLS 1.3을 기본으로 사용하며, aioquic 라이브러리도 이를 요구합니다.

#### 3.2 TCP-BBR 프로토콜 설정

TCP-BBR은 Linux 커널 수준에서 활성화해야 합니다.

**요구사항:**
- Linux 커널 4.9 이상
- Sender(송신자) 측 장치에서만 설정 필요

**커널 버전 확인:**
```bash
uname -r
```

**현재 혼잡 제어 알고리즘 확인:**
```bash
sysctl net.ipv4.tcp_congestion_control
```

**BBR 활성화:**
```bash
# BBR 모듈 로드
sudo modprobe tcp_bbr

# BBR을 기본 혼잡 제어 알고리즘으로 설정
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr

# 설정 확인
sysctl net.ipv4.tcp_congestion_control
# 출력: net.ipv4.tcp_congestion_control = bbr
```

**영구 적용 (선택사항):**
```bash
echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**테스트 후 원래 설정으로 복구:**
```bash
# CUBIC으로 복구 (일반적인 기본값)
sudo sysctl -w net.ipv4.tcp_congestion_control=cubic

# 또는 시스템 재부팅으로 자동 복구 (영구 적용하지 않은 경우)
```

**참고:** macOS는 BBR을 지원하지 않으므로 Linux 환경에서 테스트해야 합니다.

#### 3.3 UDT 및 SCTP 프로토콜

이 프로토콜들은 다음과 같은 복잡한 의존성을 요구합니다:

**UDT:**
- `pyudt` 라이브러리 (C++ 컴파일러 필요)
- UDT4 C++ 라이브러리
- 복잡한 빌드 환경 설정

**SCTP:**
- `pysctp` 라이브러리
- SCTP 커널 모듈 지원
- Linux 전용 (macOS는 제한적 지원)

**현재 구현:** 이 프로젝트에서는 UDT와 SCTP를 **스텁(stub)**으로 구현했습니다. 해당 프로토콜을 선택하면 안내 메시지가 출력되고 프로그램이 종료됩니다.

## 실행 방법

### 1단계: Receiver (수신자) 실행

다른 장치 또는 같은 장치의 다른 터미널에서 receiver를 먼저 실행합니다.

**기본 실행 (MIDTP, 포트 5000):**
```bash
python3 receiver.py --protocol midtp --host 0.0.0.0 --port 5000
```

**프로토콜별 실행 예시:**

```bash
# MIDTP (패킷 손실률 5% 시뮬레이션)
python3 receiver.py --protocol midtp --host 0.0.0.0 --port 5000 --loss-rate 0.05

# TCP (Baseline)
python3 receiver.py --protocol tcp --host 0.0.0.0 --port 5001

# TCP-BBR (Sender 측에서 BBR 활성화 필요)
python3 receiver.py --protocol bbr --host 0.0.0.0 --port 5002

# QUIC (TLS 인증서 필요)
python3 receiver.py --protocol quic --host 0.0.0.0 --port 5003

# UDT (스텁)
python3 receiver.py --protocol udt --host 0.0.0.0 --port 5004

# SCTP (스텁)
python3 receiver.py --protocol sctp --host 0.0.0.0 --port 5005
```

### 2단계: Sender (송신자) 실행

Receiver가 대기 중일 때, 다른 터미널에서 sender를 실행합니다.

**기본 실행 (MIDTP, 100MB 파일):**
```bash
python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 100
```

**프로토콜별 실행 예시:**

```bash
# MIDTP (100MB 파일 전송)
python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 100

# TCP (Baseline, 500MB 파일)
python3 sender.py --protocol tcp --host 127.0.0.1 --port 5001 --file-size 500

# TCP-BBR (1GB 파일)
python3 sender.py --protocol bbr --host 127.0.0.1 --port 5002 --file-size 1024

# QUIC (100MB 파일, 더 작은 청크 크기)
python3 sender.py --protocol quic --host 127.0.0.1 --port 5003 --file-size 100 --chunk-size 4096

# UDT (스텁)
python3 sender.py --protocol udt --host 127.0.0.1 --port 5004 --file-size 100

# SCTP (스텁)
python3 sender.py --protocol sctp --host 127.0.0.1 --port 5005 --file-size 100
```

### 명령줄 인자 설명

#### Receiver 인자:
- `--protocol`: 프로토콜 선택 (midtp, tcp, bbr, quic, udt, sctp)
- `--host`: 바인딩할 IP 주소 (기본값: 0.0.0.0)
- `--port`: 포트 번호 (기본값: 5000)
- `--loss-rate`: 패킷 손실률 시뮬레이션 (0.0~1.0, MIDTP 전용, 기본값: 0.0)

#### Sender 인자:
- `--protocol`: 프로토콜 선택 (midtp, tcp, bbr, quic, udt, sctp)
- `--host`: 수신자 IP 주소 (기본값: 127.0.0.1)
- `--port`: 포트 번호 (기본값: 5000)
- `--file-size`: 전송할 파일 크기 (MB 단위, 기본값: 100)
- `--chunk-size`: 한 번에 전송할 데이터 청크 크기 (바이트, 기본값: 8192)

## 성능 측정 결과 해석

Sender 실행 완료 시 다음 형식으로 결과가 출력됩니다:

```
=== 전송 완료 ===
프로토콜: MIDTP
파일 크기: 100.00 MB
총 소요 시간: 12.34 초
처리율: 8.10 MB/s
```

## 네트워크 환경별 테스트 시나리오

### 시나리오 1: 로컬 환경 (같은 장치)
```bash
# Receiver
python3 receiver.py --protocol midtp --host 127.0.0.1 --port 5000

# Sender
python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 100
```

### 시나리오 2: LAN 환경 (다른 장치)
```bash
# Receiver (장치 A, IP: 192.168.1.100)
python3 receiver.py --protocol tcp --host 0.0.0.0 --port 5001

# Sender (장치 B)
python3 sender.py --protocol tcp --host 192.168.1.100 --port 5001 --file-size 500
```

### 시나리오 3: 패킷 손실 환경 시뮬레이션
```bash
# Receiver (10% 손실률)
python3 receiver.py --protocol midtp --host 0.0.0.0 --port 5000 --loss-rate 0.10

# Sender
python3 sender.py --protocol midtp --host 127.0.0.1 --port 5000 --file-size 100
```

## 문제 해결

### QUIC 실행 시 "cert.pem not found" 오류
```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=NetworkLab/CN=localhost"
```

### "Permission denied" (포트 1024 미만 사용 시)
```bash
# sudo 권한으로 실행
sudo python3 receiver.py --protocol tcp --host 0.0.0.0 --port 80
```

### BBR이 활성화되지 않음
```bash
# 사용 가능한 혼잡 제어 알고리즘 확인
sysctl net.ipv4.tcp_available_congestion_control

# bbr이 목록에 없으면 커널 모듈 로드
sudo modprobe tcp_bbr
```

## 참고 자료

- **TCP BBR:** https://queue.acm.org/detail.cfm?id=3022184
- **BBR 상세 분석:** https://atoonk.medium.com/tcp-bbr-exploring-tcp-congestion-control-84c9c11dc3a9
- **BBR 설정 가이드:** https://wiki.geant.org/pages/viewpage.action?pageId=121340614
- **QUIC 프로토콜:** https://en.wikipedia.org/wiki/QUIC
- **QUIC/HTTP3:** https://www.f5.com/glossary/quic-http3

## 고급 실험: 최적의 세그먼트 크기 탐색

`find_optimal_segment.py` 스크립트를 사용하여 MIDTP와 TCP의 최적 세그먼트 크기를 실험적으로 찾을 수 있습니다.

### 실험 개요

이 실험은 청크(세그먼트) 크기를 1400 바이트부터 15400 바이트까지 변경하며 각 프로토콜의 처리율을 측정합니다. 실험 결과는 그래프로 시각화되어 최적의 세그먼트 크기를 확인할 수 있습니다.

### 사전 준비

matplotlib 라이브러리를 설치해야 합니다:
```bash
pip3 install matplotlib
```

### 실행 방법

**기본 실행 (50MB 파일, 로컬호스트):**
```bash
python3 find_optimal_segment.py
```

**파일 크기 변경:**
```bash
python3 find_optimal_segment.py --file-size 100
```

**결과를 이미지로 저장:**
```bash
python3 find_optimal_segment.py --output optimal_segment_results.png
```

**원격 수신자 테스트:**
```bash
# 수신자 측 (IP: 192.168.1.100)
python3 find_optimal_segment.py --host 0.0.0.0

# 송신자 측
python3 find_optimal_segment.py --host 192.168.1.100
```

### 실험 결과 해석

- **X축**: 청크(세그먼트) 크기 (바이트)
- **Y축**: 처리율 (MB/s)
- **노란색 마커**: MIDTP의 최적 세그먼트 크기

일반적으로 MIDTP는 특정 세그먼트 크기에서 최대 처리율을 보이며, 너무 작거나 큰 세그먼트 크기에서는 성능이 저하됩니다. 이는 UDP 버퍼 오버플로우와 관련이 있습니다.

## 라이선스

이 프로젝트는 연구 및 교육 목적으로 제작되었습니다.
# network_lab
# network_lab
