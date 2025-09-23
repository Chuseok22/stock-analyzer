#!/usr/bin/env python3
"""
통합 데이터 수집 서비스
기존 중복된 데이터 수집 기능들을 하나로 통합
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
import asyncio

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockMaster, StockDailyPrice, MarketRegion
from app.services.kis_api import KISAPIClient
from app.services.alpha_vantage_api import AlphaVantageAPIClient
from app.utils.structured_logger import StructuredLogger


class UnifiedDataCollector:
    """통합 데이터 수집기 - 모든 데이터 수집 기능을 하나로 통합"""
    
    def __init__(self):
        self.logger = StructuredLogger("data_collection")
        self.kis_client = KISAPIClient()
        self.alpha_vantage_client = AlphaVantageAPIClient()
        
        # 주요 종목 리스트
        self.kr_symbols = [
            '005930',  # 삼성전자
            '000660',  # SK하이닉스
            '035420',  # NAVER
            '005380',  # 현대차
            '000270',  # 기아
            '051910',  # LG화학
            '068270',  # 셀트리온
            '028260',  # 삼성물산
            '055550',  # 신한지주
            '086790',  # 하나금융지주
            '003670',  # 포스코홀딩스
            '096770',  # SK이노베이션
            '032830',  # 삼성생명
            '017670',  # SK텔레콤
            '090430',  # 아모레퍼시픽
            '009150',  # 삼성전기
            '018260',  # 삼성에스디에스
            '323410',  # 카카오뱅크
            '377300',  # 카카오페이
            '035720',  # 카카오
        ]
        
        self.us_symbols = [
            'AAPL',   # Apple
            'MSFT',   # Microsoft
            'GOOGL',  # Alphabet
            'AMZN',   # Amazon
            'TSLA',   # Tesla
            'META',   # Meta
            'NVDA',   # NVIDIA
            'NFLX',   # Netflix
            'ADBE',   # Adobe
            'CRM',    # Salesforce
            'PYPL',   # PayPal
            'INTC',   # Intel
            'AMD',    # AMD
            'QCOM',   # Qualcomm
            'AVGO',   # Broadcom
            'TXN',    # Texas Instruments
            'ORCL',   # Oracle
            'IBM',    # IBM
            'NOW',    # ServiceNow
            'UBER',   # Uber
        ]
    
    async def collect_daily_data(self) -> bool:
        """일일 데이터 수집 (한국 + 미국)"""
        self.logger.info("📊 일일 데이터 수집 시작")
        
        try:
            # 1. 한국 데이터 수집
            kr_success = await self.collect_korean_daily_data()
            
            # 2. 미국 데이터 수집  
            us_success = await self.collect_us_daily_data()
            
            if kr_success or us_success:
                self.logger.info("✅ 일일 데이터 수집 완료")
                return True
            else:
                self.logger.warning("⚠️ 모든 데이터 수집 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 일일 데이터 수집 오류: {e}")
            return False
    
    async def collect_korean_daily_data(self) -> bool:
        """한국 시장 일일 데이터 수집"""
        self.logger.info("🇰🇷 한국 시장 최신 데이터 수집")
        
        try:
            with get_db_session() as db:
                # 활성 한국 종목 목록
                kr_stocks = db.query(StockMaster).filter_by(
                    market_region=MarketRegion.KR.value,
                    is_active=True
                ).all()
                
                if not kr_stocks:
                    self.logger.warning("한국 종목 없음")
                    return False
                
                success_count = 0
                today = date.today()
                
                self.logger.info(f"대상 종목: {len(kr_stocks)}개")
                
                for stock in kr_stocks:
                    try:
                        # 오늘 데이터가 이미 있는지 확인
                        existing = db.query(StockDailyPrice).filter_by(
                            stock_id=stock.stock_id,
                            trade_date=today
                        ).first()
                        
                        if existing:
                            self.logger.debug(f"   {stock.stock_code}: 이미 존재")
                            continue
                        
                        # KIS API에서 데이터 가져오기
                        today = date.today()
                        yesterday = today - timedelta(days=1)
                        price_data = self.kis_client.get_stock_price_daily(
                            stock.stock_code, 
                            yesterday.strftime('%Y%m%d'), 
                            today.strftime('%Y%m%d')
                        )
                        
                        if not price_data:
                            self.logger.debug(f"   {stock.stock_code}: KIS 데이터 없음")
                            continue
                        
                        # 가장 최근 데이터 사용
                        latest_data = price_data[-1] if price_data else None
                        
                        if not latest_data:
                            self.logger.debug(f"   {stock.stock_code}: 유효한 데이터 없음")
                            continue
                        
                        # 데이터 변환 (KIS API 응답 형식에 맞춤)
                        trade_date = datetime.strptime(latest_data['date'], '%Y%m%d').date()
                        open_price = float(latest_data['open'])
                        high_price = float(latest_data['high'])
                        low_price = float(latest_data['low'])
                        close_price = float(latest_data['close'])
                        volume = int(latest_data['volume'])
                        
                        # 이미 해당 날짜 데이터가 있는지 재확인
                        existing_latest = db.query(StockDailyPrice).filter_by(
                            stock_id=stock.stock_id,
                            trade_date=trade_date
                        ).first()
                        
                        if existing_latest:
                            continue
                        
                        # 새 데이터 저장
                        new_price = StockDailyPrice(
                            stock_id=stock.stock_id,
                            trade_date=trade_date,
                            open_price=open_price,
                            high_price=high_price,
                            low_price=low_price,
                            close_price=close_price,
                            adjusted_close_price=close_price,
                            volume=volume,
                            data_source='kis_api'
                        )
                        
                        # 일일 수익률 계산
                        prev_price = db.query(StockDailyPrice).filter(
                            StockDailyPrice.stock_id == stock.stock_id,
                            StockDailyPrice.trade_date < trade_date
                        ).order_by(StockDailyPrice.trade_date.desc()).first()
                        
                        if prev_price:
                            new_price.daily_return_pct = (
                                (float(latest_data['Close']) - float(prev_price.close_price)) / 
                                float(prev_price.close_price) * 100
                            )
                            new_price.price_change = float(latest_data['Close']) - float(prev_price.close_price)
                            new_price.price_change_pct = new_price.daily_return_pct
                        
                        db.add(new_price)
                        db.commit()
                        
                        success_count += 1
                    except Exception as e:
                        self.logger.error(f"   ❌ {stock.stock_code} 수집 실패: {e}")
                        continue
                
                self.logger.info(f"🎯 한국 데이터 수집 결과: {success_count}/{len(kr_stocks)}개 성공")
                return success_count > 0
                
        except Exception as e:
            self.logger.error(f"한국 데이터 수집 실패: {e}")
            return False
    
    async def collect_us_daily_data(self) -> bool:
        """미국 시장 일일 데이터 수집"""
        self.logger.info("🇺🇸 미국 시장 최신 데이터 수집")
        
        try:
            with get_db_session() as db:
                # 활성 미국 종목 목록
                us_stocks = db.query(StockMaster).filter_by(
                    market_region=MarketRegion.US.value,
                    is_active=True
                ).all()
                
                if not us_stocks:
                    self.logger.warning("미국 종목 없음")
                    return False
                
                success_count = 0
                today = date.today()
                
                self.logger.info(f"대상 종목: {len(us_stocks)}개")
                
                for stock in us_stocks:
                    try:
                        # 오늘 데이터가 이미 있는지 확인
                        existing = db.query(StockDailyPrice).filter_by(
                            stock_id=stock.stock_id,
                            trade_date=today
                        ).first()
                        
                        if existing:
                            self.logger.debug(f"   {stock.stock_code}: 이미 존재")
                            continue
                        
                        # Alpha Vantage API에서 데이터 가져오기
                        price_data = self.alpha_vantage_api_client.get_daily_prices(stock.stock_code)
                        
                        if not price_data:
                            self.logger.debug(f"   {stock.stock_code}: Alpha Vantage 데이터 없음")
                            continue
                        
                        # 가장 최근 데이터 사용
                        latest_data = price_data[-1] if price_data else None
                        
                        if not latest_data:
                            self.logger.debug(f"   {stock.stock_code}: 유효한 데이터 없음")
                            continue
                        
                        # 데이터 변환 (Alpha Vantage API 응답 형식에 맞춤)
                        trade_date = datetime.strptime(latest_data['date'], '%Y-%m-%d').date()
                        open_price = float(latest_data['open'])
                        high_price = float(latest_data['high'])
                        low_price = float(latest_data['low'])
                        close_price = float(latest_data['close'])
                        volume = int(latest_data['volume'])
                        
                        # 이미 해당 날짜 데이터가 있는지 재확인
                        existing_latest = db.query(StockDailyPrice).filter_by(
                            stock_id=stock.stock_id,
                            trade_date=trade_date
                        ).first()
                        
                        if existing_latest:
                            continue
                        
                        # 새 데이터 저장
                        new_price = StockDailyPrice(
                            stock_id=stock.stock_id,
                            trade_date=trade_date,
                            open_price=open_price,
                            high_price=high_price,
                            low_price=low_price,
                            close_price=close_price,
                            adjusted_close_price=close_price,
                            volume=volume,
                            data_source='alpha_vantage_api'
                        )
                        
                        # 일일 수익률 계산
                        prev_price = db.query(StockDailyPrice).filter(
                            StockDailyPrice.stock_id == stock.stock_id,
                            StockDailyPrice.trade_date < trade_date
                        ).order_by(StockDailyPrice.trade_date.desc()).first()
                        
                        if prev_price:
                            new_price.daily_return_pct = (
                                (close_price - float(prev_price.close_price)) / 
                                float(prev_price.close_price) * 100
                            )
                            new_price.price_change = close_price - float(prev_price.close_price)
                            new_price.price_change_pct = new_price.daily_return_pct
                        
                        db.add(new_price)
                        db.commit()
                        
                        success_count += 1
                        self.logger.debug(f"   ✅ {stock.stock_code}: {trade_date}")
                        
                    except Exception as e:
                        self.logger.error(f"   ❌ {stock.stock_code} 수집 실패: {e}")
                        continue
                
                self.logger.info(f"🎯 미국 데이터 수집 결과: {success_count}/{len(us_stocks)}개 성공")
                return success_count > 0
                
        except Exception as e:
            self.logger.error(f"미국 데이터 수집 실패: {e}")
            return False
    
    async def collect_historical_data(self, days: int = 365) -> bool:
        """역사적 데이터 수집 (한국 + 미국)"""
        self.logger.info(f"📊 {days}일 역사적 데이터 수집 시작")
        
        try:
            # 1. 한국 역사적 데이터 수집
            kr_success = await self.collect_korean_historical_data(days)
            
            # 2. 미국 역사적 데이터 수집  
            us_success = await self.collect_us_historical_data(days)
            
            if kr_success and us_success:
                self.logger.info("✅ 역사적 데이터 수집 완료")
                return True
            else:
                self.logger.warning("⚠️ 일부 데이터 수집 실패")
                return kr_success or us_success
                
        except Exception as e:
            self.logger.error(f"❌ 역사적 데이터 수집 오류: {e}")
            return False
    
    async def collect_korean_historical_data(self, days: int = 365) -> bool:
        """한국 시장 역사적 데이터 수집"""
        self.logger.info(f"🇰🇷 한국 시장 {days}일 역사적 데이터 수집")
        
        try:
            with get_db_session() as db:
                success_count = 0
                
                for symbol in self.kr_symbols:
                    try:
                        # 종목 마스터 확인/생성
                        stock = db.query(StockMaster).filter_by(
                            market_region=MarketRegion.KR.value,
                            stock_code=symbol
                        ).first()
                        
                        if not stock:
                            # 새 종목 생성
                            stock_info = await self._get_korean_stock_info(symbol)
                            stock = StockMaster(
                                market_region=MarketRegion.KR.value,
                                stock_code=symbol,
                                stock_name=stock_info.get('name', symbol),
                                stock_name_en=stock_info.get('name_en'),
                                market_name=stock_info.get('market', 'KOSPI'),
                                sector_classification=stock_info.get('sector'),
                                data_provider='kis_api',
                                is_active=True
                            )
                            db.add(stock)
                            db.commit()
                            db.refresh(stock)
                        
                        # 이미 있는 데이터 확인
                        existing_count = db.query(StockDailyPrice).filter_by(
                            stock_id=stock.stock_id
                        ).count()
                        
                        if existing_count >= days:
                            self.logger.debug(f"   {symbol}: 충분한 데이터 존재 ({existing_count}일)")
                            success_count += 1
                            continue
                        
                        # KIS API에서 역사적 데이터 수집
                        end_date = date.today()
                        start_date = end_date - timedelta(days=days + 30)
                        price_data = self.kis_client.get_stock_price_daily(
                            symbol,
                            start_date.strftime('%Y%m%d'),
                            end_date.strftime('%Y%m%d')
                        )
                        
                        if not price_data:
                            self.logger.warning(f"   {symbol}: KIS 데이터 없음")
                            continue
                        
                        # 기존 데이터와 중복 제거
                        new_records = 0
                        for data_row in price_data:
                            trade_date = datetime.strptime(data_row['date'], '%Y%m%d').date()
                            
                            existing = db.query(StockDailyPrice).filter_by(
                                stock_id=stock.stock_id,
                                trade_date=trade_date
                            ).first()
                            
                            if existing:
                                continue
                            
                            new_price = StockDailyPrice(
                                stock_id=stock.stock_id,
                                trade_date=trade_date,
                                open_price=float(row['Open']),
                                high_price=float(row['High']),
                                low_price=float(row['Low']),
                                close_price=float(row['Close']),
                                adjusted_close_price=float(row['Close']),
                                volume=int(row['Volume']),
                                data_source='kis_api'
                            )
                            
                            db.add(new_price)
                            new_records += 1
                        
                        if new_records > 0:
                            db.commit()
                            self.logger.info(f"   ✅ {symbol}: {new_records}일 데이터 추가")
                        
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"   ❌ {symbol} 수집 실패: {e}")
                        continue
                
                self.logger.info(f"🎯 한국 역사적 데이터 수집 결과: {success_count}/{len(self.kr_symbols)}개 성공")
                return success_count > 0
                
        except Exception as e:
            self.logger.error(f"한국 역사적 데이터 수집 실패: {e}")
            return False
    
    async def collect_us_historical_data(self, days: int = 365) -> bool:
        """미국 시장 역사적 데이터 수집"""
        self.logger.info(f"🇺🇸 미국 시장 {days}일 역사적 데이터 수집")
        
        try:
            with get_db_session() as db:
                success_count = 0
                
                for symbol in self.us_symbols:
                    try:
                        # 종목 마스터 확인/생성
                        stock = db.query(StockMaster).filter_by(
                            market_region=MarketRegion.US.value,
                            stock_code=symbol
                        ).first()
                        
                        if not stock:
                            # 새 종목 생성
                            stock_info = await self._get_us_stock_info(symbol)
                            stock = StockMaster(
                                market_region=MarketRegion.US.value,
                                stock_code=symbol,
                                stock_name=stock_info.get('name', symbol),
                                stock_name_en=stock_info.get('name', symbol),
                                market_name=stock_info.get('market', 'NASDAQ'),
                                sector_classification=stock_info.get('sector'),
                                data_provider='alpha_vantage_api',
                                is_active=True
                            )
                            db.add(stock)
                            db.commit()
                            db.refresh(stock)
                        
                        # 이미 있는 데이터 확인
                        existing_count = db.query(StockDailyPrice).filter_by(
                            stock_id=stock.stock_id
                        ).count()
                        
                        if existing_count >= days:
                            self.logger.debug(f"   {symbol}: 충분한 데이터 존재 ({existing_count}일)")
                            success_count += 1
                            continue
                        
                        # Alpha Vantage API에서 역사적 데이터 수집
                        price_data = self.alpha_vantage_api_client.get_historical_prices(symbol, days=days + 30)
                        
                        if not price_data:
                            self.logger.warning(f"   {symbol}: Alpha Vantage 데이터 없음")
                            continue
                        
                        # 기존 데이터와 중복 제거
                        new_records = 0
                        for data_row in price_data:
                            trade_date = datetime.strptime(data_row['date'], '%Y-%m-%d').date()
                            
                            existing = db.query(StockDailyPrice).filter_by(
                                stock_id=stock.stock_id,
                                trade_date=trade_date
                            ).first()
                            
                            if existing:
                                continue
                            
                            new_price = StockDailyPrice(
                                stock_id=stock.stock_id,
                                trade_date=trade_date,
                                open_price=float(row['Open']),
                                high_price=float(row['High']),
                                low_price=float(row['Low']),
                                close_price=float(row['Close']),
                                adjusted_close_price=float(row['Close']),
                                volume=int(row['Volume']),
                                data_source='kis_api'
                            )
                            
                            db.add(new_price)
                            new_records += 1
                        
                        if new_records > 0:
                            db.commit()
                            self.logger.info(f"   ✅ {symbol}: {new_records}일 데이터 추가")
                        
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"   ❌ {symbol} 수집 실패: {e}")
                        continue
                
                self.logger.info(f"🎯 미국 역사적 데이터 수집 결과: {success_count}/{len(self.us_symbols)}개 성공")
                return success_count > 0
                
        except Exception as e:
            self.logger.error(f"미국 역사적 데이터 수집 실패: {e}")
            return False
    
    async def _get_korean_stock_info(self, symbol: str) -> Dict[str, Any]:
        """한국 종목 정보 가져오기"""
        try:
            # KIS API를 통한 종목 정보 조회 (간단한 버전)
            return {
                'name': f'KR_{symbol}',
                'name_en': f'KR_{symbol}',
                'market': 'KOSPI' if symbol in ['005930', '000660', '035420'] else 'KOSDAQ',
                'sector': 'Technology'
            }
        except:
            return {
                'name': symbol,
                'name_en': symbol,
                'market': 'KOSPI',
                'sector': 'Technology'
            }
    
    async def _get_us_stock_info(self, symbol: str) -> Dict[str, Any]:
        """미국 종목 정보 가져오기"""
        try:
            # Alpha Vantage API를 통한 종목 정보 조회 (간단한 버전)
            return {
                'name': symbol,
                'name_en': symbol,
                'market': 'NASDAQ',
                'sector': 'Technology'
            }
        except:
            return {
                'name': symbol,
                'name_en': symbol,
                'market': 'NASDAQ', 
                'sector': 'Technology'
            }


# CLI 실행 함수
async def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='통합 데이터 수집기')
    parser.add_argument('--daily', action='store_true', help='일일 데이터 수집')
    parser.add_argument('--historical', type=int, default=365, help='역사적 데이터 수집 (일수)')
    parser.add_argument('--kr-only', action='store_true', help='한국 데이터만')
    parser.add_argument('--us-only', action='store_true', help='미국 데이터만')
    
    args = parser.parse_args()
    
    collector = UnifiedDataCollector()
    
    try:
        if args.daily:
            if args.kr_only:
                success = await collector.collect_korean_daily_data()
            elif args.us_only:
                success = await collector.collect_us_daily_data()
            else:
                success = await collector.collect_daily_data()
        else:
            if args.kr_only:
                success = await collector.collect_korean_historical_data(args.historical)
            elif args.us_only:
                success = await collector.collect_us_historical_data(args.historical)
            else:
                success = await collector.collect_historical_data(args.historical)
        
        return success
        
    except Exception as e:
        print(f"❌ 데이터 수집 실패: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)