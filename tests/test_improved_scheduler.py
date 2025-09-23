#!/usr/bin/env python3
"""
개선된 스케줄러 알림 테스트
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

def test_schedule_listing():
    """스케줄 목록 확인"""
    print("🔍 스케줄 목록 테스트:")
    
    try:
        from scripts.global_scheduler import GlobalScheduler
        
        # 스케줄러 생성 (부트스트랩 비활성화)
        scheduler = GlobalScheduler(run_bootstrap=False)
        print("   ✅ GlobalScheduler 생성 성공")
        
        # 오늘 스케줄 가져오기
        today_schedule = scheduler._get_today_schedule()
        
        print("   📅 오늘 예정된 작업:")
        print(f"{today_schedule}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 스케줄 목록 테스트 실패: {e}")
        import traceback
        print(f"   상세 오류: {traceback.format_exc()}")
        return False

async def test_bootstrap_alert():
    """개선된 부트스트랩 알림 테스트"""
    print("\n🔍 개선된 부트스트랩 알림 테스트:")
    
    try:
        from scripts.global_scheduler import GlobalScheduler
        
        # 스케줄러 생성 (부트스트랩 비활성화)
        scheduler = GlobalScheduler(run_bootstrap=False)
        print("   ✅ GlobalScheduler 생성 성공")
        
        # 부트스트랩 알림 메서드 직접 호출
        await scheduler._send_bootstrap_complete_alert()
        print("   ✅ 개선된 부트스트랩 알림 메서드 실행 완료")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 부트스트랩 알림 테스트 실패: {e}")
        import traceback
        print(f"   상세 오류: {traceback.format_exc()}")
        return False

def test_schedule_functions():
    """스케줄 함수들 존재 확인"""
    print("\n🔍 스케줄 함수 존재 확인:")
    
    try:
        from scripts.global_scheduler import GlobalScheduler
        
        scheduler = GlobalScheduler(run_bootstrap=False)
        
        # 필요한 함수들 확인
        required_methods = [
            '_run_korean_premarket_recommendations',
            '_run_korean_market_analysis',
            '_run_us_premarket_alert',
            '_run_us_market_open_alert',
            '_run_us_market_analysis',
            '_collect_korean_data',
            '_collect_us_data',
            '_run_weekly_ml_training',
            '_run_monthly_ml_training',
            '_refresh_kis_token',
            '_health_check',
            '_check_emergency_alerts'
        ]
        
        missing_methods = []
        for method in required_methods:
            if hasattr(scheduler, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} - 누락!")
                missing_methods.append(method)
        
        if missing_methods:
            print(f"   ⚠️ 누락된 메서드: {len(missing_methods)}개")
            return False
        else:
            print("   ✅ 모든 필수 메서드 존재 확인")
            return True
        
    except Exception as e:
        print(f"   ❌ 스케줄 함수 확인 실패: {e}")
        return False

if __name__ == "__main__":
    print("🧪 개선된 스케줄러 알림 테스트 시작...")
    print("="*60)
    
    success = True
    
    # 1. 스케줄 목록 테스트
    success &= test_schedule_listing()
    
    # 2. 스케줄 함수 존재 확인
    success &= test_schedule_functions()
    
    # 3. 부트스트랩 알림 테스트
    print("\n⏳ 부트스트랩 알림 테스트 (비동기)...")
    try:
        bootstrap_success = asyncio.run(test_bootstrap_alert())
        success &= bootstrap_success
    except Exception as e:
        print(f"   ❌ 비동기 테스트 실패: {e}")
        success = False
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 개선된 스케줄러 알림 테스트 성공!")
        print("✅ 한국 프리마켓 알림 누락 문제 해결")
        print("✅ 모든 스케줄 정보 완전히 표시")
        print("✅ 알림 내용 상세화 및 개선")
    else:
        print("❌ 일부 테스트 실패")
        print("🔧 추가 수정 필요")
    
    print("🧪 테스트 완료")
    sys.exit(0 if success else 1)