#!/usr/bin/env python3
"""
새로운 스키마에 최적화된 ML 모델 학습 및 추천 시스템
대규모 서비스와 고품질 데이터를 활용한 수익률 최적화
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from decimal import Decimal

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import (
    StockMaster, StockDailyPrice, StockTechnicalIndicator,
    TradingUniverse, TradingUniverseItem, StockRecommendation
)
from app.database.redis_client import redis_client


class EnhancedMLTrainer:
    """향상된 ML 모델 학습기"""
    
    def __init__(self):
        self.universe_id = 1  # 기본 한국 유니버스
        self.prediction_days = [1, 5, 20]  # 예측 기간
    
    def verify_data_availability(self) -> Dict[str, Any]:
        """학습 데이터 가용성 확인"""
        print("🔍 학습 데이터 가용성 확인...")
        
        try:
            with get_db_session() as db:
                # 유니버스 정보
                universe = db.query(TradingUniverse).filter(
                    TradingUniverse.universe_id == self.universe_id
                ).first()
                
                if not universe:
                    return {"success": False, "error": "유니버스를 찾을 수 없습니다"}
                
                # 유니버스 종목 수
                universe_stocks = db.query(TradingUniverseItem).filter(
                    TradingUniverseItem.universe_id == self.universe_id,
                    TradingUniverseItem.is_active == True
                ).count()
                
                # 주가 데이터 수
                price_data_count = db.query(StockDailyPrice).join(
                    TradingUniverseItem,
                    StockDailyPrice.stock_id == TradingUniverseItem.stock_id
                ).filter(
                    TradingUniverseItem.universe_id == self.universe_id,
                    TradingUniverseItem.is_active == True
                ).count()
                
                # 기술적 지표 데이터 수
                indicator_data_count = db.query(StockTechnicalIndicator).join(
                    TradingUniverseItem,
                    StockTechnicalIndicator.stock_id == TradingUniverseItem.stock_id
                ).filter(
                    TradingUniverseItem.universe_id == self.universe_id,
                    TradingUniverseItem.is_active == True
                ).count()
                
                # 데이터 날짜 범위
                from sqlalchemy import text
                date_range = db.execute(text("""
                    SELECT 
                        MIN(sp.trade_date) as min_date,
                        MAX(sp.trade_date) as max_date
                    FROM stock_daily_price sp
                    INNER JOIN trading_universe_item tui ON sp.stock_id = tui.stock_id
                    WHERE tui.universe_id = :universe_id AND tui.is_active = true
                """), {"universe_id": self.universe_id}).fetchone()
                
                return {
                    "success": True,
                    "universe_name": universe.universe_name,
                    "universe_stocks": universe_stocks,
                    "price_data_count": price_data_count,
                    "indicator_data_count": indicator_data_count,
                    "date_range": {
                        "start": date_range.min_date,
                        "end": date_range.max_date
                    }
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_ml_dataset(self) -> Optional[pd.DataFrame]:
        """ML 학습용 데이터셋 생성"""
        print("📊 ML 학습용 데이터셋 생성 중...")
        
        try:
            with get_db_session() as db:
                # 통합 데이터 쿼리 (주가 + 기술적 지표)
                from sqlalchemy import text
                query = text("""
                    SELECT 
                        sm.stock_id,
                        sm.stock_code,
                        sm.stock_name,
                        sm.sector_classification,
                        sp.trade_date,
                        sp.open_price,
                        sp.high_price,
                        sp.low_price,
                        sp.close_price,
                        sp.volume,
                        sp.volume_value,
                        sp.daily_return_pct,
                        sp.price_change_pct,
                        sp.vwap,
                        sp.typical_price,
                        sp.true_range,
                        sti.sma_5,
                        sti.sma_10,
                        sti.sma_20,
                        sti.sma_50,
                        sti.ema_12,
                        sti.ema_26,
                        sti.rsi_14,
                        sti.macd_line,
                        sti.macd_signal,
                        sti.macd_histogram,
                        sti.bb_upper_20_2,
                        sti.bb_middle_20,
                        sti.bb_lower_20_2,
                        sti.bb_width,
                        sti.bb_percent,
                        sti.volume_sma_20,
                        sti.volume_ratio,
                        sti.volatility_20
                    FROM stock_master sm
                    INNER JOIN trading_universe_item tui ON sm.stock_id = tui.stock_id
                    INNER JOIN stock_daily_price sp ON sm.stock_id = sp.stock_id
                    INNER JOIN stock_technical_indicator sti ON sm.stock_id = sti.stock_id 
                        AND sp.trade_date = sti.calculation_date
                    WHERE tui.universe_id = :universe_id 
                        AND tui.is_active = true
                        AND sp.trade_date >= :start_date
                    ORDER BY sm.stock_id, sp.trade_date
                """)
                
                # 최근 30일 데이터
                start_date = datetime.now().date() - timedelta(days=30)
                
                result = db.execute(query, {
                    "universe_id": self.universe_id,
                    "start_date": start_date
                }).fetchall()
                
                if not result:
                    print("❌ 학습용 데이터가 없습니다!")
                    return None
                
                # DataFrame 생성
                df = pd.DataFrame(result)
                print(f"✅ 총 {len(df)}개 학습 샘플 생성")
                
                # 데이터 타입 변환
                numeric_columns = [
                    'open_price', 'high_price', 'low_price', 'close_price',
                    'volume', 'volume_value', 'daily_return_pct', 'price_change_pct',
                    'vwap', 'typical_price', 'true_range',
                    'sma_5', 'sma_10', 'sma_20', 'sma_50',
                    'ema_12', 'ema_26', 'rsi_14',
                    'macd_line', 'macd_signal', 'macd_histogram',
                    'bb_upper_20_2', 'bb_middle_20', 'bb_lower_20_2',
                    'bb_width', 'bb_percent', 'volume_sma_20', 'volume_ratio',
                    'volatility_20'
                ]
                
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 날짜 변환
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                return df
                
        except Exception as e:
            print(f"❌ 데이터셋 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """타겟 변수 생성 (미래 수익률)"""
        print("🎯 타겟 변수 생성 중...")
        
        try:
            # 각 종목별로 미래 수익률 계산
            result_dfs = []
            
            for stock_id in df['stock_id'].unique():
                stock_df = df[df['stock_id'] == stock_id].copy()
                stock_df = stock_df.sort_values('trade_date').reset_index(drop=True)
                
                # 미래 수익률 계산
                for days in self.prediction_days:
                    future_col = f'future_return_{days}d'
                    stock_df[future_col] = (
                        stock_df['close_price'].shift(-days) / stock_df['close_price'] - 1
                    ) * 100
                
                # 분류 타겟 (상승/하락)
                stock_df['target_1d_up'] = (stock_df['future_return_1d'] > 0).astype(int)
                stock_df['target_5d_up'] = (stock_df['future_return_5d'] > 0).astype(int)
                stock_df['target_20d_up'] = (stock_df['future_return_20d'] > 0).astype(int)
                
                # 강한 상승 타겟 (3% 이상)
                stock_df['target_1d_strong'] = (stock_df['future_return_1d'] > 3.0).astype(int)
                stock_df['target_5d_strong'] = (stock_df['future_return_5d'] > 5.0).astype(int)
                stock_df['target_20d_strong'] = (stock_df['future_return_20d'] > 10.0).astype(int)
                
                result_dfs.append(stock_df)
            
            final_df = pd.concat(result_dfs, ignore_index=True)
            
            # 미래 데이터가 없는 행 제거
            final_df = final_df.dropna(subset=[f'future_return_{days}d' for days in self.prediction_days])
            
            print(f"✅ 타겟 변수 생성 완료: {len(final_df)}개 샘플")
            return final_df
            
        except Exception as e:
            print(f"❌ 타겟 변수 생성 실패: {e}")
            return df
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """고급 피처 엔지니어링"""
        print("🔧 고급 피처 엔지니어링 중...")
        
        try:
            result_dfs = []
            
            for stock_id in df['stock_id'].unique():
                stock_df = df[df['stock_id'] == stock_id].copy()
                stock_df = stock_df.sort_values('trade_date').reset_index(drop=True)
                
                # 가격 관련 피처
                stock_df['price_momentum_5'] = (
                    stock_df['close_price'] / stock_df['close_price'].shift(5) - 1
                ) * 100
                
                stock_df['price_momentum_10'] = (
                    stock_df['close_price'] / stock_df['close_price'].shift(10) - 1
                ) * 100
                
                # 상대 강도
                stock_df['price_vs_sma20'] = (
                    stock_df['close_price'] / stock_df['sma_20'] - 1
                ) * 100
                
                stock_df['price_vs_sma50'] = (
                    stock_df['close_price'] / stock_df['sma_50'] - 1
                ) * 100
                
                # 볼륨 관련 피처
                stock_df['volume_momentum'] = (
                    stock_df['volume'] / stock_df['volume'].shift(5) - 1
                ) * 100
                
                # 변동성 관련 피처
                stock_df['volatility_zscore'] = (
                    stock_df['volatility_20'] - stock_df['volatility_20'].rolling(10).mean()
                ) / stock_df['volatility_20'].rolling(10).std()
                
                # 기술적 지표 조합
                if 'ema_12' in stock_df.columns and 'ema_26' in stock_df.columns:
                    stock_df['ema_convergence'] = stock_df['ema_12'] - stock_df['ema_26']
                
                # RSI 관련 피처
                if 'rsi_14' in stock_df.columns:
                    stock_df['rsi_overbought'] = (stock_df['rsi_14'] > 70).astype(int)
                    stock_df['rsi_oversold'] = (stock_df['rsi_14'] < 30).astype(int)
                
                # 볼린저 밴드 관련 피처
                if 'bb_percent' in stock_df.columns:
                    stock_df['bb_squeeze'] = (stock_df['bb_width'] < stock_df['bb_width'].rolling(10).quantile(0.2)).astype(int)
                
                # 트렌드 관련 피처
                stock_df['trend_strength'] = stock_df['sma_20'].pct_change(5) * 100
                
                # 가격 패턴
                stock_df['near_high'] = (
                    stock_df['close_price'] / stock_df['high_price'].rolling(20).max()
                )
                
                stock_df['near_low'] = (
                    stock_df['close_price'] / stock_df['low_price'].rolling(20).min()
                )
                
                result_dfs.append(stock_df)
            
            final_df = pd.concat(result_dfs, ignore_index=True)
            print(f"✅ 피처 엔지니어링 완료: {len(final_df.columns)}개 피처")
            
            return final_df
            
        except Exception as e:
            print(f"❌ 피처 엔지니어링 실패: {e}")
            import traceback
            traceback.print_exc()
            return df
    
    def train_ml_models(self, df: pd.DataFrame) -> Dict[str, Any]:
        """다중 ML 모델 학습"""
        print("🤖 ML 모델 학습 시작...")
        
        try:
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import train_test_split, cross_val_score
            from sklearn.metrics import classification_report, accuracy_score
            from sklearn.preprocessing import StandardScaler
            import pickle
            
            # 피처 선택
            feature_columns = [
                'daily_return_pct', 'price_change_pct', 'volume_ratio',
                'rsi_14', 'macd_line', 'bb_percent',
                'price_momentum_5', 'price_momentum_10',
                'price_vs_sma20', 'price_vs_sma50',
                'volume_momentum', 'volatility_zscore',
                'trend_strength', 'near_high', 'near_low'
            ]
            
            # 존재하는 피처만 선택
            available_features = [col for col in feature_columns if col in df.columns]
            print(f"📊 사용 가능한 피처: {len(available_features)}개")
            
            if len(available_features) < 5:
                return {"success": False, "error": "충분한 피처가 없습니다"}
            
            # 데이터 준비
            X = df[available_features].fillna(0)
            y = df['target_1d_up']  # 1일 후 상승 예측
            
            # NaN 제거
            mask = ~(X.isna().any(axis=1) | y.isna())
            X = X[mask]
            y = y[mask]
            
            if len(X) < 50:
                return {"success": False, "error": f"학습 데이터 부족: {len(X)}개"}
            
            print(f"✅ 학습 데이터 준비: {len(X)}개 샘플")
            
            # 데이터 분할
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # 스케일링
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # 모델 학습
            models = {
                'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42),
                'GradientBoosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
                'LogisticRegression': LogisticRegression(random_state=42, max_iter=1000)
            }
            
            model_results = {}
            best_model = None
            best_score = 0
            
            for name, model in models.items():
                print(f"🔄 {name} 모델 학습 중...")
                
                if name == 'LogisticRegression':
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                else:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                
                accuracy = accuracy_score(y_test, y_pred)
                cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
                
                model_results[name] = {
                    'accuracy': accuracy,
                    'cv_mean': cv_scores.mean(),
                    'cv_std': cv_scores.std(),
                    'model': model
                }
                
                print(f"   정확도: {accuracy:.4f}")
                print(f"   CV 평균: {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")
                
                if accuracy > best_score:
                    best_score = accuracy
                    best_model = model
                    best_model_name = name
            
            # 최적 모델 저장
            model_path = Path(__file__).parent / "models"
            model_path.mkdir(exist_ok=True)
            
            with open(model_path / "best_model.pkl", "wb") as f:
                pickle.dump(best_model, f)
            
            with open(model_path / "scaler.pkl", "wb") as f:
                pickle.dump(scaler, f)
            
            with open(model_path / "features.pkl", "wb") as f:
                pickle.dump(available_features, f)
            
            return {
                "success": True,
                "best_model": best_model_name,
                "best_accuracy": best_score,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "features_count": len(available_features),
                "model_results": {name: {k: v for k, v in result.items() if k != 'model'} 
                                for name, result in model_results.items()}
            }
            
        except Exception as e:
            print(f"❌ ML 모델 학습 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def generate_predictions(self) -> List[Dict[str, Any]]:
        """최신 데이터로 예측 생성"""
        print("📈 예측 생성 중...")
        
        try:
            import pickle
            from datetime import datetime
            
            model_path = Path(__file__).parent / "models"
            
            # 모델 로드
            with open(model_path / "best_model.pkl", "rb") as f:
                model = pickle.load(f)
            
            with open(model_path / "scaler.pkl", "rb") as f:
                scaler = pickle.load(f)
            
            with open(model_path / "features.pkl", "rb") as f:
                features = pickle.load(f)
            
            # 최신 데이터 가져오기
            df = self.create_ml_dataset()
            if df is None:
                return []
            
            df = self.create_features(df)
            
            # 최신 날짜 데이터만 선택
            latest_date = df['trade_date'].max()
            latest_df = df[df['trade_date'] == latest_date].copy()
            
            if len(latest_df) == 0:
                return []
            
            # 예측 수행
            X = latest_df[features].fillna(0)
            
            if hasattr(model, 'predict_proba'):
                # 확률 예측
                if 'LogisticRegression' in str(type(model)):
                    X_scaled = scaler.transform(X)
                    predictions = model.predict_proba(X_scaled)[:, 1]
                else:
                    predictions = model.predict_proba(X)[:, 1]
            else:
                predictions = model.predict(X)
            
            # 결과 생성
            results = []
            for i, (_, row) in enumerate(latest_df.iterrows()):
                results.append({
                    'stock_id': int(row['stock_id']),
                    'stock_code': row['stock_code'],
                    'stock_name': row['stock_name'],
                    'prediction_score': float(predictions[i]),
                    'prediction_date': latest_date.date(),
                    'target_date': (latest_date + timedelta(days=1)).date()
                })
            
            # 점수순 정렬
            results.sort(key=lambda x: x['prediction_score'], reverse=True)
            
            print(f"✅ {len(results)}개 종목 예측 완료")
            return results
            
        except Exception as e:
            print(f"❌ 예측 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def save_recommendations(self, predictions: List[Dict[str, Any]], top_n: int = 10) -> int:
        """추천 결과 저장"""
        print(f"💾 상위 {top_n}개 추천 저장 중...")
        
        try:
            saved_count = 0
            
            with get_db_session() as db:
                for rank, pred in enumerate(predictions[:top_n], 1):
                    # 기존 추천 확인
                    existing_rec = db.query(StockRecommendation).filter(
                        StockRecommendation.stock_id == pred['stock_id'],
                        StockRecommendation.recommendation_date == pred['prediction_date']
                    ).first()
                    
                    if existing_rec:
                        # 기존 추천 업데이트
                        existing_rec.ml_score = pred['prediction_score']
                        existing_rec.universe_rank = rank
                        existing_rec.model_name = "Enhanced ML Model"
                        existing_rec.model_version = "v2.0"
                        existing_rec.updated_at = datetime.now()
                    else:
                        # 새로운 추천 생성
                        new_rec = StockRecommendation(
                            stock_id=pred['stock_id'],
                            universe_id=self.universe_id,
                            recommendation_date=pred['prediction_date'],
                            target_date=pred['target_date'],
                            ml_score=pred['prediction_score'],
                            universe_rank=rank,
                            model_name="Enhanced ML Model",
                            model_version="v2.0",
                            recommendation_reason=f"ML Score: {pred['prediction_score']:.4f}"
                        )
                        db.add(new_rec)
                        saved_count += 1
                
                db.commit()
            
            print(f"✅ {saved_count}개 추천 저장 완료")
            return saved_count
            
        except Exception as e:
            print(f"❌ 추천 저장 실패: {e}")
            return 0


def main():
    """메인 실행 함수"""
    print("🚀 향상된 ML 모델 학습 및 추천 시스템")
    print("="*70)
    print("📋 작업 순서:")
    print("1. 데이터 가용성 확인")
    print("2. ML 데이터셋 생성")
    print("3. 타겟 변수 생성")
    print("4. 피처 엔지니어링")
    print("5. ML 모델 학습")
    print("6. 예측 생성")
    print("7. 추천 저장")
    print("="*70)
    
    trainer = EnhancedMLTrainer()
    
    # 1단계: 데이터 가용성 확인
    print("\n1️⃣ 데이터 가용성 확인")
    data_check = trainer.verify_data_availability()
    
    if not data_check["success"]:
        print(f"❌ 데이터 확인 실패: {data_check['error']}")
        return False
    
    print(f"✅ 유니버스: {data_check['universe_name']}")
    print(f"✅ 종목 수: {data_check['universe_stocks']}개")
    print(f"✅ 주가 데이터: {data_check['price_data_count']}개")
    print(f"✅ 기술적 지표: {data_check['indicator_data_count']}개")
    print(f"✅ 데이터 기간: {data_check['date_range']['start']} ~ {data_check['date_range']['end']}")
    
    # 2단계: ML 데이터셋 생성
    print("\n2️⃣ ML 데이터셋 생성")
    df = trainer.create_ml_dataset()
    
    if df is None:
        print("❌ 데이터셋 생성 실패")
        return False
    
    # 3단계: 타겟 변수 생성
    print("\n3️⃣ 타겟 변수 생성")
    df = trainer.create_target_variables(df)
    
    # 4단계: 피처 엔지니어링
    print("\n4️⃣ 피처 엔지니어링")
    df = trainer.create_features(df)
    
    # 5단계: ML 모델 학습
    print("\n5️⃣ ML 모델 학습")
    training_result = trainer.train_ml_models(df)
    
    if not training_result["success"]:
        print(f"❌ 모델 학습 실패: {training_result['error']}")
        return False
    
    print(f"✅ 최적 모델: {training_result['best_model']}")
    print(f"✅ 최고 정확도: {training_result['best_accuracy']:.4f}")
    print(f"✅ 학습 샘플: {training_result['training_samples']}개")
    print(f"✅ 테스트 샘플: {training_result['test_samples']}개")
    print(f"✅ 피처 수: {training_result['features_count']}개")
    
    # 6단계: 예측 생성
    print("\n6️⃣ 예측 생성")
    predictions = trainer.generate_predictions()
    
    if not predictions:
        print("❌ 예측 생성 실패")
        return False
    
    print(f"✅ {len(predictions)}개 종목 예측 완료")
    
    # 상위 10개 예측 출력
    print("\n🏆 상위 10개 예측:")
    for i, pred in enumerate(predictions[:10], 1):
        print(f"   {i}. {pred['stock_code']} ({pred['stock_name']}) - 점수: {pred['prediction_score']:.4f}")
    
    # 7단계: 추천 저장
    print("\n7️⃣ 추천 저장")
    saved_count = trainer.save_recommendations(predictions, top_n=10)
    
    # 성공 요약
    print("\n" + "="*70)
    print("🎉 향상된 ML 모델 학습 및 추천 시스템 완료!")
    print("="*70)
    print(f"✅ 최적 모델: {training_result['best_model']}")
    print(f"✅ 모델 정확도: {training_result['best_accuracy']:.4f}")
    print(f"✅ 학습 데이터: {training_result['training_samples']}개")
    print(f"✅ 예측 종목: {len(predictions)}개")
    print(f"✅ 저장된 추천: {saved_count}개")
    print("\n🚀 추천 시스템이 완전히 준비되었습니다!")
    
    # Discord 알림
    try:
        from app.services.notification import NotificationService
        notification = NotificationService()
        
        # 상위 5개 추천 포맷팅
        top_5_text = "\n".join([
            f"{i}. {pred['stock_code']} ({pred['stock_name']}) - {pred['prediction_score']:.4f}"
            for i, pred in enumerate(predictions[:5], 1)
        ])
        
        message = (
            f"🤖 **향상된 ML 모델 학습 완료**\n\n"
            f"📅 학습 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🎯 최적 모델: {training_result['best_model']}\n"
            f"📊 모델 정확도: {training_result['best_accuracy']:.4f}\n"
            f"🔢 학습 샘플: {training_result['training_samples']}개\n"
            f"🔧 피처 수: {training_result['features_count']}개\n\n"
            f"🏆 **상위 5개 추천:**\n{top_5_text}\n\n"
            f"✅ **추천 시스템 완전 준비!**"
        )
        notification._send_simple_slack_message(message)
        print("📱 Discord 알림 전송 완료")
    except Exception as e:
        print(f"⚠️ Discord 알림 전송 실패: {e}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
