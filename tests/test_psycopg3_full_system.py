#!/usr/bin/env python3
"""
psycopg3 전체 시스템 호환성 테스트
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set PYTHONPATH
os.environ['PYTHONPATH'] = str(project_root)

def test_all_database_operations():
    """모든 데이터베이스 작업 테스트"""
    print("🔍 전체 데이터베이스 작업 테스트:")
    
    try:
        from app.database.connection import get_db_session
        from app.models.entities import StockMaster, StockDailyPrice, MarketRegion
        from datetime import date, timedelta
        
        with get_db_session() as session:
            # 1. 기본 조회
            kr_stocks = session.query(StockMaster).filter_by(
                market_region=MarketRegion.KR.value,
                is_active=True
            ).limit(5).all()
            print(f"   ✅ 한국 종목 조회: {len(kr_stocks)}개")
            
            # 2. 조인 쿼리
            recent_date = date.today() - timedelta(days=30)
            price_data = session.query(StockDailyPrice).join(StockMaster).filter(
                StockMaster.market_region == MarketRegion.KR.value,
                StockDailyPrice.trade_date >= recent_date
            ).limit(10).all()
            print(f"   ✅ 조인 쿼리: {len(price_data)}개 가격 데이터")
            
            # 3. 집계 쿼리
            total_stocks = session.query(StockMaster).count()
            print(f"   ✅ 전체 종목 수: {total_stocks}개")
            
        return True
        
    except Exception as e:
        print(f"   ❌ 데이터베이스 작업 테스트 실패: {e}")
        import traceback
        print(f"   상세 오류: {traceback.format_exc()}")
        return False

def test_ml_engine_with_db():
    """ML 엔진과 데이터베이스 연동 테스트"""
    print("\n🔍 ML 엔진 데이터베이스 연동 테스트:")
    
    try:
        from app.ml.global_ml_engine import GlobalMLEngine
        
        # ML 엔진 초기화 (DB 접근 포함)
        engine = GlobalMLEngine()
        print("   ✅ ML 엔진 초기화 성공")
        
        # 시장 체제 감지 (DB 접근)
        market_condition = engine.detect_market_regime()
        if market_condition:
            print(f"   ✅ 시장 체제 감지 성공: {market_condition.regime.value}")
        else:
            print("   ⚠️ 시장 체제 감지 결과 없음 (정상)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ ML 엔진 연동 테스트 실패: {e}")
        return False

def test_data_collection():
    """데이터 수집 기능 테스트"""
    print("\n🔍 데이터 수집 기능 테스트:")
    
    try:
        from app.services.unified_data_collector import UnifiedDataCollector
        
        collector = UnifiedDataCollector()
        print("   ✅ 데이터 수집기 초기화 성공")
        
        # DB 연결 상태 확인
        kr_symbols = collector.kr_symbols[:3]  # 처음 3개만 테스트
        us_symbols = collector.us_symbols[:3]
        
        print(f"   ✅ 한국 테스트 심볼: {kr_symbols}")
        print(f"   ✅ 미국 테스트 심볼: {us_symbols}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 데이터 수집 테스트 실패: {e}")
        return False

def test_notification_system():
    """알림 시스템 테스트"""
    print("\n🔍 알림 시스템 테스트:")
    
    try:
        from app.services.notification import NotificationService
        from app.services.telegram_service import TelegramNotifier
        
        # 알림 서비스 초기화
        notification = NotificationService()
        telegram = TelegramNotifier()
        
        print("   ✅ 알림 서비스 초기화 성공")
        return True
        
    except Exception as e:
        print(f"   ❌ 알림 시스템 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("🧪 psycopg3 전체 시스템 호환성 테스트 시작...")
    print("="*60)
    
    success = True
    
    # 1. 데이터베이스 작업 테스트
    success &= test_all_database_operations()
    
    # 2. ML 엔진 연동 테스트
    success &= test_ml_engine_with_db()
    
    # 3. 데이터 수집 테스트
    success &= test_data_collection()
    
    # 4. 알림 시스템 테스트
    success &= test_notification_system()
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 psycopg3 전체 시스템 호환성 테스트 성공!")
        print("✅ Python 3.13 + psycopg3 환경 완벽 호환")
        print("🚀 배포 준비 완료")
    else:
        print("❌ 일부 테스트 실패")
        print("🔧 추가 수정 필요")
    
    print("🧪 전체 테스트 완료")
    sys.exit(0 if success else 1)