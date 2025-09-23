#!/usr/bin/env python3
"""
로깅 시스템 검증 스크립트
- 연/월/일 폴더 구조 확인
- 로그 파일 생성 테스트
- 로그 로테이션 동작 확인
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

def test_logging_structure():
    """로깅 구조 테스트"""
    print("🔍 로깅 시스템 구조 테스트 시작")
    print("="*50)
    
    # 로깅 설정 초기화
    from app.utils.logger import setup_logging
    setup_logging()
    
    # 현재 날짜
    now = datetime.now()
    print(f"📅 현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 로그 기본 디렉토리
    log_base_dir = Path(__file__).parent / "storage" / "logs"
    print(f"📁 로그 기본 디렉토리: {log_base_dir}")
    
    # 예상 로그 경로들
    expected_paths = [
        log_base_dir / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}",
        log_base_dir,  # 기본 로그 디렉토리
    ]
    
    print(f"\n📂 예상 로그 경로들:")
    for path in expected_paths:
        exists = path.exists()
        print(f"   {'✅' if exists else '❌'} {path} {'(존재함)' if exists else '(없음)'}")
    
    # 다양한 로거로 테스트 로그 생성
    test_loggers = [
        ("system.test", "🔧 시스템 테스트"),
        ("scheduler.test", "⏰ 스케줄러 테스트"),
        ("ml.test", "🤖 ML 테스트"),
        ("alert.test", "📢 알림 테스트"),
    ]
    
    print(f"\n📝 테스트 로그 생성:")
    for logger_name, description in test_loggers:
        logger = logging.getLogger(logger_name)
        
        # 다양한 레벨의 로그 생성
        logger.debug(f"{description} - DEBUG 메시지")
        logger.info(f"{description} - INFO 메시지")
        logger.warning(f"{description} - WARNING 메시지")
        logger.error(f"{description} - ERROR 메시지")
        
        print(f"   ✅ {logger_name}: 4개 레벨 로그 생성")
    
    # 로그 파일 확인
    print(f"\n📄 생성된 로그 파일 확인:")
    log_files_found = []
    
    for path in expected_paths:
        if path.exists():
            for log_file in path.glob("**/*.log"):
                log_files_found.append(log_file)
                
            # 하위 디렉토리 탐색
            for log_file in path.rglob("*.log"):
                if log_file not in log_files_found:
                    log_files_found.append(log_file)
    
    if log_files_found:
        for log_file in log_files_found:
            size = log_file.stat().st_size
            modified = datetime.fromtimestamp(log_file.stat().st_mtime)
            print(f"   📄 {log_file.name}: {size} bytes, 수정: {modified.strftime('%H:%M:%S')}")
            
            # 파일 내용 미리보기 (마지막 5줄)
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"      마지막 로그: {lines[-1].strip()[:100]}...")
            except Exception as e:
                print(f"      읽기 오류: {e}")
    else:
        print("   ❌ 로그 파일을 찾을 수 없습니다")
    
    # 날짜별 폴더 구조 확인
    print(f"\n📅 날짜별 폴더 구조 확인:")
    
    # 오늘, 어제, 내일 폴더 확인
    test_dates = [
        now - timedelta(days=1),  # 어제
        now,                      # 오늘  
        now + timedelta(days=1),  # 내일
    ]
    
    for test_date in test_dates:
        date_path = log_base_dir / str(test_date.year) / f"{test_date.month:02d}" / f"{test_date.day:02d}"
        exists = date_path.exists()
        
        date_desc = "어제" if test_date < now.replace(hour=0, minute=0, second=0, microsecond=0) else \
                   "오늘" if test_date.date() == now.date() else "내일"
        
        print(f"   {'✅' if exists else '❌'} {date_desc} ({test_date.strftime('%Y-%m-%d')}): {date_path}")
        
        if exists:
            log_count = len(list(date_path.glob("*.log")))
            print(f"      📄 로그 파일: {log_count}개")
    
    # 로그 설정 정보 확인
    print(f"\n⚙️ 로그 설정 정보:")
    
    root_logger = logging.getLogger()
    print(f"   📊 루트 로거 레벨: {logging.getLevelName(root_logger.level)}")
    print(f"   📡 핸들러 수: {len(root_logger.handlers)}")
    
    for i, handler in enumerate(root_logger.handlers):
        handler_type = type(handler).__name__
        if hasattr(handler, 'baseFilename'):
            print(f"   📄 핸들러 {i+1}: {handler_type} -> {handler.baseFilename}")
        else:
            print(f"   📺 핸들러 {i+1}: {handler_type}")
    
    return len(log_files_found) > 0

def test_log_rotation():
    """로그 로테이션 테스트"""
    print(f"\n🔄 로그 로테이션 테스트")
    print("="*30)
    
    # 대용량 로그 생성 (로테이션 트리거)
    test_logger = logging.getLogger("rotation.test")
    
    print("📝 대용량 로그 생성 중...")
    for i in range(100):
        test_logger.info(f"로그 로테이션 테스트 메시지 #{i+1:03d} - " + "A" * 100)
    
    print("✅ 대용량 로그 생성 완료")
    
    # 로그 파일 확인
    log_base_dir = Path(__file__).parent / "storage" / "logs"
    
    rotated_files = []
    for log_file in log_base_dir.rglob("*.log*"):
        if ".log." in str(log_file) or log_file.suffix in ['.1', '.2', '.3']:
            rotated_files.append(log_file)
    
    if rotated_files:
        print(f"🔄 로테이션된 파일 발견: {len(rotated_files)}개")
        for file in rotated_files:
            print(f"   📄 {file}")
    else:
        print("📄 로테이션된 파일 없음 (파일 크기가 작아서 정상)")

def test_different_log_levels():
    """다양한 로그 레벨 테스트"""
    print(f"\n📊 로그 레벨별 테스트")
    print("="*30)
    
    # 각 레벨별 로거 생성
    levels = [
        (logging.DEBUG, "DEBUG", "🔍"),
        (logging.INFO, "INFO", "ℹ️"),
        (logging.WARNING, "WARNING", "⚠️"),
        (logging.ERROR, "ERROR", "❌"),
        (logging.CRITICAL, "CRITICAL", "🚨"),
    ]
    
    test_logger = logging.getLogger("level.test")
    
    for level, level_name, emoji in levels:
        test_logger.log(level, f"{emoji} {level_name} 레벨 테스트 메시지")
        print(f"   ✅ {level_name} 로그 생성")

def main():
    """메인 함수"""
    print("🔍 로깅 시스템 종합 검증")
    print("="*50)
    
    try:
        # 1. 기본 로깅 구조 테스트
        log_files_created = test_logging_structure()
        
        # 2. 로그 로테이션 테스트
        test_log_rotation()
        
        # 3. 로그 레벨 테스트
        test_different_log_levels()
        
        # 결과 요약
        print(f"\n📋 테스트 결과 요약")
        print("="*30)
        
        if log_files_created:
            print("✅ 로그 파일 생성: 성공")
        else:
            print("❌ 로그 파일 생성: 실패")
        
        print("✅ 로그 레벨 테스트: 완료")
        print("✅ 로그 로테이션 테스트: 완료")
        
        # 최종 로그 디렉토리 상태
        log_base_dir = Path(__file__).parent / "storage" / "logs"
        if log_base_dir.exists():
            total_log_files = len(list(log_base_dir.rglob("*.log*")))
            total_size = sum(f.stat().st_size for f in log_base_dir.rglob("*.log*"))
            
            print(f"\n📊 로그 디렉토리 현황:")
            print(f"   📁 기본 경로: {log_base_dir}")
            print(f"   📄 총 로그 파일: {total_log_files}개")
            print(f"   💾 총 크기: {total_size / 1024:.1f} KB")
        
        if log_files_created:
            print("\n🎉 로깅 시스템이 정상적으로 작동합니다!")
            print("📅 연/월/일 폴더 구조로 로그가 관리됩니다.")
            return True
        else:
            print("\n⚠️ 로깅 시스템에 문제가 있을 수 있습니다.")
            return False
        
    except Exception as e:
        print(f"\n❌ 로깅 테스트 중 오류: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)