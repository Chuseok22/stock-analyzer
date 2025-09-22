#!/usr/bin/env python3
"""
KIS 토큰 발급 및 Redis 저장 (한 번만 실행)
"""
import sys
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.kis_api import KISAPIClient
from app.database.redis_client import redis_client
from app.config.settings import settings


def initialize_kis_token():
    """KIS 토큰을 한 번만 발급받아 Redis에 저장"""
    print("🔑 KIS 토큰 초기화 시작...\n")
    
    try:
        # Redis 연결 확인
        if not redis_client.client.ping():
            print("❌ Redis 연결 실패")
            return False
        print("✅ Redis 연결 성공")
        
        # 기존 토큰 확인
        existing_token = redis_client.get("kis:access_token")
        if existing_token:
            ttl = redis_client.get_ttl("kis:access_token")
            print(f"⚠️ 기존 토큰이 존재합니다 (TTL: {ttl}초)")
            
            response = input("기존 토큰을 삭제하고 새로 발급받으시겠습니까? (y/N): ")
            if response.lower() != 'y':
                print("✅ 기존 토큰을 유지합니다")
                return True
            else:
                redis_client.delete("kis:access_token")
                print("🗑️ 기존 토큰 삭제 완료")
        
        # KIS API 클라이언트 생성
        kis_client = KISAPIClient()
        print("✅ KIS API 클라이언트 초기화")
        
        # 토큰 발급 (한 번만!)
        print("📞 KIS API에서 토큰 발급 중... (한 번만 실행)")
        token = kis_client.get_access_token()
        
        if token:
            print(f"✅ 토큰 발급 성공: {token[:20]}...")
            
            # Redis에서 토큰 정보 확인
            cached_token = redis_client.get("kis:access_token")
            if cached_token:
                ttl = redis_client.get_ttl("kis:access_token")
                print(f"✅ Redis에 토큰 저장 완료")
                print(f"   토큰: {cached_token[:20]}...")
                print(f"   TTL: {ttl}초 ({ttl/3600:.1f}시간)")
                print(f"   만료 예정: {datetime.now().timestamp() + ttl}")
                
                # Discord 알림 전송
                try:
                    from app.services.notification import NotificationService
                    notification = NotificationService()
                    message = (
                        f"🔑 **KIS API 토큰 초기화 완료**\n\n"
                        f"📅 발급 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"⏱️ 유효 시간: {ttl/3600:.1f}시간\n"
                        f"🔄 자동 갱신: 매일 자정 00:00\n"
                        f"📊 다음 단계: 데이터 수집 및 모델 학습"
                    )
                    notification._send_simple_slack_message(message)
                    print("📱 Discord 알림 전송 완료")
                except Exception as e:
                    print(f"⚠️ Discord 알림 전송 실패: {e}")
                
                return True
            else:
                print("❌ Redis에 토큰 저장 실패")
                return False
        else:
            print("❌ 토큰 발급 실패")
            return False
            
    except Exception as e:
        print(f"❌ 토큰 초기화 중 오류 발생: {e}")
        return False


def verify_token_status():
    """토큰 상태 확인"""
    print("\n🔍 토큰 상태 확인...")
    
    try:
        # Redis에서 토큰 조회
        token = redis_client.get("kis:access_token")
        if token:
            ttl = redis_client.get_ttl("kis:access_token")
            print(f"✅ 토큰 존재: {token[:20]}...")
            print(f"✅ 남은 시간: {ttl}초 ({ttl/3600:.1f}시간)")
            
            # KIS API 클라이언트로 토큰 확인
            kis_client = KISAPIClient()
            cached_token = kis_client.get_access_token()  # 캐시된 토큰 사용
            
            if cached_token == token:
                print("✅ 토큰 일치 확인")
                return True
            else:
                print("❌ 토큰 불일치")
                return False
        else:
            print("❌ Redis에 토큰 없음")
            return False
            
    except Exception as e:
        print(f"❌ 토큰 상태 확인 중 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 KIS 토큰 초기화 및 데이터 수집 준비\n")
    print("="*50)
    print("📋 작업 계획:")
    print("1. KIS 토큰 한 번만 발급 및 Redis 저장")
    print("2. 토큰 상태 검증")
    print("3. 다음 단계: 데이터 수집 준비")
    print("="*50)
    
    # 1단계: 토큰 초기화
    print("\n1️⃣ KIS 토큰 초기화")
    token_success = initialize_kis_token()
    
    if not token_success:
        print("\n❌ 토큰 초기화 실패. 프로세스를 중단합니다.")
        return False
    
    # 2단계: 토큰 상태 확인
    print("\n2️⃣ 토큰 상태 검증")
    verify_success = verify_token_status()
    
    if not verify_success:
        print("\n❌ 토큰 검증 실패. 프로세스를 중단합니다.")
        return False
    
    # 성공 요약
    print("\n" + "="*50)
    print("🎉 KIS 토큰 초기화 완료!")
    print("="*50)
    print("✅ KIS API 토큰 발급 및 Redis 저장 완료")
    print("✅ 토큰 상태 검증 완료")
    print("🔄 토큰은 매일 자정에 자동 갱신됩니다")
    print("\n📊 다음 단계:")
    print("   1. 주요 종목 리스트 확인")
    print("   2. 주가 데이터 수집")
    print("   3. 기술적 지표 계산")
    print("   4. ML 모델 학습")
    print("   5. 추천 시스템 활성화")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
