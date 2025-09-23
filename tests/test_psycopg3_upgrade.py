#!/usr/bin/env python3
"""
psycopg3 업그레이드 테스트
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set PYTHONPATH
os.environ['PYTHONPATH'] = str(project_root)

def test_database_connection():
    """데이터베이스 연결 테스트"""
    print("🔍 psycopg3 데이터베이스 연결 테스트:")
    
    try:
        from app.database.connection import get_db_session, engine
        from app.config.settings import settings
        from sqlalchemy import text
        
        print(f"   📊 데이터베이스 URL: {settings.database_url}")
        
        # SQLAlchemy 엔진 테스트
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"   ✅ PostgreSQL 연결 성공: {version}")
        
        # 세션 테스트
        with get_db_session() as session:
            result = session.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"   ✅ 세션 연결 성공: {db_name}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 데이터베이스 연결 실패: {e}")
        return False

def test_model_import():
    """모델 import 테스트"""
    print("\n🔍 모델 import 테스트:")
    
    try:
        from app.models.entities import StockMaster, StockDailyPrice, MarketRegion
        print("   ✅ 모델 import 성공")
        
        # 간단한 쿼리 테스트
        from app.database.connection import get_db_session
        
        with get_db_session() as session:
            count = session.query(StockMaster).count()
            print(f"   ✅ StockMaster 테이블 조회 성공: {count}개 레코드")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 모델 테스트 실패: {e}")
        return False

def test_package_version():
    """패키지 버전 확인"""
    print("\n🔍 패키지 버전 확인:")
    
    try:
        import psycopg
        print(f"   ✅ psycopg 버전: {psycopg.__version__}")
        
        import sqlalchemy
        print(f"   ✅ SQLAlchemy 버전: {sqlalchemy.__version__}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 패키지 버전 확인 실패: {e}")
        return False

if __name__ == "__main__":
    print("🧪 psycopg3 업그레이드 테스트 시작...")
    
    success = True
    
    # 1. 패키지 버전 확인
    success &= test_package_version()
    
    # 2. 데이터베이스 연결 테스트
    success &= test_database_connection()
    
    # 3. 모델 테스트
    success &= test_model_import()
    
    print(f"\n{'='*50}")
    if success:
        print("✅ psycopg3 업그레이드 성공!")
        print("🎉 모든 데이터베이스 기능 정상 작동")
    else:
        print("❌ psycopg3 업그레이드 실패")
        print("🔧 추가 조치 필요")
    
    print("🧪 테스트 완료")
    sys.exit(0 if success else 1)