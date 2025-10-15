# 🧪 실험 테스트 가이드 - 어떤 코드를 실행해야 하나요?

## 🎯 빠른 답변

### 질문: "수신자는 어떤 코드를, 송신자는 어떤 코드를 실행해야 하나요?"

**답변:**

#### ✅ 방법 1: 별도 머신 (권장 - 가장 정확)

```bash
# 📍 수신자 머신에서 실행
python3 experiment_receiver.py --host 0.0.0.0

# 📍 송신자 머신에서 실행
python3 experiment_sender.py --host <수신자_IP> --file-size 100
```

#### ⚡ 방법 2: 한 대의 컴퓨터 (간단하지만 덜 정확)

```bash
# 하나의 명령으로 자동 실행
python3 find_optimal_segment.py --file-size 50
```

---

## 📋 전체 실험 스크립트 목록

| 파일명 | 역할 | 언제 사용? |
|--------|------|-----------|
| `experiment_receiver.py` | **수신자 전용** | 별도 머신에서 데이터 수신 |
| `experiment_sender.py` | **송신자 전용** | 별도 머신에서 데이터 전송 및 측정 |
| `find_optimal_segment.py` | 통합 (자동화) | 한 대 컴퓨터에서 빠른 테스트 |

## 🚀 실행 예시 - 단계별 가이드

### 예시 1: 두 대의 컴퓨터 사용 (정확한 측정)

**환경:**
- 수신자 컴퓨터: IP 192.168.1.100
- 송신자 컴퓨터: IP 192.168.1.101

**1단계: 수신자 컴퓨터에서**
```bash
cd /path/to/network_lab
python3 experiment_receiver.py --host 0.0.0.0
```

**출력:**
```
======================================================================
최적 세그먼트 크기 실험 - 수신자 (Receiver)
======================================================================
📋 바인딩 주소: 0.0.0.0
📋 TCP 포트: 9998
📋 MIDTP 포트: 9999
======================================================================

⏳ 송신자의 연결을 기다리고 있습니다...
💡 종료하려면 Ctrl+C를 누르세요.

🔵 TCP 수신자 시작: 0.0.0.0:9998
🔴 MIDTP 수신자 시작: 0.0.0.0:9999
```

**2단계: 송신자 컴퓨터에서**
```bash
cd /path/to/network_lab
python3 experiment_sender.py --host 192.168.1.100 --file-size 100
```

**출력:**
```
======================================================================
최적 세그먼트 크기 실험 - 송신자 (Sender)
======================================================================
📋 수신자 주소: 192.168.1.100:9998 (TCP), 192.168.1.100:9999 (MIDTP)
📋 파일 크기: 100 MB
📋 청크 크기 범위: [1400, 2800, 4200, ...]

📦 100MB 크기의 더미 데이터 생성 중...
✅ 데이터 생성 완료.

🧪 청크 크기별 성능 측정 시작 (총 11회)

[1/11] 청크 크기: 1400 Bytes
--------------------------------------------------
  🔵 TCP 전송 중...
  ✅ TCP 처리율: 42.35 MB/s
  🔴 MIDTP 전송 중...
  ✅ MIDTP 처리율: 38.21 MB/s
...
```

---

### 예시 2: 한 대의 컴퓨터 사용 (빠른 테스트)

**터미널 1 (수신자):**
```bash
python3 experiment_receiver.py --host 127.0.0.1
```

**터미널 2 (송신자):**
```bash
python3 experiment_sender.py --host 127.0.0.1 --file-size 50
```

---

### 예시 3: 자동화된 로컬 테스트

**하나의 터미널만 사용:**
```bash
python3 find_optimal_segment.py --file-size 50
```

이 스크립트는 내부적으로 수신자 스레드를 자동으로 시작하고 송신자 역할을 수행합니다.

---

## ⚙️ 각 스크립트의 옵션

### experiment_receiver.py (수신자)

```bash
python3 experiment_receiver.py [옵션]

옵션:
  --host IP주소          바인딩할 IP (기본: 0.0.0.0)
  --tcp-port 포트번호    TCP 포트 (기본: 9998)
  --midtp-port 포트번호  MIDTP 포트 (기본: 9999)
```

**예시:**
```bash
# 모든 네트워크 인터페이스에서 수신
python3 experiment_receiver.py --host 0.0.0.0

# 특정 IP에서만 수신
python3 experiment_receiver.py --host 192.168.1.100

# 포트 변경
python3 experiment_receiver.py --tcp-port 8000 --midtp-port 8001
```

---

### experiment_sender.py (송신자)

```bash
python3 experiment_sender.py [옵션]

옵션:
  --host IP주소          수신자 IP (기본: 127.0.0.1)
  --file-size 크기       전송 파일 크기 MB (기본: 50)
  --tcp-port 포트번호    TCP 포트 (기본: 9998)
  --midtp-port 포트번호  MIDTP 포트 (기본: 9999)
  --output 파일명        그래프 저장 파일명
  --chunk-sizes 범위     청크 크기 범위 (예: "1000-10000-500")
```

