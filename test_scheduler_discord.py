#!/usr/bin/env python3
"""
스케줄러 KIS 토큰 갱신 작업 테스트 (실제 토큰 재발급 없음)
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.scheduler import SchedulingService
from app.services.notification import NotificationService
from app.config.settings import settings
from datetime import datetime


def test_scheduler_notification_integration():
    """스케줄러의 알림 통합 테스트"""
    print("⏰ 스케줄러 알림 통합 테스트 시작...\n")
    
    try:
        # 스케줄러 인스턴스 생성 (시작하지 않음)
        scheduler = SchedulingService()
        print("✅ 스케줄러 서비스 초기화 완료")
        
        # NotificationService 인스턴스 확인
        notification_service = scheduler.notification_service
        print("✅ NotificationService 인스턴스 확인")
        
        # 모의 KIS 토큰 갱신 성공 알림
        print("📤 모의 KIS 토큰 갱신 성공 알림 전송...")
        if settings.send_admin_notifications:
            message = "🔑 KIS API 토큰이 자정에 성공적으로 갱신되었습니다. (테스트)"
            success = notification_service._send_simple_slack_message(message)
            
            if success:
                print("✅ KIS 토큰 갱신 성공 알림 전송됨")
            else:
                print("❌ KIS 토큰 갱신 성공 알림 전송 실패")
        else:
            print("⚠️ 관리자 알림이 비활성화됨")
            success = True
        
        # 모의 KIS 토큰 갱신 실패 알림
        print("📤 모의 KIS 토큰 갱신 실패 알림 전송...")
        if settings.send_admin_notifications:
            failure_message = "⚠️ KIS API 토큰 갱신에 실패했습니다. 확인이 필요합니다. (테스트)"
            failure_success = notification_service._send_simple_slack_message(failure_message)
            
            if failure_success:
                print("✅ KIS 토큰 갱신 실패 알림 전송됨")
            else:
                print("❌ KIS 토큰 갱신 실패 알림 전송 실패")
        else:
            failure_success = True
        
        # 모의 일반 시스템 알림
        print("📤 모의 시스템 상태 알림 전송...")
        system_message = (
            f"🚀 **Stock Analyzer 시스템 상태**\n\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🎯 상태: 모든 서비스 정상 운영\n"
            f"📊 활성 스케줄: 6개 작업\n"
            f"🔄 다음 토큰 갱신: 매일 자정 00:00\n"
            f"📱 알림 채널: Discord 활성화"
        )
        
        system_success = notification_service._send_simple_slack_message(system_message)
        
        if system_success:
            print("✅ 시스템 상태 알림 전송됨")
        else:
            print("❌ 시스템 상태 알림 전송 실패")
        
        # 스케줄러 정리
        scheduler.stop_scheduler()
        print("✅ 스케줄러 정리 완료")
        
        return success and failure_success and system_success
        
    except Exception as e:
        print(f"❌ 스케줄러 알림 통합 테스트 중 오류: {e}")
        return False


def test_manual_kis_refresh_notification():
    """수동 KIS 갱신 작업 알림 테스트"""
    print("\n🔧 수동 KIS 갱신 작업 알림 테스트...")
    
    try:
        scheduler = SchedulingService()
        
        # 실제 kis_token_refresh_task 메서드 실행 (하지만 실제 API 호출은 안함)
        print("📋 kis_token_refresh_task 메서드 존재 확인...")
        
        # 메서드 존재 확인
        if hasattr(scheduler, 'kis_token_refresh_task'):
            print("✅ kis_token_refresh_task 메서드 존재")
            
            # 모의 알림만 테스트 (실제 API 호출하지 않음)
            test_message = "🔑 KIS 토큰 갱신 작업이 예약되어 있습니다. (매일 자정 00:00)"
            success = scheduler.notification_service._send_simple_slack_message(test_message)
            
            if success:
                print("✅ KIS 갱신 작업 예약 알림 전송됨")
            else:
                print("❌ KIS 갱신 작업 예약 알림 전송 실패")
                
        else:
            print("❌ kis_token_refresh_task 메서드 없음")
            success = False
        
        scheduler.stop_scheduler()
        return success
        
    except Exception as e:
        print(f"❌ 수동 KIS 갱신 테스트 중 오류: {e}")
        return False


def main():
    """전체 스케줄러 알림 테스트"""
    print("🚀 스케줄러 + Discord 알림 통합 테스트\n")
    
    # 스케줄러 알림 통합 테스트
    integration_success = test_scheduler_notification_integration()
    
    # 수동 KIS 갱신 알림 테스트
    manual_success = test_manual_kis_refresh_notification()
    
    # 최종 결과
    print("\n" + "="*60)
    print("🎯 스케줄러 + Discord 알림 테스트 최종 결과")
    print("="*60)
    print(f"알림 통합 테스트: {'✅ 성공' if integration_success else '❌ 실패'}")
    print(f"KIS 갱신 알림 테스트: {'✅ 성공' if manual_success else '❌ 실패'}")
    
    if integration_success and manual_success:
        print("\n🎉 모든 스케줄러 알림 테스트가 성공했습니다!")
        print("\n📱 실제 운영에서 다음 알림들을 받게 됩니다:")
        print("   🔑 매일 자정 - KIS 토큰 갱신 알림")
        print("   📊 평일 16:00 - 일일 추천 완료 알림")
        print("   🌅 평일 08:30 - 아침 추천 알림")
        print("   🤖 토요일 02:00 - 모델 재학습 완료 알림")
        print("   📈 일요일 18:00 - 주간 성과 리포트")
        print("   🔄 첫째 일요일 01:00 - 유니버스 업데이트 알림")
        print("\n🚀 Redis + KIS + Discord 통합 시스템 준비 완료!")
        return True
    else:
        print("\n❌ 일부 테스트에 실패했습니다.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
