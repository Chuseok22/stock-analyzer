#!/usr/bin/env python3
"""
종목 정보 추가 및 데이터 수집 (개선버전)
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import Stock, Universe, UniverseItem
from app.services.data_collection import DataCollectionService
from app.database.redis_client import redis_client


def add_major_stocks_to_db():
    """주요 종목을 DB에 추가"""
    print("📊 주요 종목 DB 추가 중...")
    
    # 주요 종목 정보 (region만 사용)
    major_stocks = [
        {"code": "005930", "name": "삼성전자", "region": "KR"},
        {"code": "000660", "name": "SK하이닉스", "region": "KR"},
        {"code": "373220", "name": "LG에너지솔루션", "region": "KR"},
        {"code": "207940", "name": "삼성바이오로직스", "region": "KR"},
        {"code": "005380", "name": "현대차", "region": "KR"},
        {"code": "006400", "name": "삼성SDI", "region": "KR"},
        {"code": "051910", "name": "LG화학", "region": "KR"},
        {"code": "035420", "name": "NAVER", "region": "KR"},
        {"code": "005490", "name": "POSCO홀딩스", "region": "KR"},
        {"code": "028260", "name": "삼성물산", "region": "KR"},
        {"code": "105560", "name": "KB금융", "region": "KR"},
        {"code": "055550", "name": "신한지주", "region": "KR"},
        {"code": "086790", "name": "하나금융지주", "region": "KR"},
        {"code": "003550", "name": "LG", "region": "KR"},
        {"code": "096770", "name": "SK이노베이션", "region": "KR"},
        {"code": "034730", "name": "SK", "region": "KR"},
        {"code": "323410", "name": "카카오뱅크", "region": "KR"},
        {"code": "035720", "name": "카카오", "region": "KR"},
        {"code": "068270", "name": "셀트리온", "region": "KR"},
        {"code": "326030", "name": "SK바이오팜", "region": "KR"},
    ]
    
    try:
        with get_db_session() as db:
            added_stocks = []
            
            for stock_info in major_stocks:
                # 기존 종목 확인
                existing_stock = db.query(Stock).filter(Stock.code == stock_info["code"]).first()
                
                if not existing_stock:
                    # 새 종목 추가
                    new_stock = Stock(
                        code=stock_info["code"],
                        name=stock_info["name"],
                        region=stock_info["region"],
                        active=True,
                        created_date=datetime.now(),
                        updated_date=datetime.now()
                    )
                    db.add(new_stock)
                    added_stocks.append(stock_info["name"])
                    print(f"   + {stock_info['code']}: {stock_info['name']}")
                else:
                    print(f"   ✓ {stock_info['code']}: {stock_info['name']} (이미 존재)")
            
            db.commit()
            
            print(f"✅ 종목 추가 완료: {len(added_stocks)}개 신규 추가")
            return True
            
    except Exception as e:
        print(f"❌ 종목 추가 중 오류: {e}")
        return False


def create_universe():
    """주요 종목으로 유니버스 생성"""
    print("\n🌌 투자 유니버스 생성 중...")
    
    try:
        with get_db_session() as db:
            from datetime import date
            
            # 오늘 날짜로 유니버스 확인
            today = date.today()
            universe = db.query(Universe).filter(
                Universe.region == "KR",
                Universe.snapshot_date == today
            ).first()
            
            if not universe:
                # 활성 종목 수 확인
                active_stock_count = db.query(Stock).filter(Stock.active == True, Stock.region == "KR").count()
                
                # 새 유니버스 생성
                universe = Universe(
                    region="KR",
                    size=active_stock_count,
                    snapshot_date=today,
                    rule_version="v1.0",
                    created_date=datetime.now(),
                    updated_date=datetime.now()
                )
                db.add(universe)
                db.commit()
                print(f"✅ 새 유니버스 생성 (ID: {universe.id}, 크기: {active_stock_count})")
            else:
                print(f"✅ 기존 유니버스 사용 (ID: {universe.id}, 크기: {universe.size})")
            
            # 유니버스에 종목 추가
            existing_items = db.query(UniverseItem).filter(UniverseItem.universe_id == universe.id).count()
            
            if existing_items == 0:
                # 모든 활성 종목을 유니버스에 추가
                active_stocks = db.query(Stock).filter(Stock.active == True, Stock.region == "KR").all()
                
                for stock in active_stocks:
                    universe_item = UniverseItem(
                        universe_id=universe.id,
                        stock_id=stock.id,
                        created_date=datetime.now(),
                        updated_date=datetime.now()
                    )
                    db.add(universe_item)
                
                db.commit()
                print(f"✅ 유니버스에 {len(active_stocks)}개 종목 추가")
            else:
                print(f"✅ 유니버스에 이미 {existing_items}개 종목 존재")
            
            return True
            
    except Exception as e:
        print(f"❌ 유니버스 생성 중 오류: {e}")
        return False


def collect_stock_data_fixed():
    """개선된 주가 데이터 수집"""
    print("\n📊 주가 데이터 수집 시작...")
    
    try:
        # DataCollectionService 초기화
        data_service = DataCollectionService()
        
        # DB에서 활성 종목 코드 가져오기
        with get_db_session() as db:
            active_stocks = db.query(Stock).filter(Stock.active == True).all()
            stock_codes = [stock.code for stock in active_stocks]
        
        if not stock_codes:
            print("❌ DB에 활성 종목이 없습니다")
            return False
        
        print(f"📋 수집 대상: {len(stock_codes)}개 종목")
        
        # 최근 30일간의 데이터 수집
        collection_days = 30
        print(f"📅 수집 기간: 최근 {collection_days}일")
        
        # 데이터 수집 실행
        print("🔄 데이터 수집 중... (시간이 소요될 수 있습니다)")
        success = data_service.collect_stock_prices(stock_codes, days=collection_days)
        
        if success:
            print("✅ 주가 데이터 수집 완료")
            return True
        else:
            print("❌ 주가 데이터 수집 실패")
            return False
            
    except Exception as e:
        print(f"❌ 데이터 수집 중 오류: {e}")
        return False


def calculate_technical_indicators():
    """기술적 지표 계산"""
    print("\n🔧 기술적 지표 계산 중...")
    
    try:
        data_service = DataCollectionService()
        data_service.calculate_technical_indicators()
        print("✅ 기술적 지표 계산 완료")
        return True
    except Exception as e:
        print(f"❌ 기술적 지표 계산 중 오류: {e}")
        return False


def verify_data_in_db():
    """DB에 저장된 데이터 확인"""
    print("\n🔍 DB 저장 데이터 확인...")
    
    try:
        with get_db_session() as db:
            from app.models.entities import Stock, StockPrice, StockIndicator
            
            # 주식 종목 수 확인
            stock_count = db.query(Stock).count()
            print(f"📊 저장된 종목 수: {stock_count}개")
            
            # 주가 데이터 수 확인
            price_count = db.query(StockPrice).count()
            print(f"📈 저장된 주가 데이터: {price_count}개")
            
            # 기술적 지표 수 확인 (StockIndicator로 수정)
            indicator_count = db.query(StockIndicator).count()
            print(f"🔧 저장된 기술적 지표: {indicator_count}개")
            
            # 최근 데이터 확인
            latest_price = db.query(StockPrice).order_by(StockPrice.date.desc()).first()
            if latest_price:
                print(f"📅 최신 데이터 날짜: {latest_price.date}")
            
            if stock_count > 0 and price_count > 0:
                print("✅ DB에 충분한 데이터가 저장되어 있습니다")
                
                # Discord 알림
                try:
                    from app.services.notification import NotificationService
                    notification = NotificationService()
                    message = (
                        f"🎯 **데이터 수집 및 처리 완료**\n\n"
                        f"📅 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"📊 종목 수: {stock_count}개\n"
                        f"📈 주가 데이터: {price_count}개\n"
                        f"🔧 기술적 지표: {indicator_count}개\n"
                        f"🚀 다음 단계: ML 모델 학습"
                    )
                    notification._send_simple_slack_message(message)
                    print("📱 Discord 알림 전송 완료")
                except Exception as e:
                    print(f"⚠️ Discord 알림 전송 실패: {e}")
                
                return True
            else:
                print("❌ DB에 데이터가 부족합니다")
                return False
                
    except Exception as e:
        print(f"❌ DB 데이터 확인 중 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 종목 추가 및 데이터 수집 (개선버전)\n")
    print("="*50)
    print("📋 작업 순서:")
    print("1. KIS 토큰 상태 확인")
    print("2. 주요 종목 DB 추가")
    print("3. 투자 유니버스 생성")
    print("4. 주가 데이터 수집")
    print("5. 기술적 지표 계산")
    print("6. DB 저장 데이터 확인")
    print("="*50)
    
    # 1단계: 토큰 상태 확인
    print("\n1️⃣ KIS 토큰 상태 확인")
    try:
        token = redis_client.get("kis:access_token")
        if token:
            ttl = redis_client.get_ttl("kis:access_token")
            print(f"✅ 토큰 존재: {token[:20]}... (TTL: {ttl/3600:.1f}시간)")
        else:
            print("❌ Redis에 토큰 없음. initialize_kis_token.py를 먼저 실행하세요.")
            return False
    except Exception as e:
        print(f"❌ 토큰 확인 중 오류: {e}")
        return False
    
    # 2단계: 종목 추가
    print("\n2️⃣ 주요 종목 DB 추가")
    if not add_major_stocks_to_db():
        print("\n❌ 종목 추가 실패. 프로세스를 중단합니다.")
        return False
    
    # 3단계: 유니버스 생성
    print("\n3️⃣ 투자 유니버스 생성")
    if not create_universe():
        print("\n❌ 유니버스 생성 실패. 프로세스를 중단합니다.")
        return False
    
    # 4단계: 주가 데이터 수집
    print("\n4️⃣ 주가 데이터 수집")
    if not collect_stock_data_fixed():
        print("\n❌ 데이터 수집 실패. 프로세스를 중단합니다.")
        return False
    
    # 5단계: 기술적 지표 계산
    print("\n5️⃣ 기술적 지표 계산")
    if not calculate_technical_indicators():
        print("\n❌ 기술적 지표 계산 실패. 프로세스를 중단합니다.")
        return False
    
    # 6단계: 데이터 확인
    print("\n6️⃣ DB 저장 데이터 확인")
    if not verify_data_in_db():
        print("\n⚠️ 데이터 확인에 문제가 있습니다.")
    
    # 성공 요약
    print("\n" + "="*50)
    print("🎉 모든 데이터 준비 완료!")
    print("="*50)
    print("✅ 종목 정보 DB 추가 완료")
    print("✅ 투자 유니버스 생성 완료")
    print("✅ 주가 데이터 수집 완료")
    print("✅ 기술적 지표 계산 완료")
    print("✅ DB 저장 상태 확인 완료")
    print("\n🚀 다음 단계:")
    print("   1. ML 모델 학습 실행")
    print("   2. 추천 시스템 테스트")
    print("   3. 내일부터 자동 추천 시작")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
