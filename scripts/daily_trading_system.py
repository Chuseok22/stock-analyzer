#!/usr/bin/env python3
"""
일일 자동화 주식 추천 시스템
- 매일 정해진 시간에 실행
- 시장 데이터 업데이트
- ML 모델 학습 및 추천 생성
- 알림 발송
"""
import sys
import os
from pathlib import Path
from datetime import datetime, time
import schedule
import time as time_module
import logging

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from production_ml_system import ProductionMLSystem
from app.services.kis_api import KISAPIClient


# 로깅 설정
log_dir = Path(__file__).parent.parent / "storage" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'daily_trading_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class DailyTradingSystem:
    """일일 자동화 트레이딩 시스템"""
    
    def __init__(self):
        self.ml_system = ProductionMLSystem()
        self.kis_client = KISAPIClient()
        
    def refresh_access_token(self):
        """일일 액세스 토큰 갱신"""
        logger.info("🔄 일일 액세스 토큰 갱신 시작")
        
        try:
            success = self.kis_client.refresh_token_daily()
            if success:
                logger.info("✅ 액세스 토큰 갱신 성공")
            else:
                logger.error("❌ 액세스 토큰 갱신 실패")
                
        except Exception as e:
            logger.error(f"❌ 토큰 갱신 중 오류: {e}")
    
    def collect_daily_data(self):
        """일일 데이터 수집"""
        logger.info("📊 일일 데이터 수집 시작")
        
        try:
            # 현재 스크립트와 같은 디렉토리의 collect_enhanced_data.py 실행
            script_dir = Path(__file__).parent
            collect_script = script_dir / "collect_enhanced_data.py"
            os.system(f"cd {script_dir.parent} && python {collect_script}")
            logger.info("✅ 일일 데이터 수집 완료")
            
        except Exception as e:
            logger.error(f"❌ 데이터 수집 실패: {e}")
    
    def run_ml_analysis(self):
        """ML 분석 및 추천 생성"""
        logger.info("🤖 ML 분석 및 추천 생성 시작")
        
        try:
            # 현재 스크립트와 같은 디렉토리의 production_ml_system.py 실행
            script_dir = Path(__file__).parent
            ml_script = script_dir / "production_ml_system.py"
            os.system(f"cd {script_dir.parent} && python {ml_script}")
            logger.info("✅ ML 분석 완료")
            
        except Exception as e:
            logger.error(f"❌ ML 분석 실패: {e}")
    
    def daily_routine(self):
        """일일 루틴 실행"""
        start_time = datetime.now()
        logger.info(f"🚀 일일 트레이딩 시스템 시작 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 1. 토큰 갱신
            self.refresh_access_token()
            
            # 2. 데이터 수집 (시장 개장 후)
            logger.info("⏰ 5분 대기 후 데이터 수집...")
            time_module.sleep(300)  # 5분 대기
            self.collect_daily_data()
            
            # 3. ML 분석 및 추천
            logger.info("⏰ 2분 대기 후 ML 분석...")
            time_module.sleep(120)  # 2분 대기
            self.run_ml_analysis()
            
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"✅ 일일 루틴 완료 - 소요시간: {duration}")
            
        except Exception as e:
            logger.error(f"❌ 일일 루틴 실패: {e}")
            
            # 오류 알림
            try:
                from app.services.notification import NotificationService
                notification = NotificationService()
                error_message = (
                    f"⚠️ **일일 트레이딩 시스템 오류**\n\n"
                    f"📅 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"❌ 오류: {str(e)}\n\n"
                    f"수동 확인이 필요합니다."
                )
                notification._send_simple_slack_message(error_message)
            except:
                pass  # 알림도 실패하면 그냥 넘어감
    
    def run_scheduler(self):
        """스케줄러 실행"""
        logger.info("📅 일일 트레이딩 시스템 스케줄러 시작")
        
        # 평일 장 마감 후 (오후 4시) 실행
        schedule.every().monday.at("16:00").do(self.daily_routine)
        schedule.every().tuesday.at("16:00").do(self.daily_routine)
        schedule.every().wednesday.at("16:00").do(self.daily_routine)
        schedule.every().thursday.at("16:00").do(self.daily_routine)
        schedule.every().friday.at("16:00").do(self.daily_routine)
        
        # 주말에 한 번 (토요일 오전 9시) - 주간 분석
        schedule.every().saturday.at("09:00").do(self.daily_routine)
        
        logger.info("📅 스케줄 등록 완료:")
        logger.info("   - 평일 16:00: 일일 분석")
        logger.info("   - 토요일 09:00: 주간 분석")
        
        # 무한 루프
        while True:
            try:
                schedule.run_pending()
                time_module.sleep(60)  # 1분마다 체크
                
            except KeyboardInterrupt:
                logger.info("🛑 스케줄러 중단됨")
                break
            except Exception as e:
                logger.error(f"❌ 스케줄러 오류: {e}")
                time_module.sleep(300)  # 5분 대기 후 재시작


def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "once":
            # 즉시 한 번 실행
            logger.info("🔄 즉시 실행 모드")
            system = DailyTradingSystem()
            system.daily_routine()
            
        elif command == "schedule":
            # 스케줄러 모드
            logger.info("📅 스케줄러 모드")
            system = DailyTradingSystem()
            system.run_scheduler()
            
        else:
            print("사용법:")
            print("  python daily_trading_system.py once      # 즉시 한 번 실행")
            print("  python daily_trading_system.py schedule  # 스케줄러 모드")
    else:
        # 기본값: 즉시 실행
        logger.info("🔄 기본 모드 - 즉시 실행")
        system = DailyTradingSystem()
        system.daily_routine()


if __name__ == "__main__":
    main()
