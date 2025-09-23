# Stock Analyzer - 개발자 가이드

## 📋 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [주요 기능](#3-주요-기능)
4. [핵심 모듈 및 파일](#4-핵심-모듈-및-파일)
5. [API 명세](#5-api-명세)
6. [데이터베이스 스키마](#6-데이터베이스-스키마)
7. [핵심 알고리즘](#7-핵심-알고리즘)
8. [환경 요구사항](#8-환경-요구사항)
9. [배포 가이드](#9-배포-가이드)
10. [테스트](#10-테스트)
11. [주의사항](#11-주의사항)

---

## 1. 프로젝트 개요

**Stock Analyzer**는 한국(KRX)과 미국(NYSE/NASDAQ) 주식 시장을 대상으로 한 **실시간 AI 기반 주식 분석 및 추천 시스템**입니다.

### 🎯 핵심 목표
- **실시간 주식 데이터 수집** (KIS API, Alpha Vantage API)
- **머신러닝 기반 수익률 예측** (XGBoost, LightGBM, Random Forest)
- **자동화된 스케줄링 시스템** (APScheduler, 글로벌 타임존 지원)
- **다중 채널 알림** (Telegram, Slack, Discord, Email)
- **적응형 실시간 학습** (예측 vs 실제 결과 비교 학습)

### 🏗️ 시스템 아키텍처
```
FastAPI Server ──┐
                 ├── GlobalMLEngine (예측 엔진)
                 ├── SchedulingService (자동화)
                 ├── SmartAlertSystem (알림)
                 └── RealtimeLearningSystem (적응형 학습)
                     │
                     ├── PostgreSQL (주가 데이터)
                     ├── Redis (캐시/세션)
                     └── 외부 API (KIS, Alpha Vantage)
```

---

## 2. 프로젝트 구조

```
stock-analyzer/
├── 📂 app/                          # 핵심 애플리케이션 코드
│   ├── 📂 api/                      # FastAPI 라우터
│   │   └── health.py                # 헬스체크 엔드포인트
│   ├── 📂 config/                   # 설정 관리
│   │   └── settings.py              # Pydantic 기반 환경설정
│   ├── 📂 database/                 # 데이터베이스 연결
│   │   ├── connection.py            # SQLAlchemy 연결 관리
│   │   └── redis_client.py          # Redis 클라이언트
│   ├── 📂 ml/                       # 머신러닝 모듈
│   │   ├── global_ml_engine.py      # 글로벌 ML 예측 엔진
│   │   ├── models.py                # ML 모델 클래스들
│   │   └── realtime_learning_system.py # 실시간 적응형 학습
│   ├── 📂 models/                   # SQLAlchemy 엔티티
│   │   └── entities.py              # 데이터베이스 테이블 정의
│   ├── 📂 services/                 # 비즈니스 로직
│   │   ├── data_collection.py       # 데이터 수집 서비스
│   │   ├── kis_api.py               # 한국투자증권 API 클라이언트
│   │   ├── alpha_vantage_api.py     # Alpha Vantage API 클라이언트
│   │   ├── scheduler.py             # 스케줄링 서비스
│   │   ├── recommendation.py        # 추천 생성 서비스
│   │   ├── notification.py          # 알림 서비스
│   │   ├── smart_alert_system.py    # 지능형 알림 시스템
│   │   └── unified_data_collector.py # 통합 데이터 수집기
│   └── 📂 utils/                    # 유틸리티
│       ├── logger.py                # 로깅 유틸리티
│       ├── structured_logger.py     # 구조화된 로거
│       ├── database_utils.py        # DB 헬퍼 함수
│       ├── data_utils.py            # 데이터 처리 유틸
│       ├── market_time_utils.py     # 시장 시간 관리
│       └── api_utils.py             # API 유틸리티
├── 📂 scripts/                      # 운영 스크립트
│   ├── global_scheduler.py          # 글로벌 스케줄러 (메인 실행)
│   ├── production_ml_system.py      # 운영용 ML 시스템
│   ├── daily_trading_system.py      # 일일 트레이딩 자동화
│   └── production_security_check.py # 보안 검증
├── 📂 tools/                        # 시스템 도구
│   ├── 📂 system/
│   │   ├── server.py                # FastAPI 서버 런처
│   │   └── run_global_system.py     # 글로벌 시스템 실행기
│   └── 📂 deploy/                   # 배포 도구
│       ├── deploy.sh                # 배포 스크립트
│       └── stock-analyzer-realtime.service # systemd 서비스
├── 📂 tests/                        # 테스트 코드
│   ├── test_deployment_readiness.py # 배포 준비 상태 테스트
│   ├── test_ml_pipeline.py          # ML 파이프라인 테스트
│   └── conftest.py                  # pytest 설정
├── 📂 docs/                         # 문서
├── 📂 storage/logs/                 # 로그 파일 (년/월/일 구조)
├── 📂 data/                         # 데이터 파일
├── 📂 database/migrations/          # 데이터베이스 마이그레이션
├── requirements.txt                 # Python 패키지 의존성
├── Dockerfile                       # 컨테이너 설정
├── .env.example                     # 환경변수 템플릿
└── README.md                        # 프로젝트 소개
```

---

## 3. 주요 기능

### 🎯 **핵심 기능 목록**

#### 1. **실시간 데이터 수집**
- **한국 시장**: KIS Open API (실시간 주가, 거래량, 재무정보)
- **미국 시장**: Alpha Vantage API (S&P 500 주식 데이터)
- **기술적 지표**: SMA, EMA, RSI, MACD, Bollinger Bands, Volume 분석
- **시장 지수**: KOSPI, KOSDAQ, S&P 500, NASDAQ

#### 2. **머신러닝 예측 시스템**
- **앙상블 모델**: XGBoost + LightGBM + Random Forest
- **글로벌 예측**: 시장별 독립적 모델 + 글로벌 시장 상관관계 분석
- **실시간 학습**: 예측 vs 실제 결과 비교를 통한 모델 개선
- **시장 체제 감지**: 상승장/하락장/횡보장 자동 감지

#### 3. **자동화 스케줄링**
- **일일 추천**: 평일 16:00 (장 마감 후)
- **아침 알림**: 평일 08:30 (장 시작 전)
- **모델 학습**: 매일 06:30 (적응형), 주간 02:00 (고급 학습)
- **유니버스 업데이트**: 월 1회 (첫째 주 일요일)
- **토큰 갱신**: 2시간마다 자동

#### 4. **지능형 알림 시스템**
- **다중 채널**: Telegram, Slack, Discord, Email
- **맞춤형 메시지**: 시장 상황별 차별화된 알림
- **리스크 관리**: 손절가/목표가 자동 계산
- **성과 추적**: 추천 성과 실시간 모니터링

---

## 4. 핵심 모듈 및 파일

### 🔧 **app/ml/global_ml_engine.py**
**글로벌 머신러닝 예측 엔진**

```python
class GlobalMLEngine:
    """글로벌 머신러닝 엔진"""
    
    def __init__(self):
        self.models = {}  # 시장별 모델 저장
        self.scalers = {}  # 시장별 스케일러
        self.model_config = {...}  # 모델 설정
```

**주요 메서드:**
- `train_global_models()`: 전체 시장 모델 학습
- `predict_stocks(region, top_n)`: 시장별 주식 예측
- `detect_market_regime()`: 시장 체제 감지
- `prepare_global_features()`: 글로벌 피처 생성

**핵심 알고리즘:**
1. **피처 엔지니어링**: 80+ 기술적 지표 생성
2. **앙상블 학습**: XGBoost(50%) + LightGBM(30%) + RF(20%)
3. **시장간 상관관계**: KR-US 시장 동조화 분석
4. **리스크 점수**: 변동성 + 베타 + 시장 노출도

### 🔧 **app/services/scheduler.py**
**자동화 스케줄링 서비스**

```python
class SchedulingService:
    """자동화된 작업 스케줄링"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.universe_id = settings.default_universe_id
```

**주요 스케줄:**
- **daily_recommendation_task**: 평일 16:00
- **morning_notification_task**: 평일 08:30  
- **daily_ml_training_task**: 매일 06:30
- **weekly_advanced_training_task**: 일요일 02:00
- **monthly_universe_update_task**: 월 1회

### 🔧 **app/services/data_collection.py**
**데이터 수집 서비스**

**핵심 기능:**
- 다중 API 통합 (KIS + Alpha Vantage)
- Rate Limiting 및 에러 처리
- 실시간 기술적 지표 계산
- 데이터 품질 검증 및 정규화

### 🔧 **app/models/entities.py**
**데이터베이스 엔티티**

**주요 테이블:**
```python
class StockMaster(Base):
    """주식 마스터 정보"""
    stock_id = Column(BigInteger, primary_key=True)
    market_region = Column(String(2))  # KR, US
    stock_code = Column(String(20))
    stock_name = Column(String(200))
    market_capitalization = Column(Numeric(20, 2))

class StockDailyPrice(Base):
    """일별 주가 데이터"""
    price_id = Column(BigInteger, primary_key=True)
    stock_id = Column(BigInteger, ForeignKey("stock_master.stock_id"))
    trade_date = Column(Date)
    open_price = Column(Numeric(15, 4))
    high_price = Column(Numeric(15, 4))
    low_price = Column(Numeric(15, 4))
    close_price = Column(Numeric(15, 4))
    volume = Column(BigInteger)

class StockTechnicalIndicator(Base):
    """기술적 지표"""
    indicator_id = Column(BigInteger, primary_key=True)
    stock_id = Column(BigInteger, ForeignKey("stock_master.stock_id"))
    trade_date = Column(Date)
    sma_5 = Column(Float)
    sma_20 = Column(Float)
    rsi_14 = Column(Float)
    macd = Column(Float)
```

### 🔧 **scripts/global_scheduler.py**
**글로벌 스케줄러 메인 실행기**

**특징:**
- DST(일광절약시간) 자동 처리
- 시장별 독립적 스케줄링
- 에러 복구 및 재시도 로직
- 실시간 성능 모니터링

---

## 5. API 명세

### 🌐 **FastAPI 엔드포인트**

#### **Health Check API**
```http
GET /health/          # 기본 헬스체크
GET /health/detailed  # 상세 시스템 상태
GET /health/ready     # 서비스 준비 상태
GET /health/live      # 서비스 생존 확인
```

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-23T18:50:11",
  "service": "stock-analyzer",
  "system": {
    "cpu_percent": 15.2,
    "memory": {
      "total": 8589934592,
      "used": 4294967296,
      "percent": 50.0
    },
    "database": {
      "status": "connected"
    }
  }
}
```

#### **외부 API 연동**

**KIS Open API**
```python
# 주식 정보 조회
kis_client.get_stock_info(stock_code="005930", market="J")

# 일별 주가 데이터
kis_client.get_daily_prices(stock_code="005930", start_date="20250101")

# 시가총액 순위
kis_client.get_market_cap_ranking(market="J", count=100)
```

**Alpha Vantage API**
```python
# 미국 주식 일별 데이터
alpha_client.get_daily_prices(symbol="AAPL", outputsize="compact")

# 기술적 지표
alpha_client.get_technical_indicators(symbol="AAPL", indicator="RSI")

# S&P 500 심볼 목록
alpha_client.get_sp500_symbols()
```

---

## 6. 데이터베이스 스키마

### 📊 **PostgreSQL 테이블 구조**

#### **핵심 테이블**
1. **stock_master**: 주식 마스터 (5,000+ 종목)
2. **stock_daily_price**: 일별 주가 (5GB+ 데이터)
3. **stock_technical_indicator**: 기술적 지표 (80+ 컬럼)
4. **stock_fundamental_data**: 재무 정보
5. **stock_market_data**: 시장 데이터
6. **trading_universe**: 거래 유니버스
7. **ml_predictions**: ML 예측 결과
8. **ml_model_performance**: 모델 성과 추적

#### **인덱스 최적화**
```sql
-- 복합 인덱스
CREATE INDEX idx_price_stock_date ON stock_daily_price(stock_id, trade_date);
CREATE INDEX idx_indicator_stock_date ON stock_technical_indicator(stock_id, trade_date);

-- 파티셔닝 (월별)
CREATE TABLE stock_daily_price_202509 PARTITION OF stock_daily_price 
FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
```

### 🔴 **Redis 캐시 구조**
```python
# API 응답 캐시
redis_client.setex(f"kis_stock:{stock_code}", 300, json.dumps(data))

# 모델 예측 캐시
redis_client.setex(f"ml_prediction:{region}:{date}", 3600, predictions)

# 세션 관리
redis_client.setex(f"session:{session_id}", 1800, user_data)
```

---

## 7. 핵심 알고리즘

### 🧠 **머신러닝 파이프라인**

#### **1. 피처 엔지니어링**
```python
def prepare_global_features(self, stock_id: int, target_date: date) -> pd.DataFrame:
    """글로벌 피처 생성"""
    
    # 1. 기본 기술적 지표 (40개)
    features = {
        'sma_5', 'sma_10', 'sma_20', 'sma_60',
        'ema_12', 'ema_26', 'rsi_14', 'macd', 'macd_signal',
        'bb_upper', 'bb_middle', 'bb_lower',
        'volume_sma_20', 'volume_ratio'
    }
    
    # 2. 글로벌 시장 지표 (20개)
    global_features = {
        'kospi_return', 'nasdaq_return', 'vix_level',
        'usd_krw_rate', 'market_correlation'
    }
    
    # 3. 파생 지표 (20개)
    derived_features = {
        'price_momentum', 'volume_momentum', 'volatility_ratio',
        'trend_strength', 'market_regime_score'
    }
    
    return combined_features
```

#### **2. 앙상블 모델**
```python
def create_ensemble_model(self):
    """앙상블 모델 생성"""
    
    models = {
        'xgboost': XGBRegressor(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8
        ),
        'lightgbm': LGBMRegressor(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            feature_fraction=0.8
        ),
        'random_forest': RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5
        )
    }
    
    # 가중 평균 앙상블 (XGB:50%, LGB:30%, RF:20%)
    ensemble_weights = [0.5, 0.3, 0.2]
    
    return VotingRegressor(
        estimators=list(models.items()),
        weights=ensemble_weights
    )
```

#### **3. 실시간 학습 알고리즘**
```python
def adaptive_learning_cycle(self):
    """적응형 학습 사이클"""
    
    # 1. 예측 vs 실제 결과 비교
    performance = self.evaluate_predictions(yesterday)
    
    # 2. 성능 임계값 체크
    if performance.accuracy < 0.55:
        # 3. 모델 재학습 트리거
        self.trigger_model_retraining()
        
    # 4. 피처 중요도 업데이트
    self.update_feature_importance()
    
    # 5. 하이퍼파라미터 최적화
    if performance.accuracy < 0.50:
        self.optimize_hyperparameters()
```

### 📊 **시장 체제 감지**
```python
def detect_market_regime(self) -> MarketCondition:
    """시장 체제 감지"""
    
    # 1. 변동성 분석
    volatility_score = self.calculate_volatility_index()
    
    # 2. 트렌드 강도 분석  
    trend_strength = self.calculate_trend_strength()
    
    # 3. 공포/탐욕 지수
    fear_greed_index = self.calculate_fear_greed_index()
    
    # 4. 체제 분류
    if trend_strength > 0.7 and volatility_score < 0.3:
        return MarketCondition.BULL_MARKET
    elif trend_strength < -0.7 and volatility_score > 0.6:
        return MarketCondition.BEAR_MARKET
    else:
        return MarketCondition.SIDEWAYS_MARKET
```

### ⏰ **스케줄링 알고리즘**
```python
def setup_dynamic_schedules(self):
    """동적 스케줄 설정"""
    
    # DST 자동 처리
    if self.is_dst_period():
        us_market_open = "22:30"  # DST 기간
        us_market_close = "05:00"
    else:
        us_market_open = "23:30"  # 표준시
        us_market_close = "06:00"
    
    # 시장별 독립적 스케줄링
    kr_schedules = [
        CronTrigger(day_of_week='mon-fri', hour=8, minute=30),   # 장전 알림
        CronTrigger(day_of_week='mon-fri', hour=16, minute=0),  # 장후 분석
    ]
    
    us_schedules = [
        CronTrigger(day_of_week='mon-fri', hour=22, minute=0),  # 장전 분석
        CronTrigger(day_of_week='tue-sat', hour=5, minute=30),  # 장후 알림
    ]
```

---

## 8. 환경 요구사항

### 🐍 **Python 환경**
- **Python**: 3.9+
- **핵심 라이브러리**:
  ```txt
  fastapi==0.116.2
  uvicorn==0.35.0
  sqlalchemy==2.0.35
  psycopg==3.2.3
  redis==5.2.1
  pandas==2.3.2
  numpy==2.2.2
  scikit-learn==1.5.2
  xgboost==2.1.2
  lightgbm==4.5.0
  apscheduler==3.10.4
  pydantic==2.11.9
  requests==2.32.3
  ```

### 🗄️ **데이터베이스**
- **PostgreSQL**: 14+
  - 용량: 최소 100GB (주가 데이터)
  - 메모리: 8GB+ RAM 권장
  - CPU: 4+ cores
- **Redis**: 6+
  - 메모리: 2GB+ 할당

### 🌐 **외부 API**
- **KIS Open API**: 
  - APP_KEY, APP_SECRET 필요
  - 일일 API 호출 제한: 초당 20회
- **Alpha Vantage API**:
  - API_KEY 필요 (무료: 월 500회)
  - 프리미엄 권장 (월 75,000회)

### 🖥️ **서버 요구사항**
```yaml
최소 사양:
  CPU: 4 cores
  RAM: 8GB
  Disk: 100GB SSD
  Network: 100Mbps

권장 사양:
  CPU: 8 cores (Intel i7/AMD Ryzen 7)
  RAM: 16GB+
  Disk: 500GB NVMe SSD
  Network: 1Gbps
```

---

## 9. 배포 가이드

### 🚀 **Docker 배포**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8080

CMD ["python", "tools/system/server.py"]
```

```bash
# 이미지 빌드
docker build -t stock-analyzer:latest .

# 컨테이너 실행
docker run -d \
  --name stock-analyzer \
  -p 8080:8080 \
  --env-file .env \
  stock-analyzer:latest
```

### 🐧 **Ubuntu/Linux 배포**
```bash
# 1. 시스템 패키지 설치
sudo apt update
sudo apt install python3.9 python3-pip postgresql redis-server

# 2. Python 가상환경
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 데이터베이스 설정
sudo -u postgres createdb stock_analyzer
python database/migrations/run_migrations.py

# 4. systemd 서비스 등록
sudo cp tools/deploy/stock-analyzer-realtime.service /etc/systemd/system/
sudo systemctl enable stock-analyzer-realtime
sudo systemctl start stock-analyzer-realtime

# 5. 서비스 상태 확인
sudo systemctl status stock-analyzer-realtime
```

### ⚙️ **환경변수 설정**
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/stock_analyzer
REDIS_URL=redis://localhost:6379/0

# APIs  
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# Notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SLACK_WEBHOOK_URL=your_slack_webhook

# ML Settings
MODEL_CACHE_DIR=/app/storage/models
FEATURE_CACHE_DIR=/app/storage/features
ML_PREDICTION_THRESHOLD=0.6

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/storage/logs/stock_analyzer.log
```

---

## 10. 테스트

### 🧪 **테스트 구조**
```python
tests/
├── test_deployment_readiness.py    # 배포 준비 상태 테스트
├── test_ml_pipeline.py            # ML 파이프라인 테스트  
├── test_api_changes.py            # API 변경사항 테스트
├── test_unified_data_collector.py # 데이터 수집기 테스트
├── test_kis_token.py              # KIS API 토큰 테스트
├── test_telegram.py               # Telegram 알림 테스트
└── conftest.py                    # pytest 설정
```

### 🚀 **배포 준비 테스트**
```bash
# 전체 시스템 통합 테스트
python test_deployment_readiness.py

# 출력 예시:
# ✅ 모듈 임포트: 8/8 성공
# ✅ 데이터베이스 연결: 성공  
# ✅ 글로벌 스케줄러: 13개 작업 등록
# ✅ ML 엔진 초기화: 성공
# ⚠️ ML 모델 학습: 시간 소요로 건너뜀
# ✅ 로깅 시스템: 정상 작동
# 📊 전체 점수: 95/100
```

### 🔬 **단위 테스트**
```bash
# pytest 실행
pytest tests/ -v

# 커버리지 포함 실행
pytest tests/ --cov=app --cov-report=html

# 특정 테스트만 실행
pytest tests/test_ml_pipeline.py::test_ml_fast -v
```

### 📊 **성능 테스트**
```python
# ML 모델 성능 테스트
def test_ml_prediction_speed():
    engine = GlobalMLEngine()
    
    start_time = time.time()
    predictions = engine.predict_stocks(MarketRegion.KR, top_n=10)
    end_time = time.time()
    
    assert (end_time - start_time) < 30  # 30초 이내
    assert len(predictions) == 10
```

---

## 11. 주의사항

### ⚠️ **중요한 제약사항**

#### **1. API 제한**
- **KIS API**: 초당 20회, 일일 10,000회 제한
- **Alpha Vantage**: 분당 5회 (무료), 75,000회/월 (프리미엄)
- **Rate Limiting 필수**: APIRateLimiter 클래스 사용

#### **2. 데이터 품질**
- **시장 휴일**: 거래소 휴일 처리 로직 필요
- **기업 액션**: 액면분할, 무상증자 등 조정 필요
- **상장폐지**: 종목 비활성화 처리

#### **3. 메모리 관리**
```python
# 대용량 데이터 처리 시 청크 단위 처리
def process_large_dataset(stock_codes):
    chunk_size = 100
    for i in range(0, len(stock_codes), chunk_size):
        chunk = stock_codes[i:i + chunk_size]
        process_chunk(chunk)
        gc.collect()  # 명시적 가비지 컬렉션
```

#### **4. 시간대 처리**
- **한국 시장**: Asia/Seoul (KST)
- **미국 시장**: America/New_York (EST/EDT)
- **DST 자동 처리**: pytz 라이브러리 활용

#### **5. 에러 처리**
```python
# 견고한 에러 처리 패턴
@retry(tries=3, delay=1, backoff=2)
def robust_api_call():
    try:
        return api_client.get_data()
    except RateLimitError:
        time.sleep(60)  # Rate limit 대기
        raise
    except NetworkError:
        # 네트워크 에러 재시도
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

### 🔒 **보안 고려사항**

#### **1. API 키 관리**
```bash
# 환경변수로 관리 (절대 코드에 하드코딩 금지)
export KIS_APP_KEY="your_secret_key"
export KIS_APP_SECRET="your_secret"

# .env 파일 .gitignore 추가
echo ".env" >> .gitignore
```

#### **2. 데이터베이스 보안**
- PostgreSQL 연결 암호화 (SSL)
- 최소 권한 원칙 적용
- 정기적 백업 및 복구 테스트

#### **3. 로그 보안**
```python
# 민감 정보 마스킹
def mask_sensitive_data(log_message):
    return re.sub(r'(api_key=)[^&\s]+', r'\1***', log_message)
```

### 📈 **성능 최적화**

#### **1. 데이터베이스 최적화**
```sql
-- 인덱스 최적화
CREATE INDEX CONCURRENTLY idx_stock_date_region 
ON stock_daily_price(trade_date, market_region) 
WHERE trade_date >= '2024-01-01';

-- 파티셔닝으로 대용량 데이터 관리
CREATE TABLE stock_daily_price_2025 PARTITION OF stock_daily_price 
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

#### **2. Redis 캐싱 전략**
```python
# 계층적 캐싱
def get_stock_data_cached(stock_code, date):
    # L1: 메모리 캐시 (1분)
    cache_key = f"stock:{stock_code}:{date}"
    
    # L2: Redis 캐시 (5분)
    if not data:
        data = redis_client.get(cache_key)
    
    # L3: 데이터베이스
    if not data:
        data = fetch_from_database(stock_code, date)
        redis_client.setex(cache_key, 300, json.dumps(data))
    
    return data
```

#### **3. 비동기 처리**
```python
import asyncio
import aiohttp

async def parallel_api_calls(stock_codes):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_stock_data(session, code) for code in stock_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

---

## 📞 문의 및 지원

### 🛠️ **기술 지원**
- **이슈 트래킹**: GitHub Issues
- **문서**: `/docs` 디렉토리 참조
- **로그 분석**: `/storage/logs` 구조화된 로그

### 📚 **추가 학습 자료**
- **FastAPI 공식 문서**: https://fastapi.tiangolo.com/
- **SQLAlchemy ORM**: https://docs.sqlalchemy.org/
- **XGBoost 가이드**: https://xgboost.readthedocs.io/
- **APScheduler 문서**: https://apscheduler.readthedocs.io/

---

**© 2025 Stock Analyzer Project. All rights reserved.**

> 이 문서는 개발자와 AI 에이전트가 프로젝트를 이해하고 확장할 수 있도록 작성되었습니다.  
> 질문이나 개선사항이 있다면 GitHub Issues를 통해 문의해 주세요.