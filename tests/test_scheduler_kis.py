#!/usr/bin/env python3
"""
스케줄러 KIS 토큰 갱신 기능 테스트
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "app"))

from scripts.global_scheduler import GlobalScheduler

def test_scheduler_kis_refresh():
    """스케줄러의 KIS 토큰 갱신 기능 테스트"""
    print("⏰ 스케줄러 KIS 토큰 갱신 기능 테스트")
    print("="*50)
    
    try:
        # 1. 스케줄러 초기화 (부트스트랩 없이)
        print("1️⃣ 스케줄러 초기화...")
        scheduler = GlobalScheduler(run_bootstrap=False)
        
        # 2. KIS 토큰 갱신 메서드 직접 호출
        print("2️⃣ KIS 토큰 갱신 메서드 테스트...")
        success = scheduler._refresh_kis_token()
        
        if success:
            print("   ✅ 스케줄러 토큰 갱신 성공")
        else:
            print("   ❌ 스케줄러 토큰 갱신 실패")
            return False
        
        # 3. 스케줄 등록 확인
        print("3️⃣ 스케줄 등록 확인...")
        import schedule
        
        kis_jobs = [job for job in schedule.jobs if 'kis_token' in job.tags]
        
        if kis_jobs:
            for job in kis_jobs:
                print(f"   ✅ KIS 토큰 갱신 스케줄 등록됨: {job.next_run}")
        else:
            print("   ❌ KIS 토큰 갱신 스케줄 미등록")
            return False
        
        print("\n✅ 스케줄러 KIS 토큰 갱신 기능 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_scheduler_kis_refresh()
    sys.exit(0 if success else 1)