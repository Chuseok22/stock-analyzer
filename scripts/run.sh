#!/bin/bash
# ML 주식 추천 시스템 실행 스크립트

echo "🚀 AI 주식 추천 시스템"
echo "======================="

if [ $# -eq 0 ]; then
    echo "사용법:"
    echo "  ./run.sh analyze      # 즉시 ML 분석 실행"
    echo "  ./run.sh schedule     # 자동화 스케줄러 시작"
    echo "  ./run.sh backtest [일수]  # 백테스팅 (기본: 30일)"
    echo "  ./run.sh collect      # 데이터 수집"
    echo "  ./run.sh status       # 시스템 상태 확인"
    echo "  ./run.sh logs         # 로그 확인"
    exit 1
fi

# 프로젝트 루트로 이동
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT"

# PYTHONPATH 설정
export PYTHONPATH="$(pwd):$PYTHONPATH"

case "$1" in
    "analyze")
        echo "🤖 ML 분석 시작..."
        python scripts/production_ml_system.py
        ;;
    
    "schedule")
        echo "📅 자동화 스케줄러 시작..."
        echo "   평일 16:00, 토요일 09:00에 자동 실행됩니다."
        echo "   Ctrl+C로 중단할 수 있습니다."
        python scripts/daily_trading_system.py schedule
        ;;
    
    "backtest")
        DAYS=${2:-30}
        echo "📊 백테스팅 시작 (최근 ${DAYS}일)..."
        python scripts/backtesting_system.py $DAYS
        ;;
    
    "collect")
        echo "📊 데이터 수집 시작..."
        python scripts/collect_enhanced_data.py
        ;;
    
    "status")
        echo "📊 시스템 상태 확인..."
        
        # Redis 연결 확인
        echo "🔍 Redis 연결..."
        python -c "
import sys
sys.path.append('app')
try:
    from app.database.redis_client import redis_client
    redis_client.ping()
    print('✅ Redis 연결 정상')
except Exception as e:
    print(f'❌ Redis 연결 오류: {e}')
"
        
        # 데이터베이스 연결 확인
        echo "🔍 데이터베이스 연결..."
        python -c "
import sys
sys.path.append('app')
try:
    from app.database.connection import get_db_session
    with get_db_session() as db:
        result = db.execute('SELECT 1')
        print('✅ PostgreSQL 연결 정상')
except Exception as e:
    print(f'❌ PostgreSQL 연결 오류: {e}')
"
        
        # 최신 추천 확인
        echo "🔍 최신 추천 확인..."
        python -c "
import sys
sys.path.append('app')
try:
    from app.database.connection import get_db_session
    from sqlalchemy import text
    with get_db_session() as db:
        result = db.execute(text('SELECT COUNT(*) FROM stock_recommendation WHERE recommendation_date = CURRENT_DATE')).scalar()
        print(f'📈 오늘 추천: {result}개')
except Exception as e:
    print(f'❌ 추천 조회 오류: {e}')
"
        ;;
    
    "logs")
        echo "📄 최신 로그 확인..."
        LOG_FILE="storage/logs/daily_trading_system.log"
        if [ -f "$LOG_FILE" ]; then
            echo "📄 $LOG_FILE (최근 50줄):"
            echo "----------------------------------------"
            tail -50 "$LOG_FILE"
        else
            echo "❌ 로그 파일을 찾을 수 없습니다: $LOG_FILE"
        fi
        ;;
    
    *)
        echo "❌ 알 수 없는 명령어: $1"
        echo "사용 가능한 명령어: analyze, schedule, backtest, collect, status, logs"
        exit 1
        ;;
esac
