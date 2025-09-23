#!/usr/bin/env python3
"""
RealTimeLearningSystem 수정사항 검증 스크립트
"""
import sys
from pathlib import Path
import inspect

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.ml.realtime_learning_system import RealTimeLearningSystem


def test_method_signatures():
    """메서드 시그니처 및 타입 힌트 검증"""
    print("🔍 메서드 시그니처 검증...")
    
    system = RealTimeLearningSystem()
    
    # 1. evaluate_daily_performance 반환 타입 확인
    method = getattr(system, 'evaluate_daily_performance')
    signature = inspect.signature(method)
    return_annotation = signature.return_annotation
    
    print(f"  evaluate_daily_performance 반환 타입: {return_annotation}")
    
    # Dict[str, ModelPerformance] 확인
    if hasattr(return_annotation, '__origin__'):
        print(f"    타입 원본: {return_annotation.__origin__}")
        if hasattr(return_annotation, '__args__'):
            print(f"    타입 인자: {return_annotation.__args__}")
    
    # 2. 메서드 중복 확인
    method_names = [name for name, _ in inspect.getmembers(system, predicate=inspect.ismethod)]
    method_counts = {}
    for name in method_names:
        method_counts[name] = method_counts.get(name, 0) + 1
    
    duplicates = {name: count for name, count in method_counts.items() if count > 1}
    if duplicates:
        print(f"  ❌ 중복 메서드 발견: {duplicates}")
    else:
        print("  ✅ 메서드 중복 없음")


def test_path_references():
    """경로 참조 검증"""
    print("\n📁 경로 참조 검증...")
    
    system = RealTimeLearningSystem()
    
    # ML 엔진 모델 디렉토리 확인
    ml_engine_dir = system.ml_engine.model_dir
    print(f"  ML 엔진 모델 디렉토리: {ml_engine_dir}")
    
    # _backup_current_models의 소스 확인
    import inspect
    backup_source = inspect.getsource(system._backup_current_models)
    
    if "self.ml_engine.model_dir" in backup_source:
        print("  ✅ _backup_current_models가 self.ml_engine.model_dir 사용")
    else:
        print("  ❌ _backup_current_models가 하드코딩된 경로 사용")
    
    # _restore_backup_models의 소스 확인
    restore_source = inspect.getsource(system._restore_backup_models)
    
    if "self.ml_engine.model_dir" in restore_source:
        print("  ✅ _restore_backup_models가 self.ml_engine.model_dir 사용")
    else:
        print("  ❌ _restore_backup_models가 하드코딩된 경로 사용")


def test_intensive_training_call():
    """집중 학습 호출 방식 검증"""
    print("\n🔥 집중 학습 호출 방식 검증...")
    
    system = RealTimeLearningSystem()
    
    # _intensive_training 소스 확인
    intensive_source = inspect.getsource(system._intensive_training)
    
    if "train_global_models_intensive" in intensive_source:
        print("  ✅ _intensive_training이 train_global_models_intensive 직접 호출")
    else:
        print("  ❌ _intensive_training이 간접적 방식 사용")
    
    if "model_config" in intensive_source and "self.ml_engine.model_config" in intensive_source:
        print("  ⚠️ 여전히 model_config 설정 방식 사용 (개선 가능)")
    elif "train_global_models_intensive" in intensive_source:
        print("  ✅ 직접 메서드 호출 방식으로 개선됨")


def test_accuracy_calculation_logic():
    """정확도 계산 로직 검증 (문자열 분석)"""
    print("\n📊 정확도 계산 로직 검증...")
    
    system = RealTimeLearningSystem()
    
    # evaluate_daily_performance 소스 확인
    eval_source = inspect.getsource(system.evaluate_daily_performance)
    
    if "matched_predictions" in eval_source:
        print("  ✅ 매칭된 예측만 별도 추적")
    
    if "coverage_rate" in eval_source:
        print("  ✅ 커버리지 비율 계산 포함")
    
    if "sorted_predictions = sorted" in eval_source:
        print("  ✅ 상위 5개 예측을 정렬하여 선택")
    
    if "accurate_count / total_matched" in eval_source or "accurate_count / len(matched_predictions)" in eval_source:
        print("  ✅ 정확도를 매칭된 케이스 기준으로 계산")


def test_logger_filtering():
    """로거 시장별 필터링 검증"""
    print("\n📋 로거 시장별 필터링 검증...")
    
    system = RealTimeLearningSystem()
    
    # save_daily_predictions 소스 확인
    save_source = inspect.getsource(system.save_daily_predictions)
    
    if "market_predictions = [p for p in prediction_data if p['market_region'] == market]" in save_source:
        print("  ✅ 시장별로 필터링된 예측 데이터를 로거에 전달")
    else:
        print("  ❌ 여전히 전체 예측 데이터를 로거에 전달")


if __name__ == "__main__":
    print("🔍 RealTimeLearningSystem 수정사항 검증 시작")
    print("=" * 60)
    
    try:
        test_method_signatures()
        test_path_references()
        test_intensive_training_call()
        test_accuracy_calculation_logic()
        test_logger_filtering()
        
        print("\n" + "=" * 60)
        print("🎉 모든 검증 완료!")
        
    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {e}")
        import traceback
        print(traceback.format_exc())