# 실험 스크립트 비교표

## 📋 개요

네트워크 성능 측정을 위한 3가지 실험 방법을 제공합니다:

| 스크립트 | 용도 | 실행 환경 | 권장도 |
|---------|------|----------|--------|
| `experiment_receiver.py` + `experiment_sender.py` | 실제 네트워크 성능 측정 | 2개 머신 | ⭐⭐⭐⭐⭐ |
| `find_optimal_segment.py` | 빠른 로컬 테스트 | 1개 머신 | ⭐⭐⭐ |

## 🎯 어떤 방법을 사용해야 할까요?

### ✅ experiment_receiver.py + experiment_sender.py (권장)

**사용 시기:**
- 실제 네트워크 환경에서 정확한 성능 측정이 필요할 때
- 두 대의 컴퓨터를 사용할 수 있을 때
- 논문이나 연구 보고서용 데이터 수집

**장점:**
- 가장 정확한 측정 결과
- 실제 네트워크 지연 반영
- 각 머신의 리소스 독립적 사용

**실행 방법:**
```bash
# 머신 1 (수신자)
python3 experiment_receiver.py --host 0.0.0.0

# 머신 2 (송신자)
python3 experiment_sender.py --host <수신자_IP> --file-size 100
```

---

### ⚡ find_optimal_segment.py

**사용 시기:**
- 빠른 사전 테스트가 필요할 때
- 하나의 컴퓨터만 사용 가능할 때
- 코드 검증 및 디버깅

**장점:**
- 간단한 실행 (한 번의 명령)
- 빠른 결과 확인
- 설정이 간단함

**단점:**
- 송신자와 수신자가 같은 머신에서 실행되어 CPU/메모리 경쟁
- 네트워크 지연이 제대로 반영되지 않음
- 로컬 루프백으로 인한 비현실적인 성능

**실행 방법:**
```bash
python3 find_optimal_segment.py --file-size 50
```

## 📊 성능 측정 비교

| 측정 항목 | experiment_* (2 머신) | find_optimal (1 머신) |
|-----------|----------------------|---------------------|
| **정확도** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **실제 네트워크 반영** | ⭐⭐⭐⭐⭐ | ⭐ |
| **설정 간편성** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **실행 속도** | 보통 | 빠름 |

## 🚀 실행 시나리오별 가이드

### 시나리오 1: 논문/연구용 정확한 데이터 수집

```bash
# 🎯 목표: 가장 정확한 성능 측정
# 💻 환경: 2대의 컴퓨터

# 수신자 머신
python3 experiment_receiver.py --host 0.0.0.0

# 송신자 머신
python3 experiment_sender.py --host 192.168.1.100 --file-size 200 --output paper_results.png
```

**소요 시간:** 15-20분  
**정확도:** ⭐⭐⭐⭐⭐

---

### 시나리오 2: 빠른 사전 검증

```bash
# 🎯 목표: 코드가 제대로 작동하는지 확인
# 💻 환경: 1대의 컴퓨터

python3 find_optimal_segment.py --file-size 20
```

**소요 시간:** 3-5분  
**정확도:** ⭐⭐⭐

---

### 시나리오 3: 로컬 환경에서 정확한 측정 시도

```bash
# 🎯 목표: 한 대 컴퓨터로 최선의 결과
# 💻 환경: 1대의 컴퓨터, 2개 터미널

# 터미널 1
python3 experiment_receiver.py --host 127.0.0.1

# 터미널 2
python3 experiment_sender.py --host 127.0.0.1 --file-size 100
```

**소요 시간:** 10-15분  
**정확도:** ⭐⭐⭐⭐

## 📝 각 스크립트의 세부 기능

### experiment_receiver.py

**기능:**
- TCP와 MIDTP 패킷을 동시에 수신
- 실시간 진행 상황 표시
- 세션별 통계 출력
- 여러 송신자의 연속 테스트 지원

**명령줄 옵션:**
```bash
python3 experiment_receiver.py \
  --host 0.0.0.0 \           # 바인딩 주소
  --tcp-port 9998 \          # TCP 포트
  --midtp-port 9999          # MIDTP 포트
```

**출력 정보:**
- 수신 크기 및 처리율
- 패킷 수신/누락 통계
- 세션별 성능 지표

---

### experiment_sender.py

**기능:**
- 다양한 청크 크기로 자동 테스트
- TCP와 MIDTP 성능 비교
- 결과 그래프 자동 생성
- 커스터마이징 가능한 청크 범위

