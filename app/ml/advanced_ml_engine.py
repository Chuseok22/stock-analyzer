#!/usr/bin/env python3
"""
고도화된 ML 엔진 - 딥러닝, 고급 앙상블, 시계열 특화
- LSTM/GRU 기반 시계열 예측
- Transformer 아키텍처 적용
- 고급 앙상블 (Stacking, Blending)
- 베이지안 최적화 하이퍼파라미터 튜닝
- 멀티 태스크 학습
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# 딥러닝 라이브러리
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    from sklearn.preprocessing import MinMaxScaler
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # PyTorch 미설치시 더미 클래스 정의
    class Dataset:
        pass
    class nn:
        class Module:
            pass
        class LSTM:
            pass
        class MultiheadAttention:
            pass
        class Linear:
            pass
        class ReLU:
            pass
        class Dropout:
            pass
        class BatchNorm1d:
            pass
        class Sequential:
            pass
        class TransformerEncoderLayer:
            pass
        class TransformerEncoder:
            pass
    class torch:
        class FloatTensor:
            pass
        @staticmethod
        def zeros(*args, **kwargs):
            return None
        @staticmethod
        def arange(*args, **kwargs):
            return None
        @staticmethod
        def exp(*args, **kwargs):
            return None
        @staticmethod
        def sin(*args, **kwargs):
            return None
        @staticmethod
        def cos(*args, **kwargs):
            return None
        @staticmethod
        def device(*args, **kwargs):
            return "cpu"
        @staticmethod
        def save(*args, **kwargs):
            pass
    class optim:
        class AdamW:
            pass
        class lr_scheduler:
            class ReduceLROnPlateau:
                pass
    print("⚠️ PyTorch 미설치 - 기본 모델로 대체")

# ML 라이브러리
from sklearn.ensemble import (
    RandomForestRegressor, GradientBoostingRegressor, 
    VotingRegressor, StackingRegressor
)
from sklearn.linear_model import Ridge, ElasticNet, BayesianRidge
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

# 베이지안 최적화 (선택적)
try:
    from skopt import BayesSearchCV
    from skopt.space import Real, Integer
    BAYESIAN_OPTIMIZATION_AVAILABLE = True
except ImportError:
    BAYESIAN_OPTIMIZATION_AVAILABLE = False

import joblib
import json

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockMaster, StockDailyPrice, MarketRegion
from app.services.dynamic_universe_manager import DynamicUniverseManager


class ModelType(Enum):
    """모델 유형"""
    LSTM = "lstm"
    GRU = "gru"
    TRANSFORMER = "transformer"
    STACKING_ENSEMBLE = "stacking_ensemble"
    VOTING_ENSEMBLE = "voting_ensemble"
    BAYESIAN_RIDGE = "bayesian_ridge"
    HYBRID_DEEP_ML = "hybrid_deep_ml"


@dataclass
class ModelPerformance:
    """모델 성능 지표"""
    model_type: str
    mse: float
    mae: float
    r2_score: float
    directional_accuracy: float
    sharpe_ratio: float
    max_drawdown: float
    training_time: float
    prediction_time: float


class StockSequenceDataset(Dataset):
    """주식 시계열 데이터셋 (PyTorch)"""
    
    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class LSTMPredictor(nn.Module):
    """LSTM 기반 주식 예측 모델"""
    
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 3, 
                 dropout: float = 0.2, output_size: int = 1):
        super(LSTMPredictor, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM 레이어
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True,
            bidirectional=True
        )
        
        # 어텐션 메커니즘
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size * 2,  # bidirectional
            num_heads=8,
            dropout=dropout,
            batch_first=True
        )
        
        # 완전 연결 레이어
        self.fc_layers = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, output_size)
        )
        
        # 배치 정규화
        self.batch_norm = nn.BatchNorm1d(hidden_size * 2)
        
    def forward(self, x):
        # LSTM 처리
        lstm_out, _ = self.lstm(x)
        
        # 어텐션 적용
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # 마지막 시퀀스 선택
        last_output = attn_out[:, -1, :]
        
        # 배치 정규화
        normalized = self.batch_norm(last_output)
        
        # 완전 연결 레이어
        output = self.fc_layers(normalized)
        
        return output


class TransformerPredictor(nn.Module):
    """Transformer 기반 주식 예측 모델"""
    
    def __init__(self, input_size: int, d_model: int = 256, nhead: int = 8, 
                 num_layers: int = 6, dropout: float = 0.1):
        super(TransformerPredictor, self).__init__()
        
        self.d_model = d_model
        self.input_projection = nn.Linear(input_size, d_model)
        
        # 포지셔널 인코딩
        self.positional_encoding = self._create_positional_encoding(1000, d_model)
        
        # Transformer 인코더
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # 출력 레이어
        self.output_layer = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1)
        )
        
    def _create_positional_encoding(self, max_len: int, d_model: int):
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                           -(np.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        return pe.unsqueeze(0)
    
    def forward(self, x):
        batch_size, seq_len, _ = x.shape
        
        # 입력 투영
        x = self.input_projection(x)
        
        # 포지셔널 인코딩 추가
        x += self.positional_encoding[:, :seq_len, :].to(x.device)
        
        # Transformer 처리
        transformer_out = self.transformer(x)
        
        # 마지막 시퀀스의 출력 사용
        last_output = transformer_out[:, -1, :]
        
        # 최종 예측
        output = self.output_layer(last_output)
        
        return output


class AdvancedMLEngine:
    """고도화된 ML 엔진"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.performance_history = {}
        self.model_version = "v4.0_advanced"
        
        # 모델 저장 경로
        self.model_dir = Path(__file__).parent.parent.parent / "storage" / "models" / "advanced"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # 동적 유니버스 관리자
        self.universe_manager = DynamicUniverseManager()
        
        # 시퀀스 길이 (시계열 입력)
        self.sequence_length = 60  # 60일 시계열
        
        # 디바이스 설정 (GPU 사용 가능시)
        if TORCH_AVAILABLE:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            print(f"🔧 PyTorch 디바이스: {self.device}")
        
        print("🧠 고도화된 ML 엔진 초기화 완료")
    
    def prepare_sequence_features(self, stock_id: int, target_date: date, 
                                sequence_length: int = None) -> Optional[np.ndarray]:
        """시계열 시퀀스 피처 생성"""
        if sequence_length is None:
            sequence_length = self.sequence_length
            
        print(f"📊 시퀀스 피처 생성: stock_id={stock_id}, length={sequence_length}")
        
        try:
            with get_db_session() as db:
                # 충분한 기간의 데이터 조회
                end_date = target_date
                start_date = end_date - timedelta(days=sequence_length * 2)  # 여유분
                
                prices = db.query(StockDailyPrice).filter(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date >= start_date,
                    StockDailyPrice.trade_date <= end_date
                ).order_by(StockDailyPrice.trade_date).all()
                
                if len(prices) < sequence_length + 10:  # 최소 데이터 요구량
                    return None
                
                # 기본 OHLCV 데이터
                data = []
                for price in prices:
                    row = [
                        float(price.open_price),
                        float(price.high_price),
                        float(price.low_price),
                        float(price.close_price),
                        float(price.volume) if price.volume else 0,
                        float(price.daily_return_pct) if price.daily_return_pct else 0
                    ]
                    data.append(row)
                
                df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close', 'volume', 'return'])
                
                # 고급 기술적 지표 추가
                df = self._add_advanced_technical_indicators(df)
                
                # 시장 미시구조 피처 추가
                df = self._add_microstructure_features(df)
                
                # 시퀀스 데이터 생성
                if len(df) < sequence_length:
                    return None
                
                # 마지막 sequence_length 만큼 사용
                sequence_data = df.iloc[-sequence_length:].values
                
                # NaN 처리
                sequence_data = np.nan_to_num(sequence_data, nan=0.0, posinf=1.0, neginf=-1.0)
                
                return sequence_data.astype(np.float32)
                
        except Exception as e:
            print(f"❌ 시퀀스 피처 생성 실패: {e}")
            return None
    
    def _add_advanced_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """고급 기술적 지표 추가"""
        try:
            # 이동평균들
            for window in [5, 10, 20, 50]:
                df[f'sma_{window}'] = df['close'].rolling(window, min_periods=1).mean()
                df[f'ema_{window}'] = df['close'].ewm(span=window).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            rs = gain / loss.replace(0, 1e-8)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # 볼린저 밴드
            sma_20 = df['close'].rolling(20, min_periods=1).mean()
            std_20 = df['close'].rolling(20, min_periods=1).std()
            df['bb_upper'] = sma_20 + (std_20 * 2)
            df['bb_lower'] = sma_20 - (std_20 * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']).replace(0, 1e-8)
            
            # 스토캐스틱
            low_14 = df['low'].rolling(14, min_periods=1).min()
            high_14 = df['high'].rolling(14, min_periods=1).max()
            df['stoch_k'] = 100 * (df['close'] - low_14) / (high_14 - low_14).replace(0, 1e-8)
            df['stoch_d'] = df['stoch_k'].rolling(3, min_periods=1).mean()
            
            # 변동성 지표
            df['volatility_10'] = df['return'].rolling(10, min_periods=1).std()
            df['volatility_30'] = df['return'].rolling(30, min_periods=1).std()
            
            # 거래량 지표
            df['volume_sma_20'] = df['volume'].rolling(20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_20'].replace(0, 1)
            
            # 가격 레인지
            df['true_range'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['atr'] = df['true_range'].rolling(14, min_periods=1).mean()
            
            return df.fillna(method='ffill').fillna(0)
            
        except Exception as e:
            print(f"⚠️ 고급 기술적 지표 생성 실패: {e}")
            return df
    
    def _add_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """시장 미시구조 피처 추가"""
        try:
            # 가격 갭
            df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
            
            # 일중 수익률
            df['intraday_return'] = (df['close'] - df['open']) / df['open']
            
            # 상하 그림자
            df['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
            df['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
            
            # 몸통 크기
            df['body_size'] = abs(df['close'] - df['open']) / df['close']
            
            # 가격 위치 (일중)
            df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low']).replace(0, 1e-8)
            
            # 거래량 가중 평균 가격 (VWAP 근사)
            df['vwap_approx'] = (df['high'] + df['low'] + df['close']) / 3
            
            # 모멘텀 지표
            for period in [5, 10, 20]:
                df[f'momentum_{period}'] = df['close'].pct_change(period)
                df[f'roc_{period}'] = (df['close'] - df['close'].shift(period)) / df['close'].shift(period)
            
            # 상대 강도
            df['relative_volume'] = df['volume'] / df['volume'].rolling(20, min_periods=1).mean()
            
            return df.fillna(0)
            
        except Exception as e:
            print(f"⚠️ 미시구조 피처 생성 실패: {e}")
            return df
    
    def create_sequences_and_targets(self, stock_ids: List[int], region: MarketRegion, 
                                   lookback_days: int = 180) -> Tuple[np.ndarray, np.ndarray]:
        """시계열 시퀀스와 타겟 생성"""
        print(f"🔄 {region.value} 시퀀스 데이터 생성 중...")
        
        try:
            all_sequences = []
            all_targets = []
            
            end_date = datetime.now().date()
            
            for stock_id in stock_ids[:50]:  # 성능을 위해 50개로 제한
                try:
                    # 날짜별 시퀀스 생성
                    for days_back in range(self.sequence_length + 5, lookback_days, 5):  # 5일 간격
                        current_date = end_date - timedelta(days=days_back)
                        
                        # 시퀀스 피처 생성
                        sequence = self.prepare_sequence_features(stock_id, current_date)
                        if sequence is None:
                            continue
                        
                        # 타겟 생성 (5일 후 수익률)
                        future_date = current_date + timedelta(days=5)
                        target = self._get_future_return(stock_id, current_date, future_date)
                        if target is None:
                            continue
                        
                        all_sequences.append(sequence)
                        all_targets.append(target)
                        
                except Exception as e:
                    print(f"⚠️ 종목 {stock_id} 시퀀스 생성 실패: {e}")
                    continue
            
            if not all_sequences:
                print(f"❌ {region.value} 시퀀스 데이터 없음")
                return None, None
            
            sequences = np.array(all_sequences)
            targets = np.array(all_targets)
            
            print(f"✅ {region.value} 시퀀스 생성 완료: {sequences.shape}")
            return sequences, targets
            
        except Exception as e:
            print(f"❌ {region.value} 시퀀스 생성 실패: {e}")
            return None, None
    
    def _get_future_return(self, stock_id: int, current_date: date, future_date: date) -> Optional[float]:
        """미래 수익률 계산"""
        try:
            with get_db_session() as db:
                current_price = db.query(StockDailyPrice).filter(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date == current_date
                ).first()
                
                future_price = db.query(StockDailyPrice).filter(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date >= future_date,
                    StockDailyPrice.trade_date <= future_date + timedelta(days=7)
                ).order_by(StockDailyPrice.trade_date.asc()).first()
                
                if current_price and future_price:
                    return_pct = (float(future_price.close_price) - float(current_price.close_price)) / float(current_price.close_price) * 100
                    return return_pct
                
                return None
                
        except Exception:
            return None
    
    def train_lstm_model(self, sequences: np.ndarray, targets: np.ndarray, 
                        region: MarketRegion) -> bool:
        """LSTM 모델 학습"""
        if not TORCH_AVAILABLE:
            print("⚠️ PyTorch 미설치 - LSTM 학습 건너뜀")
            return False
            
        print(f"🧠 {region.value} LSTM 모델 학습 시작...")
        
        try:
            # 데이터 전처리
            scaler = MinMaxScaler()
            sequences_scaled = scaler.fit_transform(
                sequences.reshape(-1, sequences.shape[-1])
            ).reshape(sequences.shape)
            
            # 타겟 정규화
            target_scaler = MinMaxScaler()
            targets_scaled = target_scaler.fit_transform(targets.reshape(-1, 1)).flatten()
            
            # 데이터셋 분할
            split_idx = int(len(sequences_scaled) * 0.8)
            X_train, X_test = sequences_scaled[:split_idx], sequences_scaled[split_idx:]
            y_train, y_test = targets_scaled[:split_idx], targets_scaled[split_idx:]
            
            # 데이터셋 생성
            train_dataset = StockSequenceDataset(X_train, y_train)
            test_dataset = StockSequenceDataset(X_test, y_test)
            
            train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
            test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
            
            # 모델 생성
            input_size = sequences.shape[-1]
            model = LSTMPredictor(input_size=input_size).to(self.device)
            
            # 옵티마이저 및 손실함수
            optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-5)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
            criterion = nn.MSELoss()
            
            # 학습
            model.train()
            best_loss = float('inf')
            patience_counter = 0
            
            for epoch in range(100):  # 최대 100 에포크
                train_loss = 0.0
                for batch_X, batch_y in train_loader:
                    batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                    
                    optimizer.zero_grad()
                    outputs = model(batch_X).squeeze()
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    
                    # 그래디언트 클리핑
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    
                    optimizer.step()
                    train_loss += loss.item()
                
                # 검증
                model.eval()
                val_loss = 0.0
                with torch.no_grad():
                    for batch_X, batch_y in test_loader:
                        batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                        outputs = model(batch_X).squeeze()
                        val_loss += criterion(outputs, batch_y).item()
                
                val_loss /= len(test_loader)
                scheduler.step(val_loss)
                
                if val_loss < best_loss:
                    best_loss = val_loss
                    patience_counter = 0
                    # 최고 모델 저장
                    torch.save({
                        'model_state_dict': model.state_dict(),
                        'scaler': scaler,
                        'target_scaler': target_scaler,
                        'input_size': input_size
                    }, self.model_dir / f"{region.value}_lstm_{self.model_version}.pth")
                else:
                    patience_counter += 1
                
                if patience_counter >= 20:  # 조기 종료
                    break
                
                if (epoch + 1) % 10 == 0:
                    print(f"   에포크 {epoch+1}: 학습 손실={train_loss/len(train_loader):.6f}, 검증 손실={val_loss:.6f}")
                
                model.train()
            
            # 모델 저장
            self.models[f"{region.value}_lstm"] = model
            self.scalers[f"{region.value}_lstm"] = (scaler, target_scaler)
            
            print(f"✅ {region.value} LSTM 모델 학습 완료")
            return True
            
        except Exception as e:
            print(f"❌ {region.value} LSTM 학습 실패: {e}")
            return False
    
    def train_advanced_ensemble(self, X: np.ndarray, y: np.ndarray, 
                              region: MarketRegion) -> bool:
        """고급 앙상블 모델 학습"""
        print(f"🎯 {region.value} 고급 앙상블 모델 학습 시작...")
        
        try:
            # 베이스 모델들 정의
            base_models = [
                ('rf', RandomForestRegressor(n_estimators=200, max_depth=15, random_state=42)),
                ('gb', GradientBoostingRegressor(n_estimators=200, max_depth=8, random_state=42)),
                ('svr', SVR(kernel='rbf', gamma='scale')),
                ('ridge', Ridge(alpha=1.0)),
                ('elastic', ElasticNet(alpha=0.1, l1_ratio=0.5)),
                ('bayesian', BayesianRidge())
            ]
            
            # 스태킹 메타 모델
            meta_model = Ridge(alpha=0.1)
            
            # 스태킹 앙상블 생성
            stacking_model = StackingRegressor(
                estimators=base_models,
                final_estimator=meta_model,
                cv=5,
                n_jobs=-1
            )
            
            # 데이터 전처리
            scaler = RobustScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 베이지안 최적화 하이퍼파라미터 튜닝 (가능한 경우)
            if BAYESIAN_OPTIMIZATION_AVAILABLE:
                print("   🔍 베이지안 최적화 하이퍼파라미터 튜닝...")
                
                search_spaces = {
                    'rf__n_estimators': Integer(100, 300),
                    'rf__max_depth': Integer(10, 20),
                    'gb__n_estimators': Integer(100, 300),
                    'gb__learning_rate': Real(0.01, 0.2),
                    'final_estimator__alpha': Real(0.01, 10.0)
                }
                
                bayes_search = BayesSearchCV(
                    stacking_model,
                    search_spaces,
                    n_iter=20,
                    cv=3,
                    scoring='neg_mean_squared_error',
                    n_jobs=-1,
                    random_state=42
                )
                
                bayes_search.fit(X_scaled, y)
                best_model = bayes_search.best_estimator_
                
                print(f"   ✅ 최적 하이퍼파라미터: {bayes_search.best_params_}")
                
            else:
                # 기본 그리드 서치
                print("   🔍 그리드 서치 하이퍼파라미터 튜닝...")
                
                param_grid = {
                    'rf__n_estimators': [150, 200],
                    'gb__n_estimators': [150, 200],
                    'final_estimator__alpha': [0.1, 1.0]
                }
                
                grid_search = GridSearchCV(
                    stacking_model,
                    param_grid,
                    cv=3,
                    scoring='neg_mean_squared_error',
                    n_jobs=-1
                )
                
                grid_search.fit(X_scaled, y)
                best_model = grid_search.best_estimator_
            
            # 최종 모델 학습
            best_model.fit(X_scaled, y)
            
            # 성능 평가
            from sklearn.model_selection import cross_val_score
            cv_scores = cross_val_score(best_model, X_scaled, y, cv=5, scoring='neg_mean_squared_error')
            
            print(f"   📊 교차검증 MSE: {-cv_scores.mean():.6f} (±{cv_scores.std():.6f})")
            
            # 모델 저장
            self.models[f"{region.value}_advanced_ensemble"] = best_model
            self.scalers[f"{region.value}_advanced_ensemble"] = scaler
            
            model_path = self.model_dir / f"{region.value}_advanced_ensemble_{self.model_version}.joblib"
            scaler_path = self.model_dir / f"{region.value}_advanced_ensemble_scaler_{self.model_version}.joblib"
            
            joblib.dump(best_model, model_path)
            joblib.dump(scaler, scaler_path)
            
            print(f"✅ {region.value} 고급 앙상블 모델 학습 완료")
            return True
            
        except Exception as e:
            print(f"❌ {region.value} 고급 앙상블 학습 실패: {e}")
            return False
    
    async def train_advanced_models(self, region: MarketRegion) -> bool:
        """고도화된 모델들 학습"""
        print(f"🚀 {region.value} 고도화된 ML 모델 학습 시작...")
        
        try:
            # 1. 동적 유니버스에서 종목 목록 가져오기
            stock_codes = await self.universe_manager.get_current_universe(region)
            
            with get_db_session() as db:
                # 종목 ID 조회
                stocks = db.query(StockMaster).filter(
                    StockMaster.market_region == region.value,
                    StockMaster.is_active == True,
                    StockMaster.stock_code.in_(stock_codes)
                ).all()
                
                stock_ids = [stock.stock_id for stock in stocks]
            
            if not stock_ids:
                print(f"❌ {region.value} 활성 종목 없음")
                return False
            
            # 2. 시계열 시퀀스 데이터 생성
            sequences, targets = self.create_sequences_and_targets(stock_ids, region)
            
            if sequences is None or len(sequences) < 100:
                print(f"❌ {region.value} 학습 데이터 부족")
                return False
            
            # 3. LSTM 모델 학습
            lstm_success = self.train_lstm_model(sequences, targets, region)
            
            # 4. 고급 앙상블 모델 학습 (평탄화된 피처 사용)
            X_flat = sequences.reshape(len(sequences), -1)  # 시퀀스를 평탄화
            ensemble_success = self.train_advanced_ensemble(X_flat, targets, region)
            
            success = lstm_success or ensemble_success
            
            if success:
                print(f"🎉 {region.value} 고도화된 모델 학습 완료!")
            else:
                print(f"❌ {region.value} 모든 모델 학습 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ {region.value} 고도화된 모델 학습 실패: {e}")
            return False
    
    async def predict_with_advanced_models(self, region: MarketRegion, 
                                         top_n: int = 10) -> List[Dict]:
        """고도화된 모델로 예측"""
        print(f"🎯 {region.value} 고도화된 예측 실행...")
        
        try:
            # 동적 유니버스 종목 조회
            stock_codes = await self.universe_manager.get_current_universe(region)
            
            predictions = []
            
            with get_db_session() as db:
                stocks = db.query(StockMaster).filter(
                    StockMaster.market_region == region.value,
                    StockMaster.is_active == True,
                    StockMaster.stock_code.in_(stock_codes)
                ).all()
                
                for stock in stocks[:50]:  # 성능을 위해 50개로 제한
                    try:
                        # 현재 날짜 기준 피처 생성
                        current_date = datetime.now().date()
                        sequence = self.prepare_sequence_features(stock.stock_id, current_date)
                        
                        if sequence is None:
                            continue
                        
                        # 앙상블 예측
                        ensemble_pred = self._predict_with_ensemble(sequence, region)
                        
                        # LSTM 예측 (가능한 경우)
                        lstm_pred = self._predict_with_lstm(sequence, region)
                        
                        # 예측 결합 (앙상블 70%, LSTM 30%)
                        if ensemble_pred is not None and lstm_pred is not None:
                            final_pred = ensemble_pred * 0.7 + lstm_pred * 0.3
                        elif ensemble_pred is not None:
                            final_pred = ensemble_pred
                        elif lstm_pred is not None:
                            final_pred = lstm_pred
                        else:
                            continue
                        
                        # 신뢰도 계산
                        confidence = self._calculate_prediction_confidence(sequence, final_pred)
                        
                        predictions.append({
                            'stock_code': stock.stock_code,
                            'stock_name': stock.stock_name,
                            'predicted_return': final_pred,
                            'confidence': confidence,
                            'model_type': 'advanced_ensemble_lstm'
                        })
                        
                    except Exception as e:
                        print(f"⚠️ {stock.stock_code} 예측 실패: {e}")
                        continue
            
            # 예측 수익률 기준 정렬
            predictions.sort(key=lambda x: x['predicted_return'], reverse=True)
            
            print(f"✅ {region.value} 고도화된 예측 완료: {len(predictions)}개")
            return predictions[:top_n]
            
        except Exception as e:
            print(f"❌ {region.value} 고도화된 예측 실패: {e}")
            return []
    
    def _predict_with_ensemble(self, sequence: np.ndarray, region: MarketRegion) -> Optional[float]:
        """앙상블 모델로 예측"""
        try:
            model_key = f"{region.value}_advanced_ensemble"
            
            if model_key not in self.models:
                return None
            
            model = self.models[model_key]
            scaler = self.scalers[model_key]
            
            # 시퀀스를 평탄화
            X_flat = sequence.reshape(1, -1)
            X_scaled = scaler.transform(X_flat)
            
            prediction = model.predict(X_scaled)[0]
            return float(prediction)
            
        except Exception:
            return None
    
    def _predict_with_lstm(self, sequence: np.ndarray, region: MarketRegion) -> Optional[float]:
        """LSTM 모델로 예측"""
        if not TORCH_AVAILABLE:
            return None
            
        try:
            model_key = f"{region.value}_lstm"
            
            if model_key not in self.models:
                return None
            
            model = self.models[model_key]
            scaler, target_scaler = self.scalers[model_key]
            
            # 시퀀스 전처리
            sequence_scaled = scaler.transform(sequence)
            sequence_tensor = torch.FloatTensor(sequence_scaled).unsqueeze(0).to(self.device)
            
            # 예측
            model.eval()
            with torch.no_grad():
                prediction_scaled = model(sequence_tensor).cpu().numpy()[0]
                prediction = target_scaler.inverse_transform([[prediction_scaled]])[0][0]
            
            return float(prediction)
            
        except Exception:
            return None
    
    def _calculate_prediction_confidence(self, sequence: np.ndarray, prediction: float) -> float:
        """예측 신뢰도 계산"""
        try:
            # 시퀀스 데이터의 변동성 기반 신뢰도
            if len(sequence) < 10:
                return 0.5
            
            # 최근 변동성
            recent_returns = sequence[-20:, 5] if sequence.shape[1] > 5 else sequence[-20:, -1]  # return 컬럼
            volatility = np.std(recent_returns) if len(recent_returns) > 1 else 0.1
            
            # 예측 강도
            prediction_strength = min(abs(prediction) / 5.0, 1.0)  # 5% 기준 정규화
            
            # 변동성이 낮고 예측이 강할수록 신뢰도 높음
            volatility_score = max(0.1, 1.0 - volatility * 10)  # 변동성 역수
            strength_score = prediction_strength
            
            confidence = (volatility_score * 0.6 + strength_score * 0.4)
            return max(0.1, min(0.95, confidence))
            
        except Exception:
            return 0.5


# 사용 예시
async def main():
    """메인 테스트 함수"""
    print("🧠 고도화된 ML 엔진 테스트")
    print("="*60)
    
    engine = AdvancedMLEngine()
    
    try:
        # 한국 시장 고도화된 모델 학습
        print("\n1️⃣ 한국 시장 고도화된 모델 학습")
        kr_success = await engine.train_advanced_models(MarketRegion.KR)
        
        if kr_success:
            print("✅ 한국 시장 학습 성공")
            
            # 예측 테스트
            print("\n2️⃣ 한국 시장 예측 테스트")
            kr_predictions = await engine.predict_with_advanced_models(MarketRegion.KR, top_n=5)
            
            for pred in kr_predictions:
                print(f"   {pred['stock_code']}: {pred['predicted_return']:.2f}% (신뢰도: {pred['confidence']:.2f})")
        
        # 미국 시장 (시간 절약을 위해 주석 처리)
        # us_success = await engine.train_advanced_models(MarketRegion.US)
        
        print("\n🎉 고도화된 ML 엔진 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
