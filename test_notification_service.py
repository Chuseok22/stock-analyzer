#!/usr/bin/env python3
"""
실제 NotificationService를 통한 Discord 알림 테스트
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.notification import NotificationService
from app.config.settings import settings
from datetime import datetime


def test_notification_service():
    """NotificationService를 통한 Discord 알림 테스트"""
    print("📢 NotificationService Discord 알림 테스트 시작...\n")
    
    try:
        # NotificationService 초기화
        notification_service = NotificationService()
        print("✅ NotificationService 초기화 완료")
        
        # Discord 설정 확인
        print(f"✅ Discord 활성화: {settings.discord_enabled}")
        
        # 간단한 Discord 메시지 테스트
        test_message = (
            f"🔔 **Stock Analyzer 시스템 알림**\n\n"
            f"📅 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🎯 상태: Redis & KIS 통합 완료\n"
            f"⚙️ 스케줄러: 6개 작업 활성화\n"
            f"🔄 다음 토큰 갱신: 매일 자정 00:00"
        )
        
        print("📤 NotificationService를 통한 Discord 메시지 전송 중...")
        
        # _send_simple_slack_message 메서드를 사용 (Discord도 지원)
        success = notification_service._send_simple_slack_message(test_message)
        
        if success:
            print("✅ NotificationService Discord 알림 전송 성공!")
            return True
        else:
            print("❌ NotificationService Discord 알림 전송 실패")
            return False
            
    except Exception as e:
        print(f"❌ NotificationService 테스트 중 오류: {e}")
        return False


def test_admin_notification():
    """관리자 알림 테스트 (KIS 토큰 갱신 성공 시뮬레이션)"""
    print("\n🔑 관리자 알림 테스트 (KIS 토큰 관련)...")
    
    try:
        notification_service = NotificationService()
        
        # KIS 토큰 갱신 성공 알림 시뮬레이션
        success_message = "🔑 KIS API 토큰이 성공적으로 갱신되었습니다. (테스트)"
        
        print("📤 관리자 알림 전송 중...")
        success = notification_service._send_simple_slack_message(success_message)
        
        if success:
            print("✅ 관리자 알림 전송 성공!")
            return True
        else:
            print("❌ 관리자 알림 전송 실패")
            return False
            
    except Exception as e:
        print(f"❌ 관리자 알림 테스트 중 오류: {e}")
        return False


def main():
    """전체 알림 서비스 테스트"""
    print("🚀 Stock Analyzer 알림 서비스 테스트\n")
    
    # NotificationService 테스트
    service_success = test_notification_service()
    
    # 관리자 알림 테스트
    admin_success = test_admin_notification()
    
    # 최종 결과
    print("\n" + "="*50)
    print("📊 알림 서비스 테스트 최종 결과")
    print("="*50)
    print(f"NotificationService: {'✅ 성공' if service_success else '❌ 실패'}")
    print(f"관리자 알림: {'✅ 성공' if admin_success else '❌ 실패'}")
    
    if service_success and admin_success:
        print("\n🎉 모든 알림 서비스가 정상 작동합니다!")
        print("📱 이제 실제 운영에서 Discord 알림을 받을 수 있습니다.")
        print("\n🔔 예상 알림:")
        print("   • 일일 추천 완료 알림")
        print("   • KIS 토큰 갱신 알림")
        print("   • 모델 재학습 완료 알림")
        print("   • 시스템 오류 알림")
        return True
    else:
        print("\n❌ 일부 알림 서비스에 문제가 있습니다.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
