#!/usr/bin/env python3
"""
가격 데이터 범위 확인
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockMaster, StockDailyPrice, MarketRegion
from datetime import datetime, timedelta

def check_price_data_range():
    """가격 데이터 범위 확인"""
    print("📊 가격 데이터 범위 확인")
    print("="*50)
    
    try:
        with get_db_session() as db:
            # 샘플 종목 선택
            sample_stock = db.query(StockMaster).filter_by(
                market_region=MarketRegion.KR.value,
                is_active=True
            ).first()
            
            if not sample_stock:
                print("❌ 샘플 종목 없음")
                return
            
            print(f"📈 샘플 종목: {sample_stock.stock_code} ({sample_stock.stock_name})")
            
            # 가격 데이터 범위 확인
            price_data = db.query(StockDailyPrice).filter_by(
                stock_id=sample_stock.stock_id
            ).order_by(StockDailyPrice.trade_date.asc()).all()
            
            if not price_data:
                print("❌ 가격 데이터 없음")
                return
            
            print(f"📅 데이터 범위:")
            print(f"   시작일: {price_data[0].trade_date}")
            print(f"   종료일: {price_data[-1].trade_date}")
            print(f"   총 일수: {len(price_data)}일")
            
            # 최근 10일 데이터 출력
            recent_data = price_data[-10:]
            print(f"\n📊 최근 10일 데이터:")
            for price in recent_data:
                print(f"   {price.trade_date}: {price.close_price}원")
            
            # 30일 전 데이터 확인
            target_date = datetime.now().date() - timedelta(days=30)
            older_data = [p for p in price_data if p.trade_date <= target_date]
            
            print(f"\n🔍 30일 전 ({target_date}) 이전 데이터: {len(older_data)}개")
            
            if len(older_data) >= 30:
                print("   ✅ ML 학습용 데이터 충분")
                recommended_date = older_data[-1].trade_date
                print(f"   💡 추천 타겟 날짜: {recommended_date}")
            else:
                print("   ❌ ML 학습용 데이터 부족")
                
    except Exception as e:
        print(f"❌ 확인 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    check_price_data_range()