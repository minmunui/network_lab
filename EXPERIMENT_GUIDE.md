# 최적의 세그먼트 크기 탐색 실험 가이드

## 📚 개요

`find_optimal_segment.py`는 MIDTP와 TCP 프로토콜의 청크(세그먼트) 크기에 따른 처리율을 측정하여 최적의 세그먼트 크기를 찾는 실험 스크립트입니다.

이 실험은 논문의 **그래프 1: Chunk Size vs. Throughput**을 재현합니다.

## 🎯 실험 목적

1. **MIDTP의 최적 세그먼트 크기 발견**: UDP 버퍼 크기와 네트워크 대역폭을 고려한 최적값 도출
2. **TCP와의 성능 비교**: 세그먼트 크기 변화에 따른 두 프로토콜의 차이 분석
3. **버퍼 오버플로우 현상 관찰**: 너무 큰 세그먼트 크기에서의 성능 저하 확인

## 🔬 실험 원리

### MIDTP (UDP 기반)

UDP는 수신 버퍼가 제한적이므로:
- **세그먼트가 너무 작으면**: 헤더 오버헤드 증가, CPU 사용률 상승
- **세그먼트가 너무 크면**: 버퍼 오버플로우로 패킷 손실 증가
- **최적 세그먼트 크기**: 버퍼 크기와 네트워크 특성에 맞는 균형점

### TCP (스트림 기반)

TCP는 자동으로 흐름 제어를 수행하므로:
- 세그먼트 크기에 상대적으로 둔감
- 대부분의 크기에서 안정적인 성능 유지

## 🚀 실행 방법

### 1. 의존성 설치

```bash
pip3 install matplotlib
```

### 2. 기본 실험 실행

**로컬 환경에서 실행 (가장 간단):**

```bash
python3 find_optimal_segment.py
```

이 명령은 다음을 수행합니다:
- 50MB 더미 데이터 생성
- 청크 크기 1400~15400 바이트 범위에서 10회 측정
- TCP와 MIDTP 각각 테스트
- 결과를 그래프로 시각화

### 3. 옵션 사용

#### 파일 크기 변경

```bash
# 100MB 파일로 테스트
python3 find_optimal_segment.py --file-size 100

# 500MB 대용량 파일 테스트
python3 find_optimal_segment.py --file-size 500
```

#### 결과를 이미지로 저장

```bash
python3 find_optimal_segment.py --output results.png
python3 find_optimal_segment.py --file-size 100 --output experiment_100mb.png
```

#### 포트 변경

```bash
python3 find_optimal_segment.py --tcp-port 8000 --midtp-port 8001
```

#### 원격 환경 테스트

**수신자 머신 (IP: 192.168.1.100):**
```bash
# 스크립트는 자동으로 수신자 역할 수행
python3 find_optimal_segment.py --host 0.0.0.0 --file-size 200
```

**송신자 머신:**
```bash
python3 find_optimal_segment.py --host 192.168.1.100 --file-size 200
```

## 📊 실험 결과 예시

### 터미널 출력

