"""
Scheduling service for automated stock analysis and recommendations.
"""
import schedule
import time
from datetime import datetime, date, timedelta
from typing import Optional
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

from app.services.data_collection import DataCollectionService
from app.services.recommendation import RecommendationService
from app.services.notification import NotificationService
from app.config.settings import settings

logger = logging.getLogger(__name__)


class SchedulingService:
    """Service for scheduling automated stock analysis tasks."""
    
    def __init__(self):
        self.data_service = DataCollectionService()
        self.recommendation_service = RecommendationService()
        self.notification_service = NotificationService()
        self.scheduler = BackgroundScheduler()
        self.universe_id = settings.default_universe_id or 1
        
        # Configure scheduler
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown())
        
        logger.info("Scheduling service initialized")
    
    def setup_schedules(self):
        """Setup all scheduled tasks."""
        try:
            # Daily data collection and recommendations (평일 오후 4시 - 장 마감 후)
            self.scheduler.add_job(
                func=self.daily_recommendation_task,
                trigger=CronTrigger(
                    day_of_week='mon-fri',  # 월-금
                    hour=16,  # 오후 4시
                    minute=0
                ),
                id='daily_recommendations',
                replace_existing=True,
                misfire_grace_time=1800  # 30분 grace time
            )
            
            # Morning notification (평일 오전 8시 30분 - 장 시작 전)
            self.scheduler.add_job(
                func=self.morning_notification_task,
                trigger=CronTrigger(
                    day_of_week='mon-fri',  # 월-금
                    hour=8,  # 오전 8시
                    minute=30
                ),
                id='morning_notifications',
                replace_existing=True,
                misfire_grace_time=900  # 15분 grace time
            )
            
            # Weekly model retraining (토요일 오전 2시)
            self.scheduler.add_job(
                func=self.weekly_retrain_task,
                trigger=CronTrigger(
                    day_of_week='sat',  # 토요일
                    hour=2,  # 오전 2시
                    minute=0
                ),
                id='weekly_retrain',
                replace_existing=True,
                misfire_grace_time=3600  # 1시간 grace time
            )
            
            # Monthly universe update (매월 첫째 일요일 오전 1시)
            self.scheduler.add_job(
                func=self.monthly_universe_update_task,
                trigger=CronTrigger(
                    day_of_week='sun',  # 일요일
                    hour=1,  # 오전 1시
                    minute=0,
                    day='1-7'  # 매월 1-7일 중 일요일
                ),
                id='monthly_universe_update',
                replace_existing=True,
                misfire_grace_time=7200  # 2시간 grace time
            )
            
            # Weekly performance report (일요일 오후 6시)
            self.scheduler.add_job(
                func=self.weekly_performance_report_task,
                trigger=CronTrigger(
                    day_of_week='sun',  # 일요일
                    hour=18,  # 오후 6시
                    minute=0
                ),
                id='weekly_performance_report',
                replace_existing=True,
                misfire_grace_time=1800  # 30분 grace time
            )
            
            logger.info("All scheduled tasks configured successfully")
            self._log_scheduled_jobs()
            
        except Exception as e:
            logger.error(f"Failed to setup schedules: {e}")
            raise
    
    def daily_recommendation_task(self):
        """Daily task: collect data and generate recommendations."""
        logger.info("Starting daily recommendation task")
        
        try:
            # Skip if weekend
            if datetime.now().weekday() >= 5:  # Saturday=5, Sunday=6
                logger.info("Skipping daily task - weekend")
                return
            
            # 1. Update stock data for universe
            logger.info("Step 1: Collecting recent stock data")
            
            # Get stocks in current universe
            with self.data_service.get_db_session() as db:
                from app.models.entities import UniverseItem, Stock
                
                universe_stocks = db.query(UniverseItem).filter(
                    UniverseItem.universe_id == self.universe_id
                ).all()
                
                stock_codes = []
                for item in universe_stocks:
                    stock = db.query(Stock).filter(Stock.id == item.stock_id).first()
                    if stock and stock.active:
                        stock_codes.append(stock.code)
            
            if not stock_codes:
                logger.error("No stocks found in universe")
                return
            
            # Collect recent data (last 5 days)
            success = self.data_service.collect_stock_prices(stock_codes, days=5)
            
            if success:
                # Calculate technical indicators
                self.data_service.calculate_technical_indicators()
                logger.info("Data collection completed successfully")
            else:
                logger.error("Data collection failed")
                return
            
            # 2. Generate recommendations for tomorrow
            logger.info("Step 2: Generating recommendations")
            
            tomorrow = date.today() + timedelta(days=1)
            
            # Skip weekend
            while tomorrow.weekday() >= 5:
                tomorrow += timedelta(days=1)
            
            recommendations = self.recommendation_service.generate_recommendations(
                universe_id=self.universe_id,
                target_date=tomorrow,
                top_n=settings.daily_recommendation_count or 20
            )
            
            if recommendations:
                logger.info(f"Generated {len(recommendations)} recommendations for {tomorrow}")
                
                # Store for morning notification
                self._save_daily_recommendations(recommendations, tomorrow)
                
            else:
                logger.warning("No recommendations generated")
            
        except Exception as e:
            logger.error(f"Daily recommendation task failed: {e}")
    
    def morning_notification_task(self):
        """Morning task: send recommendations to users."""
        logger.info("Starting morning notification task")
        
        try:
            # Skip if weekend
            if datetime.now().weekday() >= 5:
                logger.info("Skipping morning notification - weekend")
                return
            
            today = date.today()
            
            # Get today's recommendations
            recommendations = self._load_daily_recommendations(today)
            
            if not recommendations:
                logger.warning("No recommendations found for today")
                return
            
            # Send notifications
            success = self.notification_service.send_daily_recommendations(
                recommendations, today
            )
            
            if success:
                logger.info("Morning notifications sent successfully")
            else:
                logger.error("Failed to send morning notifications")
            
        except Exception as e:
            logger.error(f"Morning notification task failed: {e}")
    
    def weekly_retrain_task(self):
        """Weekly task: retrain ML models."""
        logger.info("Starting weekly model retraining task")
        
        try:
            # Train model with fresh data
            result = self.recommendation_service.train_model(
                universe_id=self.universe_id,
                retrain=True
            )
            
            if result.get('success', False):
                logger.info("Weekly model retraining completed successfully")
                
                # Send notification about retraining
                if settings.send_admin_notifications:
                    message = f"🔄 주간 모델 재학습 완료\n"
                    message += f"최적 모델: {result.get('best_model', 'Unknown')}\n"
                    message += f"학습 샘플 수: {result.get('training_samples', 0)}"
                    
                    self.notification_service._send_simple_slack_message(message)
                    
            else:
                logger.error(f"Weekly model retraining failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Weekly retrain task failed: {e}")
    
    def monthly_universe_update_task(self):
        """Monthly task: update stock universe."""
        logger.info("Starting monthly universe update task")
        
        try:
            # Update universe with top stocks
            new_universe_id = self.data_service.update_universe_stocks(
                region=settings.default_region or "KR",
                top_n=settings.universe_size or 200
            )
            
            if new_universe_id:
                # Update universe ID
                old_universe_id = self.universe_id
                self.universe_id = new_universe_id
                
                logger.info(f"Universe updated: {old_universe_id} -> {new_universe_id}")
                
                # Send notification
                if settings.send_admin_notifications:
                    message = f"🔄 월간 유니버스 업데이트 완료\n"
                    message += f"새 유니버스 ID: {new_universe_id}\n"
                    message += f"포함 종목 수: {settings.universe_size or 200}개"
                    
                    self.notification_service._send_simple_slack_message(message)
                    
            else:
                logger.error("Monthly universe update failed")
                
        except Exception as e:
            logger.error(f"Monthly universe update task failed: {e}")
    
    def weekly_performance_report_task(self):
        """Weekly task: send performance report."""
        logger.info("Starting weekly performance report task")
        
        try:
            # Get performance data for last 7 days
            performance_data = self.recommendation_service.get_historical_performance(days=7)
            
            # Send performance report
            success = self.notification_service.send_performance_report(performance_data)
            
            if success:
                logger.info("Weekly performance report sent successfully")
            else:
                logger.error("Failed to send weekly performance report")
                
        except Exception as e:
            logger.error(f"Weekly performance report task failed: {e}")
    
    def _save_daily_recommendations(self, recommendations: list, target_date: date):
        """Save recommendations for morning notification."""
        try:
            import json
            import os
            
            # Create cache directory
            cache_dir = "cache"
            os.makedirs(cache_dir, exist_ok=True)
            
            filename = f"recommendations_{target_date.strftime('%Y%m%d')}.json"
            filepath = os.path.join(cache_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(recommendations, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Recommendations saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save recommendations: {e}")
    
    def _load_daily_recommendations(self, target_date: date) -> list:
        """Load recommendations for notification."""
        try:
            import json
            import os
            
            filename = f"recommendations_{target_date.strftime('%Y%m%d')}.json"
            filepath = os.path.join("cache", filename)
            
            if not os.path.exists(filepath):
                logger.warning(f"Recommendations file not found: {filepath}")
                return []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                recommendations = json.load(f)
            
            logger.info(f"Loaded {len(recommendations)} recommendations from {filepath}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to load recommendations: {e}")
            return []
    
    def _log_scheduled_jobs(self):
        """Log all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        logger.info("Scheduled jobs:")
        for job in jobs:
            logger.info(f"  - {job.id}: {job.next_run_time}")
    
    def run_manual_task(self, task_name: str) -> bool:
        """Run a scheduled task manually."""
        try:
            if task_name == "daily_recommendations":
                self.daily_recommendation_task()
            elif task_name == "morning_notifications":
                self.morning_notification_task()
            elif task_name == "weekly_retrain":
                self.weekly_retrain_task()
            elif task_name == "monthly_universe_update":
                self.monthly_universe_update_task()
            elif task_name == "weekly_performance_report":
                self.weekly_performance_report_task()
            else:
                logger.error(f"Unknown task: {task_name}")
                return False
            
            logger.info(f"Manual task '{task_name}' completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Manual task '{task_name}' failed: {e}")
            return False
    
    def get_job_status(self) -> dict:
        """Get status of all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        
        status = {
            'scheduler_running': self.scheduler.running,
            'total_jobs': len(jobs),
            'jobs': []
        }
        
        for job in jobs:
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            status['jobs'].append(job_info)
        
        return status
    
    def stop_scheduler(self):
        """Stop the scheduler gracefully."""
        logger.info("Stopping scheduler...")
        self.scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
    
    def start_scheduler(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
        else:
            logger.info("Scheduler already running")


# Simple schedule-based runner (alternative to APScheduler)
class SimpleScheduler:
    """Simple scheduler using the schedule library."""
    
    def __init__(self):
        self.data_service = DataCollectionService()
        self.recommendation_service = RecommendationService()
        self.notification_service = NotificationService()
        self.running = False
        self.universe_id = 1
    
    def setup_simple_schedules(self):
        """Setup schedules using the schedule library."""
        
        # Daily recommendations (weekdays 4 PM)
        schedule.every().monday.at("16:00").do(self._safe_run, self.daily_task)
        schedule.every().tuesday.at("16:00").do(self._safe_run, self.daily_task)
        schedule.every().wednesday.at("16:00").do(self._safe_run, self.daily_task)
        schedule.every().thursday.at("16:00").do(self._safe_run, self.daily_task)
        schedule.every().friday.at("16:00").do(self._safe_run, self.daily_task)
        
        # Morning notifications (weekdays 8:30 AM)
        schedule.every().monday.at("08:30").do(self._safe_run, self.morning_task)
        schedule.every().tuesday.at("08:30").do(self._safe_run, self.morning_task)
        schedule.every().wednesday.at("08:30").do(self._safe_run, self.morning_task)
        schedule.every().thursday.at("08:30").do(self._safe_run, self.morning_task)
        schedule.every().friday.at("08:30").do(self._safe_run, self.morning_task)
        
        # Weekly tasks
        schedule.every().saturday.at("02:00").do(self._safe_run, self.weekly_retrain_task)
        schedule.every().sunday.at("18:00").do(self._safe_run, self.weekly_report_task)
        
        logger.info("Simple schedules configured")
    
    def _safe_run(self, task_func):
        """Safely run a task with error handling."""
        try:
            task_func()
        except Exception as e:
            logger.error(f"Task {task_func.__name__} failed: {e}")
    
    def daily_task(self):
        """Daily recommendation generation."""
        logger.info("Running daily task")
        # Implementation similar to SchedulingService.daily_recommendation_task
    
    def morning_task(self):
        """Morning notification."""
        logger.info("Running morning task")
        # Implementation similar to SchedulingService.morning_notification_task
    
    def weekly_retrain_task(self):
        """Weekly model retraining."""
        logger.info("Running weekly retrain task")
        # Implementation similar to SchedulingService.weekly_retrain_task
    
    def weekly_report_task(self):
        """Weekly performance report."""
        logger.info("Running weekly report task")
        # Implementation similar to SchedulingService.weekly_performance_report_task
    
    def run_forever(self):
        """Run the scheduler forever."""
        self.running = True
        logger.info("Simple scheduler started")
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Simple scheduler stopped")
