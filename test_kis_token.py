#!/usr/bin/env python3
"""
KIS 토큰 갱신 기능 테스트
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.kis_api import KISAPIClient
from app.database.redis_client import redis_client

def test_kis_token_management():
    """KIS 토큰 관리 기능 테스트"""
    print("🔑 KIS 토큰 관리 기능 테스트")
    print("="*50)
    
    try:
        # 1. KIS API 클라이언트 초기화
        print("1️⃣ KIS API 클라이언트 초기화...")
        kis_client = KISAPIClient()
        
        # 2. 기존 토큰 확인
        print("2️⃣ 기존 토큰 확인...")
        cached_token = redis_client.get("kis:access_token")
        if cached_token:
            print(f"   ✅ 기존 토큰 발견: {cached_token[:10]}...")
        else:
            print("   ℹ️ 기존 토큰 없음")
        
        # 3. 토큰 TTL 확인
        ttl = redis_client.client.ttl("kis:access_token")
        if ttl > 0:
            print(f"   ⏰ 토큰 만료까지: {ttl}초 ({ttl/3600:.1f}시간)")
        elif ttl == -1:
            print("   ⚠️ 토큰 만료 시간 설정 안됨")
        else:
            print("   ❌ 토큰 없음 또는 만료됨")
        
        # 4. 토큰 가져오기 (캐시된 토큰 또는 새 토큰)
        print("3️⃣ 토큰 가져오기...")
        token = kis_client.get_access_token()
        
        if token:
            print(f"   ✅ 토큰 획득: {token[:10]}...")
            
            # TTL 재확인
            new_ttl = redis_client.client.ttl("kis:access_token")
            print(f"   ⏰ 새 TTL: {new_ttl}초 ({new_ttl/3600:.1f}시간)")
        else:
            print("   ❌ 토큰 획득 실패")
            return False
        
        # 5. 일일 갱신 기능 테스트
        print("4️⃣ 일일 갱신 기능 테스트...")
        refresh_success = kis_client.refresh_token_daily()
        
        if refresh_success:
            print("   ✅ 일일 갱신 성공")
            
            # 갱신 후 새 토큰 확인
            new_token = redis_client.get("kis:access_token")
            print(f"   🔄 갱신된 토큰: {new_token[:10]}...")
            
            # TTL 확인
            final_ttl = redis_client.client.ttl("kis:access_token")
            print(f"   ⏰ 갱신 후 TTL: {final_ttl}초 ({final_ttl/3600:.1f}시간)")
        else:
            print("   ❌ 일일 갱신 실패")
            return False
        
        print("\n✅ KIS 토큰 관리 기능 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_kis_token_management()
    sys.exit(0 if success else 1)