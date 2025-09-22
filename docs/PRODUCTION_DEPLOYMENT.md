# 글로벌 주식 분석 시스템 - 프로덕션 배포 가이드

## 시스템 개요

이 시스템은 한국과 미국 주식 시장을 통합 분석하여 매일 자동으로 투자 추천을 제공하는 글로벌 AI 시스템입니다.

### 🌟 주요 기능

- **🇰🇷 한국 시장**: KIS API를 통한 30개 주요 종목 분석
- **🇺🇸 미국 시장**: Alpha Vantage API를 통한 S&P 500 상위 50개 종목 분석
- **🤖 글로벌 ML**: 시장 체제 분석 및 크로스 마켓 상관관계 기반 예측
- **📱 스마트 알림**: 프리마켓 알림, 하락장 경고, 시장 마감 요약
- **⏰ 자동 스케줄링**: 24시간 무인 자동 운영

### 📅 운영 스케줄 (정확한 시간대 적용)

#### 🇰🇷 한국 시장 (KST 고정)
```
08:30 - 🇰🇷 정규장 시작 30분 전 추천 알림
09:00 - �🇷 정규장 개장
15:30 - 🇰🇷 정규장 마감
16:00 - 🇰🇷 마감 후 데이터 수집 및 ML 분석
```

#### �🇺🇸 미국 시장 (서머타임 자동 감지)
```
서머타임 적용 시 (3월~11월):
16:30 - 🇺🇸 프리마켓 시작 30분 전 알림 (프리마켓: 17:00~22:30)
22:00 - 🇺🇸 정규장 시작 30분 전 알림 (정규장: 22:30~05:00)
05:30 - 🇺🇸 정규장 마감 후 데이터 수집 및 ML 분석

표준시 적용 시 (11월~3월):
17:30 - 🇺🇸 프리마켓 시작 30분 전 알림 (프리마켓: 18:00~23:30)
23:00 - �� 정규장 시작 30분 전 알림 (정규장: 23:30~06:00)
06:30 - �� 정규장 마감 후 데이터 수집 및 ML 분석
```

#### 📊 주간 분석
```
토요일 12:00 - 🏋️ 주간 종합 분석, ML 재학습, 트렌드 리포트
```

## 🚀 배포 단계

### 1. 환경 설정

```bash
# 1. 저장소 클론
git clone <repository-url>
cd stock-analyzer

# 2. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```bash
# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost:5432/stock_analyzer
REDIS_URL=redis://localhost:6379/0

# 한국투자증권 API
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
KIS_ACCOUNT_NUMBER=your_account_number

# Alpha Vantage API (미국 주식)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# 알림 서비스
DISCORD_WEBHOOK_URL=your_discord_webhook_url
SLACK_TOKEN=your_slack_token
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# 시스템 설정
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 3. 데이터베이스 설정

```bash
# PostgreSQL 설치 및 설정
sudo apt update
sudo apt install postgresql postgresql-contrib

# 데이터베이스 생성
sudo -u postgres createdb stock_analyzer

# Redis 설치
sudo apt install redis-server

# 데이터베이스 초기화
python -c "from app.database.connection import init_database; init_database()"
```

### 4. 시스템 초기화

```bash
# 시스템 설정 및 초기 데이터 수집
python run_global_system.py --setup
python run_global_system.py --collect-data
python run_global_system.py --train-models
```

### 5. 서비스 등록 (systemd)

`/etc/systemd/system/stock-analyzer.service` 생성:

```ini
[Unit]
Description=Global Stock Analysis System
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=stock
WorkingDirectory=/opt/stock-analyzer
Environment=PATH=/opt/stock-analyzer/venv/bin
ExecStart=/opt/stock-analyzer/venv/bin/python run_global_system.py --schedule
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

서비스 활성화:

```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-analyzer.service
sudo systemctl start stock-analyzer.service
```

### 6. Cron 작업 설정 (대안)

```bash
# crontab 편집
crontab -e

