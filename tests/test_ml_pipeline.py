#!/usr/bin/env python3
"""
ML 파이프라인 테스트 - 데이터 수집, 학습, 예측까지 전체 과정
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.ml.global_ml_engine import GlobalMLEngine, MarketRegion
from app.database.connection import get_db_session
from app.models.entities import StockMaster, StockDailyPrice

def test_ml_pipeline():
    """ML 파이프라인 전체 테스트"""
    print("🤖 ML 파이프라인 전체 테스트")
    print("="*60)
    
    try:
        # 1. ML 엔진 초기화
        print("1️⃣ ML 엔진 초기화...")
        ml_engine = GlobalMLEngine()
        
        # 2. 데이터 가용성 확인
        print("2️⃣ 데이터 가용성 확인...")
        with get_db_session() as db:
            kr_stocks = db.query(StockMaster).filter_by(
                market_region=MarketRegion.KR.value,
                is_active=True
            ).count()
            
            us_stocks = db.query(StockMaster).filter_by(
                market_region=MarketRegion.US.value,
                is_active=True
            ).count()
            
            total_price_data = db.query(StockDailyPrice).count()
            
            print(f"   🇰🇷 한국 종목: {kr_stocks}개")
            print(f"   🇺🇸 미국 종목: {us_stocks}개")
            print(f"   📊 총 가격 데이터: {total_price_data}개")
            
            if kr_stocks == 0:
                print("   ❌ 충분한 한국 종목 데이터 없음")
                return False
            
            if us_stocks == 0:
                print("   ⚠️ 미국 종목 데이터 없음 - 한국 데이터만으로 테스트 진행")
            
            if total_price_data < 500:
                print("   ❌ 충분한 가격 데이터 없음")
                return False
        
        # 3. 피처 엔지니어링 테스트
        print("3️⃣ 피처 엔지니어링 테스트...")
        
        # 한국 종목 샘플 테스트
        with get_db_session() as db:
            kr_sample = db.query(StockMaster).filter_by(
                market_region=MarketRegion.KR.value,
                is_active=True
            ).first()
            
            if kr_sample:
                from datetime import datetime, timedelta
                target_date = datetime.now().date() - timedelta(days=5)
                
                features = ml_engine.prepare_global_features(kr_sample.stock_id, target_date)
                
                if features is not None and len(features) > 0:
                    print(f"   ✅ 한국 피처 생성 성공: {len(features)}개 기간, {len(features.columns)}개 피처")
                    print(f"   🎯 주요 피처: {list(features.columns[:10])}")
                else:
                    print("   ❌ 한국 피처 생성 실패")
                    return False
        
        # 4. 모델 학습 테스트 (빠른 버전)
        print("4️⃣ 모델 학습 테스트...")
        
        # 개발 환경 빠른 학습 설정
        ml_engine.model_config = {
            'n_estimators': 20,  # 매우 빠른 학습
            'max_depth': 5,
            'random_state': 42,
            'n_jobs': 2
        }
        
        training_success = ml_engine.train_global_models()
        
        if training_success:
            print("   ✅ 모델 학습 성공")
        else:
            print("   ❌ 모델 학습 실패")
            return False
        
        # 5. 예측 테스트
        print("5️⃣ 예측 테스트...")
        
        # 한국 예측
        kr_predictions = ml_engine.predict_stocks(MarketRegion.KR, top_n=3)
        if kr_predictions:
            print(f"   ✅ 한국 예측 성공: {len(kr_predictions)}개 종목")
            for i, pred in enumerate(kr_predictions, 1):
                print(f"      {i}. {pred.stock_code}: {pred.predicted_return:.2f}% (신뢰도: {pred.confidence_score:.2f})")
        else:
            print("   ❌ 한국 예측 실패")
        
        # 미국 예측 (데이터 있을 경우만)
        if us_stocks > 0:
            us_predictions = ml_engine.predict_stocks(MarketRegion.US, top_n=3)
            if us_predictions:
                print(f"   ✅ 미국 예측 성공: {len(us_predictions)}개 종목")
                for i, pred in enumerate(us_predictions, 1):
                    print(f"      {i}. {pred.stock_code}: {pred.predicted_return:.2f}% (신뢰도: {pred.confidence_score:.2f})")
            else:
                print("   ❌ 미국 예측 실패")
        else:
            print("   ⚠️ 미국 데이터 없음 - 예측 스킵")
            us_predictions = []  # 빈 리스트로 설정
        
        # 6. 시장 체제 분석 테스트
        print("6️⃣ 시장 체제 분석 테스트...")
        
        market_condition = ml_engine.detect_market_regime()
        if market_condition:
            print(f"   ✅ 시장 체제 분석 성공")
            print(f"      📊 체제: {market_condition.regime.value}")
            print(f"      📈 리스크: {market_condition.risk_level}")
            print(f"      💪 트렌드 강도: {market_condition.trend_strength:.2f}")
        else:
            print("   ❌ 시장 체제 분석 실패")
        
        # 7. 가중치 분석
        print("7️⃣ 가중치 분석...")
        
        if hasattr(ml_engine, 'models') and MarketRegion.KR.value in ml_engine.models:
            kr_model = ml_engine.models[MarketRegion.KR.value]
            
            if hasattr(kr_model, 'estimators_') and len(kr_model.estimators_) > 0:
                # Random Forest의 feature importance 확인
                rf_estimator = kr_model.estimators_[0]
                if hasattr(rf_estimator, 'feature_importances_'):
                    importances = rf_estimator.feature_importances_
                    print(f"   ✅ 피처 중요도 분석 성공")
                    print(f"      🎯 가중치 범위: {importances.min():.4f} - {importances.max():.4f}")
                    print(f"      📊 표준편차: {importances.std():.4f}")
                    
                    # 상위 5개 피처 중요도 출력
                    if len(importances) > 5:
                        top_indices = importances.argsort()[-5:][::-1]
                        print("      🏆 상위 5개 피처 중요도:")
                        for i, idx in enumerate(top_indices, 1):
                            print(f"         {i}. 피처 {idx}: {importances[idx]:.4f}")
                else:
                    print("   ⚠️ 피처 중요도 정보 없음")
            else:
                print("   ⚠️ 모델 앙상블 정보 없음")
        else:
            print("   ❌ 한국 모델 없음")
        
        # 전체 결과 평가
        success_count = 0
        if kr_predictions: success_count += 1
        if us_predictions or us_stocks == 0: success_count += 1  # 미국 데이터 없으면 성공으로 간주
        if market_condition: success_count += 1
        
        print(f"\n📊 테스트 결과 요약:")
        print(f"   ✅ 성공한 테스트: {success_count + 3}/6")  # 데이터, 피처, 학습 성공 포함
        
        if success_count >= 2:
            print("\n🎉 ML 파이프라인 테스트 성공!")
            return True
        else:
            print("\n❌ ML 파이프라인 테스트 실패")
            return False
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_ml_pipeline()
    sys.exit(0 if success else 1)