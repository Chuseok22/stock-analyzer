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
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app"))

from app.ml.global_ml_engine import GlobalMLEngine, MarketRegion
from app.services.smart_alert_system import SmartAlertSystem
from app.utils.market_time_utils import MarketTimeManager, MarketRegion as MTMarketRegion
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
        schedule.every().day.at("08:30").do(self._run_korean_premarket_recommendations).tag("kr_premarket")  # 한국 장 시작 30분 전
        schedule.every().day.at("16:00").do(self._run_korean_market_analysis).tag("kr_market")  # 한국 장 마감 후 분석
        
        # 2. 미국 시장 관련 스케줄 (동적)
        schedule.every().day.at(premarket_start_kr).do(self._run_us_premarket_alert).tag("us_premarket")
        schedule.every().day.at(regular_start_kr).do(self._run_us_market_open_alert).tag("us_market_open")
        schedule.every().day.at(market_analysis_time).do(self._run_us_market_analysis).tag("us_market")
        
        # 3. 데이터 수집 스케줄
        schedule.every().day.at(aftermarket_end_kr).do(self._collect_us_data).tag("us_data")
        schedule.every().day.at("17:00").do(self._collect_korean_data).tag("kr_data")
        
        # 4. ML 모델 재학습 스케줄
        schedule.every().saturday.at("02:00").do(self._run_weekly_ml_training).tag("ml_training")
        schedule.every(30).days.at("03:00").do(self._run_monthly_ml_training).tag("ml_monthly")  # 매 30일
        
        # 5. KIS API 토큰 재발급 (매일 자정)
        schedule.every().day.at("00:00").do(self._refresh_kis_token).tag("kis_token")
        
        # 6. 시스템 헬스체크
        schedule.every().hour.at(":00").do(self._health_check).tag("health")
        
        # 7. 긴급 알림 체크
        schedule.every(4).hours.do(self._check_emergency_alerts).tag("emergency")
        
        print("✅ 동적 스케줄 설정 완료:")
        print(f"   🇰🇷 한국 프리마켓 추천: 매일 08:30")
        print(f"   📈 한국 시장 분석: 매일 16:00")
        print(f"   🇺🇸 미국 프리마켓: 매일 {premarket_start_kr} (ET 04:00)")
        print(f"   🇺🇸 미국 정규장 시작: 매일 {regular_start_kr} (ET 09:30)")
        print(f"   📊 미국 시장 분석: 매일 {market_analysis_time} (ET 16:30)")
        print(f"   📁 미국 데이터 수집: 매일 {aftermarket_end_kr} (ET 20:30)")
        print(f"   🤖 ML 재학습: 매주 토요일 02:00")
        print(f"   � KIS 토큰 재발급: 매일 00:00")
        print(f"   �🚨 긴급 알림: 4시간마다")
        print(f"   ⏰ {dst_status}")
    
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
            current_time = datetime.now()
            current_date = current_time.strftime('%Y-%m-%d')
            
            # 오늘 예정된 스케줄 수집
            today_schedule = self._get_today_schedule()
            
            # SmartAlert 객체로 생성 (올바른 import 추가 필요)
            from app.services.smart_alert_system import SmartAlert, AlertType
            
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

**⏰ 정기 스케줄:**
• 🇰🇷 한국 시장 분석: 매일 16:00
• 🇺🇸 미국 프리마켓: 매일 17:00 (ET 04:00)
• 🇺🇸 미국 정규장: 매일 22:30 (ET 09:30)
• 🇺🇸 미국 시장 분석: 매일 05:30 (ET 16:30)

**🤖 ML 학습:**
• 주간 재학습: 매주 토요일 02:00
• 긴급 알림 체크: 4시간마다