**예시:**
```bash
# 기본 실행
python3 experiment_sender.py --host 192.168.1.100

# 대용량 파일 테스트
python3 experiment_sender.py --host 192.168.1.100 --file-size 200

# 결과 저장
python3 experiment_sender.py --host 192.168.1.100 --output my_results.png

# 커스텀 청크 크기 (1000~10000, 500씩 증가)
python3 experiment_sender.py --host 192.168.1.100 --chunk-sizes "1000-10000-500"
```

---

### find_optimal_segment.py (통합)

```bash
python3 find_optimal_segment.py [옵션]

옵션:
  --file-size 크기       전송 파일 크기 MB (기본: 50)
  --tcp-port 포트번호    TCP 포트 (기본: 9998)
  --midtp-port 포트번호  MIDTP 포트 (기본: 9999)
  --output 파일명        그래프 저장 파일명
```

**예시:**
```bash
# 기본 실행
python3 find_optimal_segment.py

# 파일 크기 변경
python3 find_optimal_segment.py --file-size 100

# 결과 저장
python3 find_optimal_segment.py --file-size 50 --output results.png
```

---

## 🎬 실제 실행 시나리오

### 시나리오 A: 논문/연구용 정확한 데이터

**목표:** 가장 정확한 성능 측정  
**소요 시간:** 15-20분  
**필요 장비:** 2대의 컴퓨터

```bash
# 수신자 컴퓨터 (192.168.1.100)
python3 experiment_receiver.py --host 0.0.0.0

# 송신자 컴퓨터 (192.168.1.101)
python3 experiment_sender.py \
  --host 192.168.1.100 \
  --file-size 200 \
  --output paper_results.png
```

---

### 시나리오 B: 빠른 검증

**목표:** 코드가 정상 작동하는지 확인  
**소요 시간:** 3-5분  
**필요 장비:** 1대의 컴퓨터

```bash
python3 find_optimal_segment.py --file-size 20
```

---

### 시나리오 C: 로컬 정밀 측정

**목표:** 한 대로 최선의 결과  
**소요 시간:** 10-15분  
**필요 장비:** 1대의 컴퓨터, 2개 터미널

```bash
# 터미널 1
python3 experiment_receiver.py --host 127.0.0.1

# 터미널 2  
python3 experiment_sender.py --host 127.0.0.1 --file-size 100
```

---

## 🔧 체크리스트

### 실행 전 확인사항

- [ ] Python 3.7 이상 설치
- [ ] matplotlib 설치 (`pip3 install matplotlib`)
- [ ] 방화벽에서 포트 9998, 9999 허용
- [ ] 두 컴퓨터가 같은 네트워크에 연결 (별도 머신 사용 시)
- [ ] 수신자의 IP 주소 확인 (`ifconfig` 또는 `ipconfig`)

### 실행 중 체크사항

- [ ] 수신자가 먼저 실행되었는가?
- [ ] "연결 대기 중" 메시지가 보이는가?
- [ ] 송신자에서 올바른 수신자 IP 사용하는가?

### 실행 후 확인사항

- [ ] 그래프가 생성되었는가?
- [ ] 최적 청크 크기가 표시되었는가?
- [ ] 결과가 합리적인가? (MIDTP 최적값 4000-8000 바이트 범위)

---

## ❓ FAQ

### Q1: 수신자와 송신자를 반대로 실행하면 어떻게 되나요?

**A:** 송신자가 "연결 거부" 오류를 받습니다. 반드시 **수신자를 먼저** 실행해야 합니다.

### Q2: 두 스크립트를 같은 컴퓨터에서 실행해도 되나요?

**A:** 네, 가능합니다. 하지만 결과가 덜 정확합니다. 로컬 루프백을 사용하면 실제 네트워크 지연이 반영되지 않습니다.

### Q3: experiment_receiver.py는 언제 종료되나요?

**A:** 수동으로 종료할 때까지 계속 실행됩니다 (Ctrl+C). 여러 송신자의 연속 테스트를 받을 수 있습니다.

### Q4: 그래프가 표시되지 않으면?

**A:** `--output` 옵션으로 파일로 저장하세요:
```bash
python3 experiment_sender.py --host 192.168.1.100 --output results.png
```

### Q5: 어떤 방법이 가장 정확한가요?

**A:** `experiment_receiver.py` + `experiment_sender.py`를 **별도 머신**에서 실행하는 것이 가장 정확합니다.

---

## 📚 더 자세한 정보

- **`EXPERIMENT_QUICKSTART.md`** - 빠른 시작 가이드
- **`EXPERIMENT_COMPARISON.md`** - 스크립트 상세 비교
- **`EXPERIMENT_GUIDE.md`** - 완전한 실험 가이드
- **`README.md`** - 프로젝트 전체 개요

---

**요약:** 정확한 측정이 필요하면 `experiment_receiver.py`와 `experiment_sender.py`를 별도 머신에서 실행하세요! 🎯
