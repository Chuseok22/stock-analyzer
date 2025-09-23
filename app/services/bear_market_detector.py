#!/usr/bin/env python3
"""
하락장 감지 및 인버스 ETF 추천 시스템
- 다중 지표 기반 하락장 감지
- 인버스/레버리지 ETF 추천
- 리스크 관리 및 상세 분석 제공
- 하락장 심도별 맞춤 전략 제공
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
from app.utils.structured_logger import StructuredLogger


class BearMarketSeverity(Enum):
    """하락장 심도"""
    MILD_CORRECTION = "mild_correction"      # 경미한 조정 (5-10% 하락)
    MODERATE_DECLINE = "moderate_decline"    # 중간 하락 (10-20% 하락)
    BEAR_MARKET = "bear_market"              # 약세장 (20% 이상 하락)
    SEVERE_CRASH = "severe_crash"            # 심각한 폭락 (30% 이상 하락)


class MarketSentiment(Enum):
    """시장 심리"""
    EXTREME_FEAR = "extreme_fear"      # 극도의 공포 (VIX > 40)
    FEAR = "fear"                      # 공포 (VIX 25-40)
    NEUTRAL = "neutral"                # 중립 (VIX 15-25)
    GREED = "greed"                    # 탐욕 (VIX < 15)


@dataclass
class BearMarketSignal:
    """하락장 신호"""
    severity: BearMarketSeverity
    confidence: float                   # 신뢰도 (0-1)
    market_decline_pct: float          # 시장 하락률
    duration_days: int                 # 지속 기간
    sentiment: MarketSentiment         # 시장 심리
    technical_indicators: Dict[str, float]  # 기술적 지표들
    fundamental_warnings: List[str]     # 펀더멘털 경고
    recommended_action: str            # 추천 행동


@dataclass
class InverseETFRecommendation:
    """인버스 ETF 추천"""
    etf_code: str
    etf_name: str
    leverage: float                    # 레버리지 배수 (1x, 2x, 3x)
    expected_return: float             # 예상 수익률
    risk_level: str                    # 리스크 수준 (LOW, MEDIUM, HIGH)
    recommendation_reason: List[str]   # 추천 이유
    target_allocation: float           # 권장 배분 비중 (0-1)
    stop_loss: float                  # 손절가
    target_price: float               # 목표가


class BearMarketDetector:
    """하락장 감지 및 인버스 ETF 추천 시스템"""
    
    def __init__(self):
        self.logger = StructuredLogger("bear_market_detector")
        self.kis_client = KISAPIClient()
        
        # 한국 인버스/레버리지 ETF 목록
        self.kr_inverse_etfs = {
            '114800': {  # KODEX 인버스
                'name': 'KODEX 인버스',
                'leverage': -1.0,
                'underlying': 'KOSPI 200',
                'risk_level': 'MEDIUM'
            },
            '225500': {  # TIGER 인버스
                'name': 'TIGER 인버스',
                'leverage': -1.0,
                'underlying': 'KOSPI 200',
                'risk_level': 'MEDIUM'
            },
            '252670': {  # TIGER 2X 인버스
                'name': 'TIGER 2X 인버스',
                'leverage': -2.0,
                'underlying': 'KOSPI 200',
                'risk_level': 'HIGH'
            },
            '251340': {  # KODEX 코스닥150 인버스
                'name': 'KODEX 코스닥150 인버스',
                'leverage': -1.0,
                'underlying': 'KOSDAQ 150',
                'risk_level': 'HIGH'
            },
            '229200': {  # KODEX 코스닥150 레버리지
                'name': 'KODEX 코스닥150 레버리지',
                'leverage': 2.0,
                'underlying': 'KOSDAQ 150',
                'risk_level': 'HIGH'
            }
        }
        
        # 시장 지수 추적 종목
        self.market_indices = {
            'KOSPI': '069500',      # KODEX 200
            'KOSDAQ': '229180',     # KODEX 코스닥150
            'KRX300': '295820'      # KODEX KRX300
        }
        
        self.logger.info("하락장 감지 시스템 초기화 완료")
    
    async def detect_bear_market_signals(self, region: MarketRegion = MarketRegion.KR) -> Optional[BearMarketSignal]:
        """종합적인 하락장 신호 감지"""
        self.logger.info(f"🐻 {region.value} 하락장 신호 감지 시작")
        
        try:
            # 1. 시장 지수 분석
            market_analysis = await self._analyze_market_indices(region)
            
            # 2. 기술적 지표 분석
            technical_signals = await self._analyze_technical_indicators(region)
            
            # 3. 시장 심리 분석
            sentiment_analysis = await self._analyze_market_sentiment(region)
            
            # 4. 거래량 및 유동성 분석
            liquidity_analysis = await self._analyze_market_liquidity(region)
            
            # 5. 종합 신호 생성
            bear_signal = self._synthesize_bear_market_signal(
                market_analysis, technical_signals, sentiment_analysis, liquidity_analysis
            )
            
            if bear_signal:
                self.logger.info(f"🚨 {region.value} 하락장 신호 감지: {bear_signal.severity.value} (신뢰도: {bear_signal.confidence:.1%})")
            else:
                self.logger.info(f"✅ {region.value} 하락장 신호 없음")
            
            return bear_signal
            
        except Exception as e:
            self.logger.error(f"❌ {region.value} 하락장 감지 실패: {e}")
            return None
    
    async def _analyze_market_indices(self, region: MarketRegion) -> Dict[str, Any]:
        """시장 지수 분석"""
        self.logger.info(f"📈 {region.value} 시장 지수 분석")
        
        try:
            analysis = {
                'decline_pct': 0.0,
                'duration_days': 0,
                'peak_to_trough': 0.0,
                'trend_strength': 0.0,
                'support_levels': []
            }
            
            with get_db_session() as db:
                if region == MarketRegion.KR:
                    # KOSPI 200 ETF 분석
                    kospi_stock = db.query(StockMaster).filter_by(
                        market_region=region.value,
                        stock_code=self.market_indices['KOSPI']
                    ).first()
                    
                    if kospi_stock:
                        # 최근 6개월 데이터
                        end_date = datetime.now().date()
                        start_date = end_date - timedelta(days=180)
                        
                        prices = db.query(StockDailyPrice).filter(
                            StockDailyPrice.stock_id == kospi_stock.stock_id,
                            StockDailyPrice.trade_date >= start_date,
                            StockDailyPrice.trade_date <= end_date
                        ).order_by(StockDailyPrice.trade_date).all()
                        
                        if len(prices) > 60:
                            closes = [float(p.close_price) for p in prices]
                            
                            # 최고점에서 현재까지 하락률
                            max_price = max(closes)
                            current_price = closes[-1]
                            analysis['decline_pct'] = (current_price - max_price) / max_price * 100
                            
                            # 하락 지속 기간 계산
                            max_price_idx = closes.index(max_price)
                            analysis['duration_days'] = len(closes) - 1 - max_price_idx
                            
                            # Peak-to-trough 분석
                            min_price_after_peak = min(closes[max_price_idx:])
                            analysis['peak_to_trough'] = (min_price_after_peak - max_price) / max_price * 100
                            
                            # 트렌드 강도 (선형 회귀)
                            x = np.arange(len(closes[-30:]))  # 최근 30일
                            y = closes[-30:]
                            if len(y) > 1:
                                slope = np.polyfit(x, y, 1)[0]
                                analysis['trend_strength'] = slope / current_price * 100  # 일일 트렌드 %
                            
                            # 지지선 분석 (최근 저점들)
                            lows = [float(p.low_price) for p in prices[-60:]]  # 최근 60일
                            support_levels = []
                            for i in range(2, len(lows) - 2):
                                if lows[i] < lows[i-1] and lows[i] < lows[i+1]:  # 지역 최소값
                                    support_levels.append(lows[i])
                            analysis['support_levels'] = sorted(set(support_levels))[-3:]  # 최근 3개
                
                self.logger.info(f"   📊 시장 하락률: {analysis['decline_pct']:.1f}%")
                self.logger.info(f"   📅 지속 기간: {analysis['duration_days']}일")
                
                return analysis
                
        except Exception as e:
            self.logger.error(f"❌ 시장 지수 분석 실패: {e}")
            return {'decline_pct': 0.0, 'duration_days': 0, 'peak_to_trough': 0.0, 'trend_strength': 0.0, 'support_levels': []}
    
    async def _analyze_technical_indicators(self, region: MarketRegion) -> Dict[str, float]:
        """기술적 지표 분석"""
        self.logger.info(f"📊 {region.value} 기술적 지표 분석")
        
        try:
            indicators = {
                'rsi_oversold': 0.0,        # RSI 과매도 신호
                'macd_bearish': 0.0,        # MACD 약세 신호
                'ma_breakdown': 0.0,        # 이동평균 붕괴
                'bollinger_squeeze': 0.0,   # 볼린저밴드 압박
                'volume_divergence': 0.0    # 거래량 다이버전스
            }
            
            with get_db_session() as db:
                if region == MarketRegion.KR:
                    # 주요 지수 ETF들 분석
                    for index_name, etf_code in self.market_indices.items():
                        etf_stock = db.query(StockMaster).filter_by(
                            market_region=region.value,
                            stock_code=etf_code
                        ).first()
                        
                        if not etf_stock:
                            continue
                        
                        # 최근 60일 데이터
                        end_date = datetime.now().date()
                        start_date = end_date - timedelta(days=60)
                        
                        prices = db.query(StockDailyPrice).filter(
                            StockDailyPrice.stock_id == etf_stock.stock_id,
                            StockDailyPrice.trade_date >= start_date
                        ).order_by(StockDailyPrice.trade_date).all()
                        
                        if len(prices) < 30:
                            continue
                        
                        # 데이터 변환
                        df = pd.DataFrame([{
                            'close': float(p.close_price),
                            'high': float(p.high_price),
                            'low': float(p.low_price),
                            'volume': int(p.volume) if p.volume else 0,
                            'return': float(p.daily_return_pct) if p.daily_return_pct else 0
                        } for p in prices])
                        
                        # RSI 계산
                        delta = df['close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                        rs = gain / loss.replace(0, 1e-8)
                        rsi = 100 - (100 / (1 + rs))
                        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
                        
                        if current_rsi < 30:  # 과매도
                            indicators['rsi_oversold'] += 1.0
                        
                        # MACD 계산
                        ema_12 = df['close'].ewm(span=12).mean()
                        ema_26 = df['close'].ewm(span=26).mean()
                        macd = ema_12 - ema_26
                        macd_signal = macd.ewm(span=9).mean()
                        
                        if len(macd) > 1 and macd.iloc[-1] < macd_signal.iloc[-1]:
                            indicators['macd_bearish'] += 1.0
                        
                        # 이동평균 붕괴 확인
                        sma_20 = df['close'].rolling(20).mean()
                        sma_50 = df['close'].rolling(50).mean()
                        
                        if len(sma_20) > 0 and len(sma_50) > 0:
                            if sma_20.iloc[-1] < sma_50.iloc[-1]:  # 단기 < 장기
                                indicators['ma_breakdown'] += 1.0
                        
                        # 볼린저밴드 압박
                        sma_20_bb = df['close'].rolling(20).mean()
                        bb_std = df['close'].rolling(20).std()
                        bb_upper = sma_20_bb + (bb_std * 2)
                        bb_lower = sma_20_bb - (bb_std * 2)
                        bb_width = (bb_upper - bb_lower) / sma_20_bb
                        
                        if len(bb_width) > 0 and bb_width.iloc[-1] < 0.1:  # 밴드 폭 10% 미만
                            indicators['bollinger_squeeze'] += 1.0
                        
                        # 거래량 다이버전스
                        price_trend = df['close'].pct_change(5).iloc[-1]  # 5일 수익률
                        volume_trend = df['volume'].pct_change(5).iloc[-1]  # 5일 거래량 변화
                        
                        # 가격 하락 + 거래량 증가 = 매도 압력
                        if price_trend < -0.02 and volume_trend > 0.1:
                            indicators['volume_divergence'] += 1.0
            
            # 지표 정규화 (0-1 범위)
            num_indices = len(self.market_indices)
            if num_indices > 0:
                for key in indicators:
                    indicators[key] = indicators[key] / num_indices
            
            self.logger.info(f"   🔍 기술적 신호 강도: {sum(indicators.values()) / len(indicators):.2f}")
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"❌ 기술적 지표 분석 실패: {e}")
            return {'rsi_oversold': 0.0, 'macd_bearish': 0.0, 'ma_breakdown': 0.0, 'bollinger_squeeze': 0.0, 'volume_divergence': 0.0}
    
    async def _analyze_market_sentiment(self, region: MarketRegion) -> Dict[str, Any]:
        """시장 심리 분석"""
        self.logger.info(f"😰 {region.value} 시장 심리 분석")
        
        try:
            sentiment = {
                'fear_greed_index': 50.0,  # 0: 극도공포, 100: 극도탐욕
                'volatility_index': 0.2,   # 변동성 지수
                'put_call_ratio': 1.0,     # Put/Call 비율
                'sentiment_score': 0.5     # 종합 심리 점수
            }
            
            # 변동성 기반 공포/탐욕 지수 계산
            with get_db_session() as db:
                if region == MarketRegion.KR:
                    kospi_stock = db.query(StockMaster).filter_by(
                        market_region=region.value,
                        stock_code=self.market_indices['KOSPI']
                    ).first()
                    
                    if kospi_stock:
                        # 최근 30일 변동성 계산
                        end_date = datetime.now().date()
                        start_date = end_date - timedelta(days=30)
                        
                        prices = db.query(StockDailyPrice).filter(
                            StockDailyPrice.stock_id == kospi_stock.stock_id,
                            StockDailyPrice.trade_date >= start_date
                        ).order_by(StockDailyPrice.trade_date).all()
                        
                        if len(prices) > 10:
                            returns = []
                            for i in range(1, len(prices)):
                                prev_price = float(prices[i-1].close_price)
                                curr_price = float(prices[i].close_price)
                                daily_return = (curr_price - prev_price) / prev_price
                                returns.append(daily_return)
                            
                            # 연환산 변동성
                            volatility = np.std(returns) * np.sqrt(252)
                            sentiment['volatility_index'] = volatility
                            
                            # 변동성 기반 공포/탐욕 지수
                            # 변동성 높음 = 공포, 변동성 낮음 = 탐욕
                            if volatility > 0.4:  # 40% 이상
                                sentiment['fear_greed_index'] = 10.0  # 극도 공포
                            elif volatility > 0.3:  # 30-40%
                                sentiment['fear_greed_index'] = 25.0  # 공포
                            elif volatility > 0.2:  # 20-30%
                                sentiment['fear_greed_index'] = 40.0  # 불안
                            elif volatility < 0.1:  # 10% 미만
                                sentiment['fear_greed_index'] = 80.0  # 탐욕
                            else:  # 10-20%
                                sentiment['fear_greed_index'] = 60.0  # 중립-탐욕
                            
                            # 최근 수익률 추가 고려
                            recent_returns = returns[-5:] if len(returns) >= 5 else returns
                            avg_recent_return = np.mean(recent_returns)
                            
                            # 수익률 조정
                            if avg_recent_return < -0.02:  # 일평균 -2% 이상 하락
                                sentiment['fear_greed_index'] = max(0, sentiment['fear_greed_index'] - 20)
                            elif avg_recent_return > 0.02:  # 일평균 +2% 이상 상승
                                sentiment['fear_greed_index'] = min(100, sentiment['fear_greed_index'] + 10)
            
            # 종합 심리 점수 계산
            if sentiment['fear_greed_index'] < 25:
                sentiment['sentiment_score'] = 0.2  # 극도 공포
            elif sentiment['fear_greed_index'] < 40:
                sentiment['sentiment_score'] = 0.4  # 공포
            elif sentiment['fear_greed_index'] < 60:
                sentiment['sentiment_score'] = 0.6  # 중립
            else:
                sentiment['sentiment_score'] = 0.8  # 탐욕
            
            self.logger.info(f"   😰 공포/탐욕 지수: {sentiment['fear_greed_index']:.1f}")
            self.logger.info(f"   📊 변동성: {sentiment['volatility_index']:.1%}")
            
            return sentiment
            
        except Exception as e:
            self.logger.error(f"❌ 시장 심리 분석 실패: {e}")
            return {'fear_greed_index': 50.0, 'volatility_index': 0.2, 'put_call_ratio': 1.0, 'sentiment_score': 0.5}
    
    async def _analyze_market_liquidity(self, region: MarketRegion) -> Dict[str, float]:
        """시장 유동성 분석"""
        self.logger.info(f"💧 {region.value} 시장 유동성 분석")
        
        try:
            liquidity = {
                'volume_trend': 0.0,        # 거래량 추세
                'bid_ask_spread': 0.0,      # 호가 스프레드 (근사)
                'market_depth': 1.0,        # 시장 깊이
                'liquidity_stress': 0.0     # 유동성 스트레스
            }
            
            with get_db_session() as db:
                if region == MarketRegion.KR:
                    # 주요 ETF들의 거래량 분석
                    total_volume_change = 0.0
                    valid_etfs = 0
                    
                    for etf_code in self.market_indices.values():
                        etf_stock = db.query(StockMaster).filter_by(
                            market_region=region.value,
                            stock_code=etf_code
                        ).first()
                        
                        if not etf_stock:
                            continue
                        
                        # 최근 20일 거래량 데이터
                        end_date = datetime.now().date()
                        start_date = end_date - timedelta(days=20)
                        
                        prices = db.query(StockDailyPrice).filter(
                            StockDailyPrice.stock_id == etf_stock.stock_id,
                            StockDailyPrice.trade_date >= start_date
                        ).order_by(StockDailyPrice.trade_date).all()
                        
                        if len(prices) < 10:
                            continue
                        
                        volumes = [int(p.volume) if p.volume else 0 for p in prices]
                        
                        # 거래량 추세 계산
                        recent_avg = np.mean(volumes[-5:])  # 최근 5일
                        previous_avg = np.mean(volumes[-15:-5])  # 이전 10일
                        
                        if previous_avg > 0:
                            volume_change = (recent_avg - previous_avg) / previous_avg
                            total_volume_change += volume_change
                            valid_etfs += 1
                        
                        # 호가 스프레드 근사 (가격 변동성으로 추정)
                        if len(prices) > 1:
                            price_volatility = np.std([float(p.close_price) for p in prices[-10:]])
                            avg_price = np.mean([float(p.close_price) for p in prices[-10:]])
                            spread_estimate = price_volatility / avg_price
                            liquidity['bid_ask_spread'] += spread_estimate
                    
                    if valid_etfs > 0:
                        liquidity['volume_trend'] = total_volume_change / valid_etfs
                        liquidity['bid_ask_spread'] = liquidity['bid_ask_spread'] / valid_etfs
                    
                    # 유동성 스트레스 계산
                    # 거래량 감소 + 스프레드 확대 = 유동성 스트레스
                    if liquidity['volume_trend'] < -0.1 and liquidity['bid_ask_spread'] > 0.02:
                        liquidity['liquidity_stress'] = 1.0
                    elif liquidity['volume_trend'] < -0.05 or liquidity['bid_ask_spread'] > 0.015:
                        liquidity['liquidity_stress'] = 0.5
                    else:
                        liquidity['liquidity_stress'] = 0.0
            
            self.logger.info(f"   📊 거래량 추세: {liquidity['volume_trend']:.1%}")
            self.logger.info(f"   💧 유동성 스트레스: {liquidity['liquidity_stress']:.1f}")
            
            return liquidity
            
        except Exception as e:
            self.logger.error(f"❌ 시장 유동성 분석 실패: {e}")
            return {'volume_trend': 0.0, 'bid_ask_spread': 0.0, 'market_depth': 1.0, 'liquidity_stress': 0.0}
    
    def _synthesize_bear_market_signal(self, market_analysis: Dict, technical_signals: Dict, 
                                     sentiment_analysis: Dict, liquidity_analysis: Dict) -> Optional[BearMarketSignal]:
        """종합 하락장 신호 생성"""
        self.logger.info("🔄 종합 하락장 신호 생성")
        
        try:
            # 1. 심도 결정
            decline_pct = market_analysis.get('decline_pct', 0.0)
            peak_to_trough = market_analysis.get('peak_to_trough', 0.0)
            
            if decline_pct <= -30 or peak_to_trough <= -30:
                severity = BearMarketSeverity.SEVERE_CRASH
            elif decline_pct <= -20 or peak_to_trough <= -20:
                severity = BearMarketSeverity.BEAR_MARKET
            elif decline_pct <= -10 or peak_to_trough <= -10:
                severity = BearMarketSeverity.MODERATE_DECLINE
            elif decline_pct <= -5 or peak_to_trough <= -5:
                severity = BearMarketSeverity.MILD_CORRECTION
            else:
                # 하락장 신호 없음
                return None
            
            # 2. 신뢰도 계산
            confidence_factors = []
            
            # 시장 하락 신뢰도
            market_confidence = min(abs(decline_pct) / 20, 1.0)  # 20% 하락 기준
            confidence_factors.append(market_confidence * 0.3)
            
            # 기술적 신호 신뢰도
            technical_avg = sum(technical_signals.values()) / len(technical_signals) if technical_signals else 0
            confidence_factors.append(technical_avg * 0.25)
            
            # 심리 신호 신뢰도 (공포 지수)
            fear_confidence = (100 - sentiment_analysis.get('fear_greed_index', 50)) / 100
            confidence_factors.append(fear_confidence * 0.25)
            
            # 유동성 신호 신뢰도
            liquidity_stress = liquidity_analysis.get('liquidity_stress', 0.0)
            confidence_factors.append(liquidity_stress * 0.2)
            
            total_confidence = sum(confidence_factors)
            
            # 3. 시장 심리 결정
            fear_greed = sentiment_analysis.get('fear_greed_index', 50)
            if fear_greed < 20:
                sentiment = MarketSentiment.EXTREME_FEAR
            elif fear_greed < 35:
                sentiment = MarketSentiment.FEAR
            elif fear_greed < 65:
                sentiment = MarketSentiment.NEUTRAL
            else:
                sentiment = MarketSentiment.GREED
            
            # 4. 추천 행동 결정
            if severity in [BearMarketSeverity.SEVERE_CRASH, BearMarketSeverity.BEAR_MARKET]:
                if total_confidence > 0.7:
                    recommended_action = "AGGRESSIVE_INVERSE_POSITION"
                else:
                    recommended_action = "MODERATE_INVERSE_POSITION"
            elif severity == BearMarketSeverity.MODERATE_DECLINE:
                recommended_action = "CAUTIOUS_INVERSE_POSITION"
            else:
                recommended_action = "DEFENSIVE_POSITION"
            
            # 5. 펀더멘털 경고 생성
            fundamental_warnings = []
            if market_analysis.get('duration_days', 0) > 30:
                fundamental_warnings.append("장기간 하락 지속 (30일 이상)")
            if sentiment_analysis.get('volatility_index', 0) > 0.3:
                fundamental_warnings.append("높은 변동성 지속")
            if liquidity_analysis.get('liquidity_stress', 0) > 0.5:
                fundamental_warnings.append("유동성 스트레스 감지")
            if technical_signals.get('volume_divergence', 0) > 0.5:
                fundamental_warnings.append("거래량 다이버전스")
            
            # 최소 신뢰도 체크
            if total_confidence < 0.3:
                self.logger.info("   📊 신뢰도 부족으로 하락장 신호 무시")
                return None
            
            bear_signal = BearMarketSignal(
                severity=severity,
                confidence=total_confidence,
                market_decline_pct=decline_pct,
                duration_days=market_analysis.get('duration_days', 0),
                sentiment=sentiment,
                technical_indicators=technical_signals,
                fundamental_warnings=fundamental_warnings,
                recommended_action=recommended_action
            )
            
            self.logger.info(f"   🚨 하락장 신호: {severity.value} (신뢰도: {total_confidence:.1%})")
            
            return bear_signal
            
        except Exception as e:
            self.logger.error(f"❌ 종합 신호 생성 실패: {e}")
            return None
    
    async def generate_inverse_etf_recommendations(self, bear_signal: BearMarketSignal) -> List[InverseETFRecommendation]:
        """인버스 ETF 추천 생성"""
        self.logger.info(f"🔄 인버스 ETF 추천 생성 (심도: {bear_signal.severity.value})")
        
        try:
            recommendations = []
            
            # 하락장 심도별 추천 전략
            if bear_signal.severity == BearMarketSeverity.SEVERE_CRASH:
                # 심각한 폭락: 고레버리지 인버스 추천
                target_etfs = ['252670', '114800', '225500']  # 2X 인버스, 1X 인버스들
                allocation_weights = [0.4, 0.3, 0.3]
            elif bear_signal.severity == BearMarketSeverity.BEAR_MARKET:
                # 약세장: 중간 레버리지 추천
                target_etfs = ['114800', '225500', '252670']
                allocation_weights = [0.4, 0.4, 0.2]
            elif bear_signal.severity == BearMarketSeverity.MODERATE_DECLINE:
                # 중간 하락: 보수적 인버스 추천
                target_etfs = ['114800', '225500']
                allocation_weights = [0.6, 0.4]
            else:  # MILD_CORRECTION
                # 경미한 조정: 최소 인버스 추천
                target_etfs = ['114800']
                allocation_weights = [1.0]
            
            for i, etf_code in enumerate(target_etfs):
                etf_info = self.kr_inverse_etfs.get(etf_code)
                if not etf_info:
                    continue
                
                try:
                    # 현재가 조회
                    current_price = await self._get_etf_current_price(etf_code)
                    if not current_price:
                        continue
                    
                    # 예상 수익률 계산
                    market_decline = abs(bear_signal.market_decline_pct)
                    leverage = abs(etf_info['leverage'])
                    expected_return = market_decline * leverage * bear_signal.confidence
                    
                    # 리스크 조정
                    if leverage > 1.5:  # 레버리지 ETF
                        expected_return *= 0.8  # 추적 오차 고려
                        risk_level = "HIGH"
                    else:
                        risk_level = "MEDIUM"
                    
                    # 목표가 및 손절가 계산
                    target_price = current_price * (1 + expected_return / 100)
                    stop_loss = current_price * 0.85  # 15% 손절
                    
                    # 추천 이유 생성
                    reasons = [
                        f"{bear_signal.severity.value.replace('_', ' ').title()} 감지",
                        f"시장 하락률: {market_decline:.1f}%",
                        f"기술적 신호 강도: {sum(bear_signal.technical_indicators.values()) / len(bear_signal.technical_indicators):.1%}",
                        f"시장 심리: {bear_signal.sentiment.value.replace('_', ' ').title()}"
                    ]
                    
                    if bear_signal.confidence > 0.7:
                        reasons.append("높은 신뢰도 신호")
                    
                    recommendation = InverseETFRecommendation(
                        etf_code=etf_code,
                        etf_name=etf_info['name'],
                        leverage=etf_info['leverage'],
                        expected_return=expected_return,
                        risk_level=risk_level,
                        recommendation_reason=reasons,
                        target_allocation=allocation_weights[i] if i < len(allocation_weights) else 0.1,
                        stop_loss=stop_loss,
                        target_price=target_price
                    )
                    
                    recommendations.append(recommendation)
                    
                except Exception as e:
                    self.logger.warning(f"ETF {etf_code} 추천 생성 실패: {e}")
                    continue
            
            # 예상 수익률 기준 정렬
            recommendations.sort(key=lambda x: x.expected_return, reverse=True)
            
            self.logger.info(f"   ✅ 인버스 ETF 추천 생성 완료: {len(recommendations)}개")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"❌ 인버스 ETF 추천 생성 실패: {e}")
            return []
    
    async def _get_etf_current_price(self, etf_code: str) -> Optional[float]:
        """ETF 현재가 조회"""
        try:
            # KIS API를 통한 현재가 조회
            stock_info = self.kis_client.get_stock_info(etf_code)
            if stock_info and 'current_price' in stock_info:
                return float(stock_info['current_price'])
            
            # DB에서 최근 가격 조회 (폴백)
            with get_db_session() as db:
                etf_stock = db.query(StockMaster).filter_by(
                    market_region=MarketRegion.KR.value,
                    stock_code=etf_code
                ).first()
                
                if etf_stock:
                    recent_price = db.query(StockDailyPrice).filter_by(
                        stock_id=etf_stock.stock_id
                    ).order_by(StockDailyPrice.trade_date.desc()).first()
                    
                    if recent_price:
                        return float(recent_price.close_price)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"ETF {etf_code} 현재가 조회 실패: {e}")
            return None
    
    async def generate_bear_market_alert(self) -> Optional[Dict[str, Any]]:
        """하락장 알림 메시지 생성"""
        self.logger.info("📢 하락장 알림 생성")
        
        try:
            # 하락장 신호 감지
            bear_signal = await self.detect_bear_market_signals()
            
            if not bear_signal:
                return None
            
            # 인버스 ETF 추천
            inverse_recommendations = await self.generate_inverse_etf_recommendations(bear_signal)
            
            # 알림 메시지 구성
            alert = {
                'alert_type': 'BEAR_MARKET_WARNING',
                'severity': bear_signal.severity.value,
                'confidence': bear_signal.confidence,
                'title': self._generate_alert_title(bear_signal),
                'message': self._generate_alert_message(bear_signal, inverse_recommendations),
                'recommendations': inverse_recommendations,
                'action_required': True,
                'urgency_level': self._determine_urgency_level(bear_signal)
            }
            
            return alert
            
        except Exception as e:
            self.logger.error(f"❌ 하락장 알림 생성 실패: {e}")
            return None
    
    def _generate_alert_title(self, bear_signal: BearMarketSignal) -> str:
        """알림 제목 생성"""
        severity_map = {
            BearMarketSeverity.MILD_CORRECTION: "📉 시장 조정",
            BearMarketSeverity.MODERATE_DECLINE: "⚠️ 중간 하락",
            BearMarketSeverity.BEAR_MARKET: "🐻 약세장 진입",
            BearMarketSeverity.SEVERE_CRASH: "🚨 심각한 폭락"
        }
        
        base_title = severity_map.get(bear_signal.severity, "📊 시장 경고")
        confidence_str = f"신뢰도 {bear_signal.confidence:.0%}"
        
        return f"{base_title} - {confidence_str}"
    
    def _generate_alert_message(self, bear_signal: BearMarketSignal, 
                              recommendations: List[InverseETFRecommendation]) -> str:
        """상세 알림 메시지 생성"""
        message_parts = []
        
        # 1. 현황 요약
        message_parts.append("📊 **시장 현황**")
        message_parts.append(f"• 하락률: {bear_signal.market_decline_pct:.1f}%")
        message_parts.append(f"• 지속기간: {bear_signal.duration_days}일")
        message_parts.append(f"• 시장 심리: {bear_signal.sentiment.value.replace('_', ' ').title()}")
        message_parts.append("")
        
        # 2. 기술적 신호
        message_parts.append("🔍 **기술적 신호**")
        tech_signals = bear_signal.technical_indicators
        for signal, value in tech_signals.items():
            if value > 0.5:
                signal_name = signal.replace('_', ' ').title()
                message_parts.append(f"• {signal_name}: 강함 ({value:.1%})")
        message_parts.append("")
        
        # 3. 경고사항
        if bear_signal.fundamental_warnings:
            message_parts.append("⚠️ **주요 경고**")
            for warning in bear_signal.fundamental_warnings:
                message_parts.append(f"• {warning}")
            message_parts.append("")
        
        # 4. 인버스 ETF 추천
        if recommendations:
            message_parts.append("🔄 **인버스 ETF 추천**")
            for rec in recommendations[:3]:  # 상위 3개만
                message_parts.append(
                    f"• **{rec.etf_name}** ({rec.etf_code})\n"
                    f"  - 예상수익률: {rec.expected_return:.1f}%\n"
                    f"  - 권장비중: {rec.target_allocation:.0%}\n"
                    f"  - 리스크: {rec.risk_level}"
                )
            message_parts.append("")
        
        # 5. 행동 권고
        message_parts.append("💡 **권장 행동**")
        action_map = {
            "AGGRESSIVE_INVERSE_POSITION": "적극적 인버스 포지션 (높은 비중)",
            "MODERATE_INVERSE_POSITION": "중간 인버스 포지션 (중간 비중)",
            "CAUTIOUS_INVERSE_POSITION": "조심스런 인버스 포지션 (낮은 비중)",
            "DEFENSIVE_POSITION": "방어적 포지션 (현금 보유 증대)"
        }
        action_desc = action_map.get(bear_signal.recommended_action, "시장 관망")
        message_parts.append(f"• {action_desc}")
        message_parts.append("• 리스크 관리 필수: 손절가 설정")
        message_parts.append("• 분산 투자 유지")
        
        return "\n".join(message_parts)
    
    def _determine_urgency_level(self, bear_signal: BearMarketSignal) -> str:
        """긴급도 수준 결정"""
        if bear_signal.severity == BearMarketSeverity.SEVERE_CRASH:
            return "CRITICAL"
        elif bear_signal.severity == BearMarketSeverity.BEAR_MARKET:
            return "HIGH"
        elif bear_signal.severity == BearMarketSeverity.MODERATE_DECLINE:
            return "MEDIUM"
        else:
            return "LOW"


# 사용 예시
async def main():
    """메인 테스트 함수"""
    print("🐻 하락장 감지 시스템 테스트")
    print("="*60)
    
    detector = BearMarketDetector()
    
    try:
        # 하락장 신호 감지
        print("\n1️⃣ 하락장 신호 감지")
        bear_signal = await detector.detect_bear_market_signals()
        
        if bear_signal:
            print(f"   🚨 하락장 감지: {bear_signal.severity.value}")
            print(f"   📊 신뢰도: {bear_signal.confidence:.1%}")
            print(f"   📉 하락률: {bear_signal.market_decline_pct:.1f}%")
            
            # 인버스 ETF 추천
            print("\n2️⃣ 인버스 ETF 추천")
            recommendations = await detector.generate_inverse_etf_recommendations(bear_signal)
            
            for rec in recommendations:
                print(f"   • {rec.etf_name}: {rec.expected_return:.1f}% (비중: {rec.target_allocation:.0%})")
        else:
            print("   ✅ 하락장 신호 없음")
        
        # 알림 생성
        print("\n3️⃣ 하락장 알림 생성")
        alert = await detector.generate_bear_market_alert()
        
        if alert:
            print(f"   📢 알림 생성: {alert['title']}")
            print(f"   🚨 긴급도: {alert['urgency_level']}")
        else:
            print("   📊 알림 생성 불필요")
        
        print("\n🎉 하락장 감지 시스템 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