**명령줄 옵션:**
```bash
python3 experiment_sender.py \
  --host 192.168.1.100 \              # 수신자 IP
  --file-size 100 \                   # 파일 크기 (MB)
  --tcp-port 9998 \                   # TCP 포트
  --midtp-port 9999 \                 # MIDTP 포트
  --output results.png \              # 그래프 저장
  --chunk-sizes "1000-10000-500"      # 청크 범위 커스텀
```

**출력 정보:**
- 청크 크기별 처리율
- 최적 세그먼트 크기
- 시각화된 그래프

---

### find_optimal_segment.py

**기능:**
- 통합 실행 (수신자 + 송신자)
- 백그라운드 스레드로 수신자 실행
- 자동화된 실험 진행

**명령줄 옵션:**
```bash
python3 find_optimal_segment.py \
  --file-size 50 \           # 파일 크기 (MB)
  --tcp-port 9998 \          # TCP 포트
  --midtp-port 9999 \        # MIDTP 포트
  --output results.png       # 그래프 저장
```

**출력 정보:**
- 통합된 실험 결과
- 최적 세그먼트 크기
- 시각화된 그래프

## 🔍 실행 예시 비교

### experiment_receiver.py + experiment_sender.py

**수신자 출력:**
```
======================================================================
최적 세그먼트 크기 실험 - 수신자 (Receiver)
======================================================================

🔵 TCP 수신자 시작: 0.0.0.0:9998
🔴 MIDTP 수신자 시작: 0.0.0.0:9999

[TCP #1] 연결 수신: ('192.168.1.101', 54321)
[TCP #1] 📦 예상 크기: 50.00 MB
[TCP #1] ✅ 수신 완료: 50.00 MB
[TCP #1] 📈 처리율: 44.64 MB/s
```

**송신자 출력:**
```
======================================================================
최적 세그먼트 크기 실험 - 송신자 (Sender)
======================================================================

[1/11] 청크 크기: 1400 Bytes
  🔵 TCP 전송 중...
  ✅ TCP 처리율: 42.35 MB/s
  🔴 MIDTP 전송 중...
  ✅ MIDTP 처리율: 38.21 MB/s

📊 MIDTP 최적 세그먼트 크기: 5600 Bytes
```

---

### find_optimal_segment.py

**통합 출력:**
```
======================================================================
최적의 세그먼트 크기 탐색 실험
======================================================================

🚀 수신자 스레드 시작 중...
🔧 TCP 포트 9998, MIDTP 포트 9999에서 수신 대기 중...

[1/11] 청크 크기: 1400 Bytes 테스트 중
  🔵 TCP 테스트 중...
  ✅ TCP 처리율: 42.35 MB/s
```

## 💡 추천 워크플로우

### 1단계: 빠른 검증
```bash
python3 find_optimal_segment.py --file-size 20
```
**목적:** 코드가 정상 작동하는지 확인

### 2단계: 로컬 정밀 테스트
```bash
# 터미널 1
python3 experiment_receiver.py --host 127.0.0.1

# 터미널 2
python3 experiment_sender.py --host 127.0.0.1 --file-size 100
```
**목적:** 더 정확한 로컬 측정

### 3단계: 실제 네트워크 측정
```bash
# 수신자 머신
python3 experiment_receiver.py --host 0.0.0.0

# 송신자 머신
python3 experiment_sender.py --host <수신자_IP> --file-size 200 --output final_results.png
```
**목적:** 최종 논문/보고서용 데이터

## 🐛 문제 해결

### "연결 거부" 오류

**원인:** 수신자가 실행되지 않음

**해결:**
```bash
# 수신자가 먼저 실행되어 있는지 확인
ps aux | grep experiment_receiver
```

### 낮은 처리율

**원인:** 로컬 루프백 사용 또는 리소스 경쟁

**해결:**
- experiment_receiver.py + experiment_sender.py를 별도 머신에서 실행
- 다른 프로그램 종료하여 리소스 확보

## 📚 관련 문서

- **`EXPERIMENT_QUICKSTART.md`** - 빠른 시작 가이드
- **`EXPERIMENT_GUIDE.md`** - 상세 실험 가이드
- **`README.md`** - 프로젝트 전체 개요

---

**권장사항:** 중요한 성능 측정은 항상 `experiment_receiver.py` + `experiment_sender.py`를 별도 머신에서 실행하세요! 🚀
