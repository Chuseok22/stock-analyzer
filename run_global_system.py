#!/usr/bin/env python3
"""
글로벌 주식 분석 시스템 - 통합 실행 스크립트
한국/미국 시장 통합 분석, ML 예측, 스마트 알림

사용법:
  python run_global_system.py --setup          # 초기 설정
  python run_global_system.py --collect-data   # 데이터 수집
  python run_global_system.py --train-models   # ML 모델 학습  
  python run_global_system.py --predict        # 주식 예측
  python run_global_system.py --alerts         # 알림 전송
  python run_global_system.py --schedule       # 스케줄러 실행
  python run_global_system.py --full           # 전체 파이프라인 실행
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
import asyncio
import logging
from typing import Dict, Any, List

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

# 로그 디렉토리 생성
log_dir = Path(__file__).parent / "storage" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# 로깅 설정
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'global_system.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
except Exception as e:
    # 파일 로깅 실패 시 콘솔만 사용
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    print(f"⚠️ 파일 로깅 설정 실패, 콘솔 로깅만 사용: {e}")

logger = logging.getLogger(__name__)


class GlobalStockAnalysisSystem:
    """글로벌 주식 분석 시스템"""
    
    def __init__(self):
        self.version = "v3.0_global"
        self.start_time = datetime.now()
        
        # 로그 디렉토리 생성
        log_dir = Path("storage/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        print("🌍 글로벌 주식 분석 시스템 시작")
        print(f"📅 시작 시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔖 버전: {self.version}")
        print("="*60)
    
    def setup_system(self) -> bool:
        """시스템 초기 설정"""
        print("🔧 시스템 초기 설정...")
        
        try:
            # 1. 환경 변수 확인
            print("📋 환경 변수 확인...")
            required_vars = [
                "DATABASE_URL", "REDIS_URL", "ALPHA_VANTAGE_API_KEY", 
                "KIS_APP_KEY", "KIS_APP_SECRET", "DISCORD_WEBHOOK_URL"
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                print(f"❌ 누락된 환경 변수: {missing_vars}")
                return False
            
            print("✅ 환경 변수 확인 완료")
            
            # 2. 디렉토리 구조 생성
            print("📁 디렉토리 구조 생성...")
            directories = [
                "storage/models/global",
                "storage/logs", 
                "storage/data",
                "storage/backups"
            ]
            
            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)
            
            print("✅ 디렉토리 구조 생성 완료")
            
            # 3. 데이터베이스 연결 테스트
            print("🗄️ 데이터베이스 연결 테스트...")
            from app.database.connection import get_db_session
            from sqlalchemy import text
            
            with get_db_session() as db:
                db.execute(text("SELECT 1"))
            
            print("✅ 데이터베이스 연결 확인")
            
            # 4. Redis 연결 테스트
            print("🔴 Redis 연결 테스트...")
            from app.database.redis_client import redis_client
            
            redis_client.ping()
            print("✅ Redis 연결 확인")
            
            # 5. API 연결 테스트
            print("📡 API 연결 테스트...")
            
            # KIS API 테스트
            from app.services.kis_api import KISAPIClient
            kis_client = KISAPIClient()
            if kis_client.get_access_token():
                print("✅ KIS API 연결 확인")
            else:
                print("⚠️ KIS API 연결 실패")
            
            # Alpha Vantage API 테스트
            from app.services.alpha_vantage_api import AlphaVantageAPIClient
            av_client = AlphaVantageAPIClient()
            test_data = av_client.get_company_overview("AAPL")
            if test_data:
                print("✅ Alpha Vantage API 연결 확인")
            else:
                print("⚠️ Alpha Vantage API 연결 실패")
            
            print("🎉 시스템 초기 설정 완료")
            return True
            
        except Exception as e:
            print(f"❌ 시스템 설정 실패: {e}")
            logger.error(f"System setup failed: {e}")
            return False
    
    def collect_all_data(self) -> bool:
        """전체 데이터 수집"""
        print("📊 전체 데이터 수집 시작...")
        
        try:
            # 1. 한국 데이터 수집
            print("🇰🇷 한국 데이터 수집...")
            from scripts.production_ml_system import ProductionMLSystem
            
            kr_system = ProductionMLSystem()
            kr_success = kr_system.collect_daily_data()
            
            if kr_success:
                print("✅ 한국 데이터 수집 완료")
            else:
                print("❌ 한국 데이터 수집 실패")
            
            # 2. 미국 데이터 수집
            print("🇺🇸 미국 데이터 수집...")
            from scripts.collect_us_data import USDataCollector
            
            us_collector = USDataCollector()
            us_success = us_collector.run_full_collection()
            
            if us_success:
                print("✅ 미국 데이터 수집 완료")
            else:
                print("❌ 미국 데이터 수집 실패")
            
            overall_success = kr_success and us_success
            
            if overall_success:
                print("🎉 전체 데이터 수집 완료")
            else:
                print("⚠️ 일부 데이터 수집 실패")
            
            return overall_success
            
        except Exception as e:
            print(f"❌ 데이터 수집 실패: {e}")
            logger.error(f"Data collection failed: {e}")
            return False
    
    def train_global_models(self) -> bool:
        """글로벌 ML 모델 학습"""
        print("🏋️ 글로벌 ML 모델 학습 시작...")
        
        try:
            from app.ml.global_ml_engine import GlobalMLEngine
            
            ml_engine = GlobalMLEngine()
            success = ml_engine.train_global_models()
            
            if success:
                print("🎉 글로벌 ML 모델 학습 완료")
            else:
                print("❌ 글로벌 ML 모델 학습 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ 모델 학습 실패: {e}")
            logger.error(f"Model training failed: {e}")
            return False
    
    async def run_predictions(self) -> Dict[str, Any]:
        """주식 예측 실행"""
        print("🎯 글로벌 주식 예측 시작...")
        
        try:
            from app.ml.global_ml_engine import GlobalMLEngine, MarketRegion
            
            ml_engine = GlobalMLEngine()
            
            # 시장 체제 분석
            print("📊 시장 체제 분석...")
            market_condition = ml_engine.detect_market_regime()
            
            # 한국 예측
            print("🇰🇷 한국 주식 예측...")
            kr_predictions = ml_engine.predict_stocks(MarketRegion.KR, top_n=10)
            
            # 미국 예측 
            print("🇺🇸 미국 주식 예측...")
            us_predictions = ml_engine.predict_stocks(MarketRegion.US, top_n=10)
            
            # 실시간 학습을 위한 예측 결과 저장
            print("💾 학습용 예측 결과 저장...")
            all_predictions = kr_predictions + us_predictions
            if all_predictions:
                ml_engine.save_predictions_for_learning(all_predictions)
            
            results = {
                "market_condition": {
                    "regime": market_condition.regime.value,
                    "volatility": market_condition.volatility_level,
                    "risk_level": market_condition.risk_level,
                    "fear_greed": market_condition.fear_greed_index
                },
                "kr_predictions": [{
                    "code": p.stock_code,
                    "return": p.predicted_return,
                    "recommendation": p.recommendation,
                    "confidence": p.confidence_score
                } for p in kr_predictions],
                "us_predictions": [{
                    "code": p.stock_code,
                    "return": p.predicted_return,
                    "recommendation": p.recommendation,
                    "confidence": p.confidence_score
                } for p in us_predictions]
            }
            
            # 결과 출력
            print("\n📊 예측 결과 요약:")
            print(f"   시장 체제: {market_condition.regime.value}")
            print(f"   리스크 레벨: {market_condition.risk_level}")
            
            print(f"\n🇰🇷 한국 상위 3개:")
            for i, pred in enumerate(kr_predictions[:3], 1):
                print(f"   {i}. {pred.stock_code}: {pred.predicted_return:+.1f}% ({pred.recommendation})")
            
            print(f"\n🇺🇸 미국 상위 3개:")
            for i, pred in enumerate(us_predictions[:3], 1):
                print(f"   {i}. {pred.stock_code}: {pred.predicted_return:+.1f}% ({pred.recommendation})")
            
            print("🎉 글로벌 예측 완료")
            return results
            
        except Exception as e:
            print(f"❌ 예측 실행 실패: {e}")
            logger.error(f"Prediction failed: {e}")
            return {}
    
    async def send_smart_alerts(self) -> bool:
        """스마트 알림 전송"""
        print("📢 스마트 알림 시스템 실행...")
        
        try:
            from app.services.smart_alert_system import SmartAlertSystem
            
            alert_system = SmartAlertSystem()
            alerts_sent = await alert_system.run_alert_cycle()
            
            if alerts_sent:
                print("✅ 스마트 알림 전송 완료")
            else:
                print("⚠️ 전송할 알림 없음")
            
            return True
            
        except Exception as e:
            print(f"❌ 알림 전송 실패: {e}")
            logger.error(f"Alert sending failed: {e}")
            return False
    
    def run_scheduler(self):
        """스케줄러 실행"""
        print("⏰ 향상된 글로벌 스케줄러 시작...")
        
        try:
            from scripts.enhanced_global_scheduler import EnhancedGlobalScheduler
            
            scheduler = EnhancedGlobalScheduler()
            scheduler.run_scheduler()
            
        except Exception as e:
            print(f"❌ 스케줄러 실행 실패: {e}")
            logger.error(f"Scheduler failed: {e}")
    
    async def run_full_pipeline(self) -> bool:
        """전체 파이프라인 실행"""
        print("🚀 전체 파이프라인 실행...")
        print("="*60)
        
        pipeline_results = {
            "setup": False,
            "data_collection": False,
            "model_training": False,
            "predictions": False,
            "alerts": False
        }
        
        try:
            # 1. 시스템 설정 확인
            print("1️⃣ 시스템 설정 확인...")
            pipeline_results["setup"] = self.setup_system()
            
            if not pipeline_results["setup"]:
                print("❌ 시스템 설정 실패, 파이프라인 중단")
                return False
            
            # 2. 데이터 수집
            print("\n2️⃣ 데이터 수집...")
            pipeline_results["data_collection"] = self.collect_all_data()
            
            # 3. ML 모델 학습 (데이터 수집 성공 시)
            if pipeline_results["data_collection"]:
                print("\n3️⃣ ML 모델 학습...")
                pipeline_results["model_training"] = self.train_global_models()
            
            # 4. 예측 실행 (모델 학습 성공 시)
            if pipeline_results["model_training"]:
                print("\n4️⃣ 주식 예측...")
                predictions = await self.run_predictions()
                pipeline_results["predictions"] = bool(predictions)
            
            # 5. 알림 전송 (예측 성공 시)
            if pipeline_results["predictions"]:
                print("\n5️⃣ 스마트 알림...")
                pipeline_results["alerts"] = await self.send_smart_alerts()
            
            # 결과 요약
            print("\n📊 파이프라인 실행 결과:")
            for step, success in pipeline_results.items():
                status = "✅" if success else "❌"
                print(f"   {status} {step}: {'성공' if success else '실패'}")
            
            overall_success = all(pipeline_results.values())
            
            end_time = datetime.now()
            duration = end_time - self.start_time
            
            print(f"\n⏱️ 총 소요 시간: {duration}")
            
            if overall_success:
                print("🎉 전체 파이프라인 성공적으로 완료!")
            else:
                print("⚠️ 일부 단계에서 실패 발생")
            
            return overall_success
            
        except Exception as e:
            print(f"❌ 파이프라인 실행 실패: {e}")
            logger.error(f"Pipeline execution failed: {e}")
            return False
    
    def show_status(self):
        """시스템 상태 표시"""
        print("📊 글로벌 시스템 상태")
        print("="*40)
        
        try:
            # 데이터베이스 상태
            from app.database.connection import get_db_session
            from app.models.entities import StockMaster, MarketRegion
            
            with get_db_session() as db:
                kr_stocks = db.query(StockMaster).filter_by(market_region=MarketRegion.KR.value).count()
                us_stocks = db.query(StockMaster).filter_by(market_region=MarketRegion.US.value).count()
                
                print(f"📈 등록된 종목:")
                print(f"   🇰🇷 한국: {kr_stocks}개")
                print(f"   🇺🇸 미국: {us_stocks}개")
            
            # 모델 상태
            model_dir = Path("storage/models/global")
            if model_dir.exists():
                kr_model = model_dir / f"KR_model_v3.0_global.joblib"
                us_model = model_dir / f"US_model_v3.0_global.joblib"
                
                print(f"\n🤖 ML 모델:")
                print(f"   🇰🇷 한국 모델: {'✅' if kr_model.exists() else '❌'}")
                print(f"   🇺🇸 미국 모델: {'✅' if us_model.exists() else '❌'}")
            
            # 로그 파일
            log_file = Path("storage/logs/global_system.log")
            if log_file.exists():
                size_mb = log_file.stat().st_size / (1024 * 1024)
                print(f"\n📝 로그 파일: {size_mb:.1f}MB")
            
            print("\n✅ 시스템 상태 확인 완료")
            
        except Exception as e:
            print(f"❌ 상태 확인 실패: {e}")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="글로벌 주식 분석 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python run_global_system.py --setup          # 초기 설정
  python run_global_system.py --collect-data   # 데이터 수집
  python run_global_system.py --train-models   # ML 모델 학습
  python run_global_system.py --predict        # 주식 예측
  python run_global_system.py --alerts         # 알림 전송
  python run_global_system.py --schedule       # 스케줄러 실행
  python run_global_system.py --full           # 전체 파이프라인
  python run_global_system.py --status         # 시스템 상태
        """
    )
    
    # 실행 모드 설정
    group = parser.add_mutually_exclusive_group(required=False)  # required=False로 변경
    group.add_argument("--setup", action="store_true", help="시스템 초기 설정")
    group.add_argument("--collect-data", action="store_true", help="데이터 수집")
    group.add_argument("--train-models", action="store_true", help="ML 모델 학습")
    group.add_argument("--predict", action="store_true", help="주식 예측")
    group.add_argument("--alerts", action="store_true", help="스마트 알림")
    group.add_argument("--schedule", action="store_true", help="스케줄러 실행")
    group.add_argument("--full", action="store_true", help="전체 파이프라인")
    group.add_argument("--status", action="store_true", help="시스템 상태")
    
    args = parser.parse_args()
    
    # 인수가 없으면 기본적으로 스케줄러 실행
    if not any([args.setup, args.collect_data, args.train_models, args.predict, 
                args.alerts, args.schedule, args.full, args.status]):
        logger.info("🚀 기본 모드: 스케줄러 실행")
        args.schedule = True
    
    # 시스템 초기화
    system = GlobalStockAnalysisSystem()
    
    try:
        if args.setup:
            success = system.setup_system()
        elif args.collect_data:
            success = system.collect_all_data()
        elif args.train_models:
            success = system.train_global_models()
        elif args.predict:
            predictions = asyncio.run(system.run_predictions())
            success = bool(predictions)
        elif args.alerts:
            success = asyncio.run(system.send_smart_alerts())
        elif args.schedule:
            system.run_scheduler()
            success = True
        elif args.full:
            success = asyncio.run(system.run_full_pipeline())
        elif args.status:
            system.show_status()
            success = True
        else:
            print("❌ 올바른 실행 모드를 선택하세요")
            success = False
        
        if success:
            print("\n🎉 실행 완료!")
            sys.exit(0)
        else:
            print("\n💥 실행 실패!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 사용자가 중단했습니다")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


def start_health_server():
    """간단한 헬스체크 서버 시작"""
    import threading
    import time
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                response = {
                    "status": "healthy", 
                    "timestamp": time.time(),
                    "service": "stock-analyzer",
                    "version": "2.0"
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 헬스체크 요청 처리됨")
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass  # HTTP 로그 억제
    
    def run_server():
        try:
            port = int(os.getenv('PORT', 8080))
            server = HTTPServer(('0.0.0.0', port), HealthHandler)
            print(f"🏥 헬스체크 서버 시작됨 - http://0.0.0.0:{port}/health")
            logger.info(f"🏥 헬스체크 서버 시작 - 포트 {port}")
            server.serve_forever()
        except Exception as e:
            print(f"❌ 헬스체크 서버 오류: {e}")
            logger.error(f"헬스체크 서버 오류: {e}")
    
    # 백그라운드에서 헬스체크 서버 실행
    health_thread = threading.Thread(target=run_server, daemon=True)
    health_thread.start()
    
    # 서버 시작 대기
    time.sleep(2)
    
    return health_thread


if __name__ == "__main__":
    # 헬스체크 서버 시작
    start_health_server()
    
    # 메인 시스템 실행
    main()