```
======================================================================
최적의 세그먼트 크기 탐색 실험
======================================================================
📋 파일 크기: 50 MB
📋 수신자 주소: 127.0.0.1
📋 TCP 포트: 9998
📋 MIDTP 포트: 9999
📋 청크 크기 범위: [1400, 2800, 4200, 5600, 7000, 8400, 9800, 11200, 12600, 14000, 15400]
======================================================================

🚀 수신자 스레드 시작 중...
🔧 TCP 포트 9998, MIDTP 포트 9999에서 수신 대기 중...

📦 50MB 크기의 더미 데이터 생성 중...
✅ 데이터 생성 완료.

🧪 청크 크기별 성능 측정을 시작합니다...

[1/11] 청크 크기: 1400 Bytes 테스트 중
--------------------------------------------------
  🔵 TCP 테스트 중...
  📡 TCP 연결 수신: ('127.0.0.1', 54321)
  ✅ TCP 수신 완료: 50.00 MB
  ✅ TCP 처리율: 42.35 MB/s
  🔴 MIDTP 테스트 중...
  📡 MIDTP 세션 시작: ('127.0.0.1', 54322), 총 37450개 패킷
  ✅ MIDTP 수신 완료
  ✅ MIDTP 처리율: 38.21 MB/s

[2/11] 청크 크기: 2800 Bytes 테스트 중
--------------------------------------------------
  🔵 TCP 테스트 중...
  ✅ TCP 처리율: 45.67 MB/s
  🔴 MIDTP 테스트 중...
  ✅ MIDTP 처리율: 52.34 MB/s

...

📊 실험 결과 요약:
======================================================================
청크 크기 (Bytes)    TCP (MB/s)      MIDTP (MB/s)   
----------------------------------------------------------------------
1400                 42.35           38.21          
2800                 45.67           52.34          
4200                 46.12           68.45          
5600                 46.89           75.23          
7000                 47.23           72.11          
8400                 47.45           65.34          
...
======================================================================

📊 MIDTP 최적 세그먼트 크기: 5600 Bytes
📊 최대 처리율: 75.23 MB/s
📊 TCP 평균 처리율: 46.50 MB/s

📈 결과 그래프를 생성합니다...
✅ 모든 작업 완료!
```

### 그래프 해석

생성된 그래프는 다음과 같은 형태를 보입니다:

```
Throughput (MB/s)
      ^
   80 |                    *  (MIDTP 최적점)
      |                 *     *
   70 |              *           *
      |           *                 *
   60 |        *                       *
      |     *                             *
   50 |  *  o---o---o---o---o---o---o---o---o  (TCP - 안정적)
      | *
   40 |*
      |
   30 +------------------------------------------------> Chunk Size (Bytes)
       1400  2800  4200  5600  7000  8400  9800  12600  14000  15400

      * = MIDTP
      o = TCP
```

**관찰 결과:**
1. **TCP (파란색 선)**: 청크 크기에 관계없이 비교적 안정적인 성능
2. **MIDTP (빨간색 선)**: 특정 크기(예: 5600 바이트)에서 최대 성능
3. **최적점**: 노란색 마커로 표시된 MIDTP의 최고 처리율 지점

## 🔍 상세 분석

### 1. 작은 세그먼트 크기 (1400-2800 bytes)

**관찰:**
- MIDTP가 TCP보다 낮은 성능
- 패킷 수 증가로 CPU 오버헤드 상승

**원인:**
- 헤더 오버헤드 비율 증가
- 시스템 콜 횟수 증가

### 2. 중간 세그먼트 크기 (4200-7000 bytes)

**관찰:**
- MIDTP가 최고 성능에 도달
- TCP보다 우수한 처리율

**원인:**
- 헤더 오버헤드와 버퍼 효율의 균형
- UDP의 낮은 프로토콜 오버헤드 활용

### 3. 큰 세그먼트 크기 (9800-15400 bytes)

**관찰:**
- MIDTP 성능 저하
- TCP는 여전히 안정적

**원인:**
- UDP 수신 버퍼 오버플로우
- 패킷 손실 증가

## 💡 최적화 가이드

### 로컬 네트워크 (LAN)

```bash
# 큰 파일로 정확한 측정
python3 find_optimal_segment.py --file-size 200
```

**예상 최적 크기:** 5000-8000 바이트

### 고속 네트워크 (10Gbps+)

```bash
# 더 큰 세그먼트 크기 범위 테스트 필요
# 스크립트를 수정하여 CHUNK_SIZE_RANGE 확장
```

**예상 최적 크기:** 8000-16000 바이트

### 저속 또는 불안정한 네트워크

```bash
# 작은 파일로 빠른 테스트
python3 find_optimal_segment.py --file-size 20
```

**예상 최적 크기:** 2000-4000 바이트

## 🛠️ 커스터마이징

### 청크 크기 범위 변경

`find_optimal_segment.py` 파일을 열어 다음 줄을 수정:

