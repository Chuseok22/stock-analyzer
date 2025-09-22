#!/usr/bin/env python3
"""
데이터 상세 분석
"""
import sys
from pathlib import Path
import pandas as pd

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from sqlalchemy import text


def analyze_data_details():
    """데이터 상세 분석"""
    print("🔍 데이터 상세 분석")
    
    try:
        with get_db_session() as db:
            query = text("""
                SELECT 
                    sm.stock_id,
                    sm.stock_code,
                    sm.stock_name,
                    sp.trade_date,
                    sp.close_price,
                    sp.volume,
                    sp.daily_return_pct,
                    sti.sma_20,
                    sti.rsi_14,
                    sti.macd_line,
                    sti.bb_percent,
                    sti.volume_ratio
                FROM stock_master sm
                INNER JOIN trading_universe_item tui ON sm.stock_id = tui.stock_id
                INNER JOIN stock_daily_price sp ON sm.stock_id = sp.stock_id
                INNER JOIN stock_technical_indicator sti ON sm.stock_id = sti.stock_id 
                    AND sp.trade_date = sti.calculation_date
                WHERE tui.universe_id = 1 
                    AND tui.is_active = true
                ORDER BY sm.stock_id, sp.trade_date
            """)
            
            result = db.execute(query).fetchall()
            
            if not result:
                print("❌ 데이터 없음")
                return False
            
            df = pd.DataFrame(result)
            print(f"✅ {len(df)}개 레코드 로드")
            
            # 데이터 타입 확인
            print(f"\n📊 데이터 타입:")
            for col in df.columns:
                print(f"   {col}: {df[col].dtype}")
            
            # 결측치 확인
            print(f"\n❓ 결측치 현황:")
            for col in df.columns:
                null_count = df[col].isnull().sum()
                print(f"   {col}: {null_count}개 ({null_count/len(df)*100:.1f}%)")
            
            # 종목별 데이터 수
            print(f"\n📈 종목별 데이터 수:")
            stock_counts = df.groupby(['stock_id', 'stock_code']).size()
            for (stock_id, stock_code), count in stock_counts.items():
                print(f"   {stock_code} (ID: {stock_id}): {count}개")
            
            # 샘플 데이터
            print(f"\n📋 첫 5개 레코드:")
            print(df.head().to_string())
            
            # 숫자 변환 테스트
            print(f"\n🔧 숫자 변환 테스트:")
            numeric_cols = ['close_price', 'volume', 'daily_return_pct', 
                           'sma_20', 'rsi_14', 'macd_line', 'bb_percent', 'volume_ratio']
            
            for col in numeric_cols:
                if col in df.columns:
                    try:
                        converted = pd.to_numeric(df[col], errors='coerce')
                        null_after = converted.isnull().sum()
                        print(f"   {col}: {null_after}개 NaN (변환 후)")
                    except Exception as e:
                        print(f"   {col}: 변환 실패 - {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🚀 데이터 상세 분석")
    print("="*50)
    
    success = analyze_data_details()
    
    print("\n" + "="*50)
    if success:
        print("✅ 분석 완료")
    else:
        print("❌ 분석 실패")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
