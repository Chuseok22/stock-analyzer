#!/usr/bin/env python3
"""
최종 간단한 ML 모델 (MACD 제외)
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockRecommendation
from sqlalchemy import text


class FinalMLTrainer:
    """최종 ML 학습기"""
    
    def __init__(self):
        self.universe_id = 1
    
    def get_clean_data(self) -> pd.DataFrame:
        """깨끗한 데이터 가져오기"""
        print("📊 데이터 로드 중...")
        
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
                               'sma_20', 'rsi_14', 'bb_percent', 'volume_ratio']
                
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                # NaN 확인
                print(f"📋 결측치 현황:")
                for col in df.columns:
                    null_count = df[col].isnull().sum()
                    if null_count > 0:
                        print(f"   {col}: {null_count}개")
                
                return df
                
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def create_final_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """최종 피처 생성"""
        print("🔧 피처 생성 중...")
        
        try:
            # 간단한 피처만 생성
            df_clean = df.copy()
            
            # RSI 구간
            df_clean['rsi_oversold'] = (df_clean['rsi_14'] < 30).astype(int)
            df_clean['rsi_overbought'] = (df_clean['rsi_14'] > 70).astype(int)
            
            # 볼린저 밴드 구간
            df_clean['bb_high'] = (df_clean['bb_percent'] > 0.8).astype(int)
            df_clean['bb_low'] = (df_clean['bb_percent'] < 0.2).astype(int)
            
            # 볼륨 비율 구간
            df_clean['volume_high'] = (df_clean['volume_ratio'] > 1.5).astype(int)
            
            # 타겟 변수 (현재 날짜 기준 상승/하락)
            df_clean['target'] = (df_clean['daily_return_pct'] > 0).astype(int)
            
            # NaN 제거
            df_clean = df_clean.dropna()
            
            print(f"✅ {len(df_clean)}개 피처 생성 완료")
            print(f"   상승: {df_clean['target'].sum()}개")
            print(f"   하락: {len(df_clean) - df_clean['target'].sum()}개")
            
            return df_clean
            
        except Exception as e:
            print(f"❌ 피처 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def train_final_model(self, df: pd.DataFrame) -> dict:
        """최종 모델 학습"""
        print("🤖 모델 학습 시작...")
        
        try:
            if len(df) < 10:
                return {"success": False, "error": f"데이터 부족: {len(df)}개"}
            
            # 피처 선택 (사용 가능한 것들만)
            feature_cols = ['rsi_14', 'bb_percent', 'volume_ratio', 
                           'rsi_oversold', 'rsi_overbought', 'bb_high', 'bb_low', 'volume_high']
            
            # 사용 가능한 피처만 선택
            available_features = [col for col in feature_cols if col in df.columns]
            print(f"📊 사용 피처: {available_features}")
            
            # 데이터 준비
            X = df[available_features]
            y = df['target']
            
            print(f"✅ 학습 데이터: {len(X)}개")
            print(f"   피처 수: {len(available_features)}개")
            
            # 간단한 모델 학습
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.metrics import accuracy_score
            
            model = RandomForestClassifier(n_estimators=10, random_state=42, max_depth=3)
            model.fit(X, y)
            
            # 예측 및 평가
            y_pred = model.predict(X)
            accuracy = accuracy_score(y, y_pred)
            
            print(f"✅ 모델 정확도: {accuracy:.4f}")
            
            # 피처 중요도
            feature_importance = dict(zip(available_features, model.feature_importances_))
            print(f"📊 피처 중요도:")
            for feat, imp in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True):
                print(f"   {feat}: {imp:.4f}")
            
            # 모델 저장
            import pickle
            model_dir = Path(__file__).parent / "models"
            model_dir.mkdir(exist_ok=True)
            
            with open(model_dir / "final_model.pkl", "wb") as f:
                pickle.dump(model, f)
            
            with open(model_dir / "final_features.pkl", "wb") as f:
                pickle.dump(available_features, f)
            
            return {
                "success": True,
                "accuracy": accuracy,
                "training_samples": len(X),
                "features": available_features,
                "feature_importance": feature_importance
            }
            
        except Exception as e:
            print(f"❌ 모델 학습 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def generate_final_predictions(self) -> list:
        """최종 예측 생성"""
        print("📈 예측 생성 중...")
        
        try:
            import pickle
            
            model_dir = Path(__file__).parent / "models"
            
            # 모델 로드
            with open(model_dir / "final_model.pkl", "rb") as f:
                model = pickle.load(f)
            
            with open(model_dir / "final_features.pkl", "rb") as f:
                features = pickle.load(f)
            
            # 최신 데이터 가져오기
            df = self.get_clean_data()
            if df.empty:
                return []
            
            df = self.create_final_features(df)
            if df.empty:
                return []
            
            # 최신 날짜 데이터
            latest_date = df['trade_date'].max()
            latest_df = df[df['trade_date'] == latest_date].copy()
            
            if len(latest_df) == 0:
                print("❌ 최신 데이터 없음")
                return []
            
            print(f"📅 예측 날짜: {latest_date.date()}")
            print(f"📊 예측 대상: {len(latest_df)}개 종목")
            
            # 예측
            X = latest_df[features]
            scores = model.predict_proba(X)[:, 1]  # 상승 확률
            
            # 결과 생성
            results = []
            for i, (_, row) in enumerate(latest_df.iterrows()):
                results.append({
                    'stock_id': int(row['stock_id']),
                    'stock_code': row['stock_code'],
                    'stock_name': row['stock_name'],
                    'score': float(scores[i]),
                    'rsi': float(row['rsi_14']),
                    'bb_percent': float(row['bb_percent']),
                    'volume_ratio': float(row['volume_ratio']),
                    'prediction_date': latest_date.date()
                })
            
            # 점수순 정렬
            results.sort(key=lambda x: x['score'], reverse=True)
            
            print(f"✅ {len(results)}개 예측 완료")
            return results
            
        except Exception as e:
            print(f"❌ 예측 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def save_final_recommendations(self, predictions: list, top_n: int = 10) -> int:
        """최종 추천 저장"""
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
                        model_name="Final Simple ML",
                        model_version="v1.0",
                        recommendation_reason=f"RSI: {pred['rsi']:.1f}, BB: {pred['bb_percent']:.2f}, Vol: {pred['volume_ratio']:.2f}"
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
    print("🚀 최종 ML 모델 학습 및 추천")
    print("="*60)
    
    trainer = FinalMLTrainer()
    
    # 1. 데이터 로드
    print("\n1️⃣ 데이터 로드")
    df = trainer.get_clean_data()
    
    if df.empty:
        print("❌ 데이터 없음")
        return False
    
    # 2. 피처 생성
    print("\n2️⃣ 피처 생성")
    df = trainer.create_final_features(df)
    
    if df.empty:
        print("❌ 피처 생성 실패")
        return False
    
    # 3. 모델 학습
    print("\n3️⃣ 모델 학습")
    result = trainer.train_final_model(df)
    
    if not result["success"]:
        print(f"❌ 학습 실패: {result['error']}")
        return False
    
    print(f"✅ 정확도: {result['accuracy']:.4f}")
    
    # 4. 예측 생성
    print("\n4️⃣ 예측 생성")
    predictions = trainer.generate_final_predictions()
    
    if not predictions:
        print("❌ 예측 실패")
        return False
    
    # 5. 결과 출력
    print(f"\n🏆 상위 10개 추천:")
    for i, pred in enumerate(predictions[:10], 1):
        print(f"   {i}. {pred['stock_code']} ({pred['stock_name']}) - {pred['score']:.4f}")
        print(f"      RSI: {pred['rsi']:.1f}, BB: {pred['bb_percent']:.2f}, Vol: {pred['volume_ratio']:.2f}")
    
    # 6. 추천 저장
    print("\n5️⃣ 추천 저장")
    saved = trainer.save_final_recommendations(predictions)
    
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
            f"🤖 **최종 ML 모델 학습 완료**\n\n"
            f"📅 학습 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🎯 모델 정확도: {result['accuracy']:.4f}\n"
            f"📊 학습 샘플: {result['training_samples']}개\n"
            f"🔧 피처 수: {len(result['features'])}개\n\n"
            f"🏆 **상위 5개 추천:**\n{top_5_text}\n\n"
            f"✅ **추천 시스템 완전 준비!**\n"
            f"🚀 **내일부터 자동 추천 시작 가능**"
        )
        notification._send_simple_slack_message(message)
        print("📱 Discord 알림 전송 완료")
    except Exception as e:
        print(f"⚠️ Discord 알림 전송 실패: {e}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
