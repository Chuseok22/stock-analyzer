#!/usr/bin/env python3
"""
간단한 ML 엔진 기능 테스트
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

def test_ml_engine_simple():
    """간단한 ML 엔진 테스트"""
    print("🤖 간단한 ML 엔진 테스트")
    print("="*50)
    
    try:
        # 1. 임포트 테스트
        print("1️⃣ 모듈 임포트 테스트...")
        from app.ml.global_ml_engine import GlobalMLEngine, MarketRegion
        print("   ✅ 모듈 임포트 성공")
        
        # 2. 엔진 초기화
        print("2️⃣ ML 엔진 초기화...")
        ml_engine = GlobalMLEngine()
        print("   ✅ 엔진 초기화 성공")
        
        # 3. 메서드 존재 확인
        print("3️⃣ 메서드 존재 확인...")
        methods_to_check = [
            'prepare_global_features',
            'train_global_models',
            'predict_stocks',
            'detect_market_regime'
        ]
        
        for method_name in methods_to_check:
            if hasattr(ml_engine, method_name):
                print(f"   ✅ {method_name}: 존재")
            else:
                print(f"   ❌ {method_name}: 누락")
        
        # 4. 데이터 준비 테스트
        print("4️⃣ 데이터 준비 테스트...")
        
        from app.database.connection import get_db_session
        from app.models.entities import StockMaster
        
        with get_db_session() as db:
            sample_stock = db.query(StockMaster).filter_by(
                market_region=MarketRegion.KR.value,
                is_active=True
            ).first()
            
            if sample_stock:
                print(f"   ✅ 샘플 종목: {sample_stock.stock_code}")
                
                # 피처 생성 테스트 (데이터 범위 내에서)
                from datetime import datetime, timedelta
                target_date = datetime.strptime("2025-09-20", "%Y-%m-%d").date()  # 확실히 있는 날짜
                
                print(f"   📅 타겟 날짜: {target_date}")
                
                features = ml_engine.prepare_global_features(sample_stock.stock_id, target_date)
                
                if features is not None:
                    print(f"   ✅ 피처 생성 성공: {len(features)}행 x {len(features.columns)}열")
                    print(f"   📊 피처 목록 (일부): {list(features.columns[:10])}")
                else:
                    print("   ❌ 피처 생성 실패")
                    return False
            else:
                print("   ❌ 샘플 종목 없음")
                return False
        
        print("\n✅ 간단한 ML 엔진 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_ml_engine_simple()
    sys.exit(0 if success else 1)