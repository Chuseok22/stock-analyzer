#!/bin/bash

# 글로벌 주식 분석 시스템 - 프로덕션 배포 스크립트
# 사용법: ./deploy.sh [environment]
# 예시: ./deploy.sh production

set -e  # 에러 발생 시 스크립트 중단

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 환경 설정
ENVIRONMENT=${1:-production}
PROJECT_NAME="stock-analyzer"
DEPLOY_USER="stock"
DEPLOY_DIR="/opt/${PROJECT_NAME}"
SERVICE_NAME="${PROJECT_NAME}.service"

log_info "🚀 글로벌 주식 분석 시스템 프로덕션 배포 시작"
log_info "환경: ${ENVIRONMENT}"
log_info "배포 경로: ${DEPLOY_DIR}"

# 1. 시스템 사용자 생성
create_system_user() {
    log_info "👤 시스템 사용자 생성..."
    
    if ! id -u ${DEPLOY_USER} > /dev/null 2>&1; then
        sudo useradd -r -m -d ${DEPLOY_DIR} -s /bin/bash ${DEPLOY_USER}
        log_success "사용자 ${DEPLOY_USER} 생성 완료"
    else
        log_info "사용자 ${DEPLOY_USER} 이미 존재"
    fi
}

# 2. 필수 패키지 설치
install_dependencies() {
    log_info "📦 시스템 패키지 설치..."
    
    sudo apt update
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        postgresql \
        postgresql-contrib \
        redis-server \
        nginx \
        certbot \
        python3-certbot-nginx \
        git \
        curl \
        htop \
        vim
    
    log_success "시스템 패키지 설치 완료"
}

# 3. 데이터베이스 설정
setup_database() {
    log_info "🗄️ PostgreSQL 데이터베이스 설정..."
    
    # PostgreSQL 서비스 시작
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    # 데이터베이스 생성 (이미 있으면 건너뛰기)
    sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw ${PROJECT_NAME} || {
        sudo -u postgres createdb ${PROJECT_NAME}
        sudo -u postgres psql -c "CREATE USER ${DEPLOY_USER} WITH PASSWORD 'secure_password';"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${PROJECT_NAME} TO ${DEPLOY_USER};"
        log_success "데이터베이스 생성 완료"
    }
    
    # Redis 설정
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    
    log_success "데이터베이스 설정 완료"
}

# 4. 애플리케이션 배포
deploy_application() {
    log_info "📁 애플리케이션 배포..."
    
    # 배포 디렉토리 생성
    sudo mkdir -p ${DEPLOY_DIR}
    sudo chown ${DEPLOY_USER}:${DEPLOY_USER} ${DEPLOY_DIR}
    
    # 현재 코드를 배포 위치로 복사
    sudo -u ${DEPLOY_USER} cp -r . ${DEPLOY_DIR}/
    
    # 가상환경 생성
    sudo -u ${DEPLOY_USER} python3 -m venv ${DEPLOY_DIR}/venv
    
    # 의존성 설치
    sudo -u ${DEPLOY_USER} ${DEPLOY_DIR}/venv/bin/pip install --upgrade pip
    sudo -u ${DEPLOY_USER} ${DEPLOY_DIR}/venv/bin/pip install -r ${DEPLOY_DIR}/requirements.txt
    
    # 필요한 디렉토리 생성
    sudo -u ${DEPLOY_USER} mkdir -p ${DEPLOY_DIR}/storage/{logs,models,data,backups}
    sudo -u ${DEPLOY_USER} mkdir -p ${DEPLOY_DIR}/storage/models/global
    
    log_success "애플리케이션 배포 완료"
}

# 5. 환경 변수 설정
setup_environment() {
    log_info "🔧 환경 변수 설정..."
    
    # .env 파일 생성 (템플릿)
    sudo -u ${DEPLOY_USER} cat > ${DEPLOY_DIR}/.env << 'EOF'
# 프로덕션 환경 설정
ENVIRONMENT=production
LOG_LEVEL=INFO

# 데이터베이스
DATABASE_URL=postgresql://stock:secure_password@localhost:5432/stock-analyzer
REDIS_URL=redis://localhost:6379/0

# 한국투자증권 API (실제 값으로 교체 필요)
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
KIS_ACCOUNT_NUMBER=your_account_number

# Alpha Vantage API (실제 값으로 교체 필요)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# 알림 서비스 (실제 값으로 교체 필요)
DISCORD_WEBHOOK_URL=your_discord_webhook_url
SLACK_TOKEN=your_slack_token

# 이메일 설정 (선택사항)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EOF

    sudo chown ${DEPLOY_USER}:${DEPLOY_USER} ${DEPLOY_DIR}/.env
    sudo chmod 600 ${DEPLOY_DIR}/.env
    
    log_warning "⚠️ ${DEPLOY_DIR}/.env 파일을 실제 API 키로 업데이트하세요!"
    log_success "환경 변수 설정 완료"
}

