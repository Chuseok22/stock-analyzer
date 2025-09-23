#!/usr/bin/env python3
"""
동적 종목 유니버스 관리 시스템
- 시가총액, 거래량, 변동성 기반 종목 선별
- 섹터 다양성 보장
- 정기적 유니버스 업데이트
- 성과 기반 종목 순환
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import asyncio

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockMaster, StockDailyPrice, MarketRegion
from app.services.kis_api import KISAPIClient
from app.services.alpha_vantage_api import AlphaVantageAPIClient
from app.utils.structured_logger import StructuredLogger


class UniverseSelectionCriteria(Enum):
    """유니버스 선별 기준"""
    MARKET_CAP = "market_cap"           # 시가총액 기준
    LIQUIDITY = "liquidity"             # 유동성 기준
    VOLATILITY = "volatility"           # 변동성 기준
    MOMENTUM = "momentum"               # 모멘텀 기준
    SECTOR_BALANCE = "sector_balance"   # 섹터 균형
    PERFORMANCE = "performance"         # 과거 성과


@dataclass
class UniverseStock:
    """유니버스 종목 정보"""
    stock_code: str
    stock_name: str
    market_region: str
    market_cap: float
    sector: str
    liquidity_score: float
    volatility_score: float
    momentum_score: float
    selection_reason: List[str]
    last_updated: datetime


class DynamicUniverseManager:
    """동적 종목 유니버스 관리자"""
    
    def __init__(self):
        self.logger = StructuredLogger("universe_manager")
        self.kis_client = KISAPIClient()
        self.alpha_client = AlphaVantageAPIClient()
        
        # 유니버스 설정
        self.kr_universe_size = 100  # 한국 종목 수
        self.us_universe_size = 100  # 미국 종목 수
        self.sector_max_weight = 0.3  # 섹터별 최대 비중
        
        # 선별 기준 가중치
        self.selection_weights = {
            UniverseSelectionCriteria.MARKET_CAP: 0.25,
            UniverseSelectionCriteria.LIQUIDITY: 0.25,
            UniverseSelectionCriteria.VOLATILITY: 0.15,
            UniverseSelectionCriteria.MOMENTUM: 0.15,
            UniverseSelectionCriteria.SECTOR_BALANCE: 0.10,
            UniverseSelectionCriteria.PERFORMANCE: 0.10
        }
        
        self.logger.info("동적 종목 유니버스 관리자 초기화 완료")
    
    async def generate_dynamic_universe(self, region: MarketRegion) -> List[UniverseStock]:
        """동적 종목 유니버스 생성"""
        self.logger.info(f"🌍 {region.value} 동적 유니버스 생성 시작")
        
        try:
            # 1. 기초 종목 데이터 수집
            base_stocks = await self._collect_base_stock_data(region)
            if not base_stocks:
                self.logger.error(f"{region.value} 기초 데이터 수집 실패")
                return []
            
            self.logger.info(f"   📊 기초 종목 수: {len(base_stocks)}개")
            
            # 2. 각 선별 기준별 점수 계산
            scored_stocks = await self._calculate_selection_scores(base_stocks, region)
            
            # 3. 종합 점수 계산 및 순위 결정
            ranked_stocks = self._calculate_composite_scores(scored_stocks)
            
            # 4. 섹터 균형 조정
            balanced_stocks = self._apply_sector_balance(ranked_stocks, region)
            
            # 5. 최종 유니버스 선별
            target_size = self.kr_universe_size if region == MarketRegion.KR else self.us_universe_size
            final_universe = balanced_stocks[:target_size]
            
            self.logger.info(f"   ✅ {region.value} 동적 유니버스 생성 완료: {len(final_universe)}개 종목")
            return final_universe
            
        except Exception as e:
            self.logger.error(f"❌ {region.value} 동적 유니버스 생성 실패: {e}")
            return []
    
    async def _collect_base_stock_data(self, region: MarketRegion) -> List[Dict[str, Any]]:
        """기초 종목 데이터 수집"""
        self.logger.info(f"📊 {region.value} 기초 데이터 수집 중...")
        
        try:
            with get_db_session() as db:
                # 활성 종목 조회 (최소 시가총액 필터링)
                min_market_cap = 1000000000000 if region == MarketRegion.KR else 1000000000  # 한국: 1조원, 미국: 10억달러
                
                stocks_query = db.query(StockMaster).filter(
                    StockMaster.market_region == region.value,
                    StockMaster.is_active == True,
                    StockMaster.is_delisted == False,
                    StockMaster.market_capitalization >= min_market_cap
                )
                
                stocks = stocks_query.all()
                
                if not stocks:
                    return []
                
                # 최근 거래 데이터 확인 (유동성 필터)
                base_stocks = []
                recent_date = datetime.now().date() - timedelta(days=7)
                
                for stock in stocks:
                    # 최근 거래 데이터 확인
                    recent_trades = db.query(StockDailyPrice).filter(
                        StockDailyPrice.stock_id == stock.stock_id,
                        StockDailyPrice.trade_date >= recent_date,
                        StockDailyPrice.volume > 0
                    ).count()
                    
                    # 최근 5일 중 3일 이상 거래된 종목만 포함
                    if recent_trades >= 3:
                        base_stocks.append({
                            'stock_id': stock.stock_id,
                            'stock_code': stock.stock_code,
                            'stock_name': stock.stock_name,
                            'market_region': stock.market_region,
                            'market_cap': float(stock.market_capitalization) if stock.market_capitalization else 0,
                            'sector': stock.sector_classification or 'UNKNOWN',
                            'listing_date': stock.listing_date
                        })
                
                self.logger.info(f"   ✅ {region.value} 활성 종목: {len(base_stocks)}개")
                return base_stocks
                
        except Exception as e:
            self.logger.error(f"❌ {region.value} 기초 데이터 수집 실패: {e}")
            return []
    
    async def _calculate_selection_scores(self, stocks: List[Dict], region: MarketRegion) -> List[Dict]:
        """각 선별 기준별 점수 계산"""
        self.logger.info(f"📈 {region.value} 선별 점수 계산 중...")
        
        try:
            scored_stocks = []
            
            for stock in stocks:
                try:
                    # 기본 점수 구조
                    scores = {
                        'market_cap_score': 0.0,
                        'liquidity_score': 0.0,
                        'volatility_score': 0.0,
                        'momentum_score': 0.0,
                        'sector_balance_score': 0.0,
                        'performance_score': 0.0
                    }
                    
                    # 1. 시가총액 점수 (정규화)
                    scores['market_cap_score'] = self._calculate_market_cap_score(stock['market_cap'], stocks)
                    
                    # 2. 유동성 점수 (거래량 기반)
                    scores['liquidity_score'] = await self._calculate_liquidity_score(stock['stock_id'])
                    
                    # 3. 변동성 점수 (적정 변동성 선호)
                    scores['volatility_score'] = await self._calculate_volatility_score(stock['stock_id'])
                    
                    # 4. 모멘텀 점수 (최근 성과)
                    scores['momentum_score'] = await self._calculate_momentum_score(stock['stock_id'])
                    
                    # 5. 섹터 균형 점수 (나중에 전체적으로 계산)
                    scores['sector_balance_score'] = 1.0  # 기본값
                    
                    # 6. 과거 성과 점수 (백테스팅 기반)
                    scores['performance_score'] = await self._calculate_performance_score(stock['stock_id'])
                    
                    # 종목 정보에 점수 추가
                    stock_with_scores = stock.copy()
                    stock_with_scores.update(scores)
                    
                    scored_stocks.append(stock_with_scores)
                    
                except Exception as e:
                    self.logger.warning(f"종목 {stock['stock_code']} 점수 계산 실패: {e}")
                    continue
            
            self.logger.info(f"   ✅ {region.value} 점수 계산 완료: {len(scored_stocks)}개")
            return scored_stocks
            
        except Exception as e:
            self.logger.error(f"❌ {region.value} 점수 계산 실패: {e}")
            return []
    
    def _calculate_market_cap_score(self, market_cap: float, all_stocks: List[Dict]) -> float:
        """시가총액 점수 계산 (상위 종목 선호)"""
        try:
            all_caps = [s['market_cap'] for s in all_stocks if s['market_cap'] > 0]
            if not all_caps:
                return 0.5
            
            # 상위 20% 이내면 만점, 하위로 갈수록 점수 감소
            percentile = np.percentile(all_caps, [20, 40, 60, 80])
            
            if market_cap >= percentile[3]:  # 상위 20%
                return 1.0
            elif market_cap >= percentile[2]:  # 상위 40%
                return 0.8
            elif market_cap >= percentile[1]:  # 상위 60%
                return 0.6
            elif market_cap >= percentile[0]:  # 상위 80%
                return 0.4
            else:
                return 0.2
                
        except Exception:
            return 0.5
    
    async def _calculate_liquidity_score(self, stock_id: int) -> float:
        """유동성 점수 계산 (거래량 기반)"""
        try:
            with get_db_session() as db:
                # 최근 30일 거래량 데이터
                recent_date = datetime.now().date() - timedelta(days=30)
                
                volumes = db.query(StockDailyPrice.volume).filter(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date >= recent_date,
                    StockDailyPrice.volume > 0
                ).all()
                
                if not volumes:
                    return 0.1
                
                volume_list = [float(v[0]) for v in volumes]
                avg_volume = np.mean(volume_list)
                volume_consistency = 1.0 - (np.std(volume_list) / avg_volume if avg_volume > 0 else 1.0)
                
                # 거래량과 일관성 모두 고려
                volume_score = min(avg_volume / 1000000, 1.0)  # 100만주 기준 정규화
                consistency_score = max(0.0, min(volume_consistency, 1.0))
                
                return (volume_score * 0.7 + consistency_score * 0.3)
                
        except Exception:
            return 0.1
    
    async def _calculate_volatility_score(self, stock_id: int) -> float:
        """변동성 점수 계산 (적정 변동성 선호)"""
        try:
            with get_db_session() as db:
                # 최근 60일 일일 수익률 데이터
                recent_date = datetime.now().date() - timedelta(days=60)
                
                prices = db.query(StockDailyPrice).filter(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date >= recent_date
                ).order_by(StockDailyPrice.trade_date).all()
                
                if len(prices) < 20:
                    return 0.1
                
                # 일일 수익률 계산
                returns = []
                for i in range(1, len(prices)):
                    prev_price = float(prices[i-1].close_price)
                    curr_price = float(prices[i].close_price)
                    if prev_price > 0:
                        daily_return = (curr_price - prev_price) / prev_price
                        returns.append(daily_return)
                
                if not returns:
                    return 0.1
                
                # 연환산 변동성
                volatility = np.std(returns) * np.sqrt(252)
                
                # 적정 변동성 범위 (15-35%)에서 높은 점수
                if 0.15 <= volatility <= 0.35:
                    return 1.0
                elif 0.10 <= volatility < 0.15 or 0.35 < volatility <= 0.50:
                    return 0.7
                elif 0.05 <= volatility < 0.10 or 0.50 < volatility <= 0.70:
                    return 0.4
                else:
                    return 0.1
                    
        except Exception:
            return 0.1
    
    async def _calculate_momentum_score(self, stock_id: int) -> float:
        """모멘텀 점수 계산 (최근 성과)"""
        try:
            with get_db_session() as db:
                # 최근 3개월 데이터
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=90)
                
                prices = db.query(StockDailyPrice).filter(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date >= start_date,
                    StockDailyPrice.trade_date <= end_date
                ).order_by(StockDailyPrice.trade_date).all()
                
                if len(prices) < 30:
                    return 0.1
                
                # 기간별 수익률 계산
                first_price = float(prices[0].close_price)
                last_price = float(prices[-1].close_price)
                
                if first_price <= 0:
                    return 0.1
                
                total_return = (last_price - first_price) / first_price
                
                # 최근 1개월, 2개월, 3개월 수익률 가중 평균
                month_1_idx = max(0, len(prices) - 20)
                month_2_idx = max(0, len(prices) - 40)
                
                returns = []
                if month_1_idx < len(prices):
                    month_1_return = (last_price - float(prices[month_1_idx].close_price)) / float(prices[month_1_idx].close_price)
                    returns.append(month_1_return * 0.5)  # 최근 1개월 50% 가중치
                
                if month_2_idx < len(prices):
                    month_2_return = (last_price - float(prices[month_2_idx].close_price)) / float(prices[month_2_idx].close_price)
                    returns.append(month_2_return * 0.3)  # 최근 2개월 30% 가중치
                
                returns.append(total_return * 0.2)  # 전체 기간 20% 가중치
                
                weighted_return = sum(returns)
                
                # 수익률을 점수로 변환 (0-1 범위)
                if weighted_return > 0.10:  # 10% 이상
                    return 1.0
                elif weighted_return > 0.05:  # 5-10%
                    return 0.8
                elif weighted_return > 0:  # 0-5%
                    return 0.6
                elif weighted_return > -0.05:  # 0 ~ -5%
                    return 0.4
                elif weighted_return > -0.10:  # -5 ~ -10%
                    return 0.2
                else:  # -10% 미만
                    return 0.1
                    
        except Exception:
            return 0.1
    
    async def _calculate_performance_score(self, stock_id: int) -> float:
        """과거 성과 점수 계산 (백테스팅 기반)"""
        try:
            # 간단한 기술적 지표 기반 성과 평가
            with get_db_session() as db:
                # 최근 6개월 데이터
                recent_date = datetime.now().date() - timedelta(days=180)
                
                prices = db.query(StockDailyPrice).filter(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date >= recent_date
                ).order_by(StockDailyPrice.trade_date).all()
                
                if len(prices) < 60:
                    return 0.5
                
                # 간단한 이동평균 크로스오버 전략 백테스팅
                closes = [float(p.close_price) for p in prices]
                
                # 20일, 60일 이동평균
                ma_20 = pd.Series(closes).rolling(20).mean().tolist()
                ma_60 = pd.Series(closes).rolling(60).mean().tolist()
                
                # 크로스오버 신호 기반 수익률 계산
                signals = []
                for i in range(60, len(closes)):
                    if ma_20[i] > ma_60[i] and ma_20[i-1] <= ma_60[i-1]:  # 골든 크로스
                        signals.append((i, 'BUY'))
                    elif ma_20[i] < ma_60[i] and ma_20[i-1] >= ma_60[i-1]:  # 데드 크로스
                        signals.append((i, 'SELL'))
                
                # 신호 기반 수익률 계산
                if len(signals) < 2:
                    return 0.5
                
                total_return = 0.0
                position = None
                entry_price = 0.0
                
                for idx, signal in signals:
                    if signal == 'BUY' and position != 'LONG':
                        if position == 'SHORT':
                            # 숏 포지션 청산
                            total_return += (entry_price - closes[idx]) / entry_price
                        position = 'LONG'
                        entry_price = closes[idx]
                    elif signal == 'SELL' and position != 'SHORT':
                        if position == 'LONG':
                            # 롱 포지션 청산
                            total_return += (closes[idx] - entry_price) / entry_price
                        position = 'SHORT'
                        entry_price = closes[idx]
                
                # 성과를 점수로 변환
                if total_return > 0.15:  # 15% 이상
                    return 1.0
                elif total_return > 0.05:  # 5-15%
                    return 0.8
                elif total_return > -0.05:  # -5 ~ 5%
                    return 0.6
                elif total_return > -0.15:  # -15 ~ -5%
                    return 0.4
                else:  # -15% 미만
                    return 0.2
                    
        except Exception:
            return 0.5
    
    def _calculate_composite_scores(self, scored_stocks: List[Dict]) -> List[Dict]:
        """종합 점수 계산 및 순위 결정"""
        self.logger.info("📊 종합 점수 계산 중...")
        
        try:
            for stock in scored_stocks:
                # 가중 평균으로 종합 점수 계산
                composite_score = (
                    stock['market_cap_score'] * self.selection_weights[UniverseSelectionCriteria.MARKET_CAP] +
                    stock['liquidity_score'] * self.selection_weights[UniverseSelectionCriteria.LIQUIDITY] +
                    stock['volatility_score'] * self.selection_weights[UniverseSelectionCriteria.VOLATILITY] +
                    stock['momentum_score'] * self.selection_weights[UniverseSelectionCriteria.MOMENTUM] +
                    stock['sector_balance_score'] * self.selection_weights[UniverseSelectionCriteria.SECTOR_BALANCE] +
                    stock['performance_score'] * self.selection_weights[UniverseSelectionCriteria.PERFORMANCE]
                )
                
                stock['composite_score'] = composite_score
                
                # 선별 이유 생성
                reasons = []
                if stock['market_cap_score'] >= 0.8:
                    reasons.append("대형주 (높은 시가총액)")
                if stock['liquidity_score'] >= 0.7:
                    reasons.append("높은 유동성")
                if stock['volatility_score'] >= 0.7:
                    reasons.append("적정 변동성")
                if stock['momentum_score'] >= 0.7:
                    reasons.append("양호한 모멘텀")
                if stock['performance_score'] >= 0.7:
                    reasons.append("우수한 과거 성과")
                
                stock['selection_reasons'] = reasons if reasons else ["종합 점수 기반"]
            
            # 종합 점수 기준 내림차순 정렬
            ranked_stocks = sorted(scored_stocks, key=lambda x: x['composite_score'], reverse=True)
            
            self.logger.info(f"   ✅ 종합 점수 계산 완료: {len(ranked_stocks)}개 종목")
            return ranked_stocks
            
        except Exception as e:
            self.logger.error(f"❌ 종합 점수 계산 실패: {e}")
            return scored_stocks
    
    def _apply_sector_balance(self, ranked_stocks: List[Dict], region: MarketRegion) -> List[Dict]:
        """섹터 균형 조정"""
        self.logger.info(f"⚖️ {region.value} 섹터 균형 조정 중...")
        
        try:
            target_size = self.kr_universe_size if region == MarketRegion.KR else self.us_universe_size
            max_per_sector = int(target_size * self.sector_max_weight)
            
            balanced_stocks = []
            sector_counts = {}
            
            for stock in ranked_stocks:
                sector = stock.get('sector', 'UNKNOWN')
                current_count = sector_counts.get(sector, 0)
                
                # 섹터별 최대 비중 체크
                if current_count < max_per_sector:
                    balanced_stocks.append(stock)
                    sector_counts[sector] = current_count + 1
                    
                    # 목표 크기 달성시 종료
                    if len(balanced_stocks) >= target_size:
                        break
                else:
                    # 섹터 비중 초과시 섹터 균형 점수 하향 조정
                    stock['sector_balance_score'] *= 0.5
                    stock['composite_score'] = self._recalculate_composite_score(stock)
            
            # 목표 크기에 못 미치면 나머지 종목도 추가 (섹터 균형보다 종목 수 우선)
            if len(balanced_stocks) < target_size:
                remaining_stocks = [s for s in ranked_stocks if s not in balanced_stocks]
                balanced_stocks.extend(remaining_stocks[:target_size - len(balanced_stocks)])
            
            self.logger.info(f"   ✅ 섹터 균형 조정 완료: {len(balanced_stocks)}개 종목")
            self.logger.info(f"   📊 섹터별 분포: {dict(sector_counts)}")
            
            return balanced_stocks
            
        except Exception as e:
            self.logger.error(f"❌ 섹터 균형 조정 실패: {e}")
            return ranked_stocks[:self.kr_universe_size if region == MarketRegion.KR else self.us_universe_size]
    
    def _recalculate_composite_score(self, stock: Dict) -> float:
        """종합 점수 재계산"""
        return (
            stock['market_cap_score'] * self.selection_weights[UniverseSelectionCriteria.MARKET_CAP] +
            stock['liquidity_score'] * self.selection_weights[UniverseSelectionCriteria.LIQUIDITY] +
            stock['volatility_score'] * self.selection_weights[UniverseSelectionCriteria.VOLATILITY] +
            stock['momentum_score'] * self.selection_weights[UniverseSelectionCriteria.MOMENTUM] +
            stock['sector_balance_score'] * self.selection_weights[UniverseSelectionCriteria.SECTOR_BALANCE] +
            stock['performance_score'] * self.selection_weights[UniverseSelectionCriteria.PERFORMANCE]
        )
    
    async def update_universe_database(self, universe_stocks: List[UniverseStock], region: MarketRegion) -> bool:
        """유니버스 정보를 데이터베이스에 업데이트"""
        self.logger.info(f"💾 {region.value} 유니버스 DB 업데이트 중...")
        
        try:
            with get_db_session() as db:
                # 기존 유니버스 정보 삭제 (region별)
                # 실제 TradingUniverse 테이블이 있다면 여기서 처리
                
                # 새 유니버스 정보 저장
                for stock in universe_stocks:
                    # 여기서 TradingUniverse 테이블에 저장
                    # 현재는 로그만 출력
                    self.logger.debug(f"   저장: {stock.stock_code} ({stock.stock_name})")
                
                db.commit()
                self.logger.info(f"   ✅ {region.value} 유니버스 DB 업데이트 완료")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ {region.value} 유니버스 DB 업데이트 실패: {e}")
            return False
    
    async def get_current_universe(self, region: MarketRegion) -> List[str]:
        """현재 활성 유니버스 종목 코드 목록 반환"""
        try:
            # 동적 유니버스 생성
            universe_stocks = await self.generate_dynamic_universe(region)
            
            # 종목 코드만 추출
            stock_codes = [stock['stock_code'] for stock in universe_stocks]
            
            self.logger.info(f"📋 {region.value} 현재 유니버스: {len(stock_codes)}개 종목")
            return stock_codes
            
        except Exception as e:
            self.logger.error(f"❌ {region.value} 유니버스 조회 실패: {e}")
            # 폴백: 기본 종목 리스트 반환
            return self._get_fallback_universe(region)
    
    def _get_fallback_universe(self, region: MarketRegion) -> List[str]:
        """폴백용 기본 종목 리스트"""
        if region == MarketRegion.KR:
            return [
                '005930', '000660', '035420', '005380', '000270',  # 대형주 5개
                '051910', '068270', '028260', '055550', '086790',  # 중형주 5개
                '003670', '096770', '032830', '017670', '090430',  # 기타 5개
                '009150', '018260', '323410', '377300', '035720'   # 기술주 5개
            ]
        else:  # US
            return [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',         # 대형 기술주
                'META', 'NVDA', 'NFLX', 'ADBE', 'CRM',           # 기술주
                'UNH', 'JNJ', 'PFE', 'ABT', 'TMO',               # 헬스케어
                'JPM', 'BAC', 'WFC', 'GS', 'MS'                  # 금융주
            ]


# 사용 예시 및 테스트
async def main():
    """메인 테스트 함수"""
    print("🌍 동적 종목 유니버스 관리자 테스트")
    print("="*60)
    
    manager = DynamicUniverseManager()
    
    try:
        # 한국 시장 동적 유니버스 생성
        print("\n1️⃣ 한국 시장 동적 유니버스 생성")
        kr_universe = await manager.get_current_universe(MarketRegion.KR)
        print(f"   ✅ 한국 유니버스: {len(kr_universe)}개")
        print(f"   📋 상위 10개: {kr_universe[:10]}")
        
        # 미국 시장 동적 유니버스 생성
        print("\n2️⃣ 미국 시장 동적 유니버스 생성")
        us_universe = await manager.get_current_universe(MarketRegion.US)
        print(f"   ✅ 미국 유니버스: {len(us_universe)}개")
        print(f"   📋 상위 10개: {us_universe[:10]}")
        
        print("\n🎉 동적 유니버스 생성 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
