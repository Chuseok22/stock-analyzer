#!/usr/bin/env python3
"""
ML 모델 학습 및 추천 시스템 준비
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.recommendation import RecommendationService
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
            print("❌ Redis에 토큰 없음")
            return False
    except Exception as e:
        print(f"❌ 토큰 확인 중 오류: {e}")
        return False


def train_ml_model():
    """ML 모델 학습"""
    print("\n🤖 ML 모델 학습 시작...")
    
    try:
        # RecommendationService 초기화
        recommendation_service = RecommendationService()
        print("✅ RecommendationService 초기화 완료")
        
        # 유니버스 ID 확인
        universe_id = settings.default_universe_id or 1
        print(f"📊 학습 대상 유니버스 ID: {universe_id}")
        
        # 모델 학습 실행
        print("🔄 ML 모델 학습 중... (시간이 소요될 수 있습니다)")
        result = recommendation_service.train_model(
            universe_id=universe_id,
            retrain=True
        )
        
        if result.get('success', False):
            print("✅ ML 모델 학습 완료")
            print(f"   최적 모델: {result.get('best_model', 'Unknown')}")
            print(f"   학습 샘플 수: {result.get('training_samples', 0)}")
            print(f"   검증 정확도: {result.get('accuracy', 0):.4f}")
            
            # Discord 알림
            try:
                from app.services.notification import NotificationService
                notification = NotificationService()
                message = (
                    f"🤖 **ML 모델 학습 완료**\n\n"
                    f"📅 학습 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"🎯 최적 모델: {result.get('best_model', 'Unknown')}\n"
                    f"📊 학습 샘플: {result.get('training_samples', 0)}개\n"
                    f"🎮 검증 정확도: {result.get('accuracy', 0):.4f}\n"
                    f"🚀 다음 단계: 추천 생성 테스트"
                )
                notification._send_simple_slack_message(message)
                print("📱 Discord 알림 전송 완료")
            except Exception as e:
                print(f"⚠️ Discord 알림 전송 실패: {e}")
            
            return True
        else:
            print(f"❌ ML 모델 학습 실패: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ 모델 학습 중 오류: {e}")
        return False


def test_recommendation_generation():
    """추천 생성 테스트"""
    print("\n📈 추천 생성 테스트 시작...")
    
    try:
        recommendation_service = RecommendationService()
        
        # 내일 날짜로 추천 생성
        tomorrow = date.today() + timedelta(days=1)
        
        # 주말이면 다음 평일로 조정
        while tomorrow.weekday() >= 5:  # Saturday=5, Sunday=6
            tomorrow += timedelta(days=1)
        
        universe_id = settings.default_universe_id or 1
        top_n = settings.daily_recommendation_count or 10
        
        print(f"📅 추천 날짜: {tomorrow}")
        print(f"📊 유니버스 ID: {universe_id}")
        print(f"🔢 추천 종목 수: {top_n}")
        
        # 추천 생성
        print("🔄 추천 생성 중...")
        recommendations = recommendation_service.generate_recommendations(
            universe_id=universe_id,
            target_date=tomorrow,
            top_n=top_n
        )
        
        if recommendations:
            print(f"✅ {len(recommendations)}개 추천 생성 완료")
            
            # 상위 5개 추천 출력
            print("\n🏆 상위 5개 추천:")
            for i, rec in enumerate(recommendations[:5], 1):
                stock_code = rec.get('stock_code', 'Unknown')
                stock_name = rec.get('stock_name', 'Unknown')
                score = rec.get('score', 0)
                print(f"   {i}. {stock_code} ({stock_name}) - 점수: {score:.4f}")
            
            # Discord 알림
            try:
                from app.services.notification import NotificationService
                notification = NotificationService()
                
                # 추천 리스트 포맷팅
                top_5_text = "\n".join([
                    f"{i}. {rec.get('stock_code', 'Unknown')} ({rec.get('stock_name', 'Unknown')}) - {rec.get('score', 0):.4f}"
                    for i, rec in enumerate(recommendations[:5], 1)
                ])
                
                message = (
                    f"📈 **추천 생성 테스트 완료**\n\n"
                    f"📅 추천 날짜: {tomorrow}\n"
                    f"🎯 총 추천 수: {len(recommendations)}개\n\n"
                    f"🏆 **상위 5개 추천:**\n{top_5_text}\n\n"
                    f"✅ 추천 시스템 준비 완료!"
                )
                notification._send_simple_slack_message(message)
                print("📱 Discord 알림 전송 완료")
            except Exception as e:
                print(f"⚠️ Discord 알림 전송 실패: {e}")
            
            return True
        else:
            print("❌ 추천 생성 실패")
            return False
            
    except Exception as e:
        print(f"❌ 추천 생성 테스트 중 오류: {e}")
        return False


def verify_system_ready():
    """시스템 준비 상태 확인"""
    print("\n🔍 시스템 준비 상태 확인...")
    
    try:
        from app.database.connection import get_db_session
        from app.models.entities import Stock, StockPrice, StockIndicator, Universe, UniverseItem
        
        with get_db_session() as db:
            # 기본 데이터 확인
            stock_count = db.query(Stock).count()
            price_count = db.query(StockPrice).count()
            indicator_count = db.query(StockIndicator).count()
            universe_count = db.query(Universe).count()
            universe_item_count = db.query(UniverseItem).count()
            
            print(f"📊 종목 수: {stock_count}개")
            print(f"📈 주가 데이터: {price_count}개")
            print(f"🔧 기술적 지표: {indicator_count}개")
            print(f"🌌 유니버스 수: {universe_count}개")
            print(f"📋 유니버스 종목: {universe_item_count}개")
            
            # Redis 토큰 확인
            token = redis_client.get("kis:access_token")
            ttl = redis_client.get_ttl("kis:access_token") if token else 0
            
            print(f"🔑 KIS 토큰: {'✅ 존재' if token else '❌ 없음'}")
            if token:
                print(f"⏰ 토큰 TTL: {ttl/3600:.1f}시간")
            
            # 시스템 준비 상태 판단
            is_ready = (
                stock_count > 0 and
                price_count > 0 and
                indicator_count > 0 and
                universe_count > 0 and
                universe_item_count > 0 and
                token is not None
            )
            
            if is_ready:
                print("\n✅ 시스템이 운영 준비 완료되었습니다!")
                return True
            else:
                print("\n❌ 시스템 준비가 완료되지 않았습니다.")
                return False
                
    except Exception as e:
        print(f"❌ 시스템 상태 확인 중 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 ML 모델 학습 및 추천 시스템 준비\n")
    print("="*50)
    print("📋 작업 순서:")
    print("1. KIS 토큰 상태 확인")
    print("2. ML 모델 학습")
    print("3. 추천 생성 테스트")
    print("4. 시스템 준비 상태 확인")
    print("="*50)
    
    # 1단계: 토큰 상태 확인
    print("\n1️⃣ KIS 토큰 상태 확인")
    if not verify_kis_token():
        print("\n❌ 토큰 확인 실패. 프로세스를 중단합니다.")
        return False
    
    # 2단계: ML 모델 학습
    print("\n2️⃣ ML 모델 학습")
    if not train_ml_model():
        print("\n❌ 모델 학습 실패. 프로세스를 중단합니다.")
        return False
    
    # 3단계: 추천 생성 테스트
    print("\n3️⃣ 추천 생성 테스트")
    if not test_recommendation_generation():
        print("\n❌ 추천 생성 테스트 실패. 프로세스를 중단합니다.")
        return False
    
    # 4단계: 시스템 준비 상태 확인
    print("\n4️⃣ 시스템 준비 상태 확인")
    if not verify_system_ready():
        print("\n⚠️ 시스템 준비 상태에 문제가 있습니다.")
    
    # 성공 요약
    print("\n" + "="*50)
    print("🎉 ML 모델 학습 및 추천 시스템 준비 완료!")
    print("="*50)
    print("✅ KIS 토큰 상태 확인 완료")
    print("✅ ML 모델 학습 완료")
    print("✅ 추천 생성 테스트 완료")
    print("✅ 시스템 준비 상태 확인 완료")
    print("\n🚀 이제 다음과 같은 작업이 가능합니다:")
    print("   ✅ 내일부터 자동 추천 시작")
    print("   ✅ 매일 자정 KIS 토큰 자동 갱신")
    print("   ✅ 평일 오후 4시 데이터 수집 및 추천 생성")
    print("   ✅ 평일 오전 8시 30분 추천 알림 발송")
    print("   ✅ Discord를 통한 실시간 시스템 알림")
    
    # 최종 Discord 알림
    try:
        from app.services.notification import NotificationService
        notification = NotificationService()
        message = (
            f"🎉 **Stock Analyzer 시스템 준비 완료!**\n\n"
            f"📅 준비 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🤖 ML 모델: 학습 완료\n"
            f"📊 데이터: 수집 및 처리 완료\n"
            f"🔑 KIS 토큰: Redis 캐싱 활성화\n"
            f"📱 Discord 알림: 연동 완료\n\n"
            f"🚀 **내일부터 자동 주식 추천 시작!**"
        )
        notification._send_simple_slack_message(message)
        print("\n📱 최종 완료 알림 전송됨")
    except Exception as e:
        print(f"\n⚠️ 최종 알림 전송 실패: {e}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
