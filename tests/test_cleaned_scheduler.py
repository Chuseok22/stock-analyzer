#!/usr/bin/env python3
"""
정리된 스케줄러 테스트 (중복 제거 검증)
"""
import sys
from pathlib import Path
import asyncio

# Add app directory to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app"))

from scripts.global_scheduler import GlobalScheduler
import schedule

def test_cleaned_scheduler():
    """중복 제거된 깔끔한 스케줄러 테스트"""
    print("🧪 정리된 스케줄러 테스트 시작...")
    print("="*60)
    
    # 기존 스케줄 모두 제거
    schedule.clear()
    
    try:
        # GlobalScheduler 생성 (부트스트랩 비활성화)
        scheduler = GlobalScheduler(run_bootstrap=False)
        
        print(f"\n🔍 등록된 스케줄 수: {len(schedule.jobs)}개")
        
        # 각 태그별 스케줄 수 확인
        tag_counts = {}
        for job in schedule.jobs:
            tags = list(job.tags)
            if tags:
                tag = tags[0]
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        print("\n📊 태그별 스케줄 수:")
        for tag, count in sorted(tag_counts.items()):
            emoji = "✅" if count == 1 else "⚠️"
            print(f"   {emoji} {tag}: {count}개")
            
        # 중복 확인
        duplicates_found = any(count > 1 for count in tag_counts.values())
        
        if duplicates_found:
            print("\n❌ 중복된 스케줄이 발견되었습니다!")
            for tag, count in tag_counts.items():
                if count > 1:
                    print(f"   🔄 {tag}: {count}개 (중복!)")
        else:
            print("\n✅ 중복 없음! 모든 스케줄이 깔끔하게 등록됨")
        
        # 오늘 스케줄 확인
        print("\n🔍 오늘 예정된 작업 확인:")
        today_schedule = scheduler._get_today_schedule()
        print(today_schedule)
        
        # 라인 수 체크 (중복 확인)
        schedule_lines = today_schedule.split('\n')
        unique_lines = set(schedule_lines)
        
        print(f"\n📏 스케줄 라인 분석:")
        print(f"   총 라인 수: {len(schedule_lines)}")
        print(f"   고유 라인 수: {len(unique_lines)}")
        
        if len(schedule_lines) == len(unique_lines):
            print("   ✅ 중복 라인 없음")
        else:
            print("   ⚠️ 중복 라인 발견!")
            
        # 부트스트랩 알림 테스트 (간단히)
        print("\n🚀 부트스트랩 알림 테스트:")
        try:
            # 비동기 실행으로 테스트
            asyncio.run(scheduler._send_bootstrap_complete_alert())
            print("   ✅ 부트스트랩 알림 처리 완료")
        except Exception as e:
            print(f"   ⚠️ 부트스트랩 알림 오류: {e}")
        
        print("\n" + "="*60)
        if not duplicates_found and len(schedule_lines) == len(unique_lines):
            print("🎉 정리된 스케줄러 테스트 성공!")
            print("✅ 중복 제거 완료")
            print("✅ 깔끔한 알림 메시지")
            print("✅ 효율적인 스케줄 관리")
        else:
            print("❌ 스케줄러에 문제가 있습니다")
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    print("🧪 테스트 완료")

if __name__ == "__main__":
    test_cleaned_scheduler()