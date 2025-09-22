#!/usr/bin/env python3
"""
KIS API 데이터 구조 확인용 테스트 스크립트
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.kis_api import KISAPIClient
from app.database.redis_client import redis_client


def test_kis_api_structure():
    """KIS API 데이터 구조 확인"""
    print("🔍 KIS API 데이터 구조 확인")
    
    try:
        # KIS 토큰 확인
        token = redis_client.get("kis:access_token")
        if not token:
            print("❌ KIS 토큰이 없습니다!")
            return False
        
        print(f"✅ KIS 토큰 확인: {token[:20]}...")
        
        # KIS API 클라이언트 초기화
        kis_client = KISAPIClient()
        
        # 삼성전자 데이터로 테스트
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=5)
        
        print(f"📅 테스트 기간: {start_date} ~ {end_date}")
        print("🔄 삼성전자 (005930) 데이터 가져오는 중...")
        
        price_data = kis_client.get_stock_price_daily(
            stock_code="005930",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d")
        )
        
        print(f"📊 받은 데이터 개수: {len(price_data)}")
        
        if price_data:
            print("\n📋 첫 번째 데이터 구조:")
            first_data = price_data[0]
            for key, value in first_data.items():
                print(f"   {key}: {value}")
            
            print("\n🔑 사용 가능한 모든 필드:")
            all_keys = set()
            for data in price_data:
                all_keys.update(data.keys())
            
            for key in sorted(all_keys):
                print(f"   - {key}")
                
            return True
        else:
            print("❌ 데이터를 받지 못했습니다!")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🚀 KIS API 데이터 구조 확인 테스트")
    print("="*50)
    
    success = test_kis_api_structure()
    
    print("\n" + "="*50)
    if success:
        print("✅ 테스트 완료")
    else:
        print("❌ 테스트 실패")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
