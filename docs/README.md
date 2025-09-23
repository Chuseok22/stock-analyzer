# Stock Analyzer

주식 데이터를 학습하여 종목을 추천하는 Python 기반 머신러닝 시스템입니다.
**독립 실행 가능**하며, 스케줄링과 알림 기능이 내장된 완전 자동화된 주식 추천 서비스입니다.

[![CI/CD Pipeline](https://github.com/yourusername/stock-analyzer/actions/workflows/stock-analyzer-cicd.yml/badge.svg)](https://github.com/yourusername/stock-analyzer/actions/workflows/stock-analyzer-cicd.yml)

## 🎯 주요 특징

- **🤖 AI 기반 예측**: XGBoost, LightGBM 앙상블 모델로 주식 상승 예측
- **📊 자동 데이터 수집**: KIS Open API를 통한 실시간 주식 데이터 수집
- **⏰ 스케줄링**: 장 마감 후 자동 분석, 장 시작 전 추천 알림
- **📱 다중 알림**: 이메일, Slack, Discord, Telegram 지원
- **🔄 자동 학습**: 주간 모델 재학습으로 성능 유지
- **📈 성과 추적**: 추천 결과 실제 수익률 분석
- **🚀 CI/CD**: GitHub Actions 자동 배포 파이프라인
- **🐳 Docker**: 컨테이너화된 배포 환경

## 🚀 배포 방법

### 자동 배포 (권장)

1. **GitHub Secrets 설정**: [SECRETS.md](SECRETS.md) 참고하여 필요한 시크릿 설정
2. **main 브랜치 푸시**: 자동으로 테스트 → 빌드 → 배포 실행
3. **서비스 확인**: `http://SERVER_IP:8090/health`에서 상태 확인

```bash
git add .
git commit -m "Deploy stock analyzer"
git push origin main
```

### 수동 배포

#### Docker Compose 사용 (권장)

```bash
# 저장소 클론
git clone https://github.com/yourusername/stock-analyzer.git
cd stock-analyzer

# 환경 파일 설정
cp .env.example .env
# .env 파일 편집

# Docker Compose 실행
docker-compose up -d

# 상태 확인
docker-compose ps
docker-compose logs -f stock-analyzer
```

#### 직접 설치

```bash
# 저장소 클론
git clone https://github.com/Chuseok22/stock-analyzer.git
cd stock-analyzer

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 패키지 설치
pip install -r requirements.txt

# 환경 설정
cp .env.example .env
# .env 파일을 편집하여 실제 설정값 입력
```

### 2. 서버 실행

```bash
# 간편 실행 (자동 설정)
./start.sh

# 또는 직접 실행
python server.py

# 백그라운드 데몬 모드
python server.py --daemon
```

### 3. 알림 설정

`.env` 파일에서 원하는 알림 채널을 활성화:

```bash
# Slack 알림 (추천)
SLACK_ENABLED=true
SLACK_TOKEN=xoxb-your-bot-token
SLACK_CHANNEL=#stock-alerts

# 이메일 알림
SMTP_ENABLED=true
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=recipient@email.com

# Telegram 알림
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 📅 자동 스케줄

서버가 실행되면 다음 작업이 자동으로 수행됩니다:

| 작업 | 시간 | 설명 |
|-----|------|------|
| 📊 데이터 수집 & 추천 생성 | 평일 16:00 | 장 마감 후 당일 데이터 수집 및 다음날 추천 생성 |
| 📱 아침 알림 | 평일 08:30 | 장 시작 전 오늘의 추천 종목 알림 |
| 🤖 일일 ML 적응 학습 | 매일 06:30 | 전일 시장 데이터 반영한 실시간 모델 업데이트 |
| 🧠 주간 고도화 학습 | 일요일 02:00 | 하이퍼파라미터 최적화 및 심화 모델 재학습 |
| 📈 성과 리포트 | 일요일 18:00 | 주간 추천 성과 분석 리포트 |
| 🔄 유니버스 업데이트 | 매월 첫째 일요일 01:00 | 시가총액 상위 종목으로 유니버스 갱신 |

## 📱 알림 예시

### 아침 추천 알림 (08:30)
```
📈 주식 추천 알림 - 2025년 01월 15일

📊 총 5개 종목 추천 (고신뢰도 3개), 평균 신뢰도: 76.2%

🎯 추천 종목

1. 삼성전자 (005930)
   🟢 신뢰도: 85.3% | 예상수익: 8.5%
   💡 RSI 과매도 구간, MACD 상승 신호

2. SK하이닉스 (000660)
   🟢 신뢰도: 78.1% | 예상수익: 7.8%
   💡 볼린저밴드 하단 터치, 거래량 급증

3. NAVER (035420)
   🟡 신뢰도: 72.4% | 예상수익: 7.2%
   💡 20일 이평선 돌파, 긍정적 모멘텀

⚠️ 투자 위험 알림: AI 예측 기반이므로 신중한 판단이 필요합니다.
```

## 🎮 서버 조작

### 인터랙티브 모드

서버 실행 후 명령어로 제어 가능:

```bash
(stock-analyzer) > help          # 도움말
(stock-analyzer) > status        # 서버 상태 확인
(stock-analyzer) > jobs          # 예약된 작업 목록
(stock-analyzer) > run daily_recommendations  # 수동 추천 생성
(stock-analyzer) > test          # 테스트 알림 발송
(stock-analyzer) > quit          # 서버 종료
```

### 원격 작업 실행

```bash
# 특정 작업만 실행하고 종료
python server.py --run-task daily_recommendations
python server.py --run-task morning_notifications

# 테스트 알림 발송
python server.py --test-notifications
```

## 🖥 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                 Stock Analyzer Server                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Scheduler  │  │  ML Engine  │  │  Notification Hub   │ │
│  │   Service   │  │   Service   │  │      Service        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────┬───────────────┬───────────────────┬─────────┘
              │               │                   │
              ▼               ▼                   ▼
    ┌─────────────┐  ┌─────────────┐    ┌─────────────────┐
    │ PostgreSQL  │  │  KIS Open   │    │   Multi-Channel │
    │  Database   │  │     API     │    │  Notifications  │
    └─────────────┘  └─────────────┘    └─────────────────┘
                                         │ │ │ │
                                         📧📱💬📲
                                      Email Slack Discord Telegram
```

## 🔧 리눅스 서버 배포

### systemd 서비스 등록

```bash
# 서비스 파일 복사
sudo cp systemd/stock-analyzer.service /etc/systemd/system/

# 서비스 활성화
sudo systemctl enable stock-analyzer
sudo systemctl start stock-analyzer

# 상태 확인
sudo systemctl status stock-analyzer

# 로그 확인
sudo journalctl -u stock-analyzer -f
```

### Docker 실행 (옵션)

```bash
# Docker 이미지 빌드
docker build -t stock-analyzer .

# 컨테이너 실행
docker run -d --name stock-analyzer \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/models:/app/models \
  stock-analyzer
```

## 사용법

### 명령어 실행

```bash
# 직접 Python 실행
python app/main.py [command] [options]

# 또는 스크립트 사용
./run.sh [command] [options]
```

### 주요 명령어

#### 1. 유니버스 업데이트 (상위 200개 종목 선정)
```bash
./run.sh update-universe --region KR --top-n 200
```

#### 2. 데이터 수집
```bash
./run.sh collect --universe-id 1 --days 252
```

#### 3. 모델 학습
```bash
./run.sh train --universe-id 1
```

#### 4. 추천 생성
```bash
./run.sh recommend --universe-id 1 --top-n 20
```

#### 5. 전체 파이프라인 실행 (일반적인 사용)
```bash
./run.sh pipeline --universe-id 1 --collect-data --retrain --top-n 20
```

#### 6. 성과 분석
```bash
./run.sh performance --days 30
```

### Spring Boot 연동

Spring Boot 스케줄러에서 다음과 같이 호출할 수 있습니다:

```java
@Scheduled(cron = "0 0 18 * * MON-FRI") // 평일 오후 6시
public void generateDailyRecommendations() {
    String command = "bash /path/to/stock-analyzer/run.sh pipeline --universe-id 1 --top-n 20";
    
    ProcessBuilder processBuilder = new ProcessBuilder("bash", "-c", command);
    // ... 프로세스 실행 및 결과 처리
}
```

## 데이터베이스 스키마

### 주요 테이블

1. **stock**: 종목 정보 (코드, 이름, 지역)
2. **universe**: 투자 유니버스 (날짜별 종목 그룹)
3. **universe_item**: 유니버스에 포함된 종목들
4. **recommendation**: AI 추천 결과 (점수, 순위, 사유)
5. **stock_price**: 주식 가격 데이터
6. **stock_indicator**: 기술적 지표 데이터

## 머신러닝 모델

### 사용 알고리즘
- **XGBoost**: 그래디언트 부스팅
- **LightGBM**: 마이크로소프트 그래디언트 부스팅
- **Random Forest**: 랜덤 포레스트
- **Ensemble**: 위 모델들의 앙상블

### 특성 (Features)
- 이동평균선 (5, 10, 20, 60일)
- 지수이동평균선 (12, 26일)
- RSI (14일)
- MACD 및 시그널
- 볼린저 밴드
- 거래량 지표
- 변동성 지표
- 모멘텀 지표

### 예측 목표
주식의 다음날 상승/하락 여부 (이진 분류)

## API 응답 형식

모든 명령어는 JSON 형식으로 결과를 반환합니다:

```json
{
  "success": true,
  "recommendations_count": 20,
  "recommendations": [
    {
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "score": 0.85,
      "rank": 1,
      "reason": {
        "summary": "Machine learning model predicts positive price movement",
        "technical_factors": [
          "RSI indicates oversold condition",
          "Price above 20-day moving average",
          "MACD shows bullish signal"
        ],
        "confidence": 0.85
      }
    }
  ],
  "execution_time_seconds": 45.2
}
```

## 로깅

시스템은 다음과 같은 로그를 생성합니다:
- **콘솔**: 실시간 진행상황
- **daily log**: 일별 로그 파일
- **rotating log**: 크기 제한이 있는 순환 로그

로그 파일 위치: `logs/` 디렉토리

## 성능 모니터링

추천 시스템의 성과는 다음 지표로 평가됩니다:
- **성공률**: 추천 종목의 상승 비율
- **평균 수익률**: 1일, 3일, 7일 수익률
- **AUC 스코어**: 모델의 예측 정확도

## 주의사항

1. **API 제한**: KIS API는 요청 횟수 제한이 있으므로 적절한 딜레이 설정 필요
2. **데이터 품질**: 주말/공휴일 데이터 처리 로직 포함
3. **모델 재학습**: 정기적인 모델 재학습으로 성능 유지
4. **메모리 사용량**: 대량 데이터 처리 시 메모리 사용량 모니터링 필요

## 문제 해결

### 일반적인 오류
1. **DB 연결 실패**: `.env` 파일의 데이터베이스 설정 확인
2. **KIS API 오류**: API 키 및 토큰 만료 확인
3. **모델 학습 실패**: 충분한 학습 데이터 확보 필요 (최소 100개 샘플)

### 디버깅
```bash
# 디버그 로그 레벨로 실행
LOG_LEVEL=DEBUG ./run.sh [command]
```

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
