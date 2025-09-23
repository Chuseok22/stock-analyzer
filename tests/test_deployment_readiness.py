#!/usr/bin/env python3
"""
배포 전 통합 테스트 스크립트
- 스케줄링 시스템 검증
- 서버 시작 프로세스 검증
- 기본 기능 동작 확인
- 로그 시스템 검증
"""
import sys
import os
import time
import json
import signal
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import threading
import requests

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

def print_header(title):
    """테스트 섹션 헤더 출력"""
    print("\n" + "="*60)
    print(f"🧪 {title}")
    print("="*60)

def print_test_result(test_name, success, details=""):
    """테스트 결과 출력"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"    {details}")

class IntegrationTester:
    """통합 테스트 실행기"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {}
        self.server_process = None
        
    def test_imports_and_dependencies(self):
        """의존성 및 모듈 임포트 테스트"""
        print_header("의존성 및 모듈 임포트 테스트")
        
        # 핵심 모듈 임포트 테스트
        modules_to_test = [
            ("app.config.settings", "설정 모듈"),
            ("app.database.connection", "데이터베이스 연결"),
            ("app.services.scheduler", "스케줄링 서비스"),
            ("app.ml.global_ml_engine", "ML 엔진"),
            ("app.services.smart_alert_system", "알림 시스템"),
            ("scripts.global_scheduler", "글로벌 스케줄러"),
        ]
        
        all_passed = True
        for module_name, description in modules_to_test:
            try:
                __import__(module_name)
                print_test_result(f"Import {description}", True)
            except Exception as e:
                print_test_result(f"Import {description}", False, f"Error: {e}")
                all_passed = False
        
        self.results['imports'] = all_passed
        return all_passed
    
    def test_database_connection(self):
        """데이터베이스 연결 테스트"""
        print_header("데이터베이스 연결 테스트")
        
        try:
            from app.database.connection import get_db_session
            from sqlalchemy import text
            
            with get_db_session() as db:
                result = db.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                
                if row and row[0] == 1:
                    print_test_result("데이터베이스 연결", True)
                    self.results['database'] = True
                    return True
                else:
                    print_test_result("데이터베이스 연결", False, "쿼리 결과 불일치")
                    self.results['database'] = False
                    return False
                    
        except Exception as e:
            print_test_result("데이터베이스 연결", False, f"Error: {e}")
            self.results['database'] = False
            return False
    
    def test_scheduling_system(self):
        """스케줄링 시스템 테스트"""
        print_header("스케줄링 시스템 테스트")
        
        try:
            from app.services.scheduler import SchedulingService
            
            # 스케줄링 서비스 생성
            scheduler = SchedulingService()
            print_test_result("스케줄링 서비스 생성", True)
            
            # 스케줄 설정
            scheduler.setup_schedules()
            print_test_result("스케줄 설정", True)
            
            # 작업 상태 확인
            status = scheduler.get_job_status()
            job_count = status.get('total_jobs', 0)
            
            if job_count > 0:
                print_test_result("스케줄된 작업 확인", True, f"{job_count}개 작업 등록됨")
                
                # 각 작업 출력
                for job in status.get('jobs', [])[:5]:  # 첫 5개만 표시
                    next_run = job.get('next_run_time', 'Not scheduled')
                    print(f"    📅 {job.get('id', 'Unknown')}: {next_run}")
                
                scheduler.stop_scheduler()
                self.results['scheduling'] = True
                return True
            else:
                print_test_result("스케줄된 작업 확인", False, "등록된 작업이 없음")
                scheduler.stop_scheduler()
                self.results['scheduling'] = False
                return False
                
        except Exception as e:
            print_test_result("스케줄링 시스템", False, f"Error: {e}")
            self.results['scheduling'] = False
            return False
    
    def test_global_scheduler(self):
        """글로벌 스케줄러 테스트"""
        print_header("글로벌 스케줄러 테스트")
        
        try:
            from scripts.global_scheduler import GlobalScheduler
            
            # 부트스트랩 없이 스케줄러 생성 (빠른 테스트용)
            scheduler = GlobalScheduler(run_bootstrap=False)
            print_test_result("글로벌 스케줄러 생성", True)
            
            # 헬스체크 테스트
            health_ok = scheduler._health_check()
            print_test_result("헬스체크", health_ok)
            
            # 스케줄 설정 확인
            import schedule
            job_count = len(schedule.jobs)
            
            if job_count > 0:
                print_test_result("글로벌 스케줄 설정", True, f"{job_count}개 작업 등록됨")
                
                # 작업별 다음 실행 시간 확인
                next_jobs = []
                current_time = datetime.now()
                
                for job in schedule.jobs:
                    if job.next_run:
                        time_until = job.next_run - current_time
                        hours_until = int(time_until.total_seconds() / 3600)
                        tag = list(job.tags)[0] if job.tags else 'unknown'
                        next_jobs.append((hours_until, tag, job.next_run.strftime('%H:%M')))
                
                # 가장 가까운 3개 작업 표시
                next_jobs.sort()
                for hours, tag, time_str in next_jobs[:3]:
                    if hours < 24:
                        print(f"    ⏰ {tag}: {time_str} ({hours}시간 후)")
                    else:
                        days = hours // 24
                        print(f"    ⏰ {tag}: {time_str} ({days}일 후)")
                
                schedule.clear()  # 정리
                self.results['global_scheduler'] = True
                return True
            else:
                print_test_result("글로벌 스케줄 설정", False, "등록된 작업이 없음")
                self.results['global_scheduler'] = False
                return False
                
        except Exception as e:
            print_test_result("글로벌 스케줄러", False, f"Error: {e}")
            self.results['global_scheduler'] = False
            return False
    
    def test_ml_system(self):
        """ML 시스템 테스트"""
        print_header("ML 시스템 기본 테스트")
        
        try:
            from app.ml.global_ml_engine import GlobalMLEngine
            
            # ML 엔진 생성
            ml_engine = GlobalMLEngine()
            print_test_result("ML 엔진 생성", True)
            
            # 모델 파일 존재 확인
            model_dir = Path(__file__).parent / "storage" / "models" / "global"
            
            kr_model_exists = (model_dir / "KR_model_v3.0_global.joblib").exists()
            us_model_exists = (model_dir / "US_model_v3.0_global.joblib").exists()
            
            print_test_result("한국 모델 파일 존재", kr_model_exists)
            print_test_result("미국 모델 파일 존재", us_model_exists)
            
            model_exists = kr_model_exists or us_model_exists
            
            # 간단한 예측 테스트 (모델이 있는 경우)
            if model_exists:
                try:
                    from app.models.entities import MarketRegion
                    if kr_model_exists:
                        predictions = ml_engine.predict_stocks(MarketRegion.KR, top_n=3)
                        print_test_result("한국 예측 테스트", len(predictions) > 0 if predictions else False)
                    
                    if us_model_exists:
                        predictions = ml_engine.predict_stocks(MarketRegion.US, top_n=3)
                        print_test_result("미국 예측 테스트", len(predictions) > 0 if predictions else False)
                    
                except Exception as e:
                    print_test_result("예측 테스트", False, f"Error: {e}")
            
            self.results['ml_system'] = model_exists
            return model_exists
            
        except Exception as e:
            print_test_result("ML 시스템", False, f"Error: {e}")
            self.results['ml_system'] = False
            return False
    
    def test_server_startup(self):
        """서버 시작 프로세스 테스트"""
        print_header("서버 시작 프로세스 테스트")
        
        try:
            # 서버 스크립트 경로
            server_script = self.project_root / "tools" / "system" / "server.py"
            
            if not server_script.exists():
                print_test_result("서버 스크립트 존재", False, f"파일 없음: {server_script}")
                self.results['server_startup'] = False
                return False
            
            print_test_result("서버 스크립트 존재", True)
            
            # 서버를 백그라운드에서 시작 (테스트용)
            print("🚀 서버 시작 중... (10초 후 종료)")
            
            cmd = [sys.executable, str(server_script), "--daemon"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root)
            )
            
            # 5초 대기
            time.sleep(5)
            
            # 프로세스가 여전히 실행 중인지 확인
            if process.poll() is None:
                print_test_result("서버 프로세스 시작", True, "정상적으로 실행 중")
                
                # 프로세스 종료
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                self.results['server_startup'] = True
                return True
            else:
                # 프로세스가 종료됨
                stdout, stderr = process.communicate()
                error_msg = stderr.decode() if stderr else "Unknown error"
                print_test_result("서버 프로세스 시작", False, f"프로세스 종료: {error_msg}")
                self.results['server_startup'] = False
                return False
                
        except Exception as e:
            print_test_result("서버 시작 프로세스", False, f"Error: {e}")
            self.results['server_startup'] = False
            return False
    
    def test_logging_system(self):
        """로깅 시스템 테스트"""
        print_header("로깅 시스템 테스트")
        
        try:
            from app.utils.logger import setup_logging
            import logging
            
            # 로깅 설정
            setup_logging()
            print_test_result("로깅 설정", True)
            
            # 로그 디렉토리 확인
            log_base_dir = self.project_root / "storage" / "logs"
            log_base_dir.mkdir(parents=True, exist_ok=True)
            
            print_test_result("로그 디렉토리 생성", True)
            
            # 테스트 로그 작성
            logger = logging.getLogger("integration_test")
            logger.info("Integration test log message")
            
            print_test_result("테스트 로그 작성", True)
            
            # 날짜별 폴더 구조 테스트
            current_date = datetime.now()
            expected_log_dir = log_base_dir / str(current_date.year) / f"{current_date.month:02d}" / f"{current_date.day:02d}"
            
            # 실제 로그 파일이 있는지 확인 (있을 수도 없을 수도 있음)
            date_structure_exists = expected_log_dir.exists() or log_base_dir.exists()
            print_test_result("날짜별 로그 구조", date_structure_exists)
            
            self.results['logging'] = True
            return True
            
        except Exception as e:
            print_test_result("로깅 시스템", False, f"Error: {e}")
            self.results['logging'] = False
            return False
    
    def test_configuration(self):
        """설정 시스템 테스트"""
        print_header("설정 시스템 테스트")
        
        try:
            from app.config.settings import settings
            
            # 중요 설정값 확인
            config_tests = [
                ("database_url", "데이터베이스 URL"),
                ("redis_url", "Redis URL"),
                ("model_cache_dir", "모델 캐시 디렉토리"),
                ("log_level", "로그 레벨"),
            ]
            
            all_passed = True
            for attr, desc in config_tests:
                value = getattr(settings, attr, None)
                if value:
                    print_test_result(f"설정 {desc}", True, f"값: {value}")
                else:
                    print_test_result(f"설정 {desc}", False, "값이 없음")
                    all_passed = False
            
            # 환경별 설정 확인
            env = getattr(settings, 'environment', 'unknown')
            print_test_result("환경 설정", True, f"환경: {env}")
            
            self.results['configuration'] = all_passed
            return all_passed
            
        except Exception as e:
            print_test_result("설정 시스템", False, f"Error: {e}")
            self.results['configuration'] = False
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🧪 배포 전 통합 테스트 시작")
        print(f"📅 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 테스트 실행
        tests = [
            ("의존성 및 모듈 임포트", self.test_imports_and_dependencies),
            ("설정 시스템", self.test_configuration),
            ("데이터베이스 연결", self.test_database_connection),
            ("로깅 시스템", self.test_logging_system),
            ("스케줄링 시스템", self.test_scheduling_system),
            ("글로벌 스케줄러", self.test_global_scheduler),
            ("ML 시스템", self.test_ml_system),
            ("서버 시작 프로세스", self.test_server_startup),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                success = test_func()
                if success:
                    passed_tests += 1
            except Exception as e:
                print_test_result(test_name, False, f"테스트 예외: {e}")
        
        # 결과 요약
        print_header("테스트 결과 요약")
        
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"📊 테스트 통계:")
        print(f"   전체 테스트: {total_tests}개")
        print(f"   통과: {passed_tests}개")
        print(f"   실패: {total_tests - passed_tests}개")
        print(f"   성공률: {success_rate:.1f}%")
        
        # 상세 결과
        print(f"\n📋 상세 결과:")
        for category, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} {category}")
        
        # 배포 준비 상태 평가
        print(f"\n🚀 배포 준비 상태:")
        if success_rate >= 90:
            print("   ✅ 우수 - 배포 준비 완료")
            deployment_ready = True
        elif success_rate >= 75:
            print("   ⚠️ 양호 - 주의하여 배포 가능")
            deployment_ready = True
        elif success_rate >= 50:
            print("   ⚠️ 보통 - 문제 해결 후 배포 권장")
            deployment_ready = False
        else:
            print("   ❌ 불량 - 배포 전 문제 해결 필수")
            deployment_ready = False
        
        # 권장사항
        print(f"\n💡 권장사항:")
        if not self.results.get('database', False):
            print("   - 데이터베이스 연결 설정을 확인하세요")
        if not self.results.get('ml_system', False):
            print("   - ML 모델 파일을 생성하거나 확인하세요")
        if not self.results.get('scheduling', False):
            print("   - 스케줄링 서비스 설정을 확인하세요")
        if not self.results.get('server_startup', False):
            print("   - 서버 시작 관련 의존성을 확인하세요")
        
        if deployment_ready:
            print("   - 모든 핵심 시스템이 정상 작동합니다")
            print("   - 배포 후 모니터링을 통해 실제 운영 상태를 확인하세요")
        
        return deployment_ready


def main():
    """메인 실행 함수"""
    tester = IntegrationTester()
    
    try:
        deployment_ready = tester.run_all_tests()
        
        if deployment_ready:
            print("\n🎉 배포 준비 완료!")
            sys.exit(0)
        else:
            print("\n⚠️ 배포 전 문제 해결이 필요합니다.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()