"""
구조화된 로그 시스템
- 연/월/일 디렉토리 구조로 로그 저장
- 배포 환경 볼륨 매핑 지원
- 다양한 로그 레벨 지원
- 유지보수 친화적 설계
"""
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import os
from datetime import datetime, date
from typing import Optional
import json


class StructuredLogger:
    """구조화된 로그 시스템"""
    
    def __init__(self, logger_name: str = "stock_analyzer"):
        self.logger_name = logger_name
        self.logger = None
        
        # Docker 환경과 로컬 환경에 따른 로그 디렉토리 설정
        if Path("/app").exists():  # Docker 환경
            self.base_volume_path = Path("/app")
            self.is_production = True
            print(f"✅ Docker 환경: /app 로그 사용")
        elif Path("/volume1/project/stock-analyzer").exists():  # Synology 직접 환경
            self.base_volume_path = Path("/volume1/project/stock-analyzer")
            self.is_production = True
            print(f"✅ 배포 환경: 볼륨 매핑 로그 사용 - {self.base_volume_path}")
        else:  # 로컬 개발 환경
            self.base_volume_path = Path("storage")
            self.is_production = False
            print("⚠️ 개발 환경: 로컬 storage 로그 사용")
        
        # 로그 베이스 디렉토리
        self.logs_base = self.base_volume_path / "logs"
        self.logs_base.mkdir(parents=True, exist_ok=True)
        
        # 로거 초기화
        self._setup_logger()
    
    def _get_log_path(self, log_date: date = None) -> Path:
        """연/월/일 구조로 로그 경로 생성"""
        if log_date is None:
            log_date = date.today()
        
        year = log_date.year
        month = f"{log_date.month:02d}"
        day = f"{log_date.day:02d}"
        
        # 경로 구조: /logs/2025/01/15/
        log_dir = self.logs_base / str(year) / month / day
        log_dir.mkdir(parents=True, exist_ok=True)
        
        return log_dir
    
    def _setup_logger(self):
        """로거 설정"""
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(logging.DEBUG)
        
        # 기존 핸들러 제거 (중복 방지)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)-15s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 콘솔 핸들러 (개발 환경에서만)
        if not self.is_production:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 파일 핸들러들 설정
        self._setup_file_handlers(formatter)
    
    def _setup_file_handlers(self, formatter):
        """파일 핸들러들 설정"""
        today = date.today()
        log_dir = self._get_log_path(today)
        
        # 1. 전체 로그 (DEBUG 레벨)
        all_log_path = log_dir / f"all_{today.strftime('%Y%m%d')}.log"
        all_handler = logging.FileHandler(all_log_path, encoding='utf-8')
        all_handler.setLevel(logging.DEBUG)
        all_handler.setFormatter(formatter)
        self.logger.addHandler(all_handler)
        
        # 2. 에러 로그만 (ERROR 레벨)
        error_log_path = log_dir / f"error_{today.strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # 3. 실시간 학습 전용 로그
        ml_log_path = log_dir / f"realtime_learning_{today.strftime('%Y%m%d')}.log"
        ml_handler = logging.FileHandler(ml_log_path, encoding='utf-8')
        ml_handler.setLevel(logging.INFO)
        ml_handler.setFormatter(formatter)
        
        # 실시간 학습 관련 로그만 필터링
        ml_filter = logging.Filter()
        ml_filter.filter = lambda record: 'learning' in record.module.lower() or 'ml' in record.module.lower()
        ml_handler.addFilter(ml_filter)
        self.logger.addHandler(ml_handler)
        
        # 4. 성능 로그 (JSON 형태)
        self.performance_log_path = log_dir / f"performance_{today.strftime('%Y%m%d')}.jsonl"
    
    def log_performance(self, data: dict):
        """성능 데이터 JSON 로그"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "date": date.today().isoformat(),
                **data
            }
            
            with open(self.performance_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
        except Exception as e:
            self.logger.error(f"성능 로그 저장 실패: {e}")
    
    def debug(self, message: str):
        """디버그 로그"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """정보 로그"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """경고 로그"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """에러 로그"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """심각한 에러 로그"""
        self.logger.critical(message)
    
    def log_system_status(self, status: dict):
        """시스템 상태 로그 (구조화된 형태)"""
        status_data = {
            "type": "system_status",
            "status": status
        }
        self.log_performance(status_data)
        self.info(f"시스템 상태: {status}")
    
    def log_prediction_result(self, market: str, predictions: list, accuracy: float = None):
        """예측 결과 로그"""
        prediction_data = {
            "type": "prediction_result",
            "market": market,
            "prediction_count": len(predictions),
            "accuracy": accuracy,
            "predictions": predictions[:5]  # 상위 5개만 저장
        }
        self.log_performance(prediction_data)
        self.info(f"{market} 시장 예측 완료: {len(predictions)}개 종목")
    
    def log_learning_result(self, market: str, old_accuracy: float, new_accuracy: float, strategy: str):
        """학습 결과 로그"""
        learning_data = {
            "type": "learning_result",
            "market": market,
            "old_accuracy": old_accuracy,
            "new_accuracy": new_accuracy,
            "improvement": new_accuracy - old_accuracy,
            "strategy": strategy
        }
        self.log_performance(learning_data)
        
        if new_accuracy > old_accuracy:
            self.info(f"{market} 학습 성공: {old_accuracy:.1f}% → {new_accuracy:.1f}% (+{new_accuracy-old_accuracy:.1f}%)")
        else:
            self.warning(f"{market} 학습 후 성능 변화: {old_accuracy:.1f}% → {new_accuracy:.1f}% ({new_accuracy-old_accuracy:.1f}%)")
    
    def create_daily_summary(self, target_date: date = None):
        """일일 로그 요약 생성"""
        if target_date is None:
            target_date = date.today()
        
        try:
            log_dir = self._get_log_path(target_date)
            performance_file = log_dir / f"performance_{target_date.strftime('%Y%m%d')}.jsonl"
            
            if not performance_file.exists():
                self.warning(f"{target_date} 성능 로그 파일 없음")
                return
            
            # 성능 로그 분석
            summary_data = {
                "prediction_count": 0,
                "learning_count": 0,
                "system_checks": 0,
                "markets": set(),
                "average_accuracy": [],
                "learning_improvements": []
            }
            
            with open(performance_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_type = entry.get('type', '')
                        
                        if entry_type == 'prediction_result':
                            summary_data["prediction_count"] += 1
                            summary_data["markets"].add(entry.get('market', ''))
                            if entry.get('accuracy'):
                                summary_data["average_accuracy"].append(entry['accuracy'])
                        
                        elif entry_type == 'learning_result':
                            summary_data["learning_count"] += 1
                            improvement = entry.get('improvement', 0)
                            summary_data["learning_improvements"].append(improvement)
                        
                        elif entry_type == 'system_status':
                            summary_data["system_checks"] += 1
                            
                    except json.JSONDecodeError:
                        continue
            
            # 요약 리포트 생성
            summary_file = log_dir / f"daily_summary_{target_date.strftime('%Y%m%d')}.md"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"# 일일 로그 요약 - {target_date.strftime('%Y년 %m월 %d일')}\n\n")
                f.write(f"## 📊 활동 요약\n")
                f.write(f"- 예측 실행: {summary_data['prediction_count']}회\n")
                f.write(f"- 학습 실행: {summary_data['learning_count']}회\n")
                f.write(f"- 시스템 체크: {summary_data['system_checks']}회\n")
                f.write(f"- 활성 시장: {', '.join(summary_data['markets'])}\n\n")
                
                if summary_data['average_accuracy']:
                    avg_acc = sum(summary_data['average_accuracy']) / len(summary_data['average_accuracy'])
                    f.write(f"## 🎯 성능 지표\n")
                    f.write(f"- 평균 정확도: {avg_acc:.1f}%\n")
                    f.write(f"- 최고 정확도: {max(summary_data['average_accuracy']):.1f}%\n")
                    f.write(f"- 최저 정확도: {min(summary_data['average_accuracy']):.1f}%\n\n")
                
                if summary_data['learning_improvements']:
                    total_improvement = sum(summary_data['learning_improvements'])
                    f.write(f"## 📈 학습 성과\n")
                    f.write(f"- 총 정확도 개선: {total_improvement:.1f}%p\n")
                    f.write(f"- 평균 개선율: {total_improvement/len(summary_data['learning_improvements']):.1f}%p\n")
                    f.write(f"- 성공적 학습: {len([x for x in summary_data['learning_improvements'] if x > 0])}회\n\n")
                
                f.write(f"---\n생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            self.info(f"일일 로그 요약 생성 완료: {summary_file}")
            
        except Exception as e:
            self.error(f"일일 로그 요약 생성 실패: {e}")
    
    def cleanup_old_logs(self, keep_days: int = 90):
        """오래된 로그 파일 정리"""
        try:
            from datetime import timedelta
            cutoff_date = date.today() - timedelta(days=keep_days)
            
            deleted_count = 0
            for year_dir in self.logs_base.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                
                year = int(year_dir.name)
                if year < cutoff_date.year:
                    # 전체 연도 삭제
                    import shutil
                    shutil.rmtree(year_dir)
                    deleted_count += 1
                    self.info(f"오래된 로그 연도 삭제: {year}")
                
                elif year == cutoff_date.year:
                    # 해당 년도 내 오래된 월/일 삭제
                    for month_dir in year_dir.iterdir():
                        if not month_dir.is_dir():
                            continue
                        
                        month = int(month_dir.name)
                        if month < cutoff_date.month:
                            import shutil
                            shutil.rmtree(month_dir)
                            deleted_count += 1
                            self.info(f"오래된 로그 월 삭제: {year}/{month}")
            
            if deleted_count > 0:
                self.info(f"로그 정리 완료: {deleted_count}개 디렉토리 삭제")
            else:
                self.info("정리할 오래된 로그 없음")
                
        except Exception as e:
            self.error(f"로그 정리 실패: {e}")


# 전역 로거 인스턴스
_global_logger = None

def get_logger(logger_name: str = "stock_analyzer") -> StructuredLogger:
    """전역 로거 인스턴스 반환"""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(logger_name)
    return _global_logger


def test_logging_system():
    """로그 시스템 테스트"""
    print("🧪 로그 시스템 테스트 시작...")
    
    logger = get_logger("test_logger")
    
    # 기본 로그 테스트
    logger.debug("디버그 메시지 테스트")
    logger.info("정보 메시지 테스트")
    logger.warning("경고 메시지 테스트")
    logger.error("에러 메시지 테스트")
    
    # 구조화된 로그 테스트
    logger.log_system_status({
        "database": "connected",
        "redis": "connected",
        "apis": {"kis": "ok", "alpha_vantage": "ok"}
    })
    
    logger.log_prediction_result("KR", [
        {"stock_code": "005930", "prediction": 2.5},
        {"stock_code": "000660", "prediction": 1.8}
    ], accuracy=72.3)
    
    logger.log_learning_result("KR", 70.1, 72.3, "fine_tune")
    
    # 일일 요약 생성
    logger.create_daily_summary()
    
    print("✅ 로그 시스템 테스트 완료")
    
    # 생성된 로그 파일 확인
    today = date.today()
    log_dir = logger._get_log_path(today)
    print(f"📁 로그 파일 위치: {log_dir}")
    
    for log_file in log_dir.iterdir():
        if log_file.is_file():
            print(f"   📄 {log_file.name} ({log_file.stat().st_size} bytes)")


if __name__ == "__main__":
    test_logging_system()
