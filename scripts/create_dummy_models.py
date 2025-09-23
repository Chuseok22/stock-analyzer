#!/usr/bin/env python3
"""
더미 ML 모델 생성 스크립트
- 서버 즉시 실행을 위한 임시 모델 생성
- 실제 학습은 백그라운드에서 진행
"""
import sys
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# Add app directory to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app"))

def create_dummy_models():
    """더미 모델 생성"""
    print("🏭 더미 ML 모델 생성 중...")
    
    try:
        # 모델 저장 경로
        model_dir = project_root / "storage" / "models" / "global"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 더미 데이터 생성 (20개 피처)
        X_dummy = np.random.randn(100, 20)  # 100개 샘플, 20개 피처
        y_dummy = np.random.randn(100)      # 100개 타겟
        
        regions = ["KR", "US"]
        
        for region in regions:
            print(f"   🇺🇸 {region} 더미 모델 생성 중...")
            
            # 더미 모델 생성
            model = RandomForestRegressor(
                n_estimators=10,  # 최소한의 트리
                max_depth=5,
                random_state=42
            )
            model.fit(X_dummy, y_dummy)
            
            # 더미 스케일러 생성
            scaler = StandardScaler()
            scaler.fit(X_dummy)
            
            # 모델 저장
            model_path = model_dir / f"{region}_model_v3.0_global.joblib"
            scaler_path = model_dir / f"{region}_scaler_v3.0_global.joblib"
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            
            print(f"   ✅ {region} 더미 모델 저장: {model_path}")
            print(f"   ✅ {region} 더미 스케일러 저장: {scaler_path}")
        
        # 더미 앙상블 모델도 생성
        ensemble_path = model_dir / "ensemble_model_v3.0_global.joblib"
        ensemble_scaler_path = model_dir / "ensemble_scaler_v3.0_global.joblib"
        
        ensemble_model = RandomForestRegressor(
            n_estimators=15,
            max_depth=6,
            random_state=42
        )
        ensemble_model.fit(X_dummy, y_dummy)
        
        ensemble_scaler = StandardScaler()
        ensemble_scaler.fit(X_dummy)
        
        joblib.dump(ensemble_model, ensemble_path)
        joblib.dump(ensemble_scaler, ensemble_scaler_path)
        
        print(f"   ✅ 앙상블 더미 모델 저장: {ensemble_path}")
        
        print("🎉 더미 모델 생성 완료!")
        print("   ⚠️ 이는 임시 모델이며, 실제 학습은 백그라운드에서 진행됩니다.")
        
        return True
        
    except Exception as e:
        print(f"❌ 더미 모델 생성 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    create_dummy_models()