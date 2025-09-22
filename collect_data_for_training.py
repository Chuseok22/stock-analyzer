#!/usr/bin/env python3
"""
주가 데이터 수집 및 DB 저장 (KIS 토큰 재사용)
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.data_collection import DataCollectionService
from app.services.kis_api import KISAPIClient
from app.database.redis_client import redis_client
from app.config.settings import settings


def verify_kis_token():
    """KIS 토큰 상태 확인"""
    print("🔍 KIS 토큰 상태 확인...")
    
    try:
        token = redis_client.get("kis:access_token")
        if token:
            ttl = redis_client.get_ttl("kis:access_token")
            print(f"✅ 토큰 존재: {token[:20]}... (TTL: {ttl/3600:.1f}시간)")
            return True
        else:
            print("❌ Redis에 토큰 없음. initialize_kis_token.py를 먼저 실행하세요.")
            return False
    except Exception as e:
        print(f"❌ 토큰 확인 중 오류: {e}")
        return False


def collect_stock_data():
    """주가 데이터 수집"""
    print("\n📊 주가 데이터 수집 시작...")
    
    try:
        # DataCollectionService 초기화
        data_service = DataCollectionService()
        print("✅ DataCollectionService 초기화 완료")
        
        # 주요 종목 코드 (한국 대형주 위주)
        major_stocks = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스  
            "373220",  # LG에너지솔루션
            "207940",  # 삼성바이오로직스
            "005380",  # 현대차
            "006400",  # 삼성SDI
            "051910",  # LG화학
            "035420",  # NAVER
            "005490",  # POSCO홀딩스
            "028260",  # 삼성물산
            "105560",  # KB금융
            "055550",  # 신한지주
            "086790",  # 하나금융지주
            "003550",  # LG
            "096770",  # SK이노베이션
            "034730",  # SK
            "323410",  # 카카오뱅크
            "035720",  # 카카오
            "068270",  # 셀트리온
            "326030",  # SK바이오팜
        ]
        
        print(f"📋 수집 대상: {len(major_stocks)}개 종목")
        
        # 최근 20일간의 데이터 수집
        collection_days = 20
        print(f"📅 수집 기간: 최근 {collection_days}일")
        
        # 데이터 수집 실행
        print("🔄 데이터 수집 중... (시간이 소요될 수 있습니다)")
        success = data_service.collect_stock_prices(major_stocks, days=collection_days)
        
        if success:
            print("✅ 주가 데이터 수집 완료")
            
            # Discord 알림
            try:
                from app.services.notification import NotificationService
                notification = NotificationService()
                message = (
                    f"📊 **주가 데이터 수집 완료**\n\n"
                    f"📅 수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"📈 수집 종목: {len(major_stocks)}개\n"
                    f"📆 수집 기간: 최근 {collection_days}일\n"
                    f"🔄 다음 단계: 기술적 지표 계산"
                )
                notification._send_simple_slack_message(message)
                print("📱 Discord 알림 전송 완료")
            except Exception as e:
                print(f"⚠️ Discord 알림 전송 실패: {e}")
            
            return True
        else:
            print("❌ 주가 데이터 수집 실패")
            return False
            
    except Exception as e:
        print(f"❌ 데이터 수집 중 오류: {e}")
        return False


def calculate_technical_indicators():
    """기술적 지표 계산"""
    print("\n🔧 기술적 지표 계산 시작...")
    
    try:
        data_service = DataCollectionService()
        
        print("📈 기술적 지표 계산 중...")
        data_service.calculate_technical_indicators()
        print("✅ 기술적 지표 계산 완료")
        
        # Discord 알림
        try:
            from app.services.notification import NotificationService
            notification = NotificationService()
            message = (
                f"🔧 **기술적 지표 계산 완료**\n\n"
                f"📅 계산 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📊 계산된 지표: RSI, MACD, 볼린저밴드 등\n"
                f"🎯 다음 단계: ML 모델 학습"
            )
            notification._send_simple_slack_message(message)
            print("📱 Discord 알림 전송 완료")
        except Exception as e:
            print(f"⚠️ Discord 알림 전송 실패: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 기술적 지표 계산 중 오류: {e}")
        return False


def verify_data_in_db():
    """DB에 저장된 데이터 확인"""
    print("\n🔍 DB 저장 데이터 확인...")
    
    try:
        data_service = DataCollectionService()
        
        # DB 세션으로 데이터 확인
        with data_service.get_db_session() as db:
            from app.models.entities import Stock, StockPrice, TechnicalIndicator
            
            # 주식 종목 수 확인
            stock_count = db.query(Stock).count()
            print(f"📊 저장된 종목 수: {stock_count}개")
            
            # 주가 데이터 수 확인
            price_count = db.query(StockPrice).count()
            print(f"📈 저장된 주가 데이터: {price_count}개")
            
            # 기술적 지표 수 확인
            indicator_count = db.query(TechnicalIndicator).count()
            print(f"🔧 저장된 기술적 지표: {indicator_count}개")
            
            # 최근 데이터 확인
            latest_price = db.query(StockPrice).order_by(StockPrice.date.desc()).first()
            if latest_price:
                print(f"📅 최신 데이터 날짜: {latest_price.date}")
            
            if stock_count > 0 and price_count > 0:
                print("✅ DB에 충분한 데이터가 저장되어 있습니다")
                return True
            else:
                print("❌ DB에 데이터가 부족합니다")
                return False
                
    except Exception as e:
        print(f"❌ DB 데이터 확인 중 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 주가 데이터 수집 및 기술적 지표 계산\n")
    print("="*50)
    print("📋 작업 순서:")
    print("1. KIS 토큰 상태 확인")
    print("2. 주가 데이터 수집")  
    print("3. 기술적 지표 계산")
    print("4. DB 저장 데이터 확인")
    print("="*50)
    
    # 1단계: 토큰 상태 확인
    print("\n1️⃣ KIS 토큰 상태 확인")
    if not verify_kis_token():
        print("\n❌ 토큰 확인 실패. 프로세스를 중단합니다.")
        return False
    
    # 2단계: 주가 데이터 수집
    print("\n2️⃣ 주가 데이터 수집")
    if not collect_stock_data():
        print("\n❌ 데이터 수집 실패. 프로세스를 중단합니다.")
        return False
    
    # 3단계: 기술적 지표 계산
    print("\n3️⃣ 기술적 지표 계산")
    if not calculate_technical_indicators():
        print("\n❌ 기술적 지표 계산 실패. 프로세스를 중단합니다.")
        return False
    
    # 4단계: 데이터 확인
    print("\n4️⃣ DB 저장 데이터 확인")
    if not verify_data_in_db():
        print("\n⚠️ 데이터 확인에 문제가 있습니다.")
    
    # 성공 요약
    print("\n" + "="*50)
    print("🎉 데이터 수집 및 처리 완료!")
    print("="*50)
    print("✅ KIS 토큰 상태 확인 완료")
    print("✅ 주가 데이터 수집 완료")
    print("✅ 기술적 지표 계산 완료")
    print("✅ DB 저장 상태 확인 완료")
    print("\n📊 다음 단계:")
    print("   1. ML 모델 학습")
    print("   2. 추천 시스템 테스트")
    print("   3. 내일부터 자동 추천 시작")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
