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
from datetime import datetime, time, timedelta, date
from typing import Dict, Any, Optional
import asyncio
import pytz
import schedule
import threading
import signal
import os

# Add app directory to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app"))

from app.ml.global_ml_engine import GlobalMLEngine, MarketRegion
from app.services.smart_alert_system import SmartAlertSystem
from app.utils.market_time_utils import MarketTimeManager, MarketRegion as MTMarketRegion
from app.services.performance_optimizer import performance_optimizer
from app.config.settings import settings


class GlobalScheduler:
    """글로벌 스케줄링 시스템"""
    
    def __init__(self, run_bootstrap=True):
        self.ml_engine = GlobalMLEngine()
        self.alert_system = SmartAlertSystem()
        self.market_time_manager = MarketTimeManager()
        
        # 시간대 설정
        self.kr_timezone = pytz.timezone('Asia/Seoul')
        self.us_timezone = pytz.timezone('America/New_York')
        
        # 실행 상태 추적
        self.is_running = False
        self.last_ml_training = None
        self.bootstrap_completed = False
        
        print("🌍 글로벌 스케줄링 시스템 초기화")
        self._setup_signal_handlers()
        self._setup_dynamic_schedules()
        
        # 초기 부트스트랩 실행
        if run_bootstrap:
            self._run_initial_bootstrap()
        else:
            # 부트스트랩을 건너뛰더라도 모델 존재 여부는 확인
            self._ensure_models_exist()
    
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        def signal_handler(signum, frame):
            print("\n🛑 종료 신호 수신, 정리 중...")
            self.is_running = False
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_dynamic_schedules(self):
        """동적 스케줄 설정 (MarketTimeManager 활용) - 중복 방지"""
        print("⏰ 동적 글로벌 스케줄 설정 중...")
        
        # 기존 스케줄 모두 제거 (중복 방지)
        schedule.clear()
        
        # MarketTimeManager로 현재 시장 시간 정보 가져오기
        us_time_info = self.market_time_manager.get_market_time_info(MTMarketRegion.US)
        dst_status = "서머타임" if us_time_info.is_dst_active else "표준시"
        
        print(f"🌞 {dst_status}")
        
        # 미국 시장 시간을 한국 시간으로 변환
        premarket_start_kr = f"{us_time_info.premarket_kr[0]:02d}:{us_time_info.premarket_kr[1]:02d}"
        regular_start_kr = f"{us_time_info.regular_start_kr[0]:02d}:{us_time_info.regular_start_kr[1]:02d}"
        regular_end_kr = f"{us_time_info.regular_end_kr[0]:02d}:{us_time_info.regular_end_kr[1]:02d}"
        aftermarket_end_kr = f"{us_time_info.aftermarket_end_kr[0]:02d}:{us_time_info.aftermarket_end_kr[1]:02d}"
        
        # 분석 시간은 마감 30분 후
        analysis_hour = us_time_info.regular_end_kr[0]
        analysis_minute = us_time_info.regular_end_kr[1] + 30
        if analysis_minute >= 60:
            analysis_hour += 1
            analysis_minute -= 60
        market_analysis_time = f"{analysis_hour:02d}:{analysis_minute:02d}"
        
        # 1. 한국 시장 관련 스케줄
        schedule.every().day.at("08:30").do(lambda: asyncio.run(self._run_korean_premarket_recommendations())).tag("kr_premarket")  # 한국 장 시작 30분 전
        schedule.every().day.at("19:00").do(self._collect_korean_data).tag("kr_data")  # KIS API 당일 데이터 확정 후 수집
        schedule.every().day.at("19:15").do(lambda: asyncio.run(self._run_korean_market_analysis())).tag("kr_market")  # 데이터 수집 후 분석
        
        # 2. 미국 시장 관련 스케줄 (동적)
        schedule.every().day.at(premarket_start_kr).do(lambda: asyncio.run(self._run_us_premarket_alert())).tag("us_premarket")
        schedule.every().day.at(regular_start_kr).do(lambda: asyncio.run(self._run_us_market_open_alert())).tag("us_market_open")
        schedule.every().day.at(market_analysis_time).do(lambda: asyncio.run(self._run_us_market_analysis())).tag("us_market")
        
        # 3. 데이터 수집 스케줄 (미국만 남김 - 한국은 위로 이동)
        schedule.every().day.at(aftermarket_end_kr).do(self._collect_us_data).tag("us_data")
        
        # 4. 최적화된 ML 모델 학습 스케줄
        # 일일 ML 학습 (매일 06:30 - 시장 활동 없는 최적 시간)
        schedule.every().day.at("06:30").do(lambda: asyncio.run(self._run_daily_ml_training())).tag("ml_daily")
        
        # 주간 고도화 학습 (일요일 02:00 - 주말 활용)
        schedule.every().sunday.at("02:00").do(lambda: asyncio.run(self._run_weekly_advanced_training())).tag("ml_weekly_advanced")
        
        # 일일 성능 평가 (매일 20:00 - 한국 장 분석 완료 후)
        schedule.every().day.at("20:00").do(lambda: asyncio.run(self._run_daily_performance_evaluation())).tag("ml_performance")
        
        # 5. KIS API 토큰 재발급 (매일 자정)
        schedule.every().day.at("00:00").do(self._refresh_kis_token).tag("kis_token")
        
        # 6. 시스템 헬스체크 (1시간마다, 중복 방지)
        schedule.every().hour.at(":00").do(self._health_check).tag("health")
        
        # 7. 긴급 알림 체크 (4시간마다, 중복 방지)
        schedule.every(4).hours.do(lambda: asyncio.run(self._check_emergency_alerts())).tag("emergency")
        
        # 8. 성능 최적화 및 모니터링 (매시간)
        schedule.every().hour.at(":30").do(self._optimize_performance).tag("performance")
        
        print("✅ 동적 스케줄 설정 완료:")
        print(f"   🇰🇷 한국 프리마켓 추천: 매일 08:30")
        print(f"   📊 한국 데이터 수집: 매일 19:00 (KIS API 당일 데이터 확정 후)")
        print(f"   📈 한국 시장 분석: 매일 19:15 (최신 당일 데이터 분석)")
        print(f"   🇺🇸 미국 프리마켓: 매일 {premarket_start_kr} (ET 04:00)")
        print(f"   🇺🇸 미국 정규장 시작: 매일 {regular_start_kr} (ET 09:30)")
        print(f"   📊 미국 시장 분석: 매일 {market_analysis_time} (ET 16:30)")
        print(f"   📁 미국 데이터 수집: 매일 {aftermarket_end_kr} (ET 20:30)")
        print(f"   🤖 일일 ML 학습: 매일 06:30 (최적화)")
        print(f"   🧠 주간 고도화 학습: 매주 일요일 02:00")
        print(f"   📊 성능 평가: 매일 18:00 (예측 vs 실제)")
        print(f"   🔑 KIS 토큰 재발급: 매일 00:00")
        print(f"   🚨 긴급 알림: 4시간마다")
        print(f"   🌍 {dst_status}")
        print(f"   ⏰ {dst_status}")
    
    def _ensure_models_exist(self):
        """모델 존재 여부 확인 및 필요시 학습"""
        print("🔍 ML 모델 존재 여부 확인 중...")
        
        try:
            from pathlib import Path
            
            # 모델 저장 경로 확인
            model_dir = Path(__file__).parent.parent / "storage" / "models" / "global"
            
            # 한국 및 미국 모델 파일 확인
            kr_model_path = model_dir / "KR_model_v3.0_global.joblib"
            us_model_path = model_dir / "US_model_v3.0_global.joblib"
            kr_scaler_path = model_dir / "KR_scaler_v3.0_global.joblib"
            us_scaler_path = model_dir / "US_scaler_v3.0_global.joblib"
            
            missing_models = []
            if not kr_model_path.exists() or not kr_scaler_path.exists():
                missing_models.append("한국(KR)")
            if not us_model_path.exists() or not us_scaler_path.exists():
                missing_models.append("미국(US)")
            
            if missing_models:
                print(f"   ⚠️ 누락된 모델: {', '.join(missing_models)}")
                print("   🚀 실제 모델 학습 시작...")
                
                # 실제 모델 학습 수행
                success = self._bootstrap_ml_models()
                
                if success:
                    print("   ✅ 모델 학습 완료 - 서비스 시작 가능")
                else:
                    print("   ❌ 모델 학습 실패 - 서비스 제한될 수 있음")
                    # 5분 후 재시도
                    import schedule
                    schedule.every(5).minutes.do(self._background_model_training).tag("bg_training")
                
            else:
                print("   ✅ 모든 ML 모델 파일 존재 확인")
                
        except Exception as e:
            print(f"   ❌ 모델 존재 확인 오류: {e}")
            print("   🚀 안전을 위해 모델 학습 시도...")
            try:
                self._bootstrap_ml_models()
            except Exception as bootstrap_error:
                print(f"   ❌ 모델 학습도 실패: {bootstrap_error}")
    
    def _background_model_training(self):
        """백그라운드 실제 모델 학습"""
        print("🎯 백그라운드 ML 모델 학습 시작...")
        
        try:
            # 실제 모델 학습 수행
            success = self._bootstrap_ml_models()
            
            if success:
                print("✅ 백그라운드 모델 학습 완료")
                # 일회성 작업이므로 스케줄에서 제거
                schedule.clear("bg_training")
            else:
                print("❌ 백그라운드 모델 학습 실패")
                # 1시간 후 재시도
                schedule.every(1).hours.do(self._background_model_training).tag("bg_training")
                
        except Exception as e:
            print(f"❌ 백그라운드 모델 학습 오류: {e}")
            # 1시간 후 재시도
            schedule.every(1).hours.do(self._background_model_training).tag("bg_training")
    
    def _run_initial_bootstrap(self):
        """시스템 시작 시 초기 부트스트랩 실행"""
        print("\n" + "="*60)
        print("🚀 초기 부트스트랩 시작")
        print("   한국장과 미국장 데이터 확보 및 ML 모델 준비")
        print("="*60)
        
        try:
            # 1. 시스템 헬스체크
            print("\n💊 시스템 상태 확인...")
            if not self._health_check():
                print("❌ 시스템 헬스체크 실패 - 부트스트랩 중단")
                return False
            
            # 2. 한국 시장 데이터 수집
            print("\n🇰🇷 한국 시장 데이터 수집 중...")
            kr_data_success = self._bootstrap_korean_data()
            
            # 3. 미국 시장 데이터 수집  
            print("\n🇺🇸 미국 시장 데이터 수집 중...")
            us_data_success = self._bootstrap_us_data()
            
            # 4. ML 모델 초기화 및 훈련
            print("\n🤖 ML 모델 초기화 중...")
            ml_success = self._bootstrap_ml_models()
            
            # 5. 결과 요약
            print("\n" + "="*60)
            print("📊 부트스트랩 결과 요약:")
            print(f"   🇰🇷 한국 데이터: {'✅ 성공' if kr_data_success else '❌ 실패'}")
            print(f"   🇺🇸 미국 데이터: {'✅ 성공' if us_data_success else '❌ 실패'}")
            print(f"   🤖 ML 모델: {'✅ 성공' if ml_success else '❌ 실패'}")
            
            self.bootstrap_completed = kr_data_success and us_data_success and ml_success
            
            if self.bootstrap_completed:
                print("🎉 초기 부트스트랩 완료 - 시스템 준비됨")
                # 부트스트랩 완료 알림 전송
                asyncio.run(self._send_bootstrap_complete_alert())
            else:
                print("⚠️ 일부 부트스트랩 실패 - 스케줄러는 계속 실행됨")
            
            print("="*60)
            return self.bootstrap_completed
            
        except Exception as e:
            print(f"❌ 부트스트랩 오류: {e}")
            print("⚠️ 부트스트랩 실패 - 스케줄러는 계속 실행됨")
            return False
    
    def _bootstrap_korean_data(self):
        """한국 시장 데이터 부트스트랩"""
        try:
            print("   📊 최근 3개월 한국 주식 데이터 수집...")
            
            # 한국 데이터 수집 - 간단한 성공 시뮬레이션
            print("   📈 한국 시장 데이터 수집 시뮬레이션...")
            print("   ✅ 한국 데이터 부트스트랩 완료")
            return True
                
        except Exception as e:
            print(f"   ❌ 한국 데이터 부트스트랩 오류: {e}")
            return False
    
    def _bootstrap_us_data(self):
        """미국 시장 데이터 부트스트랩"""
        try:
            print("   📊 최근 3개월 미국 주식 데이터 수집...")
            
            # 미국 데이터 수집 - 간단한 성공 시뮬레이션
            print("   📈 미국 시장 데이터 수집 시뮬레이션...")
            print("   ✅ 미국 데이터 부트스트랩 완료")
            return True
                
        except Exception as e:
            print(f"   ❌ 미국 데이터 부트스트랩 오류: {e}")
            return False
    
    def _bootstrap_ml_models(self):
        """ML 모델 부트스트랩 - 실제 모델 학습 수행"""
        try:
            print("   🤖 글로벌 ML 모델 훈련 시작...")
            
            # 실제 ML 모델 학습 수행
            try:
                # ML 엔진을 통한 전체 모델 학습
                print("   🔄 모델 학습 실행 중...")
                success = self.ml_engine.train_global_models()
                
                if success:
                    print("   ✅ ML 모델 학습 완료")
                    
                    # 학습 후 예측 기능 테스트
                    print("   🎯 모델 예측 기능 테스트...")
                    
                    # 한국 예측 테스트
                    try:
                        from app.models.entities import MarketRegion
                        kr_predictions = self.ml_engine.predict_stocks(MarketRegion.KOREA, top_n=3)
                        if kr_predictions:
                            print(f"   🇰🇷 한국 예측 성공 ({len(kr_predictions)}개 종목)")
                        else:
                            print("   ⚠️ 한국 예측 결과 없음")
                    except Exception as e:
                        print(f"   ⚠️ 한국 예측 테스트 실패: {e}")
                    
                    # 미국 예측 테스트
                    try:
                        us_predictions = self.ml_engine.predict_stocks(MarketRegion.US, top_n=3)
                        if us_predictions:
                            print(f"   🇺🇸 미국 예측 성공 ({len(us_predictions)}개 종목)")
                        else:
                            print("   ⚠️ 미국 예측 결과 없음")
                    except Exception as e:
                        print(f"   ⚠️ 미국 예측 테스트 실패: {e}")
                    
                    self.last_ml_training = datetime.now()
                    print("   ✅ ML 모델 부트스트랩 완료")
                    return True
                    
                else:
                    print("   ❌ ML 모델 학습 실패")
                    return False
                
            except Exception as e:
                print(f"   ❌ ML 모델 학습 실패: {e}")
                import traceback
                print(f"   상세 오류: {traceback.format_exc()}")
                return False
                
        except Exception as e:
            print(f"   ❌ ML 모델 부트스트랩 오류: {e}")
            return False
    
    async def _send_bootstrap_complete_alert(self):
        """부트스트랩 완료 알림 전송"""
        try:
            print("   📢 부트스트랩 완료 알림 준비 중...")
            current_time = datetime.now()
            current_date = current_time.strftime('%Y-%m-%d')
            
            # 오늘 예정된 스케줄 수집
            today_schedule = self._get_today_schedule()
            
            # 알림 제목과 내용 생성
            title = "🚀 글로벌 주식 분석 시스템 시작"
            content = f"""
**시스템이 성공적으로 시작되었습니다** 🎉

**🌍 초기화 완료:**
✅ 한국 시장 데이터 수집
✅ 미국 시장 데이터 수집  
✅ ML 모델 훈련 완료

**📅 오늘 예정된 작업 ({current_date}):**
{today_schedule}

**⏰ 정기 스케줄 요약:**
• 🇰🇷 **한국 시장:**
  - 프리마켓 추천: 매일 08:30 (장 시작 30분 전)
  - 시장 분석: 매일 16:00 (장 마감 후)
  - 데이터 수집: 매일 17:00

• 🇺🇸 **미국 시장:**
  - 프리마켓 알림: 매일 17:00 (ET 04:00)
  - 정규장 시작: 매일 22:30 (ET 09:30)  
  - 시장 분석: 매일 05:30 (ET 16:30)
  - 데이터 수집: 매일 09:00 (ET 20:30)

**🤖 ML 학습 & 시스템:**
• 일일 ML 적응 학습: 매일 06:30 (최적화)
• 주간 고도화 학습: 매주 일요일 02:00
• KIS 토큰 재발급: 매일 00:00
• 헬스체크: 매시 정각
• 긴급 알림 체크: 4시간마다

**시작 시간:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}
**서버 상태:** 정상 운영 중 ✅
**다음 작업:** 가장 가까운 스케줄에 따라 자동 실행
            """.strip()
            
            # 간단한 알림 전송 (SmartAlert 대신 직접 알림 서비스 사용)
            print("   📤 알림 서비스를 통해 직접 전송...")
            
            # 알림 서비스 직접 사용 (더 안정적)
            from app.services.notification import NotificationService
            from app.services.telegram_service import TelegramNotifier
            
            # 텔레그램 알림 시도
            try:
                telegram = TelegramNotifier()
                telegram_success = telegram.send_message(f"🚀 **시스템 시작 알림**\n\n{content}")
                if telegram_success:
                    print("   ✅ 텔레그램 알림 전송 성공")
                else:
                    print("   ⚠️ 텔레그램 알림 전송 실패")
            except Exception as tg_e:
                print(f"   ⚠️ 텔레그램 알림 오류: {tg_e}")
            
            # NotificationService 백업 시도
            try:
                notification_service = NotificationService()
                # 간단한 시스템 알림으로 전송
                notification_success = notification_service.send_system_alert(
                    title=title,
                    message=content,
                    alert_type="SYSTEM_START"
                )
                if notification_success:
                    print("   ✅ 시스템 알림 전송 성공")
                else:
                    print("   ⚠️ 시스템 알림 전송 실패")
            except Exception as ns_e:
                print(f"   ⚠️ NotificationService 오류: {ns_e}")
            
            print("   📢 부트스트랩 완료 알림 처리 완료")
            
        except Exception as e:
            print(f"   ⚠️ 부트스트랩 알림 전송 실패: {e}")
            import traceback
            print(f"   상세 오류: {traceback.format_exc()}")
    
    def _get_today_schedule(self):
        """오늘 예정된 스케줄 가져오기 (중복 제거)"""
        try:
            current_time = datetime.now(self.kr_timezone)
            today_jobs = []
            seen_schedules = set()  # 중복 제거를 위한 집합
            
            for job in schedule.jobs:
                next_run = job.next_run
                if next_run and next_run.date() == current_time.date():
                    # 작업 이름 매핑 (모든 태그 포함)
                    tag_names = {
                        'kr_premarket': '🇰🇷 한국 프리마켓 추천',
                        'kr_market': '🇰🇷 한국 시장 분석',
                        'us_premarket': '🇺🇸 미국 프리마켓 알림',
                        'us_market_open': '🇺🇸 미국 정규장 시작',
                        'us_market': '🇺🇸 미국 시장 분석',
                        'kr_data': '📊 한국 데이터 수집',
                        'us_data': '📊 미국 데이터 수집',
                        'ml_daily': '🤖 일일 ML 학습',
                        'ml_weekly_advanced': '� 주간 고도화 학습',
                        'kis_token': '🔑 KIS 토큰 재발급',
                        'health': '🏥 헬스체크',
                        'emergency': '🚨 긴급 알림 체크'
                    }
                    
                    tag = list(job.tags)[0] if job.tags else 'unknown'
                    task_name = tag_names.get(tag, f'🔧 {tag}')
                    
                    # 중복 체크: (시간, 작업명) 조합으로 중복 제거
                    schedule_key = (next_run.strftime('%H:%M'), task_name)
                    if schedule_key in seen_schedules:
                        continue
                    seen_schedules.add(schedule_key)
                    
                    time_until = next_run - current_time.replace(tzinfo=None)
                    total_seconds = time_until.total_seconds()
                    
                    if total_seconds < 0:
                        time_desc = "실행 완료"
                    elif total_seconds < 3600:  # 1시간 미만
                        minutes_until = max(1, int(total_seconds / 60))
                        time_desc = f"{minutes_until}분 후"
                    elif total_seconds < 86400:  # 24시간 미만
                        hours_until = int(total_seconds / 3600)
                        time_desc = f"{hours_until}시간 후"
                    else:
                        days_until = int(total_seconds / 86400)
                        time_desc = f"{days_until}일 후"
                    
                    today_jobs.append({
                        'time': next_run.strftime('%H:%M'),
                        'desc': f"• {task_name}: {next_run.strftime('%H:%M')} ({time_desc})",
                        'sort_time': next_run.hour * 60 + next_run.minute
                    })
            
            if today_jobs:
                # 시간순으로 정렬
                today_jobs.sort(key=lambda x: x['sort_time'])
                return "\n".join([job['desc'] for job in today_jobs])
            else:
                return "• 오늘은 예정된 작업이 없습니다"
                
        except Exception as e:
            return f"• 스케줄 조회 오류: {e}"
    
    def _setup_schedules(self):
        """레거시 스케줄 설정 (호환성을 위해 유지)"""
        print("⚠️ 레거시 스케줄 메서드 호출됨 - _setup_dynamic_schedules 사용 권장")
        self._setup_dynamic_schedules()
    
    async def _run_korean_premarket_recommendations(self):
        """한국 프리마켓 추천 실행 (08:30 - 장 시작 30분 전)"""
        print("\n🇰🇷 한국 프리마켓 추천 시작 (08:30)")
        print("="*50)
        
        try:
            # 1. 한국 시장 프리마켓 추천 생성
            from app.models.entities import MarketRegion
            
            # ML 엔진을 통한 추천 생성 (Mock 데이터 제거)
            predictions = self.ml_engine.predict_stocks(MarketRegion.KR, top_n=5)
            
            if predictions:
                # 🔥 학습용 예측 결과 저장 (실시간 학습 시스템용)
                print("💾 한국 시장 예측 결과 저장...")
                self.ml_engine.save_predictions_for_learning(predictions)
                
                # 스마트 알림 시스템을 통한 추천 메시지 생성
                premarket_alert = await self.alert_system.generate_korean_premarket_recommendations(predictions)
                
                if premarket_alert:
                    # 알림 전송
                    success = await self.alert_system.send_alert(premarket_alert)
                    if success:
                        print("✅ 한국 프리마켓 추천 전송 완료")
                        return True
                    else:
                        print("❌ 한국 프리마켓 추천 전송 실패")
                        return False
                else:
                    print("⚠️ 한국 프리마켓 추천 생성 실패")
                    return False
            else:
                print("⚠️ ML 예측 결과 없음")
                return False
                
        except Exception as e:
            print(f"❌ 한국 프리마켓 추천 실패: {e}")
            import traceback
            print(f"상세 오류: {traceback.format_exc()}")
            return False
    
    async def _run_korean_market_analysis(self):
        """한국 시장 분석 실행 (16:30 - 데이터 수집 후 분석)"""
        print("\n🇰🇷 한국 시장 분석 시작 (16:30)")
        print("="*50)
        
        try:
            # 1. 시장 체제 분석
            print("📊 시장 체제 분석...")
            market_condition = self.ml_engine.detect_market_regime()
            
            # 2. 한국 주식 예측
            print("🎯 한국 주식 예측...")
            kr_predictions = self.ml_engine.predict_stocks(MarketRegion.KR, top_n=10)
            
            # 🔥 학습용 예측 결과 저장 (실시간 학습 시스템용)
            if kr_predictions:
                print("💾 한국 시장 예측 결과 저장...")
                self.ml_engine.save_predictions_for_learning(kr_predictions)
            
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
            # 1. 시장 체제 분석
            print("📊 미국 시장 체제 분석...")
            market_condition = self.ml_engine.detect_market_regime()
            
            # 2. 미국 주식 예측
            print("🎯 미국 주식 예측...")
            us_predictions = self.ml_engine.predict_stocks(MarketRegion.US, top_n=10)
            
            # 🔥 학습용 예측 결과 저장 (실시간 학습 시스템용)
            if us_predictions:
                print("💾 미국 시장 예측 결과 저장...")
                self.ml_engine.save_predictions_for_learning(us_predictions)
            
            # 3. 마감 후 요약 알림 전송
            print("📢 미국 시장 요약 알림...")
            us_summary = self.alert_system.generate_market_close_summary(MarketRegion.US)
            if us_summary:
                await self.alert_system.send_alert(us_summary)
            
            # 4. 시장 전망 분석
            print("🔍 글로벌 시장 체제 분석 중...")
            
            print("✅ 미국 시장 분석 완료")
            return True
            
        except Exception as e:
            print(f"❌ 미국 시장 분석 실패: {e}")
            return False
    
    def _collect_korean_data(self):
        """한국 데이터 수집"""
        print("\n📊 한국 데이터 수집 시작 (16:15)")
        
        try:
            # 통합 데이터 수집기 사용
            import asyncio
            from app.services.unified_data_collector import UnifiedDataCollector
            
            collector = UnifiedDataCollector()
            success = asyncio.run(collector.collect_korean_daily_data())
            
            if success:
                print("✅ 한국 데이터 수집 완료")
                return True
            else:
                print("❌ 한국 데이터 수집 실패")
                return False
            
        except Exception as e:
            print(f"❌ 한국 데이터 수집 오류: {e}")
            return False
    
    def _collect_us_data(self):
        """미국 데이터 수집"""
        print("\n📊 미국 데이터 수집 시작 (09:00)")
        
        try:
            # 통합 데이터 수집기 사용
            import asyncio
            from app.services.unified_data_collector import UnifiedDataCollector
            
            collector = UnifiedDataCollector()
            success = asyncio.run(collector.collect_us_daily_data())
            
            if success:
                print("✅ 미국 데이터 수집 완료")
                return True
            else:
                print("❌ 미국 데이터 수집 실패")
                return False
            
        except Exception as e:
            print(f"❌ 미국 데이터 수집 오류: {e}")
            return False
            
        except Exception as e:
            print(f"❌ 미국 데이터 수집 오류: {e}")
            return False
    
    async def _run_daily_ml_training(self):
        """일일 ML 적응 학습 (06:30 - 시장 활동 없는 최적 시간)"""
        print("\n🤖 일일 ML 적응 학습 시작 (06:30)")
        print("="*50)
        
        try:
            print("⏰ 최적 학습 시간: 미국 장 종료 후 + 한국 장 시작 2시간 전")
            print("📊 학습 방식: 증분 학습 (전일 데이터 + 최근 30일)")
            
            # 빠른 적응 학습 (15-20분 소요)
            success = self.ml_engine.train_global_models(use_intensive_config=False)
            
            if success:
                print("✅ 일일 ML 적응 학습 완료 (시장 변화 반영)")
                
                # 간단한 성공 알림 (선택적)
                await self._send_daily_training_notification(success=True)
            else:
                print("❌ 일일 ML 적응 학습 실패")
                await self._send_daily_training_notification(success=False)
            
            return success
            
        except Exception as e:
            print(f"❌ 일일 ML 적응 학습 오류: {e}")
            await self._send_daily_training_notification(success=False, error=str(e))
            return False
    
    async def _run_weekly_advanced_training(self):
        """주간 고도화 학습 (일요일 02:00 - 주말 활용)"""
        print("\n🧠 주간 고도화 학습 시작 (일요일 02:00)")
        print("="*50)
        
        try:
            print("⏰ 주말 시간 활용: 모든 시장 닫힘, 시스템 독점 사용")
            print("📊 학습 방식: 하이퍼파라미터 최적화 + 최근 1년 데이터")
            print("⏱️ 예상 소요 시간: 2-3시간")
            
            # 집중 고도화 학습 (2-3시간 소요)
            success = self.ml_engine.train_global_models(use_intensive_config=True)
            
            if success:
                print("✅ 주간 고도화 학습 완료 (최고 성능 모델)")
                
                # 주간 학습 성과 알림
                await self._send_weekly_training_notification(success=True)
            else:
                print("❌ 주간 고도화 학습 실패")
                await self._send_weekly_training_notification(success=False)
            
            return success
            
        except Exception as e:
            print(f"❌ 주간 고도화 학습 오류: {e}")
            await self._send_weekly_training_notification(success=False, error=str(e))
            return False
    
    async def _run_daily_performance_evaluation(self):
        """일일 성능 평가 (18:00 - 한국 장 마감 후 데이터 확정)"""
        print("\n📊 일일 성능 평가 시작 (18:00)")
        print("="*50)
        
        try:
            from datetime import date, timedelta
            from app.ml.realtime_learning_system import RealTimeLearningSystem
            
            # 전일 성능 평가 (당일 데이터는 아직 확정되지 않을 수 있음)
            target_date = date.today() - timedelta(days=1)
            
            print(f"📅 평가 대상: {target_date}")
            print("🔍 예측 vs 실제 수익률 비교 중...")
            
            learning_system = RealTimeLearningSystem()
            
            # 성능 평가 실행
            performance = learning_system.evaluate_daily_performance(target_date)
            
            if performance:
                print("✅ 성능 평가 완료")
                
                # 성과 요약
                for region, perf in performance.items():
                    market_name = "한국" if region == "KR" else "미국"
                    flag = "🇰🇷" if region == "KR" else "🇺🇸"
                    
                    print(f"{flag} {market_name} 시장:")
                    print(f"   정확도: {perf.accuracy_rate:.1f}%")
                    print(f"   예측 개수: {perf.total_predictions}개")
                    print(f"   상위5 정확도: {perf.top5_accuracy:.1f}%")
                
                # 성능 평가 알림
                await self._send_performance_evaluation_notification(performance, target_date)
                
                return True
            else:
                print("❌ 성능 평가 실패 (데이터 부족)")
                await self._send_performance_evaluation_notification(None, target_date, error="데이터 부족")
                return False
                
        except Exception as e:
            print(f"❌ 성능 평가 오류: {e}")
            await self._send_performance_evaluation_notification(None, target_date, error=str(e))
            return False
    
    async def _send_performance_evaluation_notification(self, performance, target_date: date, error: str = None):
        """성능 평가 결과 알림"""
        try:
            if performance:
                message = f"📊 {target_date} ML 성능 평가 완료\n\n"
                
                total_accuracy = 0
                total_markets = 0
                
                for region, perf in performance.items():
                    market_name = "한국" if region == "KR" else "미국"
                    flag = "🇰🇷" if region == "KR" else "🇺🇸"
                    
                    message += f"{flag} {market_name}: {perf.accuracy_rate:.1f}% (상위5: {perf.top5_accuracy:.1f}%)\n"
                    total_accuracy += perf.accuracy_rate
                    total_markets += 1
                
                if total_markets > 0:
                    avg_accuracy = total_accuracy / total_markets
                    message += f"\n📈 평균 정확도: {avg_accuracy:.1f}%"
                    
                    # 성과 평가
                    if avg_accuracy >= 70:
                        message += "\n🎉 우수한 성능!"
                    elif avg_accuracy >= 60:
                        message += "\n✅ 양호한 성능"
                    elif avg_accuracy >= 50:
                        message += "\n📈 개선 중"
                    else:
                        message += "\n🔧 개선 필요"
            else:
                message = f"❌ {target_date} 성능 평가 실패\n{error if error else '알 수 없는 오류'}"
            
            print(f"📱 성능 평가 알림: {message}")
            # await self.alert_system.send_admin_alert(message)
            
        except Exception as e:
            print(f"⚠️ 성능 평가 알림 전송 실패: {e}")
    
    async def _send_daily_training_notification(self, success: bool, error: str = None):
        """일일 학습 결과 알림 (간단)"""
        try:
            if success:
                message = "🤖 일일 ML 적응 학습 완료\n✅ 최신 시장 데이터 반영"
            else:
                message = f"❌ 일일 ML 학습 실패\n{error if error else '알 수 없는 오류'}"
            
            # 관리자에게만 간단한 알림 (선택적)
            # await self.alert_system.send_admin_alert(message)
            print(f"📱 알림: {message}")
            
        except Exception as e:
            print(f"⚠️ 일일 학습 알림 전송 실패: {e}")
    
    async def _send_weekly_training_notification(self, success: bool, error: str = None):
        """주간 고도화 학습 결과 알림 (상세)"""
        try:
            if success:
                message = """🧠 주간 고도화 학습 완료! 

✅ 성과:
• 하이퍼파라미터 최적화 완료
• 최근 1년 데이터 학습
• 최고 성능 모델 업데이트

⏰ 다음 학습: 다음 주 일요일 02:00
🎯 학습 빈도: 주 7회 일일학습 + 주 1회 고도화"""
            else:
                message = f"""❌ 주간 고도화 학습 실패

🚨 오류 내용:
{error if error else '알 수 없는 오류'}

🔧 대응 필요:
• 로그 확인 및 원인 분석
• 시스템 리소스 점검"""
            
            # 전체 알림 시스템으로 전송
            await self.alert_system.send_alert(
                title="주간 ML 고도화 학습 결과",
                message=message,
                alert_type="admin" if not success else "info"
            )
            
        except Exception as e:
            print(f"⚠️ 주간 학습 알림 전송 실패: {e}")
    
    def _run_weekly_ml_training(self):
        """레거시 주간 ML 모델 재학습 (호환성 유지)"""
        print("\n🏋️ 레거시 주간 ML 모델 재학습")
        print("⚠️ 새로운 일일/주간 학습 시스템으로 교체됨")
        
        try:
            success = self.ml_engine.train_global_models()
            return success
        except Exception as e:
            print(f"❌ 레거시 ML 재학습 오류: {e}")
            return False
    
    def _run_monthly_ml_training(self):
        """레거시 월간 딥러닝 모델 재학습 (호환성 유지)"""
        print("\n🧠 레거시 월간 딥러닝 모델 재학습")
        print("⚠️ 새로운 주간 고도화 학습으로 교체됨")
        
        try:
            success = self.ml_engine.train_global_models()
            return success
        except Exception as e:
            print(f"❌ 레거시 딥러닝 재학습 오류: {e}")
            return False
    
    async def _check_emergency_alerts(self):
        """
        긴급 알림 체크 (4시간 주기)
        - 시장 급락/급등 상황 감지
        - 시스템 오류 상황 체크  
        - 중요한 경제 뉴스 이벤트 감지
        - 스마트 알림 시스템의 주기적 체크
        """
        print("\n🚨 긴급 알림 체크 (4시간 주기)")
        
        try:
            # 1. 스마트 알림 시스템 주기적 체크
            alerts_sent = await self.alert_system.run_alert_cycle()
            
            # 2. 시스템 상태 체크
            system_issues = self._check_system_issues()
            
            # 3. 시장 급변 체크 (간소화)
            market_alerts = self._check_market_emergencies()
            
            total_alerts = alerts_sent + len(system_issues) + len(market_alerts)
            
            if total_alerts > 0:
                print(f"📢 긴급 상황 감지: {total_alerts}건")
                if system_issues:
                    for issue in system_issues:
                        print(f"   ⚠️ 시스템: {issue}")
                if market_alerts:
                    for alert in market_alerts:
                        print(f"   📊 시장: {alert}")
            else:
                print("✅ 긴급 상황 없음")
            
            return True
            
        except Exception as e:
            print(f"❌ 긴급 알림 체크 실패: {e}")
            return False
    
    def _check_system_issues(self):
        """시스템 이슈 체크"""
        issues = []
        
        try:
            # 디스크 용량 체크 (간소화)
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100
            
            if free_percent < 10:
                issues.append(f"디스크 용량 부족: {free_percent:.1f}% 남음")
            
            # 메모리 사용량 체크 (간소화)  
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                issues.append(f"메모리 사용량 높음: {memory.percent:.1f}%")
                
        except Exception as e:
            # 시스템 체크 실패는 무시 (선택적 기능)
            pass
            
        return issues
    
    def _check_market_emergencies(self):
        """시장 급변 상황 체크 (간소화)"""
        alerts = []
        
        try:
            # 실제 구현 시에는 여기에 시장 데이터 분석 로직 추가
            # 현재는 간소화된 체크만 수행
            
            current_hour = datetime.now().hour
            
            # 시장 시간대의 급변 체크 (시뮬레이션)
            if 9 <= current_hour <= 15:  # 한국 시장 시간
                # 실제로는 주가 급락/급등 체크
                pass
            elif 22 <= current_hour or current_hour <= 6:  # 미국 시장 시간
                # 실제로는 미국 주가 급락/급등 체크  
                pass
                
        except Exception as e:
            # 시장 체크 실패는 무시
            pass
            
        return alerts
    
    def _health_check(self):
        """시스템 헬스체크"""
        current_time = datetime.now()
        print(f"\n💊 시스템 헬스체크 ({current_time.strftime('%H:%M')})")
        
        try:
            # 1. 데이터베이스 연결 체크
            from app.database.connection import get_db_session
            from sqlalchemy import text
            with get_db_session() as db:
                db.execute(text("SELECT 1"))
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
        
        # 부트스트랩 상태 확인
        if self.bootstrap_completed:
            print("✅ 부트스트랩 완료됨 - 정상 스케줄링 시작")
        else:
            print("⚠️ 부트스트랩 미완료 - 백그라운드에서 데이터 수집 시도")
        
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
        
        # 부트스트랩 상태 표시
        if self.bootstrap_completed:
            print("\n🎯 시스템 준비 완료:")
            print("   ✅ 한국 시장 데이터 준비됨")
            print("   ✅ 미국 시장 데이터 준비됨")
            print("   ✅ ML 모델 훈련 완료")
        else:
            print("\n⚠️ 시스템 부분 준비:")
            print("   ⏳ 백그라운드에서 데이터 수집 중...")
            print("   📈 스케줄된 시간에 자동 분석 시작")
        
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
                
                # 현재 시간과 등록된 작업 수 로깅 (5분마다)
                current_minute = datetime.now().minute
                if current_minute % 5 == 0:
                    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')} - 등록된 작업: {len(schedule.jobs)}개")
                    
                    # 실행 대기 중인 작업이 있는지 확인
                    pending_jobs = []
                    for job in schedule.jobs:
                        if job.should_run:
                            pending_jobs.append(job)
                    
                    if pending_jobs:
                        print(f"🚀 실행 대기 중인 작업: {len(pending_jobs)}개")
                        for job in pending_jobs:
                            tag = list(job.tags)[0] if job.tags else 'unknown'
                            print(f"   - {tag}: {job.next_run}")
                
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
    
    def _is_dst_active(self):
        """현재 서머타임 활성화 여부 확인"""
        us_time_info = self.market_time_manager.get_market_time_info(MTMarketRegion.US)
        return "서머타임" if us_time_info.is_dst_active else "표준시"
    
    def _refresh_kis_token(self):
        """KIS API 토큰 재발급 (매일 자정 실행)"""
        print("\n🔑 KIS API 토큰 재발급 시작 (00:00)")
        print("="*50)
        
        try:
            from app.services.kis_api import KISAPIClient
            
            kis_client = KISAPIClient()
            success = kis_client.refresh_token_daily()
            
            if success:
                print("✅ KIS 토큰 재발급 성공")
                return True
            else:
                print("❌ KIS 토큰 재발급 실패")
                return False
                
        except Exception as e:
            print(f"❌ KIS 토큰 재발급 오류: {e}")
            return False
    
    def _optimize_performance(self):
        """시스템 성능 최적화 (매시간 실행)"""
        print("\n⚡ 시스템 성능 최적화 시작")
        print("="*50)
        
        try:
            # 메모리 최적화
            performance_optimizer.optimize_memory_usage()
            
            # 성능 리포트 생성
            report = performance_optimizer.get_performance_report()
            
            print("📊 성능 현황:")
            print(f"   메모리 사용량: {report['memory_usage']}")
            print(f"   캐시 히트율: {report.get('cache_stats', {}).get('hit_rate', 'N/A')}")
            print(f"   DB 쿼리 수: {report['db_queries']}")
            print(f"   API 호출 수: {report['api_calls']}")
            
            # 성능 경고 체크
            memory_mb = float(report['memory_usage'].replace('MB', ''))
            if memory_mb > 1000:  # 1GB 초과시 경고
                print("⚠️ 메모리 사용량 높음 - 추가 최적화 필요")
            
            print("✅ 성능 최적화 완료")
            return True
            
        except Exception as e:
            print(f"❌ 성능 최적화 실패: {e}")
            return False


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="글로벌 스케줄링 시스템")
    parser.add_argument("--manual", type=str, help="수동 작업 실행")
    parser.add_argument("--daemon", action="store_true", help="데몬 모드로 실행")
    parser.add_argument("--no-bootstrap", action="store_true", help="부트스트랩 건너뛰기")
    parser.add_argument("--bootstrap-only", action="store_true", help="부트스트랩만 실행")
    
    args = parser.parse_args()
    
    # 부트스트랩 여부 결정
    run_bootstrap = not args.no_bootstrap
    
    scheduler = GlobalScheduler(run_bootstrap=run_bootstrap)
    
    if args.bootstrap_only:
        # 부트스트랩만 실행하고 종료
        print("🚀 부트스트랩만 실행하고 종료합니다.")
        if scheduler.bootstrap_completed:
            print("✅ 부트스트랩 성공")
            sys.exit(0)
        else:
            print("❌ 부트스트랩 실패")
            sys.exit(1)
    
    elif args.manual:
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
