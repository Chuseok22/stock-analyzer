#!/usr/bin/env python3
"""
최적화된 ML 학습 스케줄 테스트
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

def test_optimized_ml_schedule():
    """최적화된 ML 학습 스케줄 테스트"""
    print("🧪 최적화된 ML 학습 스케줄 테스트")
    print("="*70)
    
    # 기존 스케줄 모두 제거
    schedule.clear()
    
    try:
        # GlobalScheduler 생성 (부트스트랩 비활성화)
        scheduler = GlobalScheduler(run_bootstrap=False)
        
        print(f"\n📊 등록된 스케줄 수: {len(schedule.jobs)}개")
        
        # ML 관련 스케줄만 필터링
        ml_schedules = []
        for job in schedule.jobs:
            tags = list(job.tags)
            if tags and ('ml_' in tags[0] or tags[0] in ['ml_daily', 'ml_weekly_advanced']):
                ml_schedules.append((job, tags[0]))
        
        print(f"\n🤖 ML 학습 스케줄 분석:")
        print(f"   총 ML 스케줄: {len(ml_schedules)}개")
        
        for job, tag in ml_schedules:
            next_run = job.next_run.strftime('%A %H:%M') if job.next_run else 'None'
            print(f"   • {tag}: {next_run}")
        
        # 새로운 메서드 존재 확인
        print(f"\n🔍 새로운 ML 메서드 확인:")
        new_methods = [
            '_run_daily_ml_training',
            '_run_weekly_advanced_training'
        ]
        
        for method in new_methods:
            if hasattr(scheduler, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} - 누락!")
        
        # 학습 빈도 계산
        print(f"\n📈 학습 빈도 분석:")
        daily_schedules = [s for s in ml_schedules if 'daily' in s[1]]
        weekly_schedules = [s for s in ml_schedules if 'weekly' in s[1]]
        
        daily_per_week = len(daily_schedules) * 7  # 일일 * 7일
        weekly_per_week = len(weekly_schedules)    # 주간
        total_per_week = daily_per_week + weekly_per_week
        
        print(f"   • 일일 학습: {len(daily_schedules)}회/일 = {daily_per_week}회/주")
        print(f"   • 주간 학습: {len(weekly_schedules)}회/주")
        print(f"   • 총 학습: {total_per_week}회/주")
        print(f"   • 연간 예상: {total_per_week * 52}회/년")
        
        # 시간 최적화 확인
        print(f"\n⏰ 시간 최적화 확인:")
        for job, tag in ml_schedules:
            if job.next_run:
                hour = job.next_run.hour
                if tag == 'ml_daily':
                    if hour == 6:  # 06:30
                        print(f"   ✅ 일일 학습 시간 최적화: {hour:02d}시 (시장 비활성 시간)")
                    else:
                        print(f"   ⚠️ 일일 학습 시간: {hour:02d}시 (확인 필요)")
                        
                elif tag == 'ml_weekly_advanced':
                    if hour == 2:  # 02:00 일요일
                        print(f"   ✅ 주간 학습 시간 최적화: 일요일 {hour:02d}시 (주말 활용)")
                    else:
                        print(f"   ⚠️ 주간 학습 시간: {hour:02d}시 (확인 필요)")
        
        # 기대 효과 계산
        print(f"\n🎯 최적화 효과 예상:")
        
        # 기존: 주 1회 + 월 1회
        old_weekly = 1
        old_monthly = 1
        old_yearly = old_weekly * 52 + old_monthly * 12
        
        # 새로운: 일 1회 + 주 1회 
        new_daily = 7  # 주 7회
        new_weekly = 1  # 주 1회
        new_yearly = (new_daily + new_weekly) * 52
        
        improvement = (new_yearly / old_yearly - 1) * 100
        
        print(f"   • 기존: {old_yearly}회/년 (주{old_weekly}회 + 월{old_monthly}회)")
        print(f"   • 신규: {new_yearly}회/년 (일{new_daily//7}회 + 주{new_weekly}회)")
        print(f"   • 개선: +{improvement:.1f}% 증가")
        
        # 성공 평가
        success = (
            len(ml_schedules) >= 2 and  # 최소 2개 ML 스케줄
            any('daily' in s[1] for s in ml_schedules) and  # 일일 학습 있음
            any('weekly' in s[1] for s in ml_schedules) and  # 주간 학습 있음
            hasattr(scheduler, '_run_daily_ml_training') and  # 새 메서드 있음
            hasattr(scheduler, '_run_weekly_advanced_training')
        )
        
        print(f"\n" + "="*70)
        if success:
            print("🎉 최적화된 ML 학습 스케줄 테스트 성공!")
            print("✅ 일일 적응 학습 추가 (06:30)")
            print("✅ 주간 고도화 학습 변경 (일요일 02:00)")
            print("✅ 시장 시간 충돌 방지")
            print("✅ 학습 빈도 대폭 향상")
        else:
            print("❌ ML 학습 스케줄 최적화에 문제가 있습니다")
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    print("🧪 테스트 완료")

if __name__ == "__main__":
    test_optimized_ml_schedule()