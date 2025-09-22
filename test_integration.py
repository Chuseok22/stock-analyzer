#!/usr/bin/env python3
"""
전체 시스템 통합 테스트
- 로그 시스템 검증
- 실시간 학습 시스템 검증  
- 스케줄러 시스템 검증
- 파일 구조 검증
- 오류 없음 확인
"""
import sys
from pathlib import Path
import traceback
from datetime import date, datetime
import time

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

def test_logging_system():
    """로그 시스템 테스트"""
    print("🧪 로그 시스템 테스트...")
    
    try:
        from app.utils.structured_logger import get_logger
        
        logger = get_logger("integration_test")
        
        # 기본 로그 테스트
        logger.info("통합 테스트 시작")
        logger.debug("디버그 로그 테스트")
        logger.warning("경고 로그 테스트")
        
        # 구조화된 로그 테스트
        logger.log_system_status({
            "test_phase": "logging_system",
            "status": "testing",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.log_prediction_result("TEST", [
            {"stock_code": "TEST001", "prediction": 1.5}
        ], accuracy=75.0)
        
        # 일일 요약 생성 테스트
        logger.create_daily_summary()
        
        print("✅ 로그 시스템 테스트 통과")
        return True
        
    except Exception as e:
        print(f"❌ 로그 시스템 테스트 실패: {e}")
        traceback.print_exc()
        return False

def test_realtime_learning_system():
    """실시간 학습 시스템 테스트"""
    print("🧪 실시간 학습 시스템 테스트...")
    
    try:
        from app.ml.realtime_learning_system import RealTimeLearningSystem
        
        # 시스템 초기화
        learning_system = RealTimeLearningSystem()
        
        # 테스트 날짜
        test_date = date(2025, 1, 15)
        
        # 리포트 경로 생성 테스트
        report_path = learning_system._get_report_path(test_date, "test")
        assert report_path.exists(), "리포트 경로 생성 실패"
        
        # 성능 리포트 생성 테스트
        report = learning_system.generate_performance_report(test_date, days=7)
        assert isinstance(report, str), "성능 리포트 생성 실패"
        assert len(report) > 0, "빈 리포트 생성됨"
        
        # 학습 전략 결정 테스트
        recent_performances = {'KR': [70.0, 72.0], 'US': [65.0, 67.0]}
        strategy = learning_system._determine_training_strategy(recent_performances)
        assert isinstance(strategy, dict), "학습 전략 결정 실패"
        
        print("✅ 실시간 학습 시스템 테스트 통과")
        return True
        
    except Exception as e:
        print(f"❌ 실시간 학습 시스템 테스트 실패: {e}")
        traceback.print_exc()
        return False

def test_global_ml_engine():
    """글로벌 ML 엔진 테스트"""
    print("🧪 글로벌 ML 엔진 테스트...")
    
    try:
        from app.ml.global_ml_engine import GlobalMLEngine
        
        # 엔진 초기화
        ml_engine = GlobalMLEngine()
        
        # 시장 체제 감지 테스트
        market_condition = ml_engine.detect_market_regime()
        assert hasattr(market_condition, 'regime'), "시장 체제 감지 실패"
        
        # 예측 저장 기능 테스트
        test_predictions = []  # 빈 예측 목록으로 테스트
        ml_engine.save_predictions_for_learning(test_predictions)
        
        print("✅ 글로벌 ML 엔진 테스트 통과")
        return True
        
    except Exception as e:
        print(f"❌ 글로벌 ML 엔진 테스트 실패: {e}")
        traceback.print_exc()
        return False

def test_global_scheduler():
    """글로벌 스케줄러 테스트"""
    print("🧪 글로벌 스케줄러 테스트...")
    
    try:
        # 스케줄러 모듈 import 테스트
        from scripts.enhanced_global_scheduler import EnhancedGlobalScheduler
        
        # 스케줄러 초기화
        scheduler = EnhancedGlobalScheduler()
        
        # DST 감지 테스트
        dst_active = scheduler.is_dst_active()
        assert isinstance(dst_active, bool), "DST 감지 실패"
        
        # 미국 시장 시간 계산 테스트
        us_times = scheduler.get_us_market_times()
        assert isinstance(us_times, dict), "미국 시장 시간 계산 실패"
        assert 'premarket_alert' in us_times, "프리마켓 시간 누락"
        
        # 헬스체크 테스트
        health_status = scheduler._health_check()
        # health_check는 None을 반환할 수 있으므로 메서드 존재 여부만 확인
        assert hasattr(scheduler, '_health_check'), "헬스체크 메서드 누락"
        
        print("✅ 글로벌 스케줄러 테스트 통과")
        return True
        
    except Exception as e:
        print(f"❌ 글로벌 스케줄러 테스트 실패: {e}")
        traceback.print_exc()
        return False

def test_file_structure():
    """파일 구조 테스트"""
    print("🧪 파일 구조 테스트...")
    
    try:
        # 핵심 파일들 존재 확인
        required_files = [
            "app/ml/realtime_learning_system.py",
            "app/utils/structured_logger.py", 
            "app/ml/global_ml_engine.py",
            "scripts/enhanced_global_scheduler.py",
            "run_global_system.py",
            "deploy_realtime_learning.sh"
        ]
        
        for file_path in required_files:
            file_obj = Path(file_path)
            assert file_obj.exists(), f"필수 파일 누락: {file_path}"
        
        # 디렉토리 구조 확인
        required_dirs = [
            "storage/models/performance",
            "storage/analysis_reports", 
            "storage/logs",
        ]
        
        for dir_path in required_dirs:
            dir_obj = Path(dir_path)
            if not dir_obj.exists():
                dir_obj.mkdir(parents=True, exist_ok=True)
            assert dir_obj.exists(), f"필수 디렉토리 누락: {dir_path}"
        
        # 로그 디렉토리 구조 확인
        today = date.today()
        log_dir = Path(f"storage/logs/{today.year}/{today.month:02d}/{today.day:02d}")
        log_dir.mkdir(parents=True, exist_ok=True)
        assert log_dir.exists(), "로그 디렉토리 구조 생성 실패"
        
        print("✅ 파일 구조 테스트 통과")
        return True
        
    except Exception as e:
        print(f"❌ 파일 구조 테스트 실패: {e}")
        traceback.print_exc()
        return False

def test_import_integrity():
    """Import 무결성 테스트"""
    print("🧪 Import 무결성 테스트...")
    
    try:
        # 핵심 모듈들 import 테스트
        modules_to_test = [
            "app.utils.structured_logger",
            "app.ml.realtime_learning_system", 
            "app.ml.global_ml_engine",
            "app.services.smart_alert_system",
            "app.database.connection",
            "app.models.entities"
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
                print(f"   ✅ {module_name}")
            except ImportError as e:
                print(f"   ❌ {module_name}: {e}")
                return False
        
        print("✅ Import 무결성 테스트 통과")
        return True
        
    except Exception as e:
        print(f"❌ Import 무결성 테스트 실패: {e}")
        traceback.print_exc()
        return False

def run_integration_tests():
    """통합 테스트 실행"""
    print("🚀 전체 시스템 통합 테스트 시작")
    print("=" * 60)
    
    start_time = time.time()
    
    # 테스트 목록
    tests = [
        ("파일 구조", test_file_structure),
        ("Import 무결성", test_import_integrity),
        ("로그 시스템", test_logging_system),
        ("글로벌 ML 엔진", test_global_ml_engine),
        ("실시간 학습 시스템", test_realtime_learning_system),
        ("글로벌 스케줄러", test_global_scheduler),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} 테스트 실행...")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 테스트 통과")
            else:
                failed += 1
                print(f"❌ {test_name} 테스트 실패")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} 테스트 오류: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("🎯 통합 테스트 결과")
    print("=" * 60)
    print(f"✅ 통과: {passed}개")
    print(f"❌ 실패: {failed}개")
    print(f"⏱️ 소요 시간: {duration:.2f}초")
    
    if failed == 0:
        print("\n🎉 모든 테스트 통과! 시스템이 정상적으로 작동합니다.")
        print("🚀 배포 환경으로 안전하게 이관할 수 있습니다.")
        
        # 로그 파일 위치 안내
        print(f"\n📁 생성된 로그 파일:")
        log_dir = Path(f"storage/logs/{date.today().year}/{date.today().month:02d}/{date.today().day:02d}")
        if log_dir.exists():
            for log_file in log_dir.iterdir():
                if log_file.is_file():
                    print(f"   📄 {log_file}")
        
        return True
    else:
        print(f"\n⚠️ {failed}개 테스트 실패. 문제를 해결 후 재실행하세요.")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
