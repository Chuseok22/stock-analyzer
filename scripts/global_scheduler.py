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
from app.utils.market_time_utils import MarketTimeManager
from app.config.settings import settings


class GlobalScheduler:
    """글로벌 스케줄링 시스템"""
    
    def __init__(self):
        self.ml_engine = GlobalMLEngine()
        self.alert_system = SmartAlertSystem()
        self.market_time_manager = MarketTimeManager()
        
        # 시간대 설정
        self.kr_timezone = pytz.timezone('Asia/Seoul')
        self.us_timezone = pytz.timezone('America/New_York')
        
        # 실행 상태 추적
        self.is_running = False
        self.last_ml_training = None
        
        print("🌍 글로벌 스케줄링 시스템 초기화")
        self._setup_signal_handlers()
        self._setup_dynamic_schedules()
    
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        def signal_handler(signum, frame):
            print("\n🛑 종료 신호 수신, 정리 중...")
            self.is_running = False
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_dynamic_schedules(self):
        """동적 스케줄 설정 (MarketTimeManager 활용)"""
        print("⏰ 동적 글로벌 스케줄 설정 중...")
        
        # MarketTimeManager로 현재 시장 시간 정보 가져오기
        schedule_info = self.market_time_manager.get_market_schedule_info()
        dst_status = self.market_time_manager.format_dst_status()
        
        print(f"🌞 {dst_status}")
        
        # 미국 시장 시간을 한국 시간으로 변환 (MarketTimeManager 활용)
        us_times = self.market_time_manager.get_us_market_times_in_kr()
        
        # 1. 한국 시장 관련 스케줄 (고정)
        schedule.every().day.at("16:00").do(self._run_korean_market_analysis).tag("kr_market")
        
        # 2. 미국 시장 관련 스케줄 (동적)
        premarket_time = us_times['premarket_start_kr']
        market_open_time = us_times['regular_start_kr']
        market_analysis_time = us_times['regular_end_kr_analysis']  # 마감 30분 후
        data_collection_time = us_times['aftermarket_end_kr']       # 애프터마켓 30분 후
        
        schedule.every().day.at(premarket_time).do(self._run_us_premarket_alert).tag("us_premarket")
        schedule.every().day.at(market_open_time).do(self._run_us_market_open_alert).tag("us_market_open")
        schedule.every().day.at(market_analysis_time).do(self._run_us_market_analysis).tag("us_market")
        
        # 3. 데이터 수집 스케줄
        schedule.every().day.at(data_collection_time).do(self._collect_us_data).tag("us_data")
        schedule.every().day.at("17:00").do(self._collect_korean_data).tag("kr_data")
        
        # 4. ML 모델 재학습 스케줄
        schedule.every().saturday.at("02:00").do(self._run_weekly_ml_training).tag("ml_training")
        schedule.every().month.do(self._run_monthly_ml_training).tag("ml_monthly")
        
        # 5. 시스템 헬스체크
        schedule.every().hour.at(":00").do(self._health_check).tag("health")
        
        # 6. 긴급 알림 체크
        schedule.every(4).hours.do(self._check_emergency_alerts).tag("emergency")
        
        print("✅ 동적 스케줄 설정 완료:")
        print(f"   📈 한국 시장 분석: 매일 16:00")
        print(f"   🇺🇸 미국 프리마켓: 매일 {premarket_time} (ET 04:00)")
        print(f"   🇺🇸 미국 정규장 시작: 매일 {market_open_time} (ET 09:30)")
        print(f"   📊 미국 시장 분석: 매일 {market_analysis_time} (ET 16:30)")
        print(f"   📁 미국 데이터 수집: 매일 {data_collection_time} (ET 20:30)")
        print(f"   🤖 ML 재학습: 매주 토요일 02:00")
        print(f"   🚨 긴급 알림: 4시간마다")
        print(f"   ⏰ {dst_status}")
    
    def _setup_schedules(self):
        """레거시 스케줄 설정 (호환성을 위해 유지)"""
        print("⚠️ 레거시 스케줄 메서드 호출됨 - _setup_dynamic_schedules 사용 권장")
        self._setup_dynamic_schedules()
    
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
        """미국 프리마켓 알림 실행 (한국시간 17:00 = 미국 04:00 ET)"""
        print("\n🌅 미국 프리마켓 알림 시작 (17:00)")
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
    
    async def _run_us_market_open_alert(self):
        """미국 정규장 시작 알림 실행 (한국시간 22:30 = 미국 09:30 ET)"""
        print("\n🇺🇸 미국 정규장 시작 알림 (22:30)")
        print("="*50)
        
        try:
            # 정규장 시작 알림 생성 및 전송  
            market_open_alert = self.alert_system.generate_market_open_alert("US")
            if market_open_alert:
                success = await self.alert_system.send_alert(market_open_alert)
                if success:
                    print("✅ 정규장 시작 알림 전송 완료")
                else:
                    print("❌ 정규장 시작 알림 전송 실패")
            else:
                print("⚠️ 정규장 시작 알림 생성 실패")
            
            return True
            
        except Exception as e:
            print(f"❌ 정규장 시작 알림 실패: {e}")
            return False
    
    async def _run_us_market_analysis(self):
        """미국 시장 분석 실행 (한국시간 05:30 = 미국 16:30 ET, 마감 30분 후)"""
        print("\n🇺🇸 미국 시장 분석 시작 (05:30)")
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
        current_time = datetime.now(self.kr_timezone)
        jobs_info = []
        
        for job in schedule.jobs:
            next_run = job.next_run
            if next_run:
                # 다음 실행까지 남은 시간 계산
                time_until = next_run - current_time.replace(tzinfo=None)
                hours_until = int(time_until.total_seconds() / 3600)
                
                # 작업 이름 정리
                tag_names = {
                    'kr_market': '🇰🇷 한국 시장 분석',
                    'us_premarket': '🇺🇸 미국 프리마켓',
                    'us_market_open': '🇺🇸 미국 정규장 시작',
                    'us_market': '🇺🇸 미국 시장 분석',
                    'kr_data': '📊 한국 데이터 수집',
                    'us_data': '📊 미국 데이터 수집',
                    'ml_training': '🤖 ML 주간 학습',
                    'ml_monthly': '🤖 ML 월간 학습',
                    'health': '🏥 헬스체크',
                    'emergency': '🚨 긴급 알림 체크'
                }
                
                tag = list(job.tags)[0] if job.tags else 'unknown'
                task_name = tag_names.get(tag, tag)
                
                jobs_info.append((hours_until, task_name, next_run.strftime('%Y-%m-%d %H:%M')))
        
        # 가장 가까운 작업 순으로 정렬
        jobs_info.sort(key=lambda x: x[0])
        
        for hours_until, task_name, next_run_str in jobs_info[:5]:  # 가장 가까운 5개만 표시
            if hours_until < 24:
                print(f"   • {task_name}: {next_run_str} ({hours_until}시간 후)")
            else:
                days_until = hours_until // 24
                print(f"   • {task_name}: {next_run_str} ({days_until}일 후)")
        
        if len(jobs_info) > 5:
            print(f"   ... 외 {len(jobs_info) - 5}개 작업")
        
        # 서머타임 전환 추적용 변수
        self.last_dst_status = self._is_dst_active()
        
        print("\n🔄 스케줄러 대기 중... (Ctrl+C로 종료)")
        
        # 메인 스케줄러 루프
        while self.is_running:
            try:
                # 서머타임 전환 감지 및 스케줄 재설정
                current_dst_status = self._is_dst_active()
                if current_dst_status != self.last_dst_status:
                    print(f"\n🔄 서머타임 전환 감지!")
                    print(f"   {self.last_dst_status} → {current_dst_status}")
                    print("   스케줄 재설정 중...")
                    
                    # 기존 스케줄 삭제
                    schedule.clear()
                    
                    # 새로운 시간대로 스케줄 재설정
                    self._setup_dynamic_schedules()
                    
                    self.last_dst_status = current_dst_status
                    print("✅ 서머타임 전환에 따른 스케줄 재설정 완료")
                
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
            "us_market_open": self._run_us_market_open_alert,
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
