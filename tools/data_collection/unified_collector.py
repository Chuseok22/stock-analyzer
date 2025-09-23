#!/usr/bin/env python3
"""
통합 데이터 수집 CLI
새로운 통합 데이터 수집기를 사용하는 명령행 인터페이스

사용법:
  python unified_collector.py --daily                    # 일일 데이터 수집
  python unified_collector.py --historical --days 365   # 1년 역사적 데이터
  python unified_collector.py --kr-only --daily         # 한국만 일일 수집
  python unified_collector.py --us-only --daily         # 미국만 일일 수집
"""
import sys
import asyncio
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))

from app.services.unified_data_collector import UnifiedDataCollector


async def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='통합 데이터 수집기')
    parser.add_argument('--daily', action='store_true', help='일일 데이터 수집')
    parser.add_argument('--historical', action='store_true', help='역사적 데이터 수집')
    parser.add_argument('--days', type=int, default=365, help='역사적 데이터 수집 일수 (기본: 365일)')
    parser.add_argument('--kr-only', action='store_true', help='한국 데이터만')
    parser.add_argument('--us-only', action='store_true', help='미국 데이터만')
    
    args = parser.parse_args()
    
    if not args.daily and not args.historical:
        print("❌ --daily 또는 --historical 옵션을 선택해주세요")
        parser.print_help()
        return False
    
    collector = UnifiedDataCollector()
    
    try:
        print("🚀 통합 데이터 수집기 시작")
        print("="*60)
        
        if args.daily:
            print("📊 일일 데이터 수집 모드")
            if args.kr_only:
                success = await collector.collect_korean_daily_data()
            elif args.us_only:
                success = await collector.collect_us_daily_data()
            else:
                success = await collector.collect_daily_data()
        else:
            print(f"📈 {args.days}일 역사적 데이터 수집 모드")
            if args.kr_only:
                success = await collector.collect_korean_historical_data(args.days)
            elif args.us_only:
                success = await collector.collect_us_historical_data(args.days)
            else:
                success = await collector.collect_historical_data(args.days)
        
        if success:
            print("\n🎉 데이터 수집 완료!")
        else:
            print("\n❌ 데이터 수집 실패")
        
        return success
        
    except Exception as e:
        print(f"\n❌ 데이터 수집 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)