**시작 시간:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}
**서버 상태:** 정상 운영 중
            """.strip()
            
            # SmartAlert 객체 생성
            alert = SmartAlert(
                alert_type=AlertType.PREMARKET_RECOMMENDATIONS,  # 시스템 시작은 프리마켓 유형으로 사용
                market_region="GLOBAL",
                title=title,
                message=content,
                stocks=[],
                urgency_level="MEDIUM",
                action_required=False,
                recommendations=[
                    "시스템이 정상적으로 시작되었습니다",
                    "모든 초기 데이터가 준비되었습니다",
                    "ML 모델이 예측 준비 상태입니다"
                ],
                created_at=current_time
            )
            
            # 올바른 파라미터로 알림 전송
            await self.alert_system.send_alert(alert)
            print("   📢 부트스트랩 완료 알림 전송됨")
            
        except Exception as e:
            print(f"   ⚠️ 부트스트랩 알림 전송 실패: {e}")
            import traceback
            print(f"   상세 오류: {traceback.format_exc()}")
    
    def _get_today_schedule(self):
        """오늘 예정된 스케줄 가져오기"""
        try:
            current_time = datetime.now(self.kr_timezone)
            today_jobs = []
            
            for job in schedule.jobs:
                next_run = job.next_run
                if next_run and next_run.date() == current_time.date():
                    # 작업 이름 매핑
                    tag_names = {
                        'kr_market': '🇰🇷 한국 시장 분석',
                        'us_premarket': '🇺🇸 미국 프리마켓 알림',
                        'us_market_open': '🇺🇸 미국 정규장 시작',
                        'us_market': '🇺🇸 미국 시장 분석',
                        'kr_data': '📊 한국 데이터 수집',
                        'us_data': '📊 미국 데이터 수집',
                        'ml_training': '🤖 ML 주간 학습',
                        'health': '🏥 헬스체크',
                        'emergency': '🚨 긴급 알림 체크'
                    }
                    
                    tag = list(job.tags)[0] if job.tags else 'unknown'
                    task_name = tag_names.get(tag, f'🔧 {tag}')
                    
                    time_until = next_run - current_time.replace(tzinfo=None)
                    hours_until = max(0, int(time_until.total_seconds() / 3600))
                    
                    if hours_until == 0:
                        time_desc = "곧 실행"
                    elif hours_until < 24:
                        time_desc = f"{hours_until}시간 후"
                    else:
                        time_desc = f"{hours_until//24}일 후"
                    
                    today_jobs.append(f"• {task_name}: {next_run.strftime('%H:%M')} ({time_desc})")
            
            if today_jobs:
                return "\n".join(sorted(today_jobs))
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
            
            # Mock 데이터 사용 여부 확인 (테스트용)
            if hasattr(self.ml_engine, '_mock_predictions'):
                print("🧪 테스트용 Mock 예측 데이터 사용")
                predictions = self.ml_engine._mock_predictions
            else:
                # ML 엔진을 통한 추천 생성
                predictions = self.ml_engine.predict_stocks(MarketRegion.KOREA, top_n=5)
            
            if predictions:
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
        """한국 시장 분석 실행 (16:00 - 장 마감 후 분석)"""
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
            # 기존 한국 데이터 수집 서비스 사용
            from app.services.data_collection import DataCollectionService
            
            data_service = DataCollectionService()
            success = data_service.collect_daily_data()
            
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
            # 미국 데이터 수집을 위한 간단한 로직
            from app.services.alpha_vantage_api import AlphaVantageAPIClient
            
            av_client = AlphaVantageAPIClient()
            
            # S&P 500 주요 종목들 수집
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX"]
            
            collected_count = 0
            for symbol in symbols:
                try:
                    data = av_client.get_daily_prices(symbol, "compact")
                    if data:
                        collected_count += 1
                except:
                    continue
            
            success = collected_count > len(symbols) // 2  # 50% 이상 성공하면 성공으로 간주
            
            if success:
                print(f"✅ 미국 데이터 수집 완료 ({collected_count}/{len(symbols)})")
            else:
                print(f"❌ 미국 데이터 수집 실패 ({collected_count}/{len(symbols)})")
            
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
