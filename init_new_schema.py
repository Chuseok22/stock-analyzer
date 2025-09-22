#!/usr/bin/env python3
"""
새로운 데이터베이스 스키마로 테이블 생성 및 데이터 초기화
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session, engine
from app.models.entities import (
    StockMaster, StockDailyPrice, StockTechnicalIndicator, 
    StockFundamentalData, StockMarketData, TradingUniverse, 
    TradingUniverseItem, StockRecommendation
)


def create_all_tables():
    """새로운 스키마로 모든 테이블 생성"""
    print("🗃️  새로운 데이터베이스 스키마로 테이블 생성 중...")
    
    try:
        # Import all models to ensure they're registered
        from app.models.entities import Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ 모든 테이블이 성공적으로 생성되었습니다!")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"📋 생성된 테이블 목록 ({len(tables)}개):")
        for table in sorted(tables):
            print(f"   - {table}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테이블 생성 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def initialize_default_data():
    """기본 데이터 초기화"""
    print("\n📊 기본 데이터 초기화 중...")
    
    try:
        with get_db_session() as db:
            # 기본 한국 주식 유니버스 생성
            existing_universe = db.query(TradingUniverse).filter(
                TradingUniverse.universe_name == "Korean Major Stocks",
                TradingUniverse.market_region == "KR"
            ).first()
            
            if not existing_universe:
                from datetime import date
                default_universe = TradingUniverse(
                    universe_name="Korean Major Stocks",
                    universe_description="Top Korean stocks for ML training and recommendation",
                    market_region="KR",
                    creation_date=date.today(),
                    rebalance_frequency="DAILY",
                    created_by="System"
                )
                db.add(default_universe)
                db.commit()
                print("✅ 기본 한국 유니버스 생성 완료")
            else:
                print("✅ 기본 한국 유니버스 이미 존재")
        
        return True
        
    except Exception as e:
        print(f"❌ 기본 데이터 초기화 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_schema():
    """스키마 구조 확인"""
    print("\n🔍 데이터베이스 스키마 확인 중...")
    
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        # 각 테이블의 컬럼 정보 확인
        tables = [
            'stock_master', 'stock_daily_price', 'stock_technical_indicator',
            'stock_fundamental_data', 'stock_market_data', 'trading_universe',
            'trading_universe_item', 'stock_recommendation'
        ]
        
        for table_name in tables:
            if table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                indexes = inspector.get_indexes(table_name)
                
                print(f"\n📋 {table_name}:")
                print(f"   컬럼 수: {len(columns)}개")
                print(f"   인덱스 수: {len(indexes)}개")
                
                # 주요 컬럼 정보
                key_columns = [col for col in columns if 'id' in col['name'] or col['primary_key']]
                if key_columns:
                    print(f"   주요 컬럼: {', '.join([col['name'] for col in key_columns])}")
            else:
                print(f"❌ {table_name} 테이블이 존재하지 않습니다!")
        
        return True
        
    except Exception as e:
        print(f"❌ 스키마 확인 중 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 새로운 데이터베이스 스키마 초기화")
    print("="*60)
    print("📋 작업 순서:")
    print("1. 모든 테이블 생성")
    print("2. 기본 데이터 초기화")
    print("3. 스키마 구조 확인")
    print("="*60)
    
    # 1단계: 테이블 생성
    print("\n1️⃣ 테이블 생성")
    if not create_all_tables():
        print("\n❌ 테이블 생성 실패. 프로세스를 중단합니다.")
        return False
    
    # 2단계: 기본 데이터 초기화
    print("\n2️⃣ 기본 데이터 초기화")
    if not initialize_default_data():
        print("\n❌ 기본 데이터 초기화 실패. 프로세스를 중단합니다.")
        return False
    
    # 3단계: 스키마 확인
    print("\n3️⃣ 스키마 구조 확인")
    if not verify_schema():
        print("\n⚠️ 스키마 확인에 문제가 있습니다.")
    
    # 성공 메시지
    print("\n" + "="*60)
    print("🎉 새로운 데이터베이스 스키마 초기화 완료!")
    print("="*60)
    print("✅ 모든 테이블 생성 완료")
    print("✅ 기본 데이터 초기화 완료")
    print("✅ 스키마 구조 확인 완료")
    print("\n🚀 이제 다음 단계를 진행할 수 있습니다:")
    print("   1. 주식 마스터 데이터 수집")
    print("   2. 일일 주가 데이터 수집")
    print("   3. 기술적 지표 계산")
    print("   4. 펀더멘털 데이터 수집")
    print("   5. ML 모델 학습")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
