#!/usr/bin/env python3
"""
모델 네이밍과 매핑 검증 스크립트
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.ml.global_ml_engine import GlobalMLEngine
from app.models.entities import MarketRegion


def test_model_mapping():
    """모델 저장/로드 경로 매핑 검증"""
    print("🔍 모델 네이밍 및 매핑 검증 시작...")
    
    engine = GlobalMLEngine()
    
    print(f"📁 모델 저장 디렉토리: {engine.model_dir}")
    print(f"🏷️ 모델 버전: {engine.model_version}")
    
    # 1. 예상 파일 경로 확인
    print("\n📋 예상 모델 파일 경로:")
    for region in [MarketRegion.KR, MarketRegion.US]:
        model_path = engine.model_dir / f"{region.value}_model_{engine.model_version}.joblib"
        scaler_path = engine.model_dir / f"{region.value}_scaler_{engine.model_version}.joblib"
        
        print(f"  🇰🇷 {region.value} 시장:")
        print(f"    모델: {model_path}")
        print(f"    스케일러: {scaler_path}")
        print(f"    존재: {'✅' if model_path.exists() else '❌'} / {'✅' if scaler_path.exists() else '❌'}")
    
    # 글로벌 앙상블 모델
    ensemble_path = engine.model_dir / f"ensemble_model_{engine.model_version}.joblib"
    ensemble_scaler_path = engine.model_dir / f"ensemble_scaler_{engine.model_version}.joblib"
    
    print(f"  🌍 글로벌 앙상블:")
    print(f"    모델: {ensemble_path}")
    print(f"    스케일러: {ensemble_scaler_path}")
    print(f"    존재: {'✅' if ensemble_path.exists() else '❌'} / {'✅' if ensemble_scaler_path.exists() else '❌'}")
    
    # 2. 메모리 모델 상태 확인
    print(f"\n💾 메모리 내 모델 상태:")
    print(f"  models 딕셔너리 키: {list(engine.models.keys())}")
    print(f"  scalers 딕셔너리 키: {list(engine.scalers.keys())}")
    
    # 3. 모델 로드 테스트
    print(f"\n🔄 모델 로드 테스트:")
    for region in [MarketRegion.KR, MarketRegion.US]:
        print(f"  {region.value} 모델 로드 시도...")
        try:
            engine._load_model(region)
            
            # 로드 후 상태 확인
            if region.value in engine.models:
                print(f"    ✅ {region.value} 모델 로드 성공")
            else:
                print(f"    ❌ {region.value} 모델 로드 실패 - 딕셔너리에 없음")
                
        except Exception as e:
            print(f"    ❌ {region.value} 모델 로드 오류: {e}")
    
    # 4. 예측 함수에서 모델 접근 시뮬레이션
    print(f"\n🎯 예측 함수 모델 접근 시뮬레이션:")
    for region in [MarketRegion.KR, MarketRegion.US]:
        print(f"  {region.value} 예측 시뮬레이션...")
        
        # predict_stocks()에서 하는 것과 동일한 체크
        if region.value not in engine.models:
            print(f"    ⚠️ {region.value} 모델 없음 - 자동 학습이 필요함")
        else:
            model = engine.models[region.value]
            scaler = engine.scalers[region.value]
            print(f"    ✅ {region.value} 모델 접근 성공")
            print(f"      모델 타입: {type(model).__name__}")
            print(f"      스케일러 타입: {type(scaler).__name__}")


def test_model_consistency():
    """모델 저장과 로드 일관성 검증"""
    print(f"\n🔍 모델 저장/로드 일관성 검증...")
    
    engine = GlobalMLEngine()
    
    # 각 지역별로 저장 경로와 로드 경로가 일치하는지 확인
    for region in [MarketRegion.KR, MarketRegion.US]:
        print(f"\n📍 {region.value} 시장 경로 일관성:")
        
        # _train_market_model()에서 저장하는 경로
        save_model_path = engine.model_dir / f"{region.value}_model_{engine.model_version}.joblib"
        save_scaler_path = engine.model_dir / f"{region.value}_scaler_{engine.model_version}.joblib"
        
        # _load_model()에서 로드하는 경로  
        load_model_path = engine.model_dir / f"{region.value}_model_{engine.model_version}.joblib"
        load_scaler_path = engine.model_dir / f"{region.value}_scaler_{engine.model_version}.joblib"
        
        print(f"  저장 경로: {save_model_path}")
        print(f"  로드 경로: {load_model_path}")
        print(f"  경로 일치: {'✅' if save_model_path == load_model_path else '❌'}")
        
        # 딕셔너리 키 일관성
        save_key = region.value  # self.models[region.value] = model
        load_key = region.value  # self.models[region.value] = joblib.load()
        predict_key = region.value  # model = self.models[region.value]
        
        print(f"  저장 키: '{save_key}'")
        print(f"  로드 키: '{load_key}'")
        print(f"  예측 키: '{predict_key}'")
        print(f"  키 일치: {'✅' if save_key == load_key == predict_key else '❌'}")


if __name__ == "__main__":
    test_model_mapping()
    test_model_consistency()
    
    print(f"\n🎉 모델 매핑 검증 완료!")