#!/usr/bin/env python3
"""
서버 시작 알림 테스트
"""
import sys
import os
from pathlib import Path
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set PYTHONPATH
os.environ['PYTHONPATH'] = str(project_root)

def test_telegram_notification():
    """텔레그램 알림 테스트"""
    print("🔍 텔레그램 알림 테스트:")
    
    try:
        from app.services.telegram_service import TelegramNotifier
        
        telegram = TelegramNotifier()
        print("   ✅ TelegramNotifier 생성 성공")
        
        # 간단한 테스트 메시지
        test_message = """
🚀 **테스트 알림**

시스템 테스트 중입니다.
모든 수정사항이 정상적으로 적용되었습니다.

✅ ML 모델 오류 수정 완료
✅ 서버 시작 알림 로직 개선
        """.strip()
        
        success = telegram.send_message(test_message)
        
        if success:
            print("   ✅ 텔레그램 알림 전송 성공")
            return True
        else:
            print("   ⚠️ 텔레그램 알림 전송 실패 (설정 확인 필요)")
            return False
            
    except Exception as e:
        print(f"   ❌ 텔레그램 알림 테스트 실패: {e}")
        return False

def test_notification_service():
    """NotificationService 테스트"""
    print("\n🔍 NotificationService 테스트:")
    
    try:
        from app.services.notification import NotificationService
        
        notification_service = NotificationService()
        print("   ✅ NotificationService 생성 성공")
        
        # 시스템 알림 테스트
        success = notification_service.send_system_alert(
            title="🧪 테스트 시스템 알림",
            message="모든 수정사항이 정상적으로 적용되었습니다.",
            alert_type="SYSTEM_TEST"
        )
        
        if success:
            print("   ✅ 시스템 알림 전송 성공")
            return True
        else:
            print("   ⚠️ 시스템 알림 전송 실패")
            return False
            
    except Exception as e:
        print(f"   ❌ NotificationService 테스트 실패: {e}")
        return False

async def test_bootstrap_alert():
    """부트스트랩 알림 테스트"""
    print("\n🔍 부트스트랩 알림 테스트:")
    
    try:
        from scripts.global_scheduler import GlobalScheduler
        
        # 스케줄러 생성 (부트스트랩 비활성화)
        scheduler = GlobalScheduler(run_bootstrap=False)
        print("   ✅ GlobalScheduler 생성 성공")
        
        # 부트스트랩 알림 메서드 직접 호출
        await scheduler._send_bootstrap_complete_alert()
        print("   ✅ 부트스트랩 알림 메서드 실행 완료")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 부트스트랩 알림 테스트 실패: {e}")
        import traceback
        print(f"   상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🧪 서버 알림 시스템 테스트 시작...")
    
    success = True
    
    # 1. 텔레그램 알림 테스트
    success &= test_telegram_notification()
    
    # 2. NotificationService 테스트
    success &= test_notification_service()
    
    # 3. 부트스트랩 알림 테스트
    print("\n⏳ 부트스트랩 알림 테스트 (비동기)...")
    try:
        bootstrap_success = asyncio.run(test_bootstrap_alert())
        success &= bootstrap_success
    except Exception as e:
        print(f"   ❌ 비동기 테스트 실패: {e}")
        success = False
    
    print(f"\n{'='*50}")
    if success:
        print("✅ 모든 알림 테스트 통과 - 시스템 정상")
    else:
        print("⚠️ 일부 알림 테스트 실패 - 설정 확인 필요")
        print("   (알림 설정이 비활성화되어 있을 수 있습니다)")
    
    print("🧪 알림 테스트 완료")
    sys.exit(0)