# 다음 라인 추가:
# 미국 프리마켓 알림 (매일 06:00)
0 6 * * * cd /opt/stock-analyzer && python scripts/global_scheduler.py --manual us_premarket

# 한국 시장 분석 (매일 16:00)
0 16 * * * cd /opt/stock-analyzer && python scripts/global_scheduler.py --manual korean_analysis

# 미국 데이터 수집 (매일 07:00)
0 7 * * * cd /opt/stock-analyzer && python scripts/global_scheduler.py --manual us_data

# 한국 데이터 수집 (매일 17:00)
0 17 * * * cd /opt/stock-analyzer && python scripts/global_scheduler.py --manual korean_data

# ML 모델 재학습 (매주 토요일 02:00)
0 2 * * 6 cd /opt/stock-analyzer && python scripts/global_scheduler.py --manual ml_training
```

## 🔧 운영 관리

### 시스템 상태 확인

```bash
# 전체 시스템 상태
python run_global_system.py --status

# 서비스 상태
sudo systemctl status stock-analyzer

# 로그 확인
tail -f storage/logs/global_system.log
```

### 수동 실행

```bash
# 전체 파이프라인 실행
python run_global_system.py --full

# 개별 작업 실행
python run_global_system.py --collect-data  # 데이터 수집
python run_global_system.py --predict       # 예측 실행
python run_global_system.py --alerts        # 알림 전송
```

### 백업 및 복구

```bash
# 데이터베이스 백업
pg_dump stock_analyzer > backup_$(date +%Y%m%d).sql

# 모델 백업
tar -czf models_backup_$(date +%Y%m%d).tar.gz storage/models/

# 복구
psql stock_analyzer < backup_20231215.sql
```

## 📊 모니터링

### 핵심 지표

1. **데이터 수집 성공률**: 매일 한미 시장 데이터 수집 성공 여부
2. **모델 정확도**: 예측 정확도 추적
3. **알림 전송률**: Discord/Slack 알림 전송 성공률
4. **시스템 가동률**: 24시간 무중단 서비스 목표

### 알람 설정

```bash
# 시스템 실패 시 알림
python -c "
from app.services.notification import NotificationService
service = NotificationService()
service.send_system_alert('System Health Check Failed')
"
```

## 🚨 트러블슈팅

### 일반적인 문제

1. **API 한도 초과**
   - KIS API: 1일 20,000회 제한
   - Alpha Vantage: 1분당 5회 제한
   - 해결: Redis 캐싱 및 rate limiting 활용

2. **데이터베이스 연결 실패**
   - PostgreSQL 서비스 상태 확인
   - 연결 풀 설정 조정

3. **메모리 부족**
   - ML 모델 학습 시 메모리 사용량 증가
   - 배치 크기 조정 또는 서버 메모리 증설

### 로그 분석

```bash
# 에러 로그 확인
grep "ERROR" storage/logs/global_system.log

# 성능 로그 확인
grep "소요 시간" storage/logs/global_system.log
```

## 🔒 보안 고려사항

1. **API 키 관리**: 환경 변수로 안전하게 관리
2. **데이터베이스 접근**: 최소 권한 원칙 적용
3. **로그 파일**: 민감 정보 마스킹
4. **네트워크**: 방화벽 설정으로 필요한 포트만 개방

## 📈 성능 최적화

1. **데이터베이스 인덱싱**: 자주 조회하는 컬럼에 인덱스 생성
2. **Redis 캐싱**: API 응답 및 계산 결과 캐싱
3. **배치 처리**: 대량 데이터 처리 시 배치 단위로 처리
4. **비동기 처리**: asyncio를 활용한 비동기 작업

## 📞 지원

문제가 발생하면 다음 정보와 함께 문의하세요:

1. 시스템 상태: `python run_global_system.py --status`
2. 최근 로그: `tail -100 storage/logs/global_system.log`
3. 환경 정보: OS, Python 버전, 메모리/CPU 사양

---

**⚠️ 주의사항**: 이 시스템은 투자 참고용으로만 사용하시고, 모든 투자 결정은 본인의 책임하에 이루어져야 합니다.
