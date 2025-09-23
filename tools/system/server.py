#!/usr/bin/env python3
"""
Stock Analyzer Server - Standalone Python Application
스케줄링과 알림 기능이 포함된 독립 실행 서버
"""
import sys
import os
import signal
import argparse
import time
from datetime import datetime
import logging
import threading
import uvicorn
from fastapi import FastAPI

# Add app directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.database.connection import init_db
from app.services.scheduler import SchedulingService
from app.utils.logger import setup_logging
from app.api.health import router as health_router


class StockAnalyzerServer:
    """Main server class for the stock analyzer application."""
    
    def __init__(self):
        self.scheduler_service = None
        self.running = False
        self.fastapi_app = None
        self.web_server_thread = None
        self.setup_signal_handlers()
        self.setup_fastapi_app()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def setup_fastapi_app(self):
        """Setup FastAPI application for health checks and monitoring."""
        self.fastapi_app = FastAPI(
            title="Stock Analyzer API",
            description="주식 분석 및 추천 시스템 API",
            version="1.0.0"
        )
        
        # Add health check router
        self.fastapi_app.include_router(health_router)
        
        @self.fastapi_app.get("/")
        async def root():
            return {
                "message": "Stock Analyzer API",
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
    
    def start_web_server(self):
        """Start FastAPI web server in a separate thread."""
        def run_server():
            uvicorn.run(
                self.fastapi_app,
                host="0.0.0.0",
                port=int(os.getenv("PORT", 8080)),
                log_level="info"
            )
        
        self.web_server_thread = threading.Thread(target=run_server, daemon=True)
        self.web_server_thread.start()
        
        logger = logging.getLogger(__name__)
        logger.info(f"🌐 Web API server started on port {os.getenv('PORT', 8080)}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger = logging.getLogger(__name__)
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def start(self, daemon_mode: bool = False):
        """Start the stock analyzer server."""
        logger = logging.getLogger(__name__)
        
        try:
            # Initialize database
            init_db()
            logger.info("Database connection initialized")
            
            # Start web server for health checks and monitoring
            self.start_web_server()
            
            # Initialize scheduler service
            self.scheduler_service = SchedulingService()
            self.scheduler_service.setup_schedules()
            
            logger.info("🚀 Stock Analyzer Server started successfully!")
            logger.info("📊 Automated stock analysis and recommendation system is running")
            logger.info("⏰ Scheduled tasks:")
            logger.info("   - Daily recommendations: Weekdays 4:00 PM (after market close)")
            logger.info("   - Morning notifications: Weekdays 8:30 AM (before market open)")
            logger.info("   - Weekly model retraining: Saturdays 2:00 AM")
            logger.info("   - Monthly universe update: First Sunday of month 1:00 AM")
            logger.info("   - Weekly performance report: Sundays 6:00 PM")
            
            # Print job status
            status = self.scheduler_service.get_job_status()
            logger.info(f"📅 Active jobs: {status['total_jobs']}")
            
            self.running = True
            
            if daemon_mode:
                self._run_daemon()
            else:
                self._run_interactive()
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            sys.exit(1)
    
    def _run_daemon(self):
        """Run in daemon mode."""
        logger = logging.getLogger(__name__)
        logger.info("Running in daemon mode...")
        
        try:
            while self.running:
                time.sleep(60)  # Sleep for 1 minute
                
                # Health check
                if not self.scheduler_service.scheduler.running:
                    logger.error("Scheduler stopped unexpectedly!")
                    break
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def _run_interactive(self):
        """Run in interactive mode."""
        logger = logging.getLogger(__name__)
        logger.info("Running in interactive mode. Type 'help' for available commands.")
        
        try:
            while self.running:
                try:
                    command = input("\n(stock-analyzer) > ").strip().lower()
                    
                    if command == 'help':
                        self._show_help()
                    elif command == 'status':
                        self._show_status()
                    elif command == 'jobs':
                        self._show_jobs()
                    elif command.startswith('run '):
                        task_name = command[4:]
                        self._run_manual_task(task_name)
                    elif command == 'test':
                        self._run_test_notification()
                    elif command in ['quit', 'exit', 'stop']:
                        break
                    elif command == '':
                        continue
                    else:
                        print(f"Unknown command: {command}. Type 'help' for available commands.")
                        
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit gracefully.")
                    
        finally:
            self.stop()
    
    def _show_help(self):
        """Show available commands."""
        help_text = """
Available commands:
  help                    - Show this help message
  status                  - Show server status
  jobs                    - Show scheduled jobs
  run <task>             - Run a task manually
    Available tasks:
      daily_recommendations    - Generate daily recommendations
      morning_notifications   - Send morning notifications
      weekly_retrain         - Retrain ML models
      monthly_universe_update - Update stock universe
      weekly_performance_report - Send performance report
  test                   - Send test notification
  quit/exit/stop         - Stop the server
        """
        print(help_text)
    
    def _show_status(self):
        """Show server status."""
        status = self.scheduler_service.get_job_status()
        
        print(f"\n📊 Server Status:")
        print(f"   Running: {'✅ Yes' if self.running else '❌ No'}")
        print(f"   Scheduler: {'✅ Active' if status['scheduler_running'] else '❌ Inactive'}")
        print(f"   Active jobs: {status['total_jobs']}")
        print(f"   Universe ID: {self.scheduler_service.universe_id}")
        
        # Show notification channels
        print(f"\n📢 Notification Channels:")
        print(f"   Email: {'✅' if settings.smtp_enabled else '❌'}")
        print(f"   Slack: {'✅' if settings.slack_enabled else '❌'}")
        print(f"   Discord: {'✅' if settings.discord_enabled else '❌'}")
        print(f"   Telegram: {'✅' if settings.telegram_enabled else '❌'}")
    
    def _show_jobs(self):
        """Show scheduled jobs."""
        status = self.scheduler_service.get_job_status()
        
        print(f"\n⏰ Scheduled Jobs ({status['total_jobs']} total):")
        for job in status['jobs']:
            next_run = job['next_run_time']
            if next_run:
                next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                next_run_str = next_run_dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                next_run_str = "Not scheduled"
            
            print(f"   📅 {job['id']}: {next_run_str}")
    
    def _run_manual_task(self, task_name: str):
        """Run a task manually."""
        print(f"\n🔄 Running task: {task_name}")
        
        start_time = datetime.now()
        success = self.scheduler_service.run_manual_task(task_name)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        if success:
            print(f"✅ Task completed successfully in {duration:.1f} seconds")
        else:
            print(f"❌ Task failed after {duration:.1f} seconds")
    
    def _run_test_notification(self):
        """Send a test notification."""
        print("\n📧 Sending test notification...")
        
        test_recommendations = [
            {
                'stock_code': 'TEST001',
                'stock_name': '테스트 종목 1',
                'score': 0.85,
                'rank': 1,
                'expected_return': '8.5%',
                'reason': {
                    'summary': '테스트용 추천입니다',
                    'technical_factors': ['RSI 과매도 구간', 'MACD 상승 신호'],
                    'confidence': 0.85
                }
            }
        ]
        
        success = self.scheduler_service.notification_service.send_daily_recommendations(
            test_recommendations
        )
        
        if success:
            print("✅ Test notification sent successfully")
        else:
            print("❌ Failed to send test notification")
    
    def stop(self):
        """Stop the server gracefully."""
        logger = logging.getLogger(__name__)
        logger.info("Stopping Stock Analyzer Server...")
        
        self.running = False
        
        if self.scheduler_service:
            self.scheduler_service.stop_scheduler()
        
        logger.info("🛑 Stock Analyzer Server stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Stock Analyzer Server')
    parser.add_argument(
        '--daemon', '-d', 
        action='store_true',
        help='Run in daemon mode (background)'
    )
    parser.add_argument(
        '--test-notifications', 
        action='store_true',
        help='Send test notifications and exit'
    )
    parser.add_argument(
        '--run-task',
        help='Run a specific task and exit'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Print banner
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    Stock Analyzer Server                     ║
║                                                               ║
║    🤖 AI-Powered Stock Recommendation System                 ║
║    📊 Automated Data Collection & Analysis                   ║
║    📱 Multi-Channel Notifications                           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    server = StockAnalyzerServer()
    
    try:
        if args.test_notifications:
            # Test notifications only
            logger.info("Testing notification system...")
            server._run_test_notification()
            return
        
        if args.run_task:
            # Run specific task
            logger.info(f"Running task: {args.run_task}")
            
            # Initialize services
            init_db()
            scheduler_service = SchedulingService()
            success = scheduler_service.run_manual_task(args.run_task)
            
            sys.exit(0 if success else 1)
        
        # Start server
        server.start(daemon_mode=args.daemon)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
