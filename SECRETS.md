# GitHub Secrets 설정 가이드

이 프로젝트의 CI/CD 파이프라인을 사용하기 위해 다음 GitHub Secrets를 설정해야 합니다.

## 환경 설정 파일 (중요!)
- `ENV_FILE`: 전체 환경 변수 설정이 포함된 .env 파일 내용

### ENV_FILE 예시
```env
# Database Configuration (기존 서버 DB 사용)
DATABASE_URL=postgresql://username:password@host:port/database

# Redis Configuration (기존 서버 Redis 사용)  
REDIS_URL=redis://host:port

# KIS API Configuration
KIS_APP_KEY=your_kis_app_key
KIS_SECRET_KEY=your_kis_secret_key
KIS_BASE_URL=https://openapi.koreainvestment.com:9443

# Notification Configuration
NOTIFICATION_EMAIL_ENABLED=true
NOTIFICATION_EMAIL_SMTP_SERVER=smtp.gmail.com
NOTIFICATION_EMAIL_SMTP_PORT=587
NOTIFICATION_EMAIL_USER=your_email@gmail.com
NOTIFICATION_EMAIL_PASSWORD=your_app_password
NOTIFICATION_EMAIL_TO=recipient@email.com

NOTIFICATION_SLACK_ENABLED=true
NOTIFICATION_SLACK_WEBHOOK_URL=https://hooks.slack.com/your_webhook

NOTIFICATION_DISCORD_ENABLED=false
NOTIFICATION_TELEGRAM_ENABLED=false

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=/app/logs/stock_analyzer.log

# Scheduler Configuration
SCHEDULER_TIMEZONE=Asia/Seoul
SCHEDULER_RECOMMENDATION_TIME=16:00
SCHEDULER_MORNING_ALERT_TIME=08:30
SCHEDULER_RETRAIN_DAY=0
SCHEDULER_RETRAIN_TIME=02:00
```

## Docker Hub 관련
- `DOCKERHUB_USERNAME`: Docker Hub 사용자명
- `DOCKERHUB_TOKEN`: Docker Hub 액세스 토큰

## 서버 배포 관련
- `SERVER_HOST`: 배포 대상 서버 IP 주소
- `SERVER_USER`: SSH 접속 사용자명
- `SERVER_PASSWORD`: SSH 접속 비밀번호
- `SERVER_PORT`: SSH 포트 (기본값: 22)

## KIS API 관련
- `KIS_APP_KEY`: 한국투자증권 Open API 앱 키
- `KIS_SECRET_KEY`: 한국투자증권 Open API 시크릿 키

## 데이터베이스 관련
- `DATABASE_URL`: 기존 PostgreSQL 데이터베이스 연결 URL (예: postgresql://username:password@host:port/database)
- `REDIS_URL`: 기존 Redis 서버 연결 URL (예: redis://host:port 또는 redis://username:password@host:port)

## 이메일 알림 관련
- `EMAIL_USER`: 발신 이메일 주소
- `EMAIL_PASSWORD`: 이메일 계정 비밀번호 또는 앱 비밀번호
- `EMAIL_TO`: 수신 이메일 주소 (쉼표로 구분하여 여러 주소 가능)

## Slack 알림 관련
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL

## Discord 알림 관련 (선택사항)
- `DISCORD_WEBHOOK_URL`: Discord Webhook URL

## Telegram 알림 관련 (선택사항)
- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
- `TELEGRAM_CHAT_ID`: Telegram Chat ID

## Secrets 설정 방법

### 1. ENV_FILE 설정 (가장 중요!)
1. 위의 ENV_FILE 예시를 복사
2. 실제 값들로 수정 (DATABASE_URL, KIS API 키, 이메일 설정 등)
3. GitHub 저장소 → Settings → Secrets and variables → Actions
4. "New repository secret" 클릭
5. Name: `ENV_FILE`, Secret: 수정한 .env 파일 전체 내용 붙여넣기

### 2. 나머지 Secrets 설정
1. GitHub 저장소 페이지로 이동
2. Settings → Secrets and variables → Actions 클릭
3. "New repository secret" 버튼 클릭
4. 위의 Docker Hub 및 서버 관련 시크릿들 설정

## 배포 프로세스

1. `main` 브랜치에 코드 푸시
2. GitHub Actions가 자동으로 실행
3. 테스트 → Docker 이미지 빌드 → Docker Hub 푸시 → 서버 배포 순서로 진행
4. 배포 완료 후 `http://SERVER_IP:8090`에서 서비스 확인 가능

## 서버 요구사항

- Docker 설치 (Docker Compose 불필요)
- 기존 PostgreSQL 데이터베이스 (별도 설정 완료)
- 기존 Redis 서버 (별도 설정 완료)
- 애플리케이션 포트 8090 사용 가능
- `/opt/stock-analyzer` 디렉터리 생성 권한
- `/volume1/project/stock-analyzer` 디렉터리 생성 권한 (데이터/로그 저장용)

## 모니터링

배포된 서비스는 다음 URL에서 상태 확인 가능:
- Health Check: `http://SERVER_IP:8090/health`
- 로그 확인: `sudo docker logs -f stock-analyzer`
- 데이터 디렉터리: `/volume1/project/stock-analyzer/data`
- 로그 디렉터리: `/volume1/project/stock-analyzer/logs`
