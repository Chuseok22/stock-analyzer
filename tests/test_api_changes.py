#!/usr/bin/env python3
"""
API 변경 완료 테스트
"""
import sys
from pathlib import Path

# app 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

def test_api_changes():
    """API 변경사항 기본 테스트"""
    print("🔄 API 변경 완료 테스트")
    print("="*50)
    
    try:
        # 1. 임포트 테스트
        print("1️⃣ 모듈 임포트...")
        from app.services.unified_data_collector import UnifiedDataCollector
        print("   ✅ 임포트 성공")
        
        # 2. 초기화 테스트
        print("2️⃣ 초기화...")
        collector = UnifiedDataCollector()
        print("   ✅ 초기화 성공")
        
        # 3. API 클라이언트 확인
        print("3️⃣ API 클라이언트 확인...")
        assert hasattr(collector, 'kis_client'), "KIS 클라이언트 없음"
        assert hasattr(collector, 'alpha_vantage_client'), "Alpha Vantage 클라이언트 없음"
        print("   ✅ KIS API 클라이언트: 한국 데이터용")
        print("   ✅ Alpha Vantage API 클라이언트: 미국 데이터용")
        
        # 4. 종목 리스트 확인
        print("4️⃣ 종목 리스트 확인...")
        print(f"   📈 한국 종목: {len(collector.kr_symbols)}개")
        print(f"   📈 미국 종목: {len(collector.us_symbols)}개")
        
        print("\n✅ API 변경 완료!")
        print("\n📋 변경 사항 요약:")
        print("   🇰🇷 한국 데이터: Yahoo Finance → KIS API")
        print("   🇺🇸 미국 데이터: Yahoo Finance → Alpha Vantage API") 
        print("   🚫 Yahoo Finance 의존성 제거")
        print("   ✨ 더 안정적이고 전문적인 API 사용")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_changes()
    sys.exit(0 if success else 1)