#!/usr/bin/env python3
"""
시장 시간 분석 및 최적 ML 학습 시간 결정
"""
from datetime import datetime, time

def analyze_market_hours():
    """한국과 미국 시장 시간 분석"""
    print("📊 시장 시간 분석 (한국 시간 기준)")
    print("="*60)
    
    market_hours = {
        "한국 시장": {
            "정규장": "09:00 - 15:30",
            "시간외": "15:30 - 09:00 (다음날)",
            "프리마켓": "08:30 - 09:00 (권장 시간)",
            "애프터마켓": "15:30 - 17:00"
        },
        "미국 시장 (서머타임)": {
            "프리마켓": "17:00 - 22:30 (한국시간)",
            "정규장": "22:30 - 05:00 (한국시간)",
            "애프터마켓": "05:00 - 09:00 (한국시간)"
        },
        "미국 시장 (표준시)": {
            "프리마켓": "18:00 - 23:30 (한국시간)", 
            "정규장": "23:30 - 06:00 (한국시간)",
            "애프터마켓": "06:00 - 10:00 (한국시간)"
        }
    }
    
    for region, hours in market_hours.items():
        print(f"\n🔸 {region}:")
        for session, time_range in hours.items():
            print(f"   • {session}: {time_range}")
    
    return market_hours

def find_optimal_ml_times():
    """최적 ML 학습 시간 찾기"""
    print("\n\n🎯 최적 ML 학습 시간 분석")
    print("="*60)
    
    # 시장 활동이 없는 시간대 찾기
    optimal_times = {
        "일일 ML 학습": {
            "최적 시간": "06:30",
            "이유": [
                "미국 애프터마켓 종료 후 (06:00)",
                "한국 프리마켓 시작 전 (08:30)",
                "서버 부하가 낮은 새벽 시간",
                "전일 데이터 완전 수집 완료 후"
            ],
            "소요 시간": "15-20분",
            "데이터": "전일 + 최근 30일"
        },
        "주간 고도화 학습": {
            "최적 시간": "일요일 02:00",
            "이유": [
                "주말로 시장 활동 없음",
                "토요일 → 일요일로 변경 (더 여유)",
                "한 주간 데이터 완전 정리 후",
                "월요일 장 시작 전 충분한 시간"
            ],
            "소요 시간": "2-3시간",
            "데이터": "최근 1년 + 하이퍼파라미터 최적화"
        }
    }
    
    for training_type, details in optimal_times.items():
        print(f"\n🔸 {training_type}:")
        print(f"   ⏰ 최적 시간: {details['최적 시간']}")
        print(f"   ⏱️ 소요 시간: {details['소요 시간']}")
        print(f"   📊 데이터: {details['데이터']}")
        print("   🎯 선정 이유:")
        for reason in details['이유']:
            print(f"      • {reason}")
    
    return optimal_times

def create_time_conflict_matrix():
    """시간 충돌 매트릭스 생성"""
    print("\n\n⚠️ 시간 충돌 분석")
    print("="*60)
    
    # 24시간을 1시간 단위로 분석
    hours = list(range(24))
    conflicts = {}
    
    for hour in hours:
        conflict_sources = []
        
        # 한국 시장 시간
        if 9 <= hour <= 15:
            conflict_sources.append("한국 정규장")
        elif 8 <= hour < 9:
            conflict_sources.append("한국 프리마켓")
        elif 15 < hour <= 17:
            conflict_sources.append("한국 애프터마켓")
        
        # 미국 시장 시간 (서머타임)
        if 17 <= hour <= 22:
            conflict_sources.append("미국 프리마켓(서머타임)")
        elif (22 <= hour <= 23) or (0 <= hour <= 5):
            conflict_sources.append("미국 정규장(서머타임)")
        elif 5 < hour <= 9:
            conflict_sources.append("미국 애프터마켓(서머타임)")
        
        conflicts[hour] = conflict_sources
    
    # 충돌 없는 시간 찾기
    safe_hours = [hour for hour, sources in conflicts.items() if not sources]
    busy_hours = [hour for hour, sources in conflicts.items() if sources]
    
    print(f"🟢 안전한 시간대: {[f'{h:02d}:00' for h in safe_hours]}")
    print(f"🔴 위험한 시간대: {[f'{h:02d}:00' for h in busy_hours]}")
    
    # 특히 안전한 시간 (아무 시장도 열리지 않음)
    print("\n🎯 최적 시간대 (시장 활동 전혀 없음):")
    for hour in safe_hours:
        print(f"   • {hour:02d}:00 - {hour:02d}:59")
    
    return safe_hours, conflicts

def main():
    """메인 분석"""
    print("⏰ ML 학습 최적 시간 분석")
    print("="*80)
    
    # 1. 시장 시간 분석
    market_hours = analyze_market_hours()
    
    # 2. 최적 시간 결정
    optimal_times = find_optimal_ml_times()
    
    # 3. 충돌 분석
    safe_hours, conflicts = create_time_conflict_matrix()
    
    print("\n\n🚀 최종 권장사항")
    print("="*60)
    print("✅ 일일 ML 학습: 매일 06:30")
    print("   • 이유: 미국 장 완전 종료 후, 한국 장 시작 2시간 전")
    print("   • 장점: 시장 영향 없음, 전일 데이터 완전 반영")
    print("   • 소요: 15-20분 (부담 없음)")
    
    print("\n✅ 주간 고도화 학습: 매주 일요일 02:00")
    print("   • 이유: 완전한 주말, 모든 시장 닫힘")
    print("   • 장점: 충분한 시간, 시스템 독점 사용")
    print("   • 소요: 2-3시간 (주말 활용)")
    
    print("\n📈 예상 효과:")
    print("   • 학습 빈도: 주 1회 → 일 7회 (700% 증가)")
    print("   • 고도화: 월 1회 → 주 1회 (400% 증가)")
    print("   • 총 학습: 64회/년 → 416회/년 (650% 증가)")
    print("   • 대응성: 실시간 시장 변화 반영")

if __name__ == "__main__":
    main()