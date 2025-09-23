# 🚀 Stock Analyzer - AI 주식 분석 시스템

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.8+-red.svg)](https://pytorch.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AI 기반 글로벌 주식 분석 및 실시간 추천 시스템**

한국(KRX)과 미국(NYSE/NASDAQ) 주식 시장을 대상으로 고도화된 머신러닝 모델을 활용한 실시간 주식 분석, 예측, 그리고 다채널 알림 서비스를 제공합니다.

---

## 🎯 주요 기능

### 🧠 **고도화된 AI 분석 엔진**
- **딥러닝 모델**: LSTM, Transformer 기반 시계열 예측
- **앙상블 학습**: XGBoost, LightGBM, Random Forest 조합
- **베이지안 최적화**: 자동 하이퍼파라미터 튜닝
- **실시간 적응 학습**: 시장 변화에 따른 모델 자동 업데이트

### 📊 **동적 종목 유니버스**
- **스마트 종목 선택**: 시장 조건에 따른 동적 포트폴리오 구성
- **다양성 보장**: 섹터별, 시가총액별 균형 있는 분석
- **성과 기반 갱신**: 예측 정확도에 따른 종목 교체

### 🌍 **글로벌 시장 지원**
- **한국 시장**: KIS API 연동, 실시간 데이터 수집
- **미국 시장**: Alpha Vantage API, 프리마켓/애프터마켓 지원
- **시간대 자동 관리**: DST(일광절약시간) 자동 처리

### 📱 **다채널 알림 시스템**
- **Telegram**: 실시간 매매 신호 및 시장 분석
- **Discord**: 상세한 분석 리포트 및 차트
- **Slack**: 팀 협업용 알림 및 요약
- **Email**: 일일/주간 성과 리포트

### ⚡ **고성능 시스템 아키텍처**
- **비동기 처리**: aiohttp, asyncio 기반 고속 데이터 처리
- **멀티레벨 캐싱**: 메모리 + Redis 하이브리드 캐싱
- **자동 성능 최적화**: 메모리 관리 및 실시간 모니터링
- **확장 가능한 설계**: Docker 컨테이너 기반 마이크로서비스

---

## 🛠️ 기술 스택

### **백엔드 & API**
- **FastAPI**: 고성능 웹 프레임워크
- **Python 3.13**: 최신 파이썬 기능 활용
- **PostgreSQL**: 주식 데이터 저장
- **Redis**: 캐싱 및 세션 관리

### **머신러닝 & AI**
- **PyTorch**: 딥러닝 모델 구현
- **scikit-learn**: 전통적 ML 알고리즘
- **XGBoost/LightGBM**: 그래디언트 부스팅
- **scikit-optimize**: 베이지안 최적화

### **데이터 처리**
- **pandas/numpy**: 데이터 분석 및 처리
- **yfinance**: 미국 주식 데이터
- **beautifulsoup4**: 웹 스크래핑
- **TA-Lib**: 기술적 지표 계산

### **인프라 & 배포**
- **Docker**: 컨테이너화
- **GitHub Actions**: CI/CD 파이프라인
- **systemd**: 리눅스 서비스 관리
- **APScheduler**: 작업 스케줄링

---

## 🚀 빠른 시작

### **1. 환경 설정**

```bash
# 저장소 클론
git clone https://github.com/your-repo/stock-analyzer.git
cd stock-analyzer

# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt
```

### **2. 환경 변수 설정**

`.env` 파일을 생성하고 다음 정보를 입력하세요:

```env
# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost/stock_analyzer
REDIS_URL=redis://localhost:6379

# API 키
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# 알림 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook
SLACK_BOT_TOKEN=your_slack_token

# 시스템 설정
ENVIRONMENT=development
DEBUG=true
```

### **3. 데이터베이스 초기화**

```bash
# PostgreSQL 데이터베이스 생성
createdb stock_analyzer

# 마이그레이션 실행
python -m alembic upgrade head
```

### **4. 시스템 실행**

```bash
# 개발 환경에서 실행
python app/main.py

# 또는 프로덕션 환경
python scripts/global_scheduler.py
```

---

## 📋 주요 스케줄

### **🇰🇷 한국 시장**
- **08:30** - 프리마켓 추천 생성 및 알림
- **19:00** - 당일 데이터 수집 (KIS API)
- **19:15** - 시장 분석 및 다음날 예측

### **🇺🇸 미국 시장** *(한국 시간)*
- **22:00** - 프리마켓 알림 (ET 04:00)
- **23:30** - 정규장 시작 알림 (ET 09:30)
- **06:30+1** - 마켓 클로즈 분석 (ET 16:30)
- **10:30+1** - 애프터마켓 데이터 수집 (ET 20:30)

### **🤖 ML 시스템**
- **06:30** - 일일 모델 학습 및 업데이트
- **일요일 02:00** - 주간 고도화 학습
- **20:00** - 일일 성과 평가 및 리포트

### **🔧 시스템 관리**
- **00:00** - KIS 토큰 재발급
- **매시간 :00** - 시스템 헬스체크
- **매시간 :30** - 성능 최적화 실행
- **4시간마다** - 긴급 알림 체크

---

## 🏗️ 프로젝트 구조

```
stock-analyzer/
├── 📂 app/                          # 핵심 애플리케이션
│   ├── config/                      # 설정 관리
│   ├── database/                    # DB 연결 및 Redis
│   ├── ml/                         # 머신러닝 엔진
│   │   ├── global_ml_engine.py     # 통합 ML 엔진
│   │   ├── advanced_ml_engine.py   # 고도화된 딥러닝 모델
│   │   └── models.py               # 기본 ML 모델
│   ├── services/                   # 비즈니스 로직
│   │   ├── unified_data_collector.py  # 통합 데이터 수집
│   │   ├── dynamic_universe_manager.py # 동적 종목 관리
│   │   ├── bear_market_detector.py     # 하락장 감지
│   │   ├── performance_optimizer.py    # 성능 최적화
│   │   └── notification.py             # 다채널 알림
│   └── utils/                      # 유틸리티
├── 📂 scripts/                     # 실행 스크립트
│   ├── global_scheduler.py         # 메인 스케줄러
│   └── production_ml_system.py     # 프로덕션 ML 시스템
├── 📂 database/migrations/         # DB 마이그레이션
├── 📂 storage/                     # 데이터 저장소
│   ├── logs/                       # 로그 파일 (연/월/일별)
│   ├── models/                     # ML 모델 파일
│   └── data/                       # 임시 데이터
├── 📂 docs/                        # 상세 문서
└── 📂 tests/                       # 테스트 코드
```

---

## 🎛️ API 엔드포인트

### **헬스체크**
```http
GET /health
```

### **주식 분석**
```http
POST /analyze
Content-Type: application/json

{
  "market": "KR",  // "KR" 또는 "US"
  "symbols": ["005930", "000660"],
  "analysis_type": "advanced"
}
```

### **실시간 예측**
```http
GET /predict/{market}/{symbol}
```

### **성능 리포트**
```http
GET /performance/daily
GET /performance/weekly
```

---

## 📊 ML 모델 성능

### **예측 정확도** *(백테스팅 기준)*
- **한국 시장**: 평균 73.2% (상위 20개 종목)
- **미국 시장**: 평균 71.8% (S&P 500 대상)
- **베어마켓 감지**: 85.4% 정확도

### **모델 구성**
1. **기본 앙상블** (60% 가중치)
   - XGBoost + LightGBM + Random Forest
2. **딥러닝 모델** (30% 가중치)
   - LSTM + Transformer
3. **시장 체제 감지** (10% 가중치)
   - 변동성 기반 체제 분류

---

## 🔧 운영 및 모니터링

### **로그 시스템**
- **구조화된 로깅**: JSON 형태의 상세 로그
- **자동 로테이션**: 연/월/일별 폴더 구조
- **실시간 모니터링**: 에러 및 성능 지표 추적

### **성능 최적화**
- **메모리 자동 정리**: 가비지 컬렉션 최적화
- **캐시 히트율**: 평균 85%+ 유지
- **API 응답시간**: 평균 200ms 이하

### **에러 처리**
- **자동 복구**: API 장애 시 재시도 로직
- **Graceful Degradation**: 부분 장애 시 서비스 지속
- **실시간 알림**: 시스템 오류 즉시 통지

---

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

---

## 📞 지원 및 문의

- **이슈 리포트**: [GitHub Issues](https://github.com/your-repo/stock-analyzer/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/your-repo/stock-analyzer/discussions)
- **이메일**: support@stockanalyzer.com

---

## 🎉 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들의 도움을 받았습니다:

- [FastAPI](https://fastapi.tiangolo.com/) - 고성능 웹 프레임워크
- [PyTorch](https://pytorch.org/) - 딥러닝 라이브러리
- [scikit-learn](https://scikit-learn.org/) - 머신러닝 도구
- [pandas](https://pandas.pydata.org/) - 데이터 분석 라이브러리

---

**⚠️ 투자 위험 고지**: 이 시스템의 예측 결과는 투자 참고용이며, 실제 투자 결정은 신중하게 하시기 바랍니다. 투자에 따른 손실은 투자자 본인의 책임입니다.
