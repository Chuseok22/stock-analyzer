#!/usr/bin/env python3
"""
데이터베이스 유틸리티 테스트
"""
import sys
from pathlib import Path

# app 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

def test_database_utils():
    """데이터베이스 유틸리티 기본 기능 테스트"""
    print("🗄️ 데이터베이스 유틸리티 테스트")
    print("="*50)
    
    try:
        # 1. 임포트 테스트
        print("1️⃣ 모듈 임포트...")
        from app.utils.database_utils import DatabaseUtils
        from app.database.connection import get_db_session
        print("   ✅ 임포트 성공")
        
        # 2. 초기화 테스트
        print("2️⃣ 데이터베이스 유틸리티 초기화...")
        db_utils = DatabaseUtils()
        print("   ✅ 초기화 성공")
        
        # 3. 데이터베이스 연결 테스트
        print("3️⃣ 데이터베이스 연결 테스트...")
        with get_db_session() as db:
            stocks = db_utils.get_active_stocks(db)
            print(f"   ✅ 활성 종목 조회: {len(stocks)}개")
            
            if len(stocks) > 0:
                # 첫 번째 종목으로 상세 테스트
                first_stock = stocks[0]
                stock_by_code = db_utils.get_stock_by_code(db, first_stock.stock_code)
                assert stock_by_code is not None, "종목 조회 실패"
                print(f"   ✅ 종목 조회: {stock_by_code.stock_code} - {stock_by_code.stock_name}")
        
        # 4. 메소드 확인
        print("4️⃣ 메소드 확인...")
        methods = ['get_active_stocks', 'get_stock_by_code', 'save_price_data']
        for method in methods:
            assert hasattr(db_utils, method), f"{method} 메소드 없음"
        print("   ✅ 필수 메소드 존재 확인")
        
        print("\n✅ 데이터베이스 유틸리티 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_utils()
    sys.exit(0 if success else 1)