```python
# 기본값
CHUNK_SIZE_RANGE = range(1400, 15401, 1400)

# 더 세밀한 측정 (1000 바이트씩 증가)
CHUNK_SIZE_RANGE = range(1000, 10001, 1000)

# 큰 세그먼트 테스트
CHUNK_SIZE_RANGE = range(5000, 30001, 2500)
```

### 측정 반복 횟수 추가

각 크기를 여러 번 측정하여 평균을 내려면:

```python
# 각 크기별 3회 측정 후 평균
for size in CHUNK_SIZE_RANGE:
    tcp_results_tmp = []
    midtp_results_tmp = []
    
    for _ in range(3):
        tcp_throughput = run_tcp_transfer(...)
        tcp_results_tmp.append(tcp_throughput)
        
        midtp_throughput = run_midtp_transfer(...)
        midtp_results_tmp.append(midtp_throughput)
    
    tcp_avg = sum(tcp_results_tmp) / 3
    midtp_avg = sum(midtp_results_tmp) / 3
    
    tcp_results.append((size, tcp_avg))
    midtp_results.append((size, midtp_avg))
```

## ⚠️ 주의사항

### 1. 방화벽 설정

포트 9998, 9999가 열려 있어야 합니다:

```bash
# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add python3

# Linux (ufw)
sudo ufw allow 9998/tcp
sudo ufw allow 9999/udp
```

### 2. 시스템 리소스

대용량 파일 테스트 시 충분한 메모리 필요:
- 50MB 파일: 최소 200MB RAM
- 500MB 파일: 최소 2GB RAM

### 3. 네트워크 상태

일관된 결과를 위해:
- 다른 네트워크 트래픽 최소화
- 안정적인 네트워크 환경에서 테스트
- VPN 또는 프록시 비활성화

### 4. 실행 권한

일부 시스템에서는 포트 바인딩에 권한 필요:

```bash
# 권한이 필요한 경우 (1024 미만 포트)
sudo python3 find_optimal_segment.py --tcp-port 80 --midtp-port 53
```

## 🧪 실험 시나리오

### 시나리오 1: 빠른 사전 테스트

```bash
# 20MB 파일로 빠른 실험
python3 find_optimal_segment.py --file-size 20
```

**소요 시간:** 약 2-3분
**목적:** 시스템이 정상 작동하는지 확인

### 시나리오 2: 정밀 측정

```bash
# 200MB 파일로 정확한 측정
python3 find_optimal_segment.py --file-size 200 --output precise_results.png
```

**소요 시간:** 약 10-15분
**목적:** 논문 수준의 정확한 결과 도출

### 시나리오 3: 다양한 조건 비교

```bash
# 여러 파일 크기로 반복 실험
for size in 50 100 200 500; do
    python3 find_optimal_segment.py --file-size $size --output "results_${size}mb.png"
done
```

**소요 시간:** 약 30-60분
**목적:** 파일 크기에 따른 최적값 변화 관찰

## 📚 참고 자료

- **UDP Buffer Size**: `sysctl net.inet.udp.recvspace` (macOS)
- **TCP Window Size**: `sysctl net.inet.tcp.recvspace`
- **MTU 확인**: `netstat -i` 또는 `ip link show`

## 🤝 문제 해결

### "연결 거부" 오류

```bash
# 수신자 스레드가 시작되지 않음
# -> 포트가 이미 사용 중인지 확인
lsof -i :9998
lsof -i :9999

# 프로세스 종료
kill -9 <PID>
```

### 그래프가 표시되지 않음

```bash
# matplotlib 백엔드 문제
# -> 저장 옵션 사용
python3 find_optimal_segment.py --output results.png
```

### 메모리 부족

```bash
# 파일 크기 줄이기
python3 find_optimal_segment.py --file-size 20
```

## 📈 결과 활용

실험 결과를 바탕으로:

1. **sender.py 최적화**: 최적 청크 크기를 기본값으로 설정
2. **동적 조정**: 네트워크 상태에 따라 청크 크기 조정
3. **논문 작성**: 실험 결과를 그래프로 포함
4. **성능 튜닝**: 시스템별 최적 설정 도출

---

**Happy Experimenting! 🚀**
