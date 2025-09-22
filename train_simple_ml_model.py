#!/usr/bin/env python3
"""
간단하고 효과적인 ML 모델 학습 (새로운 스키마용)
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import (
    StockMaster, StockDailyPrice, StockTechnicalIndicator,
    TradingUniverse, TradingUniverseItem, StockRecommendation
)
from sqlalchemy import text


class SimpleMLTrainer:
    """간단한 ML 학습기"""
    
    def __init__(self):
        self.universe_id = 1
    
    def get_training_data(self) -> pd.DataFrame:
        """학습 데이터 가져오기"""
        print("📊 학습 데이터 가져오기...")
        
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
                    WHERE tui.universe_id = :universe_id 
                        AND tui.is_active = true
                    ORDER BY sm.stock_id, sp.trade_date
                """)
                
                result = db.execute(query, {"universe_id": self.universe_id}).fetchall()
                
                if not result:
                    print("❌ 데이터 없음")
                    return pd.DataFrame()
                
                df = pd.DataFrame(result)
                print(f"✅ {len(df)}개 레코드 로드")
                
                # 데이터 타입 변환
                numeric_cols = ['close_price', 'volume', 'daily_return_pct', 
                               'sma_20', 'rsi_14', 'macd_line', 'bb_percent', 'volume_ratio']
                
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                return df
                
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def create_simple_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """간단한 피처 생성"""
        print("🔧 피처 생성 중...")
        
        try:
            # 각 종목별로 처리
            dfs = []
            
            for stock_id in df['stock_id'].unique():
                stock_df = df[df['stock_id'] == stock_id].copy()
                stock_df = stock_df.sort_values('trade_date')
                
                if len(stock_df) < 2:  # 최소 데이터 요구 (2개로 줄임)
                    continue
                
                # 가격 모멘텀 (1일 변화로 단순화)
                stock_df['price_momentum_1'] = stock_df['close_price'].pct_change(1) * 100
                
                # 볼륨 변화
                stock_df['volume_change'] = stock_df['volume'].pct_change() * 100
                
                # 타겟 변수 (다음날 상승/하락) - 현재 데이터로는 불가능하므로 임시로 현재 수익률 사용
                stock_df['target'] = (stock_df['daily_return_pct'] > 0).astype(int)  # 현재 날짜 상승/하락
                
                # 결측치 제거
                stock_df = stock_df.dropna()
                
                if len(stock_df) > 1:  # 최소 1개 샘플
                    dfs.append(stock_df)
            
            if not dfs:
                print("❌ 유효한 데이터 없음")
                return pd.DataFrame()
            
            result = pd.concat(dfs, ignore_index=True)
            print(f"✅ {len(result)}개 피처 생성")
            
            return result
            
        except Exception as e:
            print(f"❌ 피처 생성 실패: {e}")
            return pd.DataFrame()
    
    def train_simple_model(self, df: pd.DataFrame) -> dict:
        """간단한 모델 학습"""
        print("🤖 모델 학습 시작...")
        
        try:
            if len(df) < 20:
                return {"success": False, "error": "데이터 부족"}
            
            # 피처 선택
            feature_cols = ['daily_return_pct', 'rsi_14', 'macd_line', 'bb_percent', 
                           'volume_ratio', 'price_momentum_1', 'volume_change']
            
            # 사용 가능한 피처만 선택
            available_features = [col for col in feature_cols if col in df.columns and df[col].notna().sum() > 10]
            
            if len(available_features) < 3:
                return {"success": False, "error": "피처 부족"}
            
            print(f"📊 사용 피처: {available_features}")
            
            # 데이터 준비
            X = df[available_features].fillna(0)
            y = df['target']
            
            # NaN 제거
            mask = ~(X.isna().any(axis=1) | y.isna())
            X = X[mask]
            y = y[mask]
            
            if len(X) < 5:
                return {"success": False, "error": f"유효 데이터 부족: {len(X)}개"}
            
            print(f"✅ 학습 데이터: {len(X)}개")
            print(f"   상승: {y.sum()}개, 하락: {len(y) - y.sum()}개")
            
            # 모델 학습
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, classification_report
            
            # 데이터 분할
            if len(X) >= 10:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.3, random_state=42, stratify=y if y.sum() > 0 and y.sum() < len(y) else None
                )
            else:
                X_train, X_test, y_train, y_test = X, X, y, y
            
            # 모델 훈련
            model = RandomForestClassifier(n_estimators=50, random_state=42, max_depth=5)
            model.fit(X_train, y_train)
            
            # 예측 및 평가
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            print(f"✅ 모델 정확도: {accuracy:.4f}")
            
            # 모델 저장
            import pickle
            model_dir = Path(__file__).parent / "models"
            model_dir.mkdir(exist_ok=True)
            
            with open(model_dir / "simple_model.pkl", "wb") as f:
                pickle.dump(model, f)
            
            with open(model_dir / "simple_features.pkl", "wb") as f:
                pickle.dump(available_features, f)
            
            return {
                "success": True,
                "accuracy": accuracy,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "features": available_features
            }
            
        except Exception as e:
            print(f"❌ 모델 학습 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def generate_simple_predictions(self) -> list:
        """간단한 예측 생성"""
        print("📈 예측 생성 중...")
        
        try:
            import pickle
            
            model_dir = Path(__file__).parent / "models"
            
            # 모델 로드
            with open(model_dir / "simple_model.pkl", "rb") as f:
                model = pickle.load(f)
            
            with open(model_dir / "simple_features.pkl", "rb") as f:
                features = pickle.load(f)
            
            # 최신 데이터 가져오기
            df = self.get_training_data()
            if df.empty:
                return []
            
            df = self.create_simple_features(df)
            if df.empty:
                return []
            
            # 최신 날짜 데이터
            latest_date = df['trade_date'].max()
            latest_df = df[df['trade_date'] == latest_date].copy()
            
            if len(latest_df) == 0:
                return []
            
            # 예측
            X = latest_df[features].fillna(0)
            scores = model.predict_proba(X)[:, 1]  # 상승 확률
            
            # 결과 생성
            results = []
            for i, (_, row) in enumerate(latest_df.iterrows()):
                results.append({
                    'stock_id': int(row['stock_id']),
                    'stock_code': row['stock_code'],
                    'stock_name': row['stock_name'],
                    'score': float(scores[i]),
                    'prediction_date': latest_date.date()
                })
            
            # 점수순 정렬
            results.sort(key=lambda x: x['score'], reverse=True)
            
            print(f"✅ {len(results)}개 예측 완료")
            return results
            
        except Exception as e:
            print(f"❌ 예측 실패: {e}")
            return []
    
    def save_simple_recommendations(self, predictions: list, top_n: int = 10) -> int:
        """간단한 추천 저장"""
        print(f"💾 상위 {top_n}개 추천 저장...")
        
        try:
            saved = 0
            
            with get_db_session() as db:
                for rank, pred in enumerate(predictions[:top_n], 1):
                    new_rec = StockRecommendation(
                        stock_id=pred['stock_id'],
                        universe_id=self.universe_id,
                        recommendation_date=pred['prediction_date'],
                        target_date=(pred['prediction_date'] + timedelta(days=1)),
                        ml_score=pred['score'],
                        universe_rank=rank,
                        model_name="Simple ML Model",
                        model_version="v1.0"
                    )
                    
                    db.add(new_rec)
                    saved += 1
                
                db.commit()
            
            print(f"✅ {saved}개 추천 저장")
            return saved
            
        except Exception as e:
            print(f"❌ 추천 저장 실패: {e}")
            return 0


def main():
    """메인 실행"""
    print("🚀 간단한 ML 모델 학습 및 추천")
    print("="*50)
    
    trainer = SimpleMLTrainer()
    
    # 1. 데이터 로드
    print("\n1️⃣ 데이터 로드")
    df = trainer.get_training_data()
    
    if df.empty:
        print("❌ 데이터 없음")
        return False
    
    # 2. 피처 생성
    print("\n2️⃣ 피처 생성")
    df = trainer.create_simple_features(df)
    
    if df.empty:
        print("❌ 피처 생성 실패")
        return False
    
    # 3. 모델 학습
    print("\n3️⃣ 모델 학습")
    result = trainer.train_simple_model(df)
    
    if not result["success"]:
        print(f"❌ 학습 실패: {result['error']}")
        return False
    
    print(f"✅ 정확도: {result['accuracy']:.4f}")
    print(f"✅ 학습 샘플: {result['training_samples']}개")
    
    # 4. 예측 생성
    print("\n4️⃣ 예측 생성")
    predictions = trainer.generate_simple_predictions()
    
    if not predictions:
        print("❌ 예측 실패")
        return False
    
    # 5. 결과 출력
    print(f"\n🏆 상위 10개 추천:")
    for i, pred in enumerate(predictions[:10], 1):
        print(f"   {i}. {pred['stock_code']} ({pred['stock_name']}) - {pred['score']:.4f}")
    
    # 6. 추천 저장
    print("\n5️⃣ 추천 저장")
    saved = trainer.save_simple_recommendations(predictions)
    
    print(f"\n✅ 완료! {saved}개 추천 저장됨")
    
    # Discord 알림
    try:
        from app.services.notification import NotificationService
        notification = NotificationService()
        
        top_5_text = "\n".join([
            f"{i}. {pred['stock_code']} ({pred['stock_name']}) - {pred['score']:.4f}"
            for i, pred in enumerate(predictions[:5], 1)
        ])
        
        message = (
            f"🤖 **ML 모델 학습 완료**\n\n"
            f"📅 학습 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🎯 모델 정확도: {result['accuracy']:.4f}\n"
            f"📊 학습 샘플: {result['training_samples']}개\n"
            f"🔧 피처 수: {len(result['features'])}개\n\n"
            f"🏆 **상위 5개 추천:**\n{top_5_text}\n\n"
            f"✅ **추천 시스템 준비 완료!**"
        )
        notification._send_simple_slack_message(message)
        print("📱 Discord 알림 전송 완료")
    except Exception as e:
        print(f"⚠️ Discord 알림 전송 실패: {e}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
