#!/usr/bin/env python3
"""
데이터베이스 데이터 확인 및 디버깅
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import Stock, StockPrice, StockIndicator, Universe, UniverseItem, Recommendation
from sqlalchemy import text


def check_database_data():
    """데이터베이스 데이터 상세 확인"""
    print("🔍 데이터베이스 데이터 상세 확인\n")
    
    try:
        with get_db_session() as db:
            # 1. 종목 정보 확인
            print("1️⃣ 종목 정보 확인")
            stocks = db.query(Stock).all()
            print(f"   총 종목 수: {len(stocks)}")
            
            if stocks:
                print("   상위 5개 종목:")
                for stock in stocks[:5]:
                    print(f"   - ID: {stock.id}, 코드: {stock.code}, 이름: {stock.name}, 지역: {getattr(stock, 'region', 'N/A')}")
            
            # 2. 유니버스 정보 확인
            print("\n2️⃣ 유니버스 정보 확인")
            universes = db.query(Universe).all()
            print(f"   총 유니버스 수: {len(universes)}")
            
            if universes:
                for universe in universes:
                    print(f"   - ID: {universe.id}, 지역: {universe.region}, 크기: {universe.size}, 날짜: {universe.snapshot_date}")
            
            # 3. 유니버스 종목 확인
            print("\n3️⃣ 유니버스 종목 확인")
            universe_items = db.query(UniverseItem).all()
            print(f"   총 유니버스 종목 수: {len(universe_items)}")
            
            if universe_items:
                print("   상위 5개 유니버스 종목:")
                for item in universe_items[:5]:
                    stock_name = db.query(Stock).filter(Stock.id == item.stock_id).first()
                    print(f"   - 유니버스 ID: {item.universe_id}, 종목 ID: {item.stock_id}, 종목명: {stock_name.name if stock_name else 'Unknown'}")
            
            # 4. 주가 데이터 확인
            print("\n4️⃣ 주가 데이터 확인")
            stock_prices = db.query(StockPrice).all()
            print(f"   총 주가 데이터 수: {len(stock_prices)}")
            
            if stock_prices:
                # 날짜별 분포 확인
                date_counts = db.execute(text("""
                    SELECT trade_date, COUNT(*) as count 
                    FROM stock_price 
                    GROUP BY trade_date 
                    ORDER BY trade_date DESC 
                    LIMIT 10
                """)).fetchall()
                
                print("   최근 10일 데이터 분포:")
                for row in date_counts:
                    print(f"   - {row[0]}: {row[1]}개")
                
                # 종목별 분포 확인
                stock_counts = db.execute(text("""
                    SELECT s.code, s.name, COUNT(sp.id) as count
                    FROM stock s
                    LEFT JOIN stock_price sp ON s.id = sp.stock_id
                    GROUP BY s.id, s.code, s.name
                    ORDER BY count DESC
                    LIMIT 5
                """)).fetchall()
                
                print("\n   종목별 주가 데이터 (상위 5개):")
                for row in stock_counts:
                    print(f"   - {row[0]} ({row[1]}): {row[2]}개")
            
            # 5. 기술적 지표 확인
            print("\n5️⃣ 기술적 지표 확인")
            stock_indicators = db.query(StockIndicator).all()
            print(f"   총 기술적 지표 수: {len(stock_indicators)}")
            
            if stock_indicators:
                # 날짜별 분포 확인
                indicator_date_counts = db.execute(text("""
                    SELECT trade_date, COUNT(*) as count 
                    FROM stock_indicator 
                    GROUP BY trade_date 
                    ORDER BY trade_date DESC 
                    LIMIT 10
                """)).fetchall()
                
                print("   최근 10일 지표 분포:")
                for row in indicator_date_counts:
                    print(f"   - {row[0]}: {row[1]}개")
            
            # 6. ML 모델용 데이터 조회 테스트
            print("\n6️⃣ ML 모델용 데이터 조회 테스트")
            
            # 유니버스 1의 데이터 조회 (ML 모델에서 사용하는 쿼리와 동일)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # Universe 1에 포함된 종목들의 주가와 지표 데이터 조회
            ml_data_query = db.execute(text("""
                SELECT 
                    s.id as stock_id,
                    s.code,
                    s.name,
                    sp.trade_date,
                    sp.close_price,
                    sp.volume,
                    si.rsi_14,
                    si.macd,
                    si.bb_upper,
                    si.bb_lower,
                    si.sma_20,
                    si.ema_12,
                    si.ema_26
                FROM stock s
                INNER JOIN universe_item ui ON s.id = ui.stock_id
                INNER JOIN stock_price sp ON s.id = sp.stock_id
                INNER JOIN stock_indicator si ON s.id = si.stock_id AND sp.trade_date = si.trade_date
                WHERE ui.universe_id = 1 
                    AND sp.trade_date >= :start_date
                ORDER BY s.id, sp.trade_date
            """), {"start_date": thirty_days_ago.date()}).fetchall()
            
            print(f"   Universe 1 ML 데이터 수: {len(ml_data_query)}")
            
            if ml_data_query:
                print("   샘플 데이터 (첫 3개):")
                for i, row in enumerate(ml_data_query[:3]):
                    print(f"   - {i+1}. 종목: {row.code} ({row.name}), 날짜: {row.trade_date}, 종가: {row.close_price}")
            else:
                print("   ❌ ML 학습용 데이터가 없습니다!")
                
                # 디버깅을 위한 개별 테이블 확인
                print("\n   🔍 디버깅을 위한 개별 확인:")
                
                # UniverseItem에서 Universe 1 종목들
                universe_1_stocks = db.execute(text("""
                    SELECT s.id, s.code, s.name
                    FROM stock s
                    INNER JOIN universe_item ui ON s.id = ui.stock_id
                    WHERE ui.universe_id = 1
                """)).fetchall()
                print(f"   - Universe 1 종목 수: {len(universe_1_stocks)}")
                
                if universe_1_stocks:
                    stock_id = universe_1_stocks[0].id
                    print(f"   - 첫 번째 종목 ID: {stock_id}")
                    
                    # 해당 종목의 주가 데이터
                    stock_prices_for_stock = db.execute(text("""
                        SELECT date, close_price 
                        FROM stock_price 
                        WHERE stock_id = :stock_id 
                        ORDER BY date DESC 
                        LIMIT 5
                    """), {"stock_id": stock_id}).fetchall()
                    print(f"   - 해당 종목 주가 데이터 수: {len(stock_prices_for_stock)}")
                    
                    # 해당 종목의 지표 데이터
                    stock_indicators_for_stock = db.execute(text("""
                        SELECT date, rsi, macd 
                        FROM stock_indicator 
                        WHERE stock_id = :stock_id 
                        ORDER BY date DESC 
                        LIMIT 5
                    """), {"stock_id": stock_id}).fetchall()
                    print(f"   - 해당 종목 지표 데이터 수: {len(stock_indicators_for_stock)}")
            
            # 7. 추천 데이터 확인
            print("\n7️⃣ 추천 데이터 확인")
            recommendations = db.query(Recommendation).all()
            print(f"   총 추천 데이터 수: {len(recommendations)}")
            
            return True
            
    except Exception as e:
        print(f"❌ 데이터 확인 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🔍 Stock Analyzer 데이터베이스 데이터 확인\n")
    print("="*60)
    
    success = check_database_data()
    
    print("\n" + "="*60)
    if success:
        print("✅ 데이터 확인 완료")
    else:
        print("❌ 데이터 확인 실패")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
