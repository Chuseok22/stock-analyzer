#!/usr/bin/env python3
"""
글로벌 스케줄링 시스템
- 한국 시장: 16:00 데이터 분석 및 알림
- 미국 시장: 06:00 프리마켓 알림, 새벽 마감 분석
- 자동 ML 학습 스케줄링
- 서버 배포용 cron 작업 설정
"""
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional
import asyncio
import pytz
import schedule
import threading
import signal
import os

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.ml.global_ml_engine import GlobalMLEngine, MarketRegion
from app.services.smart_alert_system import SmartAlertSystem
from app.config.settings import settings


class GlobalScheduler:
    """글로벌 스케줄링 시스템"""
    
    def __init__(self):
        self.ml_engine = GlobalMLEngine()
        self.alert_system = SmartAlertSystem()
        
        # 시간대 설정
        self.kr_timezone = pytz.timezone('Asia/Seoul')
        self.us_timezone = pytz.timezone('America/New_York')
        
        # 실행 상태 추적
        self.is_running = False
        self.last_ml_training = None
        
        print("🌍 글로벌 스케줄링 시스템 초기화")
        self._setup_signal_handlers()
        self._setup_schedules()
    
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        def signal_handler(signum, frame):
            print("\n🛑 종료 신호 수신, 정리 중...")
            self.is_running = False
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_schedules(self):
        """스케줄 설정"""
        print("⏰ 글로벌 스케줄 설정 중...")
        
        # 1. 한국 시장 관련 스케줄
        # 매일 16:00 - 한국 시장 마감 후 분석 및 알림
        schedule.every().day.at("16:00").do(self._run_korean_market_analysis).tag("kr_market")
        
        # 2. 미국 시장 관련 스케줄  
        # 매일 06:00 - 미국 프리마켓 알림 (장 시작 30분 전)
        schedule.every().day.at("06:00").do(self._run_us_premarket_alert).tag("us_premarket")
        
        # 매일 06:30 - 미국 시장 마감 후 분석 (한국시간 새벽, 미국 현지 마감 후)
        schedule.every().day.at("06:30").do(self._run_us_market_analysis).tag("us_market")
        
        # 3. 데이터 수집 스케줄
        # 매일 07:00 - 미국 데이터 수집 (시장 마감 후)
        schedule.every().day.at("07:00").do(self._collect_us_data).tag("us_data")
        
        # 매일 17:00 - 한국 데이터 수집 (시장 마감 후)  
        schedule.every().day.at("17:00").do(self._collect_korean_data).tag("kr_data")
        
        # 4. ML 모델 재학습 스케줄
        # 매주 토요일 02:00 - 주간 모델 재학습
        schedule.every().saturday.at("02:00").do(self._run_weekly_ml_training).tag("ml_training")
        
        # 매월 1일 03:00 - 월간 모델 재학습 (더 깊은 학습)
        schedule.every().month.do(self._run_monthly_ml_training).tag("ml_monthly")
        
        # 5. 시스템 헬스체크
        # 매시간 정각 - 시스템 상태 체크
        schedule.every().hour.at(":00").do(self._health_check).tag("health")
        
        # 6. 긴급 알림 체크
        # 4시간마다 - 하락장 경고 등 긴급 알림 체크
        schedule.every(4).hours.do(self._check_emergency_alerts).tag("emergency")
        
        print("✅ 스케줄 설정 완료:")
        print("   📈 한국 시장 분석: 매일 16:00")
        print("   🇺🇸 미국 프리마켓: 매일 06:00") 
        print("   📊 미국 시장 분석: 매일 06:30")
        print("   🤖 ML 재학습: 매주 토요일 02:00")
        print("   🚨 긴급 알림: 4시간마다")
    
    async def _run_korean_market_analysis(self):
        """한국 시장 분석 실행"""
        print("\n🇰🇷 한국 시장 분석 시작 (16:00)")
        print("="*50)
        
        try:
            # 1. 시장 체제 분석
            print("📊 시장 체제 분석...")
            market_condition = self.ml_engine.detect_market_regime()
            
            # 2. 한국 주식 예측
            print("🎯 한국 주식 예측...")
            kr_predictions = self.ml_engine.predict_stocks(MarketRegion.KR, top_n=10)
            
            # 3. 마감 후 요약 알림 전송
            print("📢 한국 시장 요약 알림...")
            kr_summary = self.alert_system.generate_market_close_summary(MarketRegion.KR)
            if kr_summary:
                await self.alert_system.send_alert(kr_summary)
            
            # 4. 하락장 경고 체크
            bear_warning = self.alert_system.generate_bear_market_warning()
            if bear_warning:
                await self.alert_system.send_alert(bear_warning)
            
            print("✅ 한국 시장 분석 완료")
            return True
            
        except Exception as e:
            print(f"❌ 한국 시장 분석 실패: {e}")
            return False
    
    async def _run_us_premarket_alert(self):
        """미국 프리마켓 알림 실행"""
        print("\n🌅 미국 프리마켓 알림 시작 (06:00)")
        print("="*50)
        
        try:
            # 프리마켓 알림 생성 및 전송
            premarket_alert = self.alert_system.generate_premarket_alert()
            if premarket_alert:
                success = await self.alert_system.send_alert(premarket_alert)
                if success:
                    print("✅ 프리마켓 알림 전송 완료")
                else:
                    print("❌ 프리마켓 알림 전송 실패")
            else:
                print("⚠️ 프리마켓 알림 생성 실패")
            
            return True
            
        except Exception as e:
            print(f"❌ 프리마켓 알림 실패: {e}")
            return False
    
    async def _run_us_market_analysis(self):
        """미국 시장 분석 실행"""
        print("\n🇺🇸 미국 시장 분석 시작 (06:30)")
        print("="*50)
        
        try:
            # 미국 시장 마감 후 요약
            us_summary = self.alert_system.generate_market_close_summary(MarketRegion.US)
            if us_summary:
                await self.alert_system.send_alert(us_summary)
            
            print("✅ 미국 시장 분석 완료")
            return True
            
        except Exception as e:
            print(f"❌ 미국 시장 분석 실패: {e}")
            return False
    
    def _collect_korean_data(self):
        """한국 데이터 수집"""
        print("\n📊 한국 데이터 수집 시작 (17:00)")
        
        try:
            # 기존 한국 데이터 수집 스크립트 실행
            from scripts.production_ml_system import ProductionMLSystem
            
            ml_system = ProductionMLSystem()
            success = ml_system.collect_daily_data()
            
            if success:
                print("✅ 한국 데이터 수집 완료")
            else:
                print("❌ 한국 데이터 수집 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ 한국 데이터 수집 오류: {e}")
            return False
    
    def _collect_us_data(self):
        """미국 데이터 수집"""
        print("\n📊 미국 데이터 수집 시작 (07:00)")
        
        try:
            # 미국 데이터 수집 스크립트 실행
            from scripts.collect_us_data import USDataCollector
            
            collector = USDataCollector()
            success = collector.run_full_collection()
            
            if success:
                print("✅ 미국 데이터 수집 완료")
            else:
                print("❌ 미국 데이터 수집 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ 미국 데이터 수집 오류: {e}")
            return False
    
    def _run_weekly_ml_training(self):
        """주간 ML 모델 재학습"""
        print("\n🏋️ 주간 ML 모델 재학습 시작")
        print("="*50)
        
        try:
            # 글로벌 모델 재학습
            success = self.ml_engine.train_global_models()
            
            if success:
                self.last_ml_training = datetime.now()
                print("✅ 주간 ML 재학습 완료")
            else:
                print("❌ 주간 ML 재학습 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ 주간 ML 재학습 오류: {e}")
            return False
    
    def _run_monthly_ml_training(self):
        """월간 딥러닝 모델 재학습"""
        print("\n🧠 월간 딥러닝 모델 재학습 시작")
        print("="*50)
        
        try:
            # 더 깊은 학습 (더 많은 데이터, 더 복잡한 모델)
            # 향후 딥러닝 모델 확장 시 여기에 구현
            
            # 현재는 일반 모델 재학습
            success = self.ml_engine.train_global_models()
            
            if success:
                print("✅ 월간 딥러닝 재학습 완료") 
            else:
                print("❌ 월간 딥러닝 재학습 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ 월간 딥러닝 재학습 오류: {e}")
            return False
    
    async def _check_emergency_alerts(self):
        """긴급 알림 체크"""
        print("\n🚨 긴급 알림 체크 (4시간 주기)")
        
        try:
            # 알림 주기 실행
            alerts_sent = await self.alert_system.run_alert_cycle()
            
            if alerts_sent:
                print("📢 긴급 알림 전송됨")
            else:
                print("✅ 긴급 상황 없음")
            
            return True
            
        except Exception as e:
            print(f"❌ 긴급 알림 체크 실패: {e}")
            return False
    
    def _health_check(self):
        """시스템 헬스체크"""
        current_time = datetime.now()
        print(f"\n💊 시스템 헬스체크 ({current_time.strftime('%H:%M')})")
        
        try:
            # 1. 데이터베이스 연결 체크
            from app.database.connection import get_db_session
            with get_db_session() as db:
                db.execute("SELECT 1")
            print("   ✅ 데이터베이스: 정상")
            
            # 2. Redis 연결 체크
            from app.database.redis_client import redis_client
            redis_client.ping()
            print("   ✅ Redis: 정상")
            
            # 3. ML 모델 상태 체크
            model_status = "정상" if self.ml_engine.models else "모델 없음"
            print(f"   📊 ML 모델: {model_status}")
            
            # 4. 마지막 ML 학습 시간
            if self.last_ml_training:
                days_since = (current_time - self.last_ml_training).days
                print(f"   🏋️ 마지막 학습: {days_since}일 전")
            else:
                print("   ⚠️ ML 학습 기록 없음")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 헬스체크 실패: {e}")
            return False
    
    def run_scheduler(self):
        """스케줄러 실행"""
        print("🚀 글로벌 스케줄러 시작")
        print("="*60)
        
        self.is_running = True
        
        # 초기 헬스체크
        self._health_check()
        
        print("\n⏰ 예정된 작업:")
        for job in schedule.jobs:
            print(f"   • {job.tags}: {job.next_run}")
        
        print("\n🔄 스케줄러 대기 중... (Ctrl+C로 종료)")
        
        # 메인 스케줄러 루프
        while self.is_running:
            try:
                # 예정된 작업 실행
                schedule.run_pending()
                
                # 1분 대기
                import time
                time.sleep(60)
                
            except KeyboardInterrupt:
                print("\n🛑 사용자 종료 요청")
                break
            except Exception as e:
                print(f"\n❌ 스케줄러 오류: {e}")
                # 오류 발생해도 계속 실행
                import time
                time.sleep(60)
        
        print("✅ 글로벌 스케줄러 종료")
    
    def run_manual_task(self, task_name: str):
        """수동 작업 실행"""
        print(f"🔧 수동 작업 실행: {task_name}")
        
        tasks = {
            "korean_analysis": self._run_korean_market_analysis,
            "us_premarket": self._run_us_premarket_alert,
            "us_analysis": self._run_us_market_analysis,
            "korean_data": self._collect_korean_data,
            "us_data": self._collect_us_data,
            "ml_training": self._run_weekly_ml_training,
            "health_check": self._health_check,
            "emergency_check": self._check_emergency_alerts
        }
        
        if task_name not in tasks:
            print(f"❌ 알 수 없는 작업: {task_name}")
            print(f"사용 가능한 작업: {list(tasks.keys())}")
            return False
        
        task = tasks[task_name]
        
        try:
            if asyncio.iscoroutinefunction(task):
                result = asyncio.run(task())
            else:
                result = task()
            
            if result:
                print(f"✅ {task_name} 완료")
            else:
                print(f"❌ {task_name} 실패")
            
            return result
            
        except Exception as e:
            print(f"❌ {task_name} 실행 오류: {e}")
            return False


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="글로벌 스케줄링 시스템")
    parser.add_argument("--manual", type=str, help="수동 작업 실행")
    parser.add_argument("--daemon", action="store_true", help="데몬 모드로 실행")
    
    args = parser.parse_args()
    
    scheduler = GlobalScheduler()
    
    if args.manual:
        # 수동 작업 실행
        success = scheduler.run_manual_task(args.manual)
        sys.exit(0 if success else 1)
    
    elif args.daemon:
        # 데몬 모드 (백그라운드 실행)
        print("👻 데몬 모드로 실행")
        scheduler.run_scheduler()
    
    else:
        # 일반 모드 (포그라운드 실행)
        scheduler.run_scheduler()


if __name__ == "__main__":
    main()
