#!/usr/bin/env python3
"""
글로벌 스케줄링 시스템 v2.0
정확한 시장 시간대 기반 자동화

한국 시장:
- 08:30: 정규장 시작 30분 전 알림
- 16:00: 장 마감 후 데이터 수집 및 ML 분석

미국 시장 (서머타임 자동 감지):
- 프리마켓 30분 전: 16:30(DST) / 17:30(STD)
- 정규장 30분 전: 22:00(DST) / 23:00(STD)  
- 마감 후 분석: 05:30(DST) / 06:30(STD)

주간 분석:
- 토요일 12:00: 주간 종합 분석 및 리포트
"""
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, Tuple
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


class EnhancedGlobalScheduler:
    """향상된 글로벌 스케줄링 시스템"""
    
    def __init__(self):
        self.ml_engine = GlobalMLEngine()
        self.alert_system = SmartAlertSystem()
        
        # 시간대 설정
        self.kr_timezone = pytz.timezone('Asia/Seoul')
        self.us_timezone = pytz.timezone('America/New_York')
        
        # 실행 상태 추적
        self.is_running = False
        self.last_ml_training = None
        
        print("🌍 향상된 글로벌 스케줄링 시스템 초기화")
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
    
    def is_dst_active(self, date: datetime = None) -> bool:
        """미국 서머타임 적용 여부 확인"""
        if date is None:
            date = datetime.now(self.us_timezone)
        
        # 미국 동부시간 기준으로 서머타임 확인
        us_time = date.astimezone(self.us_timezone)
        return bool(us_time.dst())
    
    def get_us_market_times(self) -> Dict[str, str]:
        """현재 서머타임 적용 여부에 따른 미국 시장 시간 반환 (KST 기준)"""
        is_dst = self.is_dst_active()
        
        if is_dst:  # 서머타임 적용
            return {
                "premarket_alert": "16:30",    # 프리마켓 17:00 시작 30분 전
                "regular_alert": "22:00",      # 정규장 22:30 시작 30분 전
                "market_close_analysis": "05:30"  # 정규장 05:00 마감 30분 후
            }
        else:  # 표준시 적용
            return {
                "premarket_alert": "17:30",    # 프리마켓 18:00 시작 30분 전
                "regular_alert": "23:00",      # 정규장 23:30 시작 30분 전
                "market_close_analysis": "06:30"  # 정규장 06:00 마감 30분 후
            }
    
    def _setup_dynamic_schedules(self):
        """동적 스케줄 설정 (서머타임 자동 감지)"""
        print("⏰ 동적 글로벌 스케줄 설정 중...")
        
        # 기존 스케줄 초기화
        schedule.clear()
        
        # 1. 한국 시장 스케줄 (고정)
        schedule.every().day.at("08:30").do(self._run_korean_premarket_alert).tag("kr_premarket")
        schedule.every().day.at("16:00").do(self._run_korean_market_analysis).tag("kr_analysis")
        
        # 2. 미국 시장 스케줄 (서머타임 기반 동적 설정)
        us_times = self.get_us_market_times()
        
        schedule.every().day.at(us_times["premarket_alert"]).do(
            self._run_us_premarket_alert
        ).tag("us_premarket")
        
        schedule.every().day.at(us_times["regular_alert"]).do(
            self._run_us_regular_alert
        ).tag("us_regular")
        
        schedule.every().day.at(us_times["market_close_analysis"]).do(
            self._run_us_market_analysis
        ).tag("us_analysis")
        
        # 3. 데이터 수집 스케줄
        schedule.every().day.at("16:30").do(self._collect_korean_data).tag("kr_data")
        schedule.every().day.at("07:00").do(self._collect_us_data).tag("us_data")
        
        # 4. 주간 종합 분석 (토요일 정오)
        schedule.every().saturday.at("12:00").do(self._run_weekly_analysis).tag("weekly_analysis")
        
        # 5. 시스템 헬스체크
        schedule.every().hour.at(":00").do(self._health_check).tag("health")
        
        # 6. 스케줄 업데이트 (매일 자정에 서머타임 변경 체크)
        schedule.every().day.at("00:00").do(self._update_schedules).tag("schedule_update")
        
        dst_status = "서머타임" if self.is_dst_active() else "표준시"
        print(f"✅ 스케줄 설정 완료 ({dst_status} 적용):")
        print("   🇰🇷 한국 프리마켓 알림: 08:30")
        print("   🇰🇷 한국 마감 분석: 16:00")
        print(f"   🇺🇸 미국 프리마켓 알림: {us_times['premarket_alert']}")
        print(f"   🇺🇸 미국 정규장 알림: {us_times['regular_alert']}")
        print(f"   🇺🇸 미국 마감 분석: {us_times['market_close_analysis']}")
        print("   📊 주간 종합 분석: 토요일 12:00")
    
    def _update_schedules(self):
        """스케줄 업데이트 (서머타임 변경 감지)"""
        print("🔄 스케줄 업데이트 체크...")
        
        current_us_times = self.get_us_market_times()
        
        # 기존 미국 시장 스케줄 제거
        schedule.clear("us_premarket")
        schedule.clear("us_regular") 
        schedule.clear("us_analysis")
        
        # 새로운 미국 시장 스케줄 추가
        schedule.every().day.at(current_us_times["premarket_alert"]).do(
            self._run_us_premarket_alert
        ).tag("us_premarket")
        
        schedule.every().day.at(current_us_times["regular_alert"]).do(
            self._run_us_regular_alert
        ).tag("us_regular")
        
        schedule.every().day.at(current_us_times["market_close_analysis"]).do(
            self._run_us_market_analysis
        ).tag("us_analysis")
        
        dst_status = "서머타임" if self.is_dst_active() else "표준시"
        print(f"✅ 스케줄 업데이트 완료 ({dst_status})")
    
    async def _run_korean_premarket_alert(self):
        """한국 정규장 시작 30분 전 알림"""
        print("\n🇰🇷 한국 정규장 시작 30분 전 알림 (08:30)")
        print("="*50)
        
        try:
            # 한국 주식 예측
            kr_predictions = self.ml_engine.predict_stocks(MarketRegion.KR, top_n=5)
            
            if not kr_predictions:
                print("   ⚠️ 한국 예측 데이터 없음")
                return False
            
            # 프리마켓 스타일 알림 생성
            alert = self._generate_korean_premarket_alert(kr_predictions)
            if alert:
                await self.alert_system.send_alert(alert)
            
            print("✅ 한국 프리마켓 알림 완료")
            return True
            
        except Exception as e:
            print(f"❌ 한국 프리마켓 알림 실패: {e}")
            return False
    
    async def _run_us_premarket_alert(self):
        """미국 프리마켓 시작 30분 전 알림"""
        us_times = self.get_us_market_times()
        dst_status = "서머타임" if self.is_dst_active() else "표준시"
        
        print(f"\n🇺🇸 미국 프리마켓 알림 ({us_times['premarket_alert']}, {dst_status})")
        print("="*50)
        
        try:
            # 기존 프리마켓 알림 로직 사용
            premarket_alert = self.alert_system.generate_premarket_alert()
            if premarket_alert:
                # 알림 제목에 프리마켓 표시 추가
                premarket_alert.title = f"🌅 미국 프리마켓 추천 ({dst_status})"
                success = await self.alert_system.send_alert(premarket_alert)
                if success:
                    print("✅ 미국 프리마켓 알림 전송 완료")
                else:
                    print("❌ 미국 프리마켓 알림 전송 실패")
            else:
                print("⚠️ 미국 프리마켓 알림 생성 실패")
            
            return True
            
        except Exception as e:
            print(f"❌ 미국 프리마켓 알림 실패: {e}")
            return False
    
    async def _run_us_regular_alert(self):
        """미국 정규장 시작 30분 전 알림"""
        us_times = self.get_us_market_times()
        dst_status = "서머타임" if self.is_dst_active() else "표준시"
        
        print(f"\n🇺🇸 미국 정규장 시작 30분 전 알림 ({us_times['regular_alert']}, {dst_status})")
        print("="*50)
        
        try:
            # 미국 주식 예측
            us_predictions = self.ml_engine.predict_stocks(MarketRegion.US, top_n=5)
            
            if not us_predictions:
                print("   ⚠️ 미국 예측 데이터 없음")
                return False
            
            # 정규장 알림 생성
            alert = self._generate_us_regular_alert(us_predictions, dst_status)
            if alert:
                await self.alert_system.send_alert(alert)
            
            print("✅ 미국 정규장 알림 완료")
            return True
            
        except Exception as e:
            print(f"❌ 미국 정규장 알림 실패: {e}")
            return False
    
    async def _run_korean_market_analysis(self):
        """한국 시장 마감 후 분석"""
        print("\n🇰🇷 한국 시장 마감 후 분석 (16:00)")
        print("="*50)
        
        try:
            # 시장 체제 분석
            market_condition = self.ml_engine.detect_market_regime()
            
            # 한국 주식 예측
            kr_predictions = self.ml_engine.predict_stocks(MarketRegion.KR, top_n=10)
            
            # 마감 후 요약 알림
            kr_summary = self.alert_system.generate_market_close_summary(MarketRegion.KR)
            if kr_summary:
                await self.alert_system.send_alert(kr_summary)
            
            # 하락장 경고 체크
            bear_warning = self.alert_system.generate_bear_market_warning()
            if bear_warning:
                await self.alert_system.send_alert(bear_warning)
            
            # ML 모델 재학습 (한국 데이터 기반)
            print("🤖 한국 ML 모델 업데이트...")
            self.ml_engine.train_global_models()
            
            # 실시간 학습 실행 (예측 vs 실제 성과 분석)
            print("🧠 한국 시장 실시간 학습 시작...")
            try:
                from app.ml.realtime_learning_system import RealTimeLearningSystem
                learning_system = RealTimeLearningSystem()
                
                # 당일 예측 결과 저장 (다음날 비교용)
                if kr_predictions:
                    learning_system.save_daily_predictions(kr_predictions)
                
                # 전일 성과 평가 및 학습 (하루 뒤 실행)
                from datetime import date, timedelta
                yesterday = date.today() - timedelta(days=1)
                learning_system.run_daily_learning_cycle(yesterday)
                
                print("✅ 한국 실시간 학습 완료")
            except Exception as learning_error:
                print(f"⚠️ 한국 실시간 학습 실패: {learning_error}")
            
            print("✅ 한국 시장 분석 완료")
            return True
            
        except Exception as e:
            print(f"❌ 한국 시장 분석 실패: {e}")
            return False
    
    async def _run_us_market_analysis(self):
        """미국 시장 마감 후 분석"""
        us_times = self.get_us_market_times()
        dst_status = "서머타임" if self.is_dst_active() else "표준시"
        
        print(f"\n🇺🇸 미국 시장 마감 후 분석 ({us_times['market_close_analysis']}, {dst_status})")
        print("="*50)
        
        try:
            # 미국 시장 마감 후 요약
            us_summary = self.alert_system.generate_market_close_summary(MarketRegion.US)
            if us_summary:
                us_summary.title = f"🇺🇸 미국 시장 마감 분석 ({dst_status})"
                await self.alert_system.send_alert(us_summary)
            
            # ML 모델 재학습 (미국 데이터 기반)
            print("🤖 미국 ML 모델 업데이트...")
            self.ml_engine.train_global_models()
            
            # 실시간 학습 실행 (예측 vs 실제 성과 분석)
            print("🧠 미국 시장 실시간 학습 시작...")
            try:
                from app.ml.realtime_learning_system import RealTimeLearningSystem
                learning_system = RealTimeLearningSystem()
                
                # 전일 성과 평가 및 학습
                from datetime import date, timedelta
                yesterday = date.today() - timedelta(days=1)
                learning_system.run_daily_learning_cycle(yesterday)
                
                print("✅ 미국 실시간 학습 완료")
            except Exception as learning_error:
                print(f"⚠️ 미국 실시간 학습 실패: {learning_error}")
            
            print("✅ 미국 시장 분석 완료")
            return True
            
        except Exception as e:
            print(f"❌ 미국 시장 분석 실패: {e}")
            return False
    
    def _collect_korean_data(self):
        """한국 데이터 수집 (16:30)"""
        print("\n📊 한국 데이터 수집 시작 (16:30)")
        
        try:
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
        """미국 데이터 수집 (07:00)"""
        print("\n📊 미국 데이터 수집 시작 (07:00)")
        
        try:
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
    
    def _run_weekly_analysis(self):
        """주간 종합 분석 및 리포트 (토요일 12:00)"""
        print("\n📈 주간 종합 분석 및 리포트 시작 (토요일 12:00)")
        print("="*60)
        
        try:
            # 1. 실시간 학습 주간 성능 리포트 생성
            print("📊 주간 ML 성능 리포트 생성...")
            try:
                from app.ml.realtime_learning_system import RealTimeLearningSystem
                from datetime import date, timedelta
                
                learning_system = RealTimeLearningSystem()
                today = date.today()
                weekly_report = learning_system.generate_performance_report(today, days=7)
                
                # 성능 리포트 Discord 전송
                if weekly_report:
                    from app.services.smart_alert_system import AlertMessage
                    
                    # 배포 환경에서는 더 상세한 리포트
                    is_production = Path("/volume1/project/stock-analyzer").exists()
                    report_title = "📈 주간 ML 성능 리포트" + (" (배포환경)" if is_production else " (개발환경)")
                    
                    performance_alert = AlertMessage(
                        title=report_title,
                        description=weekly_report[:1800] + "\n\n*전체 리포트는 서버에 저장됨*" if len(weekly_report) > 1800 else weekly_report,
                        market_region="GLOBAL",
                        alert_type="PERFORMANCE_REPORT",
                        importance="HIGH"
                    )
                    asyncio.run(self.alert_system.send_alert(performance_alert))
                    
                print("✅ 주간 성능 리포트 완료")
                
            except Exception as perf_error:
                print(f"⚠️ 성능 리포트 생성 실패: {perf_error}")
            
            # 2. 주간 ML 모델 재학습
            print("🏋️ 주간 ML 모델 재학습...")
            ml_success = self.ml_engine.train_global_models()
            
            # 3. 주간 시장 동향 분석
            print("📊 주간 시장 동향 분석...")
            weekly_market_report = self._generate_weekly_market_report()
            
            # 4. 종합 주간 리포트 전송
            if weekly_market_report:
                print("📧 주간 시장 리포트 전송...")
                market_alert = AlertMessage(
                    title="� 주간 시장 동향 분석",
                    description=weekly_market_report,
                    market_region="GLOBAL",
                    alert_type="WEEKLY_ANALYSIS",
                    importance="MEDIUM"
                )
                asyncio.run(self.alert_system.send_alert(market_alert))
            
            self.last_ml_training = datetime.now()
            print("✅ 주간 종합 분석 완료")
            return True
            
        except Exception as e:
            print(f"❌ 주간 분석 실패: {e}")
            return False
    
    def _generate_weekly_market_report(self) -> Optional[str]:
        """주간 시장 분석 리포트 생성"""
        try:
            # 주간 시장 동향, 글로벌 경제 지표 등
            report = "📊 **주간 시장 동향 분석**\n\n"
            report += "🔍 **분석 기간**: 지난 7일\n"
            report += "📈 **주요 동향**: 시장 체제 분석 및 트렌드 요약\n"
            report += "🎯 **다음 주 전망**: ML 모델 기반 예측\n"
            report += "⚠️ **리스크 요인**: 글로벌 경제 이슈 모니터링\n"
            
            return report
        except Exception:
            return None
    
    def _generate_korean_premarket_alert(self, predictions) -> Optional[Any]:
        """한국 프리마켓 알림 생성"""
        from app.services.smart_alert_system import SmartAlert, AlertType
        
        try:
            title = "🇰🇷 한국 시장 개장 30분 전 추천"
            
            message = "🌅 **한국 시장 개장 임박!**\n\n"
            message += "🎯 **오늘의 추천 종목**\n"
            
            for i, pred in enumerate(predictions[:5], 1):
                rec_emoji = {"STRONG_BUY": "🚀", "BUY": "📈", "HOLD": "⏸️"}.get(pred.recommendation, "📊")
                message += f"{i}. {rec_emoji} **{pred.stock_code}** "
                message += f"예상: **{pred.predicted_return:+.1f}%**\n"
            
            message += "\n🎯 **투자 준비사항**\n"
            message += "• 📊 시장 상황을 체크하세요\n"
            message += "• 💰 진입 계획을 확인하세요\n"
            message += "• 🛡️ 손절가를 설정하세요"
            
            return SmartAlert(
                alert_type=AlertType.PREMARKET_RECOMMENDATIONS,
                market_region="KR",
                title=title,
                message=message,
                stocks=[],
                urgency_level="MEDIUM",
                action_required=True,
                recommendations=[],
                created_at=datetime.now()
            )
            
        except Exception as e:
            print(f"한국 프리마켓 알림 생성 실패: {e}")
            return None
    
    def _generate_us_regular_alert(self, predictions, dst_status) -> Optional[Any]:
        """미국 정규장 알림 생성"""
        from app.services.smart_alert_system import SmartAlert, AlertType
        
        try:
            title = f"🇺🇸 미국 정규장 개장 30분 전 ({dst_status})"
            
            message = f"🌃 **미국 정규장 개장 임박! ({dst_status})**\n\n"
            message += "🎯 **정규장 추천 종목**\n"
            
            for i, pred in enumerate(predictions[:5], 1):
                rec_emoji = {"STRONG_BUY": "🚀", "BUY": "📈", "HOLD": "⏸️"}.get(pred.recommendation, "📊")
                message += f"{i}. {rec_emoji} **{pred.stock_code}** "
                message += f"예상: **{pred.predicted_return:+.1f}%**\n"
            
            message += "\n🎯 **정규장 전략**\n"
            message += "• 📈 프리마켓 동향을 반영하세요\n"
            message += "• 🎯 정규장 진입 타이밍을 잡으세요\n"
            message += "• 📊 거래량 증가를 주시하세요"
            
            return SmartAlert(
                alert_type=AlertType.PREMARKET_RECOMMENDATIONS,
                market_region="US",
                title=title,
                message=message,
                stocks=[],
                urgency_level="HIGH",
                action_required=True,
                recommendations=[],
                created_at=datetime.now()
            )
            
        except Exception as e:
            print(f"미국 정규장 알림 생성 실패: {e}")
            return None
    
    def _health_check(self):
        """시스템 헬스체크"""
        current_time = datetime.now()
        print(f"\n💊 시스템 헬스체크 ({current_time.strftime('%H:%M')})")
        
        try:
            # 서머타임 상태 체크
            dst_status = "서머타임" if self.is_dst_active() else "표준시"
            print(f"   🕐 시간대 상태: {dst_status}")
            
            # 데이터베이스 연결 체크
            from app.database.connection import get_db_session
            from sqlalchemy import text
            with get_db_session() as db:
                db.execute(text("SELECT 1"))
            print("   ✅ 데이터베이스: 정상")
            
            # Redis 연결 체크
            from app.database.redis_client import redis_client
            redis_client.ping()
            print("   ✅ Redis: 정상")
            
            # 스케줄 상태 체크
            us_times = self.get_us_market_times()
            print(f"   📅 다음 미국 알림: {us_times['premarket_alert']}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 헬스체크 실패: {e}")
            return False
    
    def run_scheduler(self):
        """스케줄러 실행"""
        print("🚀 향상된 글로벌 스케줄러 시작")
        print("="*60)
        
        self.is_running = True
        
        # 초기 헬스체크
        self._health_check()
        
        print("\n⏰ 현재 스케줄:")
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
        
        print("✅ 향상된 글로벌 스케줄러 종료")
    
    def run_manual_task(self, task_name: str):
        """수동 작업 실행"""
        print(f"🔧 수동 작업 실행: {task_name}")
        
        tasks = {
            "korean_premarket": self._run_korean_premarket_alert,
            "korean_analysis": self._run_korean_market_analysis,
            "us_premarket": self._run_us_premarket_alert,
            "us_regular": self._run_us_regular_alert,
            "us_analysis": self._run_us_market_analysis,
            "korean_data": self._collect_korean_data,
            "us_data": self._collect_us_data,
            "weekly_analysis": self._run_weekly_analysis,
            "health_check": self._health_check,
            "update_schedules": self._update_schedules
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
    
    parser = argparse.ArgumentParser(description="향상된 글로벌 스케줄링 시스템")
    parser.add_argument("--manual", type=str, help="수동 작업 실행")
    parser.add_argument("--daemon", action="store_true", help="데몬 모드로 실행")
    parser.add_argument("--check-dst", action="store_true", help="서머타임 상태 확인")
    
    args = parser.parse_args()
    
    scheduler = EnhancedGlobalScheduler()
    
    if args.check_dst:
        # 서머타임 상태 확인
        dst_status = "서머타임" if scheduler.is_dst_active() else "표준시"
        us_times = scheduler.get_us_market_times()
        print(f"🕐 현재 시간대: {dst_status}")
        print(f"📅 미국 시장 시간 (KST):")
        print(f"   프리마켓 알림: {us_times['premarket_alert']}")
        print(f"   정규장 알림: {us_times['regular_alert']}")
        print(f"   마감 후 분석: {us_times['market_close_analysis']}")
        return
    
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
