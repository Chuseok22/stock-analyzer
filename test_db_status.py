#!/usr/bin/env python3
"""
데이터베이스 상태 확인
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockMaster, StockDailyPrice, MarketRegion
from datetime import datetime, timedelta

def check_database_status():
    """데이터베이스 상태 확인"""
    print("📊 데이터베이스 상태 확인")
    print("="*50)
    
    try:
        with get_db_session() as db:
            # 1. 종목 데이터 확인
            print("1️⃣ 종목 데이터 현황:")
            
            kr_stocks = db.query(StockMaster).filter_by(
                market_region=MarketRegion.KR.value,
                is_active=True
            ).all()
            
            us_stocks = db.query(StockMaster).filter_by(
                market_region=MarketRegion.US.value,
                is_active=True
            ).all()
            
            print(f"   🇰🇷 한국 종목: {len(kr_stocks)}개")
            if kr_stocks:
                for stock in kr_stocks[:5]:
                    print(f"      - {stock.stock_code}: {stock.stock_name}")
            
            print(f"   🇺🇸 미국 종목: {len(us_stocks)}개")
            if us_stocks:
                for stock in us_stocks[:5]:
                    print(f"      - {stock.stock_code}: {stock.stock_name}")
            
            # 2. 가격 데이터 확인
            print("\n2️⃣ 가격 데이터 현황:")
            
            recent_date = datetime.now().date() - timedelta(days=7)
            
            kr_recent_prices = db.query(StockDailyPrice).join(StockMaster).filter(
                StockMaster.market_region == MarketRegion.KR.value,
                StockDailyPrice.trade_date >= recent_date
            ).count()
            
            us_recent_prices = db.query(StockDailyPrice).join(StockMaster).filter(
                StockMaster.market_region == MarketRegion.US.value,
                StockDailyPrice.trade_date >= recent_date
            ).count()
            
            print(f"   🇰🇷 한국 최근 7일 가격 데이터: {kr_recent_prices}개")
            print(f"   🇺🇸 미국 최근 7일 가격 데이터: {us_recent_prices}개")
            
            # 3. 전체 가격 데이터
            total_prices = db.query(StockDailyPrice).count()
            print(f"   📊 전체 가격 데이터: {total_prices}개")
            
            # 4. 샘플 가격 데이터 확인
            if kr_stocks:
                sample_stock = kr_stocks[0]
                sample_prices = db.query(StockDailyPrice).filter_by(
                    stock_id=sample_stock.stock_id
                ).order_by(StockDailyPrice.trade_date.desc()).limit(5).all()
                
                print(f"\n3️⃣ 샘플 종목 ({sample_stock.stock_code}) 최근 가격:")
                for price in sample_prices:
                    print(f"   {price.trade_date}: {price.close_price}원 (거래량: {price.volume})")
            
            # 5. 데이터 수집 가능성 확인
            print("\n4️⃣ 데이터 수집 상태:")
            
            if len(kr_stocks) >= 10 and kr_recent_prices >= 50:
                print("   ✅ 한국 데이터 충분 - ML 학습 가능")
                kr_ready = True
            else:
                print("   ❌ 한국 데이터 부족")
                kr_ready = False
            
            if len(us_stocks) >= 10 and us_recent_prices >= 50:
                print("   ✅ 미국 데이터 충분 - ML 학습 가능")
                us_ready = True
            else:
                print("   ❌ 미국 데이터 부족 - 수집 필요")
                us_ready = False
            
            return kr_ready, us_ready
            
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return False, False

if __name__ == "__main__":
    kr_ready, us_ready = check_database_status()
    print(f"\n📋 결과:")
    print(f"   🇰🇷 한국 데이터: {'준비됨' if kr_ready else '부족'}")
    print(f"   🇺🇸 미국 데이터: {'준비됨' if us_ready else '부족'}")