# 6. systemd 서비스 설정
setup_systemd_service() {
    log_info "⚙️ systemd 서비스 설정..."
    
    # 서비스 파일 생성
    sudo tee /etc/systemd/system/${SERVICE_NAME} > /dev/null << EOF
[Unit]
Description=Global Stock Analysis System
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${DEPLOY_DIR}
Environment=PATH=${DEPLOY_DIR}/venv/bin
ExecStart=${DEPLOY_DIR}/venv/bin/python ${DEPLOY_DIR}/scripts/enhanced_global_scheduler.py --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 보안 설정
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=${DEPLOY_DIR}/storage

[Install]
WantedBy=multi-user.target
EOF

    # 서비스 등록
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}
    
    log_success "systemd 서비스 설정 완료"
}

# 7. 로그 로테이션 설정
setup_log_rotation() {
    log_info "📝 로그 로테이션 설정..."
    
    sudo tee /etc/logrotate.d/${PROJECT_NAME} > /dev/null << EOF
${DEPLOY_DIR}/storage/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ${DEPLOY_USER} ${DEPLOY_USER}
    postrotate
        systemctl reload ${SERVICE_NAME} > /dev/null 2>&1 || true
    endscript
}
EOF

    log_success "로그 로테이션 설정 완료"
}

# 8. 방화벽 설정
setup_firewall() {
    log_info "🔥 방화벽 설정..."
    
    # ufw가 설치되어 있으면 설정
    if command -v ufw > /dev/null; then
        sudo ufw --force reset
        sudo ufw default deny incoming
        sudo ufw default allow outgoing
        sudo ufw allow ssh
        sudo ufw allow http
        sudo ufw allow https
        sudo ufw --force enable
        log_success "방화벽 설정 완료"
    else
        log_info "ufw가 설치되지 않음, 방화벽 설정 건너뛰기"
    fi
}

# 9. SSL 인증서 설정 (선택사항)
setup_ssl() {
    if [ ! -z "$2" ]; then
        log_info "🔒 SSL 인증서 설정..."
        DOMAIN_NAME=$2
        
        # Nginx 기본 설정
        sudo tee /etc/nginx/sites-available/${PROJECT_NAME} > /dev/null << EOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

        sudo ln -sf /etc/nginx/sites-available/${PROJECT_NAME} /etc/nginx/sites-enabled/
        sudo nginx -t && sudo systemctl reload nginx
        
        # Let's Encrypt 인증서 발급
        sudo certbot --nginx -d ${DOMAIN_NAME} --non-interactive --agree-tos --email admin@${DOMAIN_NAME}
        
        log_success "SSL 인증서 설정 완료"
    fi
}

# 10. 시스템 초기화
initialize_system() {
    log_info "🔄 시스템 초기화..."
    
    # 데이터베이스 초기화
    sudo -u ${DEPLOY_USER} ${DEPLOY_DIR}/venv/bin/python -c "
import os
os.chdir('${DEPLOY_DIR}')
from app.database.connection import init_database
init_database()
"
    
    # 시스템 설정
    sudo -u ${DEPLOY_USER} ${DEPLOY_DIR}/venv/bin/python ${DEPLOY_DIR}/run_global_system.py --setup
    
    log_success "시스템 초기화 완료"
}

# 11. 서비스 시작
start_services() {
    log_info "🚀 서비스 시작..."
    
    sudo systemctl start ${SERVICE_NAME}
    
    # 서비스 상태 확인
    sleep 5
    if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
        log_success "서비스가 성공적으로 시작되었습니다"
        sudo systemctl status ${SERVICE_NAME} --no-pager
    else
        log_error "서비스 시작 실패"
        sudo journalctl -u ${SERVICE_NAME} --no-pager -n 20
        exit 1
    fi
}

# 12. 헬스체크
health_check() {
    log_info "💊 시스템 헬스체크..."
    
    # 시스템 상태 확인
    sudo -u ${DEPLOY_USER} ${DEPLOY_DIR}/venv/bin/python ${DEPLOY_DIR}/run_global_system.py --status
    
    log_success "헬스체크 완료"
}

# 13. cron 작업 설정 (대안)
setup_cron_jobs() {
    log_info "⏰ Cron 작업 설정 (정확한 시간대 적용)..."
    
    # cron 작업 추가
    sudo -u ${DEPLOY_USER} crontab -l > /tmp/cron_backup 2>/dev/null || true
    
    cat >> /tmp/cron_new << EOF
# 글로벌 주식 분석 시스템 Cron 작업 (향상된 스케줄러 사용)
# 한국 프리마켓 알림 (매일 08:30)
30 8 * * * cd ${DEPLOY_DIR} && ./venv/bin/python scripts/enhanced_global_scheduler.py --manual korean_premarket >> storage/logs/cron.log 2>&1

# 한국 시장 분석 (매일 16:00)
0 16 * * * cd ${DEPLOY_DIR} && ./venv/bin/python scripts/enhanced_global_scheduler.py --manual korean_analysis >> storage/logs/cron.log 2>&1

# 미국 프리마켓 알림 (서머타임 자동 감지, 매일 16:30 또는 17:30)
30 16 * * * cd ${DEPLOY_DIR} && ./venv/bin/python scripts/enhanced_global_scheduler.py --manual us_premarket >> storage/logs/cron.log 2>&1

# 미국 정규장 알림 (서머타임 자동 감지, 매일 22:00 또는 23:00)
0 22 * * * cd ${DEPLOY_DIR} && ./venv/bin/python scripts/enhanced_global_scheduler.py --manual us_regular >> storage/logs/cron.log 2>&1

# 주간 종합 분석 (토요일 12:00)
0 12 * * 6 cd ${DEPLOY_DIR} && ./venv/bin/python scripts/enhanced_global_scheduler.py --manual weekly_analysis >> storage/logs/cron.log 2>&1

# 시스템 헬스체크 (매시간)
0 * * * * cd ${DEPLOY_DIR} && ./venv/bin/python scripts/enhanced_global_scheduler.py --manual health_check >> storage/logs/cron.log 2>&1

# 스케줄 업데이트 (매일 자정 - 서머타임 변경 감지)
0 0 * * * cd ${DEPLOY_DIR} && ./venv/bin/python scripts/enhanced_global_scheduler.py --manual update_schedules >> storage/logs/cron.log 2>&1
EOF

    sudo -u ${DEPLOY_USER} crontab /tmp/cron_new
    rm -f /tmp/cron_new /tmp/cron_backup
    
    log_success "Cron 작업 설정 완료"
}

# 메인 실행 함수
main() {
    log_info "🌍 글로벌 주식 분석 시스템 프로덕션 배포 시작"
    
    # Root 권한 확인
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        log_error "이 스크립트는 sudo 권한이 필요합니다"
        exit 1
    fi
    
    # 배포 단계 실행
    create_system_user
    install_dependencies
    setup_database
    deploy_application
    setup_environment
    setup_systemd_service
    setup_log_rotation
    setup_firewall
    setup_ssl "$@"
    initialize_system
    setup_cron_jobs
    start_services
    health_check
    
    log_success "🎉 프로덕션 배포 완료!"
    
    echo ""
    echo "==============================================="
    echo "📋 배포 후 할 일:"
    echo "==============================================="
    echo "1. ${DEPLOY_DIR}/.env 파일의 API 키들을 실제 값으로 업데이트"
    echo "2. 서비스 재시작: sudo systemctl restart ${SERVICE_NAME}"
    echo "3. 로그 확인: sudo journalctl -u ${SERVICE_NAME} -f"
    echo "4. 시스템 상태: sudo -u ${DEPLOY_USER} ${DEPLOY_DIR}/venv/bin/python ${DEPLOY_DIR}/run_global_system.py --status"
    echo ""
    echo "🔗 유용한 명령어:"
    echo "- 서비스 상태: sudo systemctl status ${SERVICE_NAME}"
    echo "- 로그 확인: tail -f ${DEPLOY_DIR}/storage/logs/global_system.log"
    echo "- 수동 실행: sudo -u ${DEPLOY_USER} ${DEPLOY_DIR}/venv/bin/python ${DEPLOY_DIR}/run_global_system.py --full"
    echo ""
}

# 스크립트 실행
main "$@"
