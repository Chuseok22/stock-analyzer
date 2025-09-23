#!/usr/bin/env python3
"""
통합 데이터 수집기 테스트
"""
import sys
from pathlib import Path

# app 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

def test_unified_data_collector():
    """통합 데이터 수집기 기본 기능 테스트"""
    print("🚀 통합 데이터 수집기 테스트")
    print("="*50)
    
    try:
        # 1. 임포트 테스트
        print("1️⃣ 모듈 임포트...")
        from app.services.unified_data_collector import UnifiedDataCollector
        print("   ✅ 임포트 성공")
        
        # 2. 초기화 테스트
        print("2️⃣ 데이터 수집기 초기화...")
        collector = UnifiedDataCollector()
        print("   ✅ 초기화 성공")
        
        # 3. 속성 확인
        print("3️⃣ 속성 확인...")
        assert hasattr(collector, 'kr_symbols'), "한국 종목 리스트 속성 없음"
        assert hasattr(collector, 'us_symbols'), "미국 종목 리스트 속성 없음"
        assert len(collector.kr_symbols) > 0, "한국 종목 리스트 비어있음"
        assert len(collector.us_symbols) > 0, "미국 종목 리스트 비어있음"
        print(f"   ✅ 한국 종목: {len(collector.kr_symbols)}개")
        print(f"   ✅ 미국 종목: {len(collector.us_symbols)}개")
        
        # 4. 메소드 확인
        print("4️⃣ 메소드 확인...")
        methods = ['collect_korean_daily_data', 'collect_us_daily_data', 'collect_historical_data']
        for method in methods:
            assert hasattr(collector, method), f"{method} 메소드 없음"
        print("   ✅ 필수 메소드 존재 확인")
        
        print("\n✅ 통합 데이터 수집기 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_unified_data_collector()
    sys.exit(0 if success else 1)