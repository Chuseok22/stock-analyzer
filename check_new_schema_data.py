#!/usr/bin/env python3
"""
새로운 스키마 데이터 확인
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from sqlalchemy import text


def check_new_schema_data():
    """새로운 스키마 데이터 확인"""
    print("🔍 새로운 스키마 데이터 확인")
    
    try:
        with get_db_session() as db:
            # 1. 주식 마스터
            stock_count = db.execute(text("SELECT COUNT(*) FROM stock_master")).scalar()
            print(f"📊 주식 마스터: {stock_count}개")
            
            # 2. 주가 데이터
            price_count = db.execute(text("SELECT COUNT(*) FROM stock_daily_price")).scalar()
            print(f"📈 주가 데이터: {price_count}개")
            
            # 3. 기술적 지표
            indicator_count = db.execute(text("SELECT COUNT(*) FROM stock_technical_indicator")).scalar()
            print(f"🔧 기술적 지표: {indicator_count}개")
            
            # 4. 유니버스
            universe_count = db.execute(text("SELECT COUNT(*) FROM trading_universe")).scalar()
            universe_item_count = db.execute(text("SELECT COUNT(*) FROM trading_universe_item")).scalar()
            print(f"🌌 유니버스: {universe_count}개")
            print(f"📋 유니버스 종목: {universe_item_count}개")
            
            # 5. 샘플 데이터 확인
            print("\n📋 샘플 주가 데이터:")
            sample_prices = db.execute(text("""
                SELECT sm.stock_code, sm.stock_name, sp.trade_date, sp.close_price
                FROM stock_master sm
                JOIN stock_daily_price sp ON sm.stock_id = sp.stock_id
                ORDER BY sp.trade_date DESC
                LIMIT 5
            """)).fetchall()
            
            for row in sample_prices:
                print(f"   {row.stock_code} ({row.stock_name}) - {row.trade_date}: {row.close_price}")
            
            print("\n📋 샘플 기술적 지표:")
            sample_indicators = db.execute(text("""
                SELECT sm.stock_code, sti.calculation_date, sti.sma_20, sti.rsi_14
                FROM stock_master sm
                JOIN stock_technical_indicator sti ON sm.stock_id = sti.stock_id
                ORDER BY sti.calculation_date DESC
                LIMIT 5
            """)).fetchall()
            
            for row in sample_indicators:
                print(f"   {row.stock_code} - {row.calculation_date}: SMA20={row.sma_20}, RSI={row.rsi_14}")
            
            # 6. 조인 테스트
            print("\n🔗 조인 테스트:")
            join_test = db.execute(text("""
                SELECT COUNT(*) as count
                FROM stock_master sm
                INNER JOIN trading_universe_item tui ON sm.stock_id = tui.stock_id
                INNER JOIN stock_daily_price sp ON sm.stock_id = sp.stock_id
                INNER JOIN stock_technical_indicator sti ON sm.stock_id = sti.stock_id 
                    AND sp.trade_date = sti.calculation_date
                WHERE tui.universe_id = 1 AND tui.is_active = true
            """)).scalar()
            
            print(f"   조인된 레코드: {join_test}개")
            
            if join_test == 0:
                print("\n🔍 조인 실패 원인 분석:")
                
                # 각 테이블별 데이터 확인
                universe_stocks = db.execute(text("""
                    SELECT COUNT(*) FROM trading_universe_item WHERE universe_id = 1 AND is_active = true
                """)).scalar()
                print(f"   유니버스 1 활성 종목: {universe_stocks}개")
                
                if universe_stocks > 0:
                    sample_universe_item = db.execute(text("""
                        SELECT stock_id FROM trading_universe_item WHERE universe_id = 1 AND is_active = true LIMIT 1
                    """)).scalar()
                    
                    price_for_stock = db.execute(text("""
                        SELECT COUNT(*) FROM stock_daily_price WHERE stock_id = :stock_id
                    """), {"stock_id": sample_universe_item}).scalar()
                    
                    indicator_for_stock = db.execute(text("""
                        SELECT COUNT(*) FROM stock_technical_indicator WHERE stock_id = :stock_id
                    """), {"stock_id": sample_universe_item}).scalar()
                    
                    print(f"   종목 ID {sample_universe_item} 주가 데이터: {price_for_stock}개")
                    print(f"   종목 ID {sample_universe_item} 지표 데이터: {indicator_for_stock}개")
                    
                    # 날짜 매칭 확인
                    date_match = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM stock_daily_price sp
                        INNER JOIN stock_technical_indicator sti ON sp.stock_id = sti.stock_id 
                            AND sp.trade_date = sti.calculation_date
                        WHERE sp.stock_id = :stock_id
                    """), {"stock_id": sample_universe_item}).scalar()
                    
                    print(f"   종목 ID {sample_universe_item} 날짜 매칭: {date_match}개")
            
            return True
            
    except Exception as e:
        print(f"❌ 데이터 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🚀 새로운 스키마 데이터 확인")
    print("="*50)
    
    success = check_new_schema_data()
    
    print("\n" + "="*50)
    if success:
        print("✅ 데이터 확인 완료")
    else:
        print("❌ 데이터 확인 실패")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
