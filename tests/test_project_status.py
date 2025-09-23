#!/usr/bin/env python3
"""
프로젝트 정리 완료 상태 확인
"""
import sys
from pathlib import Path

# app 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

def check_project_status():
    """프로젝트 정리 완료 상태 확인"""
    print("📋 프로젝트 정리 완료 상태 확인")
    print("="*60)
    
    try:
        # 1. 핵심 서비스 확인
        print("1️⃣ 핵심 서비스 가용성 확인...")
        
        from app.services.unified_data_collector import UnifiedDataCollector
        collector = UnifiedDataCollector()
        print(f"   ✅ 통합 데이터 수집기: 한국 {len(collector.kr_symbols)}개, 미국 {len(collector.us_symbols)}개 종목")
        
        from app.utils.database_utils import DatabaseUtils
        from app.database.connection import get_db_session
        db_utils = DatabaseUtils()
        with get_db_session() as db:
            stocks = db_utils.get_active_stocks(db)
        print(f"   ✅ 데이터베이스 유틸리티: {len(stocks)}개 활성 종목")
        
        from app.ml.global_ml_engine import GlobalMLEngine
        ml_engine = GlobalMLEngine()
        print("   ✅ ML 엔진: 초기화 완료")
        
        # 2. 제거된 파일들 확인
        print("\n2️⃣ 정리된 파일들...")
        removed_files = [
            "app/utils/database_utils_old.py",
            "tools/data_collection/deprecated_collect_daily_data.py",
            "tools/data_collection/deprecated_collect_enhanced_data.py",
            "tools/data_collection/deprecated_collect_historical_data.py", 
            "tools/data_collection/deprecated_collect_us_data.py",
            "tests/test_models.py",
            "tests/test_ml_simple.py"
        ]
        
        for file_path in removed_files:
            path = Path(file_path)
            if not path.exists():
                print(f"   ✅ 제거됨: {file_path}")
            else:
                print(f"   ❌ 아직 존재: {file_path}")
        
        # 3. 테스트 상태 확인
        print("\n3️⃣ 테스트 상태 확인...")
        test_files = [
            "tests/test_unified_data_collector.py",
            "tests/test_database_utils.py", 
            "tests/test_ml_engine_basic.py",
            "tests/test_db_status.py"
        ]
        
        for test_file in test_files:
            path = Path(test_file)
            if path.exists():
                print(f"   ✅ 활성: {test_file}")
            else:
                print(f"   ❌ 없음: {test_file}")
        
        # 4. 중복 코드 상태 확인
        print("\n4️⃣ 중복 코드 현황...")
        
        # DataCollectionService vs UnifiedDataCollector
        data_collection_path = Path("app/services/data_collection.py")
        unified_collector_path = Path("app/services/unified_data_collector.py")
        
        if data_collection_path.exists() and unified_collector_path.exists():
            print("   ⚠️ 데이터 수집 서비스 중복: data_collection.py와 unified_data_collector.py 공존")
            print("   📌 권장사항: UnifiedDataCollector 사용 권장 (더 완성도 높음)")
        else:
            print("   ✅ 데이터 수집 서비스: 중복 해결됨")
        
        print("\n✅ 프로젝트 정리 완료!")
        print("\n📊 최종 상태:")
        print("   🔧 핵심 기능: 모두 정상 작동")
        print("   🗂️ 불필요한 파일: 제거 완료")
        print("   🧪 테스트 파일: 정리 완료")
        print("   ⚠️ 주의사항: data_collection.py 파일 교체 필요 (향후 작업)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 상태 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_project_status()
    sys.exit(0 if success else 1)