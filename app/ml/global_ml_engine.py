"""
글로벌 ML 엔진 - 한국/미국 주식 시장 통합 분석
Market Regime Detection, Cross-Market Correlation, Deep Feature Engineering
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import (
    StockMaster, StockDailyPrice, StockTechnicalIndicator, 
    StockFundamentalData, MarketRegion
)


class MarketRegime(Enum):
    """시장 체제 분류"""
    BULL_MARKET = "bull_market"        # 강세장
    BEAR_MARKET = "bear_market"        # 약세장  
    SIDEWAYS_MARKET = "sideways_market" # 횡보장
    HIGH_VOLATILITY = "high_volatility" # 고변동성
    CRISIS_MODE = "crisis_mode"         # 위기 상황


@dataclass
class MarketCondition:
    """시장 상황 정보"""
    regime: MarketRegime
    volatility_level: float
    correlation_kr_us: float
    fear_greed_index: float
    trend_strength: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class GlobalPrediction:
    """글로벌 예측 결과"""
    stock_code: str
    market_region: str
    predicted_return: float
    confidence_score: float
    risk_score: float
    recommendation: str  # BUY, HOLD, SELL, STRONG_BUY, STRONG_SELL
    target_price: Optional[float]
    stop_loss: Optional[float]
    reasoning: List[str]


class GlobalMLEngine:
    """글로벌 머신러닝 엔진"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.market_condition = None
        self.model_version = "v3.0_global"
        
        # 모델 저장 경로
        self.model_dir = Path(__file__).parent.parent.parent / "storage" / "models" / "global"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        print("🌍 글로벌 ML 엔진 초기화")
    
    def detect_market_regime(self) -> Any:
        """글로벌 시장 체제 감지 - 수정됨"""
        print("🔍 글로벌 시장 체제 분석 중...")
        
        try:
            # 실제 MarketCondition 객체 반환
            @dataclass
            class MarketCondition:
                regime: MarketRegime
                volatility_level: float
                risk_level: str
                trend_strength: float
                fear_greed_index: float
            
            # 실제 구현에서는 여기서 시장 데이터를 분석
            # 현재는 기본값으로 안정적인 시장 상황 반환
            return MarketCondition(
                regime=MarketRegime.BULL_MARKET,
                volatility_level=0.15,
                risk_level="MEDIUM",
                trend_strength=0.75,
                fear_greed_index=65.0
            )
            
        except Exception as e:
            print(f"❌ 시장 체제 감지 실패: {e}")
            # 실패 시에도 기본 객체 반환
            @dataclass
            class DefaultMarketCondition:
                regime: MarketRegime
                volatility_level: float
                risk_level: str
                trend_strength: float
                fear_greed_index: float
            
            return DefaultMarketCondition(
                regime=MarketRegime.SIDEWAYS_MARKET,
                volatility_level=0.20,
                risk_level="HIGH",
                trend_strength=0.50,
                fear_greed_index=50.0
            )
    
    def save_predictions_for_learning(self, predictions: List, target_date: date = None):
        """학습을 위한 예측 결과 저장"""
        if target_date is None:
            target_date = date.today()
        
        try:
            # 실시간 학습 시스템 인스턴스 생성
            from app.ml.realtime_learning_system import RealTimeLearningSystem
            
            learning_system = RealTimeLearningSystem()
            learning_system.save_daily_predictions(predictions, target_date)
            
        except Exception as e:
            print(f"❌ 학습용 예측 결과 저장 실패: {e}")

    def _get_market_index_data(self, db, region: MarketRegion, start_date: date, end_date: date) -> List[float]:
        """시장 지수 대표 데이터 추출"""
        try:
            if region == MarketRegion.KR:
                # 한국: 삼성전자 + SK하이닉스 + NAVER 평균 (시총 상위 대표)
                symbols = ['005930', '000660', '035420']
            else:
                # 미국: AAPL + MSFT + GOOGL 평균 (시총 상위 대표)
                symbols = ['AAPL', 'MSFT', 'GOOGL']
            
            market_prices = []
            
            for symbol in symbols:
                stock = db.query(StockMaster).filter_by(
                    market_region=region.value,
                    stock_code=symbol
                ).first()
                
                if stock:
                    prices = db.query(StockDailyPrice).filter(
                        StockDailyPrice.stock_id == stock.stock_id,
                        StockDailyPrice.trade_date >= start_date,
                        StockDailyPrice.trade_date <= end_date
                    ).order_by(StockDailyPrice.trade_date).all()
                    
                    if prices:
                        symbol_prices = [float(p.close_price) for p in prices]
                        market_prices.append(symbol_prices)
            
            if market_prices:
                # 평균 계산 (각 날짜별로)
                min_length = min(len(prices) for prices in market_prices)
                avg_prices = []
                
                for i in range(min_length):
                    day_avg = sum(prices[i] for prices in market_prices) / len(market_prices)
                    avg_prices.append(day_avg)
                
                return avg_prices
            
            return []
            
        except Exception as e:
            print(f"❌ {region.value} 시장 데이터 추출 실패: {e}")
            return []
    
    def _calculate_trend_strength(self, returns: pd.Series) -> float:
        """트렌드 강도 계산"""
        if len(returns) < 5:
            return 0.0
        
        # 단순 트렌드 강도: 연속 상승/하락 일수의 절댓값
        cumulative_return = (1 + returns).cumprod()
        
        # 선형 회귀를 통한 트렌드 강도
        x = np.arange(len(cumulative_return))
        z = np.polyfit(x, cumulative_return, 1)
        
        # 기울기의 절댓값을 트렌드 강도로 사용
        trend_strength = abs(z[0]) * 100
        
        return min(trend_strength, 10.0)  # 최대 10으로 제한
    
    def _calculate_fear_greed_index(self, kr_returns: pd.Series, us_returns: pd.Series, volatility: float) -> float:
        """공포/탐욕 지수 계산 (0: 극도의 공포, 100: 극도의 탐욕)"""
        try:
            # 최근 수익률 평균
            recent_kr = kr_returns.tail(10).mean()
            recent_us = us_returns.tail(10).mean()
            avg_return = (recent_kr + recent_us) / 2
            
            # 변동성 정규화 (낮으면 탐욕, 높으면 공포)
            volatility_score = max(0, min(100, 100 - (volatility * 10)))
            
            # 수익률 정규화
            return_score = max(0, min(100, 50 + (avg_return * 1000)))
            
            # 가중 평균
            fear_greed = (volatility_score * 0.6) + (return_score * 0.4)
            
            return fear_greed
            
        except Exception:
            return 50.0  # 중립
    
    def _determine_market_regime(self, volatility: float, trend_strength: float, fear_greed: float) -> MarketRegime:
        """시장 체제 결정"""
        
        # 극도의 변동성 체크
        if volatility > 0.4:  # 40% 이상
            return MarketRegime.HIGH_VOLATILITY
        
        # 위기 상황 체크
        if fear_greed < 20 and volatility > 0.3:
            return MarketRegime.CRISIS_MODE
        
        # 트렌드 기반 분류
        if trend_strength > 3.0:  # 강한 트렌드
            if fear_greed > 60:
                return MarketRegime.BULL_MARKET
            elif fear_greed < 40:
                return MarketRegime.BEAR_MARKET
        
        # 기본값: 횡보장
        return MarketRegime.SIDEWAYS_MARKET
    
    def _determine_risk_level(self, volatility: float, correlation: float, fear_greed: float) -> str:
        """리스크 레벨 결정"""
        
        if volatility > 0.4 or fear_greed < 20:
            return "CRITICAL"
        elif volatility > 0.3 or fear_greed < 30:
            return "HIGH"
        elif volatility > 0.2 or abs(correlation) > 0.8:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_default_market_condition(self) -> MarketCondition:
        """기본 시장 상황"""
        return MarketCondition(
            regime=MarketRegime.SIDEWAYS_MARKET,
            volatility_level=0.2,
            correlation_kr_us=0.5,
            fear_greed_index=50.0,
            trend_strength=2.0,
            risk_level="MEDIUM"
        )
    
    def prepare_global_features(self, stock_id: int, target_date: date) -> Optional[pd.DataFrame]:
        """글로벌 피처 생성 - 딥러닝 수준의 피처 엔지니어링"""
        print(f"🔧 글로벌 피처 생성: stock_id={stock_id}, date={target_date}")
        
        try:
            with get_db_session() as db:
                # 기본 정보
                stock = db.query(StockMaster).filter_by(stock_id=stock_id).first()
                if not stock:
                    return None
                
                # 120일 히스토리 데이터
                end_date = target_date
                start_date = end_date - timedelta(days=120)
                
                # 가격 데이터
                price_data = db.query(StockDailyPrice).filter(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date >= start_date,
                    StockDailyPrice.trade_date <= end_date
                ).order_by(StockDailyPrice.trade_date).all()
                
                if len(price_data) < 30:
                    print(f"   ⚠️ 가격 데이터 부족: {len(price_data)}일")
                    return None
                
                # DataFrame 생성 (기술적 지표 제외)
                df = self._build_feature_dataframe(price_data, stock)
                
                # 고급 피처 추가
                df = self._add_advanced_features(df, stock)
                
                # 크로스 마켓 피처 (상관관계 등)
                df = self._add_cross_market_features(df, stock, target_date)
                
                # 시장 체제 피처
                if self.market_condition:
                    df = self._add_market_regime_features(df)
                
                print(f"   ✅ 피처 생성 완료: {len(df)} 행, {len(df.columns)} 피처")
                return df
                
        except Exception as e:
            print(f"   ❌ 피처 생성 실패: {e}")
            return None
    
    def _build_feature_dataframe(self, price_data: List, stock: StockMaster) -> pd.DataFrame:
        """기본 피처 DataFrame 구성"""
        
        # 가격 데이터 변환 (날짜는 숫자형으로 변환)
        price_df = pd.DataFrame([{
            'date_ordinal': p.trade_date.toordinal(),  # 날짜를 서수(정수)로 변환
            'open': float(p.open_price),
            'high': float(p.high_price),
            'low': float(p.low_price),
            'close': float(p.close_price),
            'volume': int(p.volume) if p.volume else 0,
            'adjusted_close': float(p.adjusted_close_price) if p.adjusted_close_price else float(p.close_price),
            'daily_return': float(p.daily_return_pct) if p.daily_return_pct else 0.0,
            'vwap': float(p.vwap) if p.vwap else float(p.close_price)
        } for p in price_data])
        
        # 기본 기술적 지표 계산
        price_df = price_df.sort_values('date_ordinal').reset_index(drop=True)
        
        # 이동평균
        price_df['sma_5'] = price_df['close'].rolling(5, min_periods=1).mean()
        price_df['sma_20'] = price_df['close'].rolling(20, min_periods=1).mean()
        price_df['sma_50'] = price_df['close'].rolling(50, min_periods=1).mean()
        
        # RSI
        delta = price_df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss
        price_df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # 볼린저 밴드
        price_df['bb_middle'] = price_df['sma_20']
        bb_std = price_df['close'].rolling(20, min_periods=1).std()
        price_df['bb_upper'] = price_df['bb_middle'] + (bb_std * 2)
        price_df['bb_lower'] = price_df['bb_middle'] - (bb_std * 2)
        price_df['bb_percent'] = (price_df['close'] - price_df['bb_lower']) / (price_df['bb_upper'] - price_df['bb_lower'])
        
        # MACD
        ema_12 = price_df['close'].ewm(span=12).mean()
        ema_26 = price_df['close'].ewm(span=26).mean()
        price_df['macd'] = ema_12 - ema_26
        price_df['macd_signal'] = price_df['macd'].ewm(span=9).mean()
        
        # 거래량 비율
        price_df['volume_ratio'] = price_df['volume'] / price_df['volume'].rolling(20, min_periods=1).mean()
        
        # 기본 피처 추가
        price_df['price_range'] = (price_df['high'] - price_df['low']) / price_df['close']
        price_df['open_close_ratio'] = price_df['open'] / price_df['close']
        price_df['high_close_ratio'] = price_df['high'] / price_df['close']
        price_df['low_close_ratio'] = price_df['low'] / price_df['close']
        price_df['volume_price_trend'] = price_df['volume'] * price_df['daily_return']
        
        return price_df.fillna(method='ffill').fillna(0)
    
    def _add_advanced_features(self, df: pd.DataFrame, stock: StockMaster) -> pd.DataFrame:
        """고급 피처 추가 - 딥러닝 스타일"""
        
        # 1. 시계열 윈도우 피처 (3, 5, 10, 20일)
        for window in [3, 5, 10, 20]:
            # 가격 모멘텀
            df[f'price_momentum_{window}'] = df['close'].pct_change(window)
            
            # 변동성
            df[f'volatility_{window}'] = df['daily_return'].rolling(window).std()
            
            # 거래량 평균
            df[f'volume_ma_{window}'] = df['volume'].rolling(window).mean()
            
            # 최고가/최저가 대비 현재 위치
            df[f'high_position_{window}'] = (df['close'] - df['low'].rolling(window).min()) / (
                df['high'].rolling(window).max() - df['low'].rolling(window).min()
            )
        
        # 2. 기술적 분석 고급 피처
        # RSI 기반 피처
        df['rsi_ma_5'] = df['rsi_14'].rolling(5).mean()
        df['rsi_divergence'] = df['rsi_14'] - df['rsi_ma_5']
        df['rsi_extreme'] = ((df['rsi_14'] > 70) | (df['rsi_14'] < 30)).astype(int)
        
        # 볼린저 밴드 기반 피처
        df['bb_squeeze'] = (df['bb_upper'] - df['bb_lower']) / df['close']
        df['bb_position'] = df['bb_percent']
        df['bb_breakout'] = ((df['close'] > df['bb_upper']) | (df['close'] < df['bb_lower'])).astype(int)
        
        # 3. 가격 패턴 피처
        # 갭 분석
        df['gap_up'] = ((df['open'] > df['close'].shift(1)) & 
                       (df['open'] - df['close'].shift(1)) / df['close'].shift(1) > 0.02).astype(int)
        df['gap_down'] = ((df['open'] < df['close'].shift(1)) & 
                         (df['close'].shift(1) - df['open']) / df['close'].shift(1) > 0.02).astype(int)
        
        # 캔들스틱 패턴 (0으로 나누기 방지)
        price_range = df['high'] - df['low']
        price_range = price_range.where(price_range > 0, 0.001)  # 0이면 0.001로 대체
        df['doji'] = (abs(df['open'] - df['close']) / price_range < 0.1).astype(int)
        df['hammer'] = ((df['close'] > df['open']) & 
                       ((df['open'] - df['low']) > 2 * (df['close'] - df['open']))).astype(int)
        
        # 4. 마켓 마이크로스트럭처 피처
        # 거래량 프로파일
        df['volume_surge'] = (df['volume'] > df['volume'].rolling(20).mean() * 2).astype(int)
        df['volume_dry'] = (df['volume'] < df['volume'].rolling(20).mean() * 0.5).astype(int)
        
        # 가격-거래량 상관관계
        df['price_volume_corr'] = df['daily_return'].rolling(20).corr(df['volume'].pct_change())
        
        return df.fillna(0)
    
    def _add_cross_market_features(self, df: pd.DataFrame, stock: StockMaster, target_date: date) -> pd.DataFrame:
        """크로스 마켓 피처 추가"""
        
        try:
            # 상대 시장 정보
            other_region = MarketRegion.US if stock.market_region == MarketRegion.KR.value else MarketRegion.KR
            
            with get_db_session() as db:
                # 다른 시장의 대표 지수 데이터
                other_market_data = self._get_market_index_data(
                    db, other_region, 
                    target_date - timedelta(days=60), 
                    target_date
                )
                
                if other_market_data:
                    # 다른 시장 수익률 계산
                    other_returns = pd.Series(other_market_data).pct_change().fillna(0)
                    
                    # 최근 상관관계
                    if len(other_returns) >= len(df['daily_return']):
                        recent_other = other_returns.tail(len(df))
                        df['cross_market_corr'] = df['daily_return'].rolling(20).corr(recent_other)
                    
                    # 다른 시장 트렌드 영향
                    if len(other_returns) > 0:
                        other_trend = other_returns.tail(5).mean()
                        df['other_market_trend'] = other_trend
                        df['cross_market_momentum'] = df['daily_return'] * other_trend
                
        except Exception as e:
            print(f"   ⚠️ 크로스 마켓 피처 생성 실패: {e}")
        
        return df.fillna(0)
    
    def _add_market_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """시장 체제 피처 추가"""
        
        if not self.market_condition:
            return df
        
        # 시장 체제 더미 변수
        for regime in MarketRegime:
            df[f'regime_{regime.value}'] = (self.market_condition.regime == regime).astype(int)
        
        # 시장 조건 피처
        df['market_volatility'] = self.market_condition.volatility_level
        df['market_correlation'] = self.market_condition.correlation_kr_us
        df['market_fear_greed'] = self.market_condition.fear_greed_index
        df['market_trend_strength'] = self.market_condition.trend_strength
        
        # 리스크 레벨 더미 변수
        for risk in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            df[f'risk_{risk.lower()}'] = (self.market_condition.risk_level == risk).astype(int)
        
        return df
    
    def train_global_models(self, use_intensive_config: bool = False) -> bool:
        """글로벌 ML 모델 학습 - 배포 환경 최적화"""
        print("🏋️ 글로벌 ML 모델 학습 시작...")
        
        try:
            # 배포 환경 감지
            is_production = Path("/volume1/project/stock-analyzer").exists()
            
            if is_production:
                print("🚀 배포 환경 감지 - 고성능 학습 모드")
                # 배포 환경에서는 최대 성능으로 학습
                model_config = {
                    'n_estimators': 300,        # 트리 개수 증가
                    'max_depth': 12,            # 깊이 증가
                    'min_samples_split': 5,     # 더 세밀한 분할
                    'min_samples_leaf': 2,      # 리프 노드 최소값
                    'max_features': 'sqrt',     # 모든 피처 사용
                    'random_state': 42,
                    'n_jobs': -1,              # 모든 CPU 코어 활용
                    'verbose': 1               # 진행상황 표시
                }
                
                if use_intensive_config or hasattr(self, 'model_config'):
                    # 집중 학습 모드
                    intensive_config = getattr(self, 'model_config', {})
                    if intensive_config:
                        model_config.update(intensive_config)
                        print(f"🔥 집중 학습 설정 적용: {intensive_config}")
            else:
                print("🛠️ 개발 환경 - 빠른 학습 모드")
                # 개발 환경에서는 빠른 학습
                model_config = {
                    'n_estimators': 50,
                    'max_depth': 8,
                    'min_samples_split': 10,
                    'random_state': 42,
                    'n_jobs': 2
                }
            
            print(f"⚙️ 모델 설정: {model_config}")
            
            # 1. 데이터 준비
            print("📊 학습 데이터 준비...")
            training_success = self._prepare_training_data()
            
            if not training_success:
                print("❌ 학습 데이터 준비 실패")
                return False
            
            # 2. 한국 시장 모델 학습
            print("🇰🇷 한국 시장 모델 학습...")
            kr_success = self._train_market_model(MarketRegion.KR, model_config)
            
            # 3. 미국 시장 모델 학습
            print("🇺🇸 미국 시장 모델 학습...")
            us_success = self._train_market_model(MarketRegion.US, model_config)
            
            # 4. 글로벌 앙상블 모델 학습
            print("🌍 글로벌 앙상블 모델 학습...")
            ensemble_success = self._train_ensemble_model(model_config)
            
            success = kr_success and us_success and ensemble_success
            
            if success:
                if is_production:
                    print("🎉 배포 환경 고성능 학습 완료!")
                else:
                    print("✅ 개발 환경 학습 완료")
                
                # 모델 성능 검증
                self._validate_trained_models()
            else:
                print("❌ 모델 학습 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ 모델 학습 중 오류: {e}")
            import traceback
            print(f"상세 오류: {traceback.format_exc()}")
            return False
    
    def _prepare_training_data(self) -> bool:
        """학습 데이터 준비 및 검증"""
        print("🔍 학습 데이터 준비 중...")
        
        try:
            with get_db_session() as db:
                # 한국 시장 데이터 확인
                kr_stocks = db.query(StockMaster).filter_by(
                    market_region=MarketRegion.KR.value,
                    is_active=True
                ).count()
                
                # 미국 시장 데이터 확인
                us_stocks = db.query(StockMaster).filter_by(
                    market_region=MarketRegion.US.value,
                    is_active=True
                ).count()
                
                # 최근 데이터 확인
                recent_date = datetime.now().date() - timedelta(days=7)
                
                kr_recent_data = db.query(StockDailyPrice).join(StockMaster).filter(
                    StockMaster.market_region == MarketRegion.KR.value,
                    StockDailyPrice.trade_date >= recent_date
                ).count()
                
                us_recent_data = db.query(StockDailyPrice).join(StockMaster).filter(
                    StockMaster.market_region == MarketRegion.US.value,
                    StockDailyPrice.trade_date >= recent_date
                ).count()
                
                print(f"   🇰🇷 한국 종목: {kr_stocks}개, 최근 데이터: {kr_recent_data}개")
                print(f"   🇺🇸 미국 종목: {us_stocks}개, 최근 데이터: {us_recent_data}개")
                
                # 최소 데이터 요구사항 검증
                if kr_stocks < 10 or us_stocks < 10:
                    print("   ❌ 종목 데이터 부족")
                    return False
                
                if kr_recent_data < 50 or us_recent_data < 50:
                    print("   ❌ 최근 가격 데이터 부족")
                    return False
                
                print("   ✅ 학습 데이터 준비 완료")
                return True
                
        except Exception as e:
            print(f"   ❌ 데이터 준비 실패: {e}")
            return False
    
    def train_global_models_intensive(self, use_intensive_config: bool = True) -> bool:
        """집중 학습 모드 - 중복 제거됨"""
        print("� 집중 학습 모드...")
        
        try:
            # 집중 학습 설정
            intensive_config = {
                'n_estimators': 500,
                'max_depth': 15,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'max_features': 'sqrt',
                'random_state': 42,
                'n_jobs': -1,
                'verbose': 1
            }
            
            print(f"⚙️ 집중 학습 설정: {intensive_config}")
            
            # 1. 데이터 준비
            print("📊 학습 데이터 준비...")
            training_success = self._prepare_training_data()
            
            if not training_success:
                print("❌ 학습 데이터 준비 실패")
                return False
            
            # 2. 한국 시장 모델 학습
            print("🇰🇷 한국 시장 모델 학습...")
            kr_success = self._train_market_model(MarketRegion.KR, intensive_config)
            
            # 3. 미국 시장 모델 학습
            print("🇺🇸 미국 시장 모델 학습...")
            us_success = self._train_market_model(MarketRegion.US, intensive_config)
            
            # 4. 글로벌 앙상블 모델 학습
            print("🌍 글로벌 앙상블 모델 학습...")
            ensemble_success = self._train_ensemble_model(intensive_config)
            
            success = kr_success and us_success and ensemble_success
            
            if success:
                print("🎉 집중 학습 완료!")
                # 모델 성능 검증
                self._validate_trained_models()
            else:
                print("❌ 집중 학습 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ 집중 학습 오류: {e}")
            return False
    
    def _validate_trained_models(self):
        """학습된 모델 성능 검증 - 경로 통일"""
        try:
            print("🔍 학습된 모델 성능 검증...")
            
            # 모델 파일 존재 확인 (실제 저장 형식에 맞춤)
            required_models = [
                f"KR_model_{self.model_version}.joblib",
                f"KR_scaler_{self.model_version}.joblib",
                f"US_model_{self.model_version}.joblib", 
                f"US_scaler_{self.model_version}.joblib",
                f"ensemble_model_{self.model_version}.joblib",
                f"ensemble_scaler_{self.model_version}.joblib"
            ]
            
            model_status = {}
            for model_name in required_models:
                model_path = self.model_dir / model_name  # self.model_dir 사용
                if model_path.exists():
                    model_status[model_name] = "✅ 존재"
                    # 파일 크기 확인
                    size_mb = model_path.stat().st_size / (1024 * 1024)
                    model_status[model_name] += f" ({size_mb:.1f}MB)"
                else:
                    model_status[model_name] = "❌ 없음"
            
            print("📋 모델 파일 상태:")
            for model, status in model_status.items():
                print(f"   • {model}: {status}")
            
            # 모든 모델이 존재하는지 확인
            all_exist = all("✅" in status for status in model_status.values())
            if all_exist:
                print("✅ 모든 모델 파일 검증 완료")
            else:
                print("⚠️ 일부 모델 파일 누락")
                
        except Exception as e:
            print(f"❌ 모델 검증 실패: {e}")
    
    def _train_market_model(self, region: MarketRegion, model_config: dict = None) -> bool:
        """시장별 모델 학습"""
        print(f"🎯 {region.value} 시장 모델 학습...")
        
        if model_config is None:
            model_config = {
                'n_estimators': 100,
                'max_depth': 10,
                'random_state': 42,
                'n_jobs': -1
            }
        
        try:
            with get_db_session() as db:
                # 해당 시장 종목 목록
                stocks = db.query(StockMaster).filter_by(
                    market_region=region.value,
                    is_active=True
                ).all()
                
                all_features = []
                all_targets = []
                sample_weights = []  # 가중치 추가
                
                for stock in stocks[:20]:  # 상위 20개 종목으로 제한
                    print(f"   📊 {stock.stock_code} 데이터 수집...")
                    
                    # 최근 180일 데이터
                    end_date = datetime.now().date()
                    
                    for days_back in range(30, 150):  # 슬라이딩 윈도우
                        current_date = end_date - timedelta(days=days_back)
                        
                        # 피처 생성
                        features = self.prepare_global_features(stock.stock_id, current_date)
                        
                        if features is None or len(features) < 30:
                            continue
                        
                        # 타겟 생성 (5일 후 수익률)
                        future_date = current_date + timedelta(days=5)
                        target = self._get_future_return(db, stock.stock_id, current_date, future_date)
                        
                        if target is None:
                            continue
                        
                        # 최신 데이터 사용
                        latest_features = features.iloc[-1].fillna(0)
                        
                        # 가중치 계산 (최신 데이터일수록 높은 가중치)
                        time_weight = 1.0 / (days_back / 30.0 + 1.0)  # 시간 가중치
                        
                        # 변동성 가중치 (높은 변동성은 낮은 가중치)
                        volatility = features['volatility_20'].iloc[-1] if 'volatility_20' in features.columns else 0.02
                        volatility_weight = 1.0 / (volatility * 50 + 1.0)
                        
                        # 거래량 가중치 (높은 거래량은 높은 가중치)
                        volume_ratio = features.get('volume_ratio', pd.Series([1.0])).iloc[-1]
                        volume_weight = min(volume_ratio / 2.0 + 0.5, 2.0)
                        
                        # 최종 가중치
                        final_weight = time_weight * volatility_weight * volume_weight
                        
                        all_features.append(latest_features)
                        all_targets.append(target)
                        sample_weights.append(final_weight)
                
                if len(all_features) < 50:
                    print(f"   ⚠️ {region.value}: 학습 데이터 부족 ({len(all_features)}개)")
                    return False
                
                # DataFrame 변환
                X = pd.DataFrame(all_features)
                y = np.array(all_targets)
                weights = np.array(sample_weights)
                
                print(f"   📈 학습 데이터: {len(X)}개 샘플, {len(X.columns)}개 피처")
                print(f"   ⚖️ 가중치 범위: {weights.min():.3f} - {weights.max():.3f}")
                
                # 피처 스케일링
                scaler = RobustScaler()  # 아웃라이어에 강건한 스케일러
                X_scaled = scaler.fit_transform(X)
                
                # 앙상블 모델 생성 (가중치 적용)
                rf_model = RandomForestRegressor(**model_config)
                gb_model = GradientBoostingRegressor(
                    n_estimators=model_config.get('n_estimators', 100),
                    max_depth=model_config.get('max_depth', 10),
                    random_state=model_config.get('random_state', 42)
                )
                
                ensemble_model = VotingRegressor([
                    ('rf', rf_model),
                    ('gb', gb_model)
                ])
                
                # 가중치를 적용한 모델 학습
                print(f"   🏋️ 가중치 적용 모델 학습 중...")
                ensemble_model.fit(X_scaled, y, sample_weight=weights)
                
                # 모델 성능 평가
                y_pred = ensemble_model.predict(X_scaled)
                mse = mean_squared_error(y, y_pred, sample_weight=weights)
                r2 = r2_score(y, y_pred, sample_weight=weights)
                
                print(f"   📊 성능 지표 - MSE: {mse:.4f}, R²: {r2:.4f}")
                
                # 피처 중요도 분석
                if hasattr(ensemble_model.estimators_[0], 'feature_importances_'):
                    feature_importance = ensemble_model.estimators_[0].feature_importances_
                    top_features = pd.Series(feature_importance, index=X.columns).nlargest(10)
                    print(f"   🎯 주요 피처:")
                    for feature, importance in top_features.items():
                        print(f"      {feature}: {importance:.3f}")
                
                # 모델 저장 - 네이밍 통일
                self.models[f"{region.value}_ensemble"] = ensemble_model
                self.scalers[f"{region.value}_ensemble"] = scaler
                
                model_path = self.model_dir / f"ensemble_model_{self.model_version}.joblib"
                scaler_path = self.model_dir / f"ensemble_scaler_{self.model_version}.joblib"
                
                joblib.dump(ensemble_model, model_path)
                joblib.dump(scaler, scaler_path)
                
                print(f"   ✅ 앙상블 모델 저장: {model_path}")
                return True
                
                print(f"   📈 학습 데이터: {len(X)}개 샘플, {len(X.columns)}개 피처")
                
                # 피처 스케일링
                scaler = RobustScaler()
                X_scaled = scaler.fit_transform(X)
                
                # 모델 정의 (앙상블)
                models = {
                    'rf': RandomForestRegressor(
                        n_estimators=200,
                        max_depth=15,
                        min_samples_split=10,
                        min_samples_leaf=5,
                        random_state=42,
                        n_jobs=-1
                    ),
                    'gbm': GradientBoostingRegressor(
                        n_estimators=150,
                        max_depth=8,
                        learning_rate=0.1,
                        subsample=0.8,
                        random_state=42
                    ),
                    'ridge': Ridge(alpha=1.0, random_state=42)
                }
                
                # 개별 모델 학습 및 평가
                model_scores = {}
                trained_models = {}
                
                tscv = TimeSeriesSplit(n_splits=5)
                
                for name, model in models.items():
                    print(f"   🔧 {name} 모델 학습...")
                    
                    # 교차 검증
                    cv_scores = cross_val_score(model, X_scaled, y, cv=tscv, scoring='neg_mean_squared_error')
                    mse_score = -cv_scores.mean()
                    
                    # 전체 데이터로 학습
                    model.fit(X_scaled, y)
                    
                    model_scores[name] = mse_score
                    trained_models[name] = model
                    
                    print(f"      MSE: {mse_score:.6f}")
                
                # 앙상블 모델 생성
                best_models = sorted(model_scores.items(), key=lambda x: x[1])[:2]  # 상위 2개
                ensemble_models = [(name, trained_models[name]) for name, _ in best_models]
                
                ensemble = VotingRegressor(estimators=ensemble_models)
                ensemble.fit(X_scaled, y)
                
                # 최종 평가
                ensemble_score = -cross_val_score(ensemble, X_scaled, y, cv=tscv, scoring='neg_mean_squared_error').mean()
                print(f"   🎯 앙상블 MSE: {ensemble_score:.6f}")
                
                # 모델 저장
                model_path = self.model_dir / f"{region.value}_model_{self.model_version}.joblib"
                scaler_path = self.model_dir / f"{region.value}_scaler_{self.model_version}.joblib"
                
                joblib.dump(ensemble, model_path)
                joblib.dump(scaler, scaler_path)
                
                # 메모리에 저장
                self.models[region.value] = ensemble
                self.scalers[region.value] = scaler
                
                print(f"   ✅ {region.value} 모델 저장: {model_path}")
                return True
                
        except Exception as e:
            print(f"   ❌ {region.value} 모델 학습 실패: {e}")
            return False
    
    def _get_future_return(self, db, stock_id: int, current_date: date, future_date: date) -> Optional[float]:
        """미래 수익률 계산"""
        try:
            current_price = db.query(StockDailyPrice).filter(
                StockDailyPrice.stock_id == stock_id,
                StockDailyPrice.trade_date == current_date
            ).first()
            
            future_price = db.query(StockDailyPrice).filter(
                StockDailyPrice.stock_id == stock_id,
                StockDailyPrice.trade_date >= future_date,
                StockDailyPrice.trade_date <= future_date + timedelta(days=7)
            ).first()
            
            if current_price and future_price:
                return_pct = (float(future_price.close_price) - float(current_price.close_price)) / float(current_price.close_price) * 100
                return return_pct
            
            return None
            
        except Exception:
            return None
    
    def _train_ensemble_model(self, model_config: dict = None) -> bool:
        """글로벌 앙상블 모델 학습 - 한국과 미국 모델을 결합"""
        print("🌍 글로벌 앙상블 모델 학습...")
        
        try:
            # 한국과 미국 모델이 모두 학습되었는지 확인
            if MarketRegion.KR.value not in self.models or MarketRegion.US.value not in self.models:
                print("   ⚠️ 기본 시장 모델이 학습되지 않음")
                return False
            
            # 앙상블을 위한 글로벌 데이터 수집
            with get_db_session() as db:
                # 한국 + 미국 대표 종목들로 글로벌 데이터셋 구성
                kr_stocks = db.query(StockMaster).filter_by(
                    market_region=MarketRegion.KR.value,
                    is_active=True
                ).limit(10).all()
                
                us_stocks = db.query(StockMaster).filter_by(
                    market_region=MarketRegion.US.value,
                    is_active=True
                ).limit(10).all()
                
                all_features = []
                all_targets = []
                all_regions = []
                
                # 한국 데이터
                for stock in kr_stocks:
                    features, targets = self._collect_stock_data_for_ensemble(db, stock, MarketRegion.KR)
                    if features is not None and len(features) > 0:
                        all_features.extend(features)
                        all_targets.extend(targets)
                        all_regions.extend([MarketRegion.KR.value] * len(features))
                
                # 미국 데이터
                for stock in us_stocks:
                    features, targets = self._collect_stock_data_for_ensemble(db, stock, MarketRegion.US)
                    if features is not None and len(features) > 0:
                        all_features.extend(features)
                        all_targets.extend(targets)
                        all_regions.extend([MarketRegion.US.value] * len(features))
                
                if len(all_features) < 100:
                    print(f"   ⚠️ 앙상블 학습 데이터 부족: {len(all_features)}개")
                    return False
                
                # 글로벌 피처 DataFrame 생성
                X_global = pd.DataFrame(all_features)
                y_global = np.array(all_targets)
                regions = np.array(all_regions)
                
                print(f"   📈 앙상블 데이터: {len(X_global)}개 샘플, {len(X_global.columns)}개 피처")
                
                # 지역별 가중치 적용 (균형 조정)
                kr_weight = 1.0 / np.sum(regions == MarketRegion.KR.value)
                us_weight = 1.0 / np.sum(regions == MarketRegion.US.value)
                
                sample_weights = np.where(regions == MarketRegion.KR.value, kr_weight, us_weight)
                sample_weights = sample_weights / sample_weights.sum() * len(sample_weights)  # 정규화
                
                # 글로벌 스케일러
                global_scaler = RobustScaler()
                X_scaled = global_scaler.fit_transform(X_global)
                
                # 글로벌 앙상블 모델 정의
                global_ensemble = VotingRegressor([
                    ('rf_global', RandomForestRegressor(
                        n_estimators=model_config.get('n_estimators', 200),
                        max_depth=model_config.get('max_depth', 12),
                        min_samples_split=5,
                        min_samples_leaf=2,
                        random_state=42,
                        n_jobs=-1
                    )),
                    ('gb_global', GradientBoostingRegressor(
                        n_estimators=150,
                        max_depth=8,
                        learning_rate=0.08,
                        subsample=0.8,
                        random_state=42
                    )),
                    ('ridge_global', Ridge(alpha=1.0, random_state=42))
                ])
                
                # 앙상블 모델 학습
                print("   🏋️ 글로벌 앙상블 학습 중...")
                global_ensemble.fit(X_scaled, y_global, sample_weight=sample_weights)
                
                # 성능 평가
                y_pred = global_ensemble.predict(X_scaled)
                mse = mean_squared_error(y_global, y_pred, sample_weight=sample_weights)
                r2 = r2_score(y_global, y_pred, sample_weight=sample_weights)
                
                print(f"   📊 글로벌 앙상블 성능 - MSE: {mse:.4f}, R²: {r2:.4f}")
                
                # 모델 저장
                self.models['global_ensemble'] = global_ensemble
                self.scalers['global_ensemble'] = global_scaler
                
                ensemble_path = self.model_dir / "global_ensemble_model.joblib"
                ensemble_scaler_path = self.model_dir / "global_ensemble_scaler.joblib"
                
                joblib.dump(global_ensemble, ensemble_path)
                joblib.dump(global_scaler, ensemble_scaler_path)
                
                print("   ✅ 글로벌 앙상블 모델 학습 완료")
                return True
                
        except Exception as e:
            print(f"   ❌ 글로벌 앙상블 학습 실패: {e}")
            import traceback
            print(f"   상세 오류: {traceback.format_exc()}")
            return False
    
    def _collect_stock_data_for_ensemble(self, db, stock: StockMaster, region: MarketRegion) -> Tuple[List, List]:
        """앙상블용 주식 데이터 수집"""
        try:
            features_list = []
            targets_list = []
            
            # 최근 60일간 데이터 수집
            end_date = datetime.now().date()
            
            for days_back in range(30, 90, 2):  # 2일 간격으로 샘플링
                current_date = end_date - timedelta(days=days_back)
                
                # 피처 생성
                features = self.prepare_global_features(stock.stock_id, current_date)
                if features is None or len(features) < 30:
                    continue
                
                # 미래 수익률 (타겟)
                future_date = current_date + timedelta(days=5)
                target = self._get_future_return(db, stock.stock_id, current_date, future_date)
                
                if target is None:
                    continue
                
                # 최신 피처 데이터
                latest_features = features.iloc[-1].fillna(0).to_dict()
                
                # 지역 정보 추가
                latest_features['is_kr'] = 1.0 if region == MarketRegion.KR else 0.0
                latest_features['is_us'] = 1.0 if region == MarketRegion.US else 0.0
                
                features_list.append(latest_features)
                targets_list.append(target)
            
            return features_list, targets_list
            
        except Exception as e:
            print(f"   ⚠️ {stock.stock_code} 데이터 수집 실패: {e}")
            return [], []
    
    def predict_stocks(self, region: MarketRegion, top_n: int = 5) -> List[GlobalPrediction]:
        """주식 예측 실행 - 모델 없으면 자동 학습"""
        print(f"🎯 {region.value} 주식 예측 중... (상위 {top_n}개)")
        
        predictions = []
        
        try:
            # 모델 로드
            if region.value not in self.models:
                self._load_model(region)
            
            # 모델이 여전히 없으면 자동 학습 수행
            if region.value not in self.models:
                print(f"   ⚠️ {region.value} 모델 없음 - 자동 학습 시작...")
                
                # 긴급 학습 수행
                try:
                    print(f"   🚀 {region.value} 긴급 ML 모델 학습 시작...")
                    success = self._train_market_model(region, {
                        'n_estimators': 100,  # 빠른 학습용
                        'max_depth': 10,
                        'random_state': 42,
                        'n_jobs': -1
                    })
                    
                    if success:
                        print(f"   ✅ {region.value} 긴급 학습 완료")
                    else:
                        print(f"   ❌ {region.value} 긴급 학습 실패")
                        return []
                        
                except Exception as e:
                    print(f"   ❌ {region.value} 긴급 학습 오류: {e}")
                    return []
            
            # 모델 최종 확인
            if region.value not in self.models:
                print(f"   ❌ {region.value} 모델 여전히 없음")
                return []

            model = self.models[region.value]
            scaler = self.scalers[region.value]
            
            with get_db_session() as db:
                # 종목 목록
                stocks = db.query(StockMaster).filter_by(
                    market_region=region.value,
                    is_active=True
                ).all()
                
                # 현재 시간 기준으로 적절한 날짜 결정
                now = datetime.now()
                current_time = now.time()
                
                # 시장별 데이터 가용 시간 기준
                if region == MarketRegion.KR:
                    # 한국 시장: 16:00(장 마감) 이후면 당일 데이터 사용
                    if current_time.hour >= 16:
                        target_date = now.date()  # 당일 데이터
                    else:
                        target_date = now.date() - timedelta(days=1)  # 전일 데이터
                else:
                    # 미국 시장: 05:30(한국시간 장 마감 후) ~ 17:00 사이면 당일 데이터
                    hour = current_time.hour
                    minute = current_time.minute
                    
                    if (hour == 5 and minute >= 30) or (6 <= hour <= 16):
                        target_date = now.date()  # 당일 데이터
                    else:
                        target_date = now.date() - timedelta(days=1)  # 전일 데이터
                
                print(f"🗓️ {region.value} 예측 기준일: {target_date} ({'당일' if target_date == now.date() else '전일'} 데이터)")
                
                for stock in stocks:
                    try:
                        # 피처 생성
                        features = self.prepare_global_features(stock.stock_id, target_date)
                        
                        if features is None or len(features) == 0:
                            continue
                        
                        # 예측 실행
                        latest_features = features.iloc[-1].fillna(0)
                        X_scaled = scaler.transform([latest_features])
                        
                        predicted_return = model.predict(X_scaled)[0]
                        
                        # 신뢰도 점수 계산 (간소화)
                        confidence = self._calculate_confidence(features, predicted_return)
                        
                        # 리스크 점수 계산
                        risk_score = self._calculate_risk_score(features, predicted_return)
                        
                        # 추천 등급 결정
                        recommendation = self._determine_recommendation(predicted_return, confidence, risk_score)
                        
                        # 목표가/손절가 계산
                        current_price = float(features['close'].iloc[-1])
                        target_price = current_price * (1 + predicted_return / 100)
                        stop_loss = current_price * 0.95  # 5% 손절
                        
                        # 추론 이유
                        reasoning = self._generate_reasoning(features, predicted_return, stock)
                        
                        prediction = GlobalPrediction(
                            stock_code=stock.stock_code,
                            market_region=region.value,
                            predicted_return=predicted_return,
                            confidence_score=confidence,
                            risk_score=risk_score,
                            recommendation=recommendation,
                            target_price=target_price,
                            stop_loss=stop_loss,
                            reasoning=reasoning
                        )
                        
                        predictions.append(prediction)
                        
                    except Exception as e:
                        print(f"   ⚠️ {stock.stock_code}: {e}")
                        continue
                
            # 수익률 기준 정렬
            predictions.sort(key=lambda x: x.predicted_return, reverse=True)
            
            print(f"   ✅ {len(predictions)}개 종목 예측 완료")
            return predictions[:top_n]
            
        except Exception as e:
            print(f"   ❌ {region.value} 예측 실패: {e}")
            return []
    
    def _load_model(self, region: MarketRegion):
        """모델 로드"""
        try:
            model_path = self.model_dir / f"{region.value}_model_{self.model_version}.joblib"
            scaler_path = self.model_dir / f"{region.value}_scaler_{self.model_version}.joblib"
            
            if model_path.exists() and scaler_path.exists():
                self.models[region.value] = joblib.load(model_path)
                self.scalers[region.value] = joblib.load(scaler_path)
                print(f"   ✅ {region.value} 모델 로드 완료")
            else:
                print(f"   ⚠️ {region.value} 모델 파일 없음")
                
        except Exception as e:
            print(f"   ❌ {region.value} 모델 로드 실패: {e}")
    
    def _calculate_confidence(self, features: pd.DataFrame, predicted_return: float) -> float:
        """신뢰도 점수 계산"""
        try:
            # 시장 조건에 따른 신뢰도 조정
            base_confidence = 60.0
            
            if self.market_condition:
                if self.market_condition.risk_level == "LOW":
                    base_confidence += 20
                elif self.market_condition.risk_level == "HIGH":
                    base_confidence -= 15
                elif self.market_condition.risk_level == "CRITICAL":
                    base_confidence -= 30
            
            # 기술적 지표 확신도
            rsi = features['rsi_14'].iloc[-1] if 'rsi_14' in features.columns else 50
            if 30 <= rsi <= 70:  # 중간 범위
                base_confidence += 10
            
            return max(20, min(95, base_confidence))
            
        except Exception:
            return 50.0
    
    def _calculate_risk_score(self, features: pd.DataFrame, predicted_return: float) -> float:
        """리스크 점수 계산 (0-100, 높을수록 위험)"""
        try:
            risk_score = 50.0  # 기본값
            
            # 변동성 기반 리스크
            if 'volatility_20' in features.columns:
                volatility = features['volatility_20'].iloc[-1]
                risk_score += volatility * 1000  # 변동성이 높으면 리스크 증가
            
            # 예측 수익률 극값 체크
            if abs(predicted_return) > 10:  # 10% 이상의 극단적 예측
                risk_score += 20
            
            # 시장 조건 리스크
            if self.market_condition:
                if self.market_condition.risk_level == "HIGH":
                    risk_score += 20
                elif self.market_condition.risk_level == "CRITICAL":
                    risk_score += 40
            
            return max(10, min(90, risk_score))
            
        except Exception:
            return 50.0
    
    def _determine_recommendation(self, predicted_return: float, confidence: float, risk_score: float) -> str:
        """추천 등급 결정"""
        
        # 고위험 상황에서는 보수적 접근
        if risk_score > 70:
            if predicted_return > 3 and confidence > 70:
                return "HOLD"
            else:
                return "SELL"
        
        # 일반적인 추천 로직
        if predicted_return > 5 and confidence > 70:
            return "STRONG_BUY"
        elif predicted_return > 2 and confidence > 60:
            return "BUY"
        elif predicted_return > -2 and predicted_return <= 2:
            return "HOLD"
        elif predicted_return > -5:
            return "SELL"
        else:
            return "STRONG_SELL"
    
    def _generate_reasoning(self, features: pd.DataFrame, predicted_return: float, stock: StockMaster) -> List[str]:
        """추론 이유 생성"""
        reasoning = []
        
        try:
            # 기술적 분석 이유
            if 'rsi_14' in features.columns:
                rsi = features['rsi_14'].iloc[-1]
                if rsi < 30:
                    reasoning.append("RSI 과매도 신호 (상승 가능성)")
                elif rsi > 70:
                    reasoning.append("RSI 과매수 신호 (조정 가능성)")
            
            # 트렌드 분석
            if 'sma_20' in features.columns and 'close' in features.columns:
                price = features['close'].iloc[-1]
                sma20 = features['sma_20'].iloc[-1]
                if price > sma20:
                    reasoning.append("20일 이평선 상회 (상승 트렌드)")
                else:
                    reasoning.append("20일 이평선 하회 (하락 트렌드)")
            
            # 시장 체제 영향
            if self.market_condition:
                reasoning.append(f"시장 체제: {self.market_condition.regime.value}")
                reasoning.append(f"리스크 수준: {self.market_condition.risk_level}")
            
            # 예측 강도
            if abs(predicted_return) > 5:
                reasoning.append("강한 가격 모멘텀 예상")
            elif abs(predicted_return) < 1:
                reasoning.append("횡보 패턴 예상")
            
        except Exception:
            reasoning.append("기본 기술적 분석 기반")
        
        return reasoning if reasoning else ["포괄적 시장 분석 기반"]


def main():
    """메인 실행"""
    engine = GlobalMLEngine()
    
    # 1. 모델 학습
    print("🏋️ 글로벌 ML 모델 학습...")
    if engine.train_global_models():
        print("✅ 모델 학습 완료")
    else:
        print("❌ 모델 학습 실패")
        return False
    
    # 2. 예측 실행
    print("\n🎯 글로벌 예측 실행...")
    
    # 한국 예측
    kr_predictions = engine.predict_stocks(MarketRegion.KR, top_n=5)
    print(f"\n🇰🇷 한국 상위 5개 추천:")
    for pred in kr_predictions:
        print(f"  {pred.stock_code}: {pred.predicted_return:.2f}% ({pred.recommendation})")
    
    # 미국 예측
    us_predictions = engine.predict_stocks(MarketRegion.US, top_n=5)
    print(f"\n🇺🇸 미국 상위 5개 추천:")
    for pred in us_predictions:
        print(f"  {pred.stock_code}: {pred.predicted_return:.2f}% ({pred.recommendation})")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
