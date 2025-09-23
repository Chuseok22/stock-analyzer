#!/usr/bin/env python3
"""
ML 엔진 기본 기능 테스트
"""
import sys
from pathlib import Path

# app 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

def test_ml_engine():
    """ML 엔진 기본 기능 테스트"""
    print("🤖 ML 엔진 기본 기능 테스트")
    print("="*50)
    
    try:
        # 1. 임포트 테스트
        print("1️⃣ 모듈 임포트...")
        from app.ml.global_ml_engine import GlobalMLEngine
        print("   ✅ 임포트 성공")
        
        # 2. 초기화 테스트
        print("2️⃣ ML 엔진 초기화...")
        ml_engine = GlobalMLEngine()
        print("   ✅ 초기화 성공")
        
        # 3. 속성 확인
        print("3️⃣ 속성 확인...")
        assert hasattr(ml_engine, 'models'), "모델 속성 없음"
        assert hasattr(ml_engine, 'scalers'), "스케일러 속성 없음"
        assert hasattr(ml_engine, 'model_dir'), "모델 디렉토리 속성 없음"
        print("   ✅ 필수 속성 존재 확인")
        
        # 4. 메소드 확인
        print("4️⃣ 메소드 확인...")
        methods = ['train_global_models', 'predict_stocks', 'detect_market_regime']
        for method in methods:
            if hasattr(ml_engine, method):
                print(f"   ✅ {method} 메소드 존재")
            else:
                print(f"   ⚠️ {method} 메소드 없음")
        
        print("\n✅ ML 엔진 기본 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ml_engine()
    sys.exit(0 if success else 1)