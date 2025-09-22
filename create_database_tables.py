#!/usr/bin/env python3
"""
데이터베이스 테이블 생성 및 초기화
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import engine, Base
from app.models.entities import *  # 모든 모델 임포트


def create_database_tables():
    """데이터베이스 테이블 생성"""
    print("🗄️ 데이터베이스 테이블 생성 중...")
    
    try:
        # 모든 테이블 생성
        Base.metadata.create_all(bind=engine)
        print("✅ 모든 테이블이 성공적으로 생성되었습니다")
        
        # 생성된 테이블 목록 확인
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n📋 생성된 테이블 목록 ({len(tables)}개):")
        for table in sorted(tables):
            print(f"   - {table}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테이블 생성 중 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 데이터베이스 초기화\n")
    
    success = create_database_tables()
    
    if success:
        print("\n🎉 데이터베이스 초기화 완료!")
        print("이제 setup_stocks_and_collect_data.py를 실행할 수 있습니다.")
    else:
        print("\n❌ 데이터베이스 초기화 실패")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
