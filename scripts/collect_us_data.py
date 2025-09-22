#!/usr/bin/env python3
"""
US 주식 데이터 수집 시스템
Alpha Vantage API를 사용하여 S&P 500 주요 종목 데이터 수집
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import json
import time
import pandas as pd
import numpy as np

# Add app directory to path  
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import (
    StockMaster, StockDailyPrice, StockTechnicalIndicator,
    StockFundamentalData, TradingUniverse, TradingUniverseItem, MarketRegion
)
from app.services.alpha_vantage_api import AlphaVantageAPIClient
from app.database.redis_client import redis_client
from app.config.settings import settings


class USDataCollector:
    """US 주식 데이터 수집기"""
    
    def __init__(self):
        self.alpha_vantage = AlphaVantageAPIClient()
        self.universe_id = 2  # US market universe
        self.market_region = MarketRegion.US
        
        # US 주요 종목 (S&P 500 상위 50개)
        self.us_major_stocks = [
            # Mega Cap Technology
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'CRM',
            'ADBE', 'NFLX', 'AMD', 'INTC', 'CSCO', 'PYPL', 'QCOM', 'IBM', 'UBER', 'SNOW',
            
            # Healthcare & Pharma
            'UNH', 'JNJ', 'PFE', 'ABT', 'TMO', 'ABBV', 'MRK', 'DHR', 'BMY', 'AMGN',
            
            # Financial Services
            'BRK.B', 'JPM', 'BAC', 'WFC', 'GS', 'MS', 'AXP', 'BLK', 'SPGI', 'CB',
            
            # Consumer & Retail
            'HD', 'WMT', 'PG', 'KO', 'PEP', 'COST', 'MCD', 'NKE', 'SBUX', 'TGT'
        ]
        
        print(f"🇺🇸 US 데이터 수집기 초기화: {len(self.us_major_stocks)}개 종목")
    
    def ensure_trading_universe(self):
        """US 트레이딩 유니버스 생성/확인"""
        print("🌍 US 트레이딩 유니버스 설정...")
        
        try:
            with get_db_session() as db:
                # US 유니버스 확인/생성
                universe = db.query(TradingUniverse).filter_by(universe_id=self.universe_id).first()
                
                if not universe:
                    universe = TradingUniverse(
                        universe_id=self.universe_id,
                        universe_name="US Major Stocks",
                        universe_description="S&P 500 Major Stocks for US Market Analysis",
                        is_active=True
                    )
                    db.add(universe)
                    db.commit()
                    print(f"✅ US 유니버스 생성: {universe.universe_name}")
                else:
                    print(f"✅ US 유니버스 확인: {universe.universe_name}")
                
                return True
                
        except Exception as e:
            print(f"❌ US 유니버스 설정 실패: {e}")
            return False
    
    def collect_stock_master_data(self):
        """US 종목 마스터 데이터 수집"""
        print("📊 US 종목 마스터 데이터 수집 중...")
        
        collected = 0
        updated = 0
        
        try:
            with get_db_session() as db:
                for i, symbol in enumerate(self.us_major_stocks):
                    try:
                        print(f"📈 {symbol} 기본 정보 수집 중... ({i+1}/{len(self.us_major_stocks)})")
                        
                        # 기존 종목 확인
                        existing_stock = db.query(StockMaster).filter_by(
                            market_region=self.market_region.value,
                            stock_code=symbol
                        ).first()
                        
                        # 회사 개요 데이터 가져오기
                        overview = self.alpha_vantage.get_company_overview(symbol)
                        
                        if not overview:
                            print(f"   ⚠️ {symbol}: 회사 정보 없음")
                            continue
                        
                        if existing_stock:
                            # 기존 데이터 업데이트
                            existing_stock.stock_name = overview.get('name', symbol)
                            existing_stock.stock_name_en = overview.get('name', symbol)
                            existing_stock.market_name = overview.get('exchange', 'NASDAQ')
                            existing_stock.sector_classification = overview.get('sector', '')
                            existing_stock.industry_classification = overview.get('industry', '')
                            existing_stock.market_capitalization = overview.get('market_cap')
                            existing_stock.last_updated = datetime.now()
                            updated += 1
                            
                            stock = existing_stock
                        else:
                            # 새 종목 생성
                            stock = StockMaster(
                                market_region=self.market_region.value,
                                stock_code=symbol,
                                stock_name=overview.get('name', symbol),
                                stock_name_en=overview.get('name', symbol),
                                market_name=overview.get('exchange', 'NASDAQ'),
                                sector_classification=overview.get('sector', ''),
                                industry_classification=overview.get('industry', ''),
                                market_capitalization=overview.get('market_cap'),
                                is_active=True,
                                data_provider="Alpha Vantage"
                            )
                            db.add(stock)
                            collected += 1
                        
                        # 유니버스에 추가
                        universe_item = db.query(TradingUniverseItem).filter_by(
                            universe_id=self.universe_id,
                            stock_id=stock.stock_id
                        ).first() if existing_stock else None
                        
                        if not universe_item:
                            db.flush()  # stock_id 확보
                            universe_item = TradingUniverseItem(
                                universe_id=self.universe_id,
                                stock_id=stock.stock_id,
                                weight=1.0 / len(self.us_major_stocks),
                                is_active=True
                            )
                            db.add(universe_item)
                        
                        db.commit()
                        print(f"   ✅ {symbol}: {overview.get('name', symbol)}")
                        
                        # Rate limiting (Alpha Vantage: 5 calls/minute)
                        if i < len(self.us_major_stocks) - 1:
                            time.sleep(12)  # 12초 대기
                        
                    except Exception as e:
                        print(f"   ❌ {symbol}: {e}")
                        db.rollback()
                        continue
                
            print(f"✅ US 마스터 데이터 수집 완료: 신규 {collected}개, 업데이트 {updated}개")
            return True
            
        except Exception as e:
            print(f"❌ US 마스터 데이터 수집 실패: {e}")
            return False
    
    def collect_daily_price_data(self, days_back: int = 100):
        """US 종목 일봉 데이터 수집"""
        print(f"💰 US 일봉 데이터 수집 중... (최근 {days_back}일)")
        
        collected = 0
        
        try:
            with get_db_session() as db:
                # US 종목 목록 가져오기
                us_stocks = db.query(StockMaster).filter_by(
                    market_region=self.market_region.value,
                    is_active=True
                ).all()
                
                for i, stock in enumerate(us_stocks):
                    try:
                        symbol = stock.stock_code
                        print(f"📈 {symbol} 가격 데이터 수집 중... ({i+1}/{len(us_stocks)})")
                        
                        # 가격 데이터 가져오기
                        price_data = self.alpha_vantage.get_daily_prices(symbol, "compact")
                        
                        if not price_data:
                            print(f"   ⚠️ {symbol}: 가격 데이터 없음")
                            continue
                        
                        # 최근 데이터만 처리
                        recent_data = price_data[:days_back]
                        
                        for price_info in recent_data:
                            trade_date = datetime.strptime(price_info['date'], '%Y-%m-%d').date()
                            
                            # 기존 데이터 확인
                            existing_price = db.query(StockDailyPrice).filter_by(
                                stock_id=stock.stock_id,
                                trade_date=trade_date
                            ).first()
                            
                            if existing_price:
                                continue  # 이미 있는 데이터는 스킵
                            
                            # 일일 수익률 계산
                            daily_return_pct = None
                            try:
                                if len(recent_data) > recent_data.index(price_info) + 1:
                                    prev_close = recent_data[recent_data.index(price_info) + 1]['close']
                                    daily_return_pct = ((price_info['close'] - prev_close) / prev_close) * 100
                            except:
                                pass
                            
                            # VWAP 계산 (간단 버전)
                            vwap = (price_info['high'] + price_info['low'] + price_info['close']) / 3
                            
                            # 새 가격 데이터 생성
                            new_price = StockDailyPrice(
                                stock_id=stock.stock_id,
                                trade_date=trade_date,
                                open_price=Decimal(str(price_info['open'])),
                                high_price=Decimal(str(price_info['high'])),
                                low_price=Decimal(str(price_info['low'])),
                                close_price=Decimal(str(price_info['close'])),
                                adjusted_close_price=Decimal(str(price_info['adjusted_close'])),
                                volume=price_info['volume'],
                                daily_return_pct=daily_return_pct,
                                vwap=Decimal(str(vwap)),
                                typical_price=Decimal(str(vwap)),
                                is_adjusted=True,
                                has_dividend=price_info['dividend_amount'] > 0,
                                has_split=price_info['split_coefficient'] != 1.0,
                                data_source="Alpha Vantage"
                            )
                            
                            db.add(new_price)
                            collected += 1
                        
                        db.commit()
                        print(f"   ✅ {symbol}: {len(recent_data)}일 데이터 수집")
                        
                        # Rate limiting
                        if i < len(us_stocks) - 1:
                            time.sleep(12)  # 12초 대기
                        
                    except Exception as e:
                        print(f"   ❌ {stock.stock_code}: {e}")
                        db.rollback()
                        continue
                
            print(f"✅ US 가격 데이터 수집 완료: {collected}개 레코드")
            return True
            
        except Exception as e:
            print(f"❌ US 가격 데이터 수집 실패: {e}")
            return False
    
    def calculate_technical_indicators(self):
        """US 종목 기술적 지표 계산"""
        print("🔧 US 기술적 지표 계산 중...")
        
        calculated = 0
        
        try:
            with get_db_session() as db:
                # US 종목별로 처리
                us_stocks = db.query(StockMaster).filter_by(
                    market_region=self.market_region.value,
                    is_active=True
                ).all()
                
                for stock in us_stocks:
                    try:
                        symbol = stock.stock_code
                        print(f"📊 {symbol} 기술적 지표 계산...")
                        
                        # 가격 데이터 가져오기 (최근 200일)
                        price_data = db.query(StockDailyPrice).filter_by(
                            stock_id=stock.stock_id
                        ).order_by(StockDailyPrice.trade_date.desc()).limit(200).all()
                        
                        if len(price_data) < 20:
                            print(f"   ⚠️ {symbol}: 데이터 부족 ({len(price_data)}일)")
                            continue
                        
                        # 데이터 정렬 (오래된 것부터)
                        price_data.reverse()
                        
                        # 기술적 지표 계산
                        indicators = self._calculate_indicators_for_stock(price_data)
                        
                        # 각 날짜별로 지표 저장
                        for i, price in enumerate(price_data):
                            if i < 20:  # 최소 20일 데이터 필요
                                continue
                            
                            # 기존 지표 확인
                            existing_indicator = db.query(StockTechnicalIndicator).filter_by(
                                stock_id=stock.stock_id,
                                calculation_date=price.trade_date
                            ).first()
                            
                            if existing_indicator:
                                continue  # 이미 계산된 지표는 스킵
                            
                            # 새 지표 생성
                            new_indicator = StockTechnicalIndicator(
                                stock_id=stock.stock_id,
                                calculation_date=price.trade_date,
                                **indicators[i] if i < len(indicators) else {}
                            )
                            
                            db.add(new_indicator)
                            calculated += 1
                        
                        db.commit()
                        print(f"   ✅ {symbol}: 기술적 지표 계산 완료")
                        
                    except Exception as e:
                        print(f"   ❌ {stock.stock_code}: {e}")
                        db.rollback()
                        continue
                
            print(f"✅ US 기술적 지표 계산 완료: {calculated}개 레코드")
            return True
            
        except Exception as e:
            print(f"❌ US 기술적 지표 계산 실패: {e}")
            return False
    
    def _calculate_indicators_for_stock(self, price_data: List) -> List[Dict]:
        """종목별 기술적 지표 계산"""
        
        # 가격 데이터를 DataFrame으로 변환
        df = pd.DataFrame([{
            'date': p.trade_date,
            'open': float(p.open_price),
            'high': float(p.high_price),
            'low': float(p.low_price),
            'close': float(p.close_price),
            'volume': p.volume
        } for p in price_data])
        
        indicators = []
        
        for i in range(len(df)):
            if i < 20:  # 최소 데이터 필요
                indicators.append({})
                continue
            
            # 현재까지의 데이터
            current_data = df.iloc[:i+1]
            
            # 이동평균들
            sma_5 = current_data['close'].tail(5).mean() if len(current_data) >= 5 else None
            sma_10 = current_data['close'].tail(10).mean() if len(current_data) >= 10 else None
            sma_20 = current_data['close'].tail(20).mean() if len(current_data) >= 20 else None
            sma_50 = current_data['close'].tail(50).mean() if len(current_data) >= 50 else None
            
            # EMA 계산
            ema_12 = current_data['close'].ewm(span=12).mean().iloc[-1] if len(current_data) >= 12 else None
            ema_26 = current_data['close'].ewm(span=26).mean().iloc[-1] if len(current_data) >= 26 else None
            
            # RSI 계산 (14일)
            rsi_14 = self._calculate_rsi(current_data['close'], 14) if len(current_data) >= 14 else None
            
            # 볼린저 밴드 (20일, 2 표준편차)
            bb_data = self._calculate_bollinger_bands(current_data['close'], 20, 2) if len(current_data) >= 20 else (None, None, None, None)
            bb_upper, bb_middle, bb_lower, bb_percent = bb_data
            
            # 거래량 비율
            volume_sma_20 = current_data['volume'].tail(20).mean() if len(current_data) >= 20 else None
            volume_ratio = current_data['volume'].iloc[-1] / volume_sma_20 if volume_sma_20 else None
            
            # MACD
            macd_data = self._calculate_macd(current_data['close']) if len(current_data) >= 26 else (None, None, None)
            macd_line, macd_signal, macd_histogram = macd_data
            
            indicators.append({
                'sma_5': sma_5,
                'sma_10': sma_10,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'ema_12': ema_12,
                'ema_26': ema_26,
                'rsi_14': rsi_14,
                'bb_upper_20_2': bb_upper,
                'bb_middle_20': bb_middle,
                'bb_lower_20_2': bb_lower,
                'bb_percent': bb_percent,
                'volume_ratio': volume_ratio,
                'macd_line': macd_line,
                'macd_signal': macd_signal,
                'macd_histogram': macd_histogram,
                'calculation_version': 'v2.0'
            })
        
        return indicators
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """RSI 계산"""
        if len(prices) < period + 1:
            return None
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2):
        """볼린저 밴드 계산"""
        if len(prices) < period:
            return None, None, None, None
        
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        # %B 계산 (현재가의 볼린저 밴드 내 위치)
        current_price = prices.iloc[-1]
        bb_percent = (current_price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
        
        return upper.iloc[-1], sma.iloc[-1], lower.iloc[-1], bb_percent
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD 계산"""
        if len(prices) < slow:
            return None, None, None
        
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal).mean()
        macd_histogram = macd_line - macd_signal
        
        return macd_line.iloc[-1], macd_signal.iloc[-1], macd_histogram.iloc[-1]
    
    def run_full_collection(self):
        """전체 US 데이터 수집 실행"""
        print("🇺🇸 US 주식 데이터 수집 시작")
        print("="*60)
        
        start_time = datetime.now()
        
        try:
            # 1. 유니버스 설정
            if not self.ensure_trading_universe():
                return False
            
            # 2. 마스터 데이터 수집
            if not self.collect_stock_master_data():
                return False
            
            # 3. 가격 데이터 수집
            if not self.collect_daily_price_data():
                return False
            
            # 4. 기술적 지표 계산
            if not self.calculate_technical_indicators():
                return False
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            print(f"\n✅ US 데이터 수집 완료!")
            print(f"📊 소요 시간: {duration}")
            print(f"🎯 수집 종목: {len(self.us_major_stocks)}개")
            
            return True
            
        except Exception as e:
            print(f"❌ US 데이터 수집 실패: {e}")
            return False


def main():
    """메인 실행 함수"""
    collector = USDataCollector()
    success = collector.run_full_collection()
    
    if success:
        print("\n🎉 US 데이터 수집 성공적으로 완료!")
    else:
        print("\n💥 US 데이터 수집 실패")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
