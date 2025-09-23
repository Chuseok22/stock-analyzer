#!/usr/bin/env python3
"""
한국 프리마켓 추천 기능 테스트
"""
import sys
from pathlib import Path
import asyncio

# Add app directory to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "app"))

async def test_korean_premarket():
    """한국 프리마켓 추천 기능 테스트"""
    print("🇰🇷 한국 프리마켓 추천 기능 테스트")
    print("="*60)
    
    try:
        # 1. 스케줄러 초기화 (부트스트랩 없이)
        print("1️⃣ 스케줄러 초기화...")
        from scripts.global_scheduler import GlobalScheduler
        scheduler = GlobalScheduler(run_bootstrap=False)
        
        # 2. Mock 예측 데이터 생성 (ML 학습 데이터 부족으로)
        print("2️⃣ Mock 예측 데이터 생성...")
        
        from app.ml.global_ml_engine import GlobalPrediction
        
        # 실제 한국 종목으로 Mock 예측 생성
        mock_predictions = [
            GlobalPrediction(
                stock_code="005930",
                market_region="KR", 
                predicted_return=2.5,
                confidence_score=0.85,
                risk_score=0.3,
                recommendation="BUY",
                target_price=75000,
                stop_loss=70000,
                reasoning=["기술적 분석 긍정적", "시장 모멘텀 상승"]
            ),
            GlobalPrediction(
                stock_code="000660",
                market_region="KR",
                predicted_return=1.8,
                confidence_score=0.78,
                risk_score=0.4,
                recommendation="BUY",
                target_price=140000,
                stop_loss=130000,
                reasoning=["반도체 업황 개선", "메모리 가격 상승"]
            ),
            GlobalPrediction(
                stock_code="035420",
                market_region="KR",
                predicted_return=1.2,
                confidence_score=0.72,
                risk_score=0.35,
                recommendation="HOLD",
                target_price=230000,
                stop_loss=215000,
                reasoning=["AI 사업 확장", "네이버페이 성장"]
            )
        ]
        
        print(f"   ✅ Mock 예측 데이터 생성: {len(mock_predictions)}개 종목")
        for pred in mock_predictions:
            print(f"      - {pred.stock_code}: {pred.predicted_return:.1f}% ({pred.recommendation})")
        
        # 3. 스마트 알림 시스템 테스트
        print("3️⃣ 스마트 알림 시스템 테스트...")
        
        alert = await scheduler.alert_system.generate_korean_premarket_recommendations(mock_predictions)
        
        if alert:
            print("   ✅ 한국 프리마켓 알림 생성 성공")
            print(f"   📋 제목: {alert.title}")
            print(f"   📝 메시지 길이: {len(alert.message)}자")
            print(f"   ⚠️ 긴급도: {alert.urgency_level}")
            print(f"   🎯 종목 수: {len(alert.stocks)}")
            
            # 메시지 일부 출력
            message_lines = alert.message.split('\n')[:10]
            print("   📄 메시지 미리보기:")
            for line in message_lines:
                print(f"      {line}")
        else:
            print("   ❌ 한국 프리마켓 알림 생성 실패")
            return False
        
        # 4. 스케줄러 메서드 직접 테스트
        print("4️⃣ 스케줄러 프리마켓 메서드 테스트...")
        
        # Mock 예측을 ML 엔진에 설정 (테스트용)
        scheduler.ml_engine._mock_predictions = mock_predictions
        
        # _run_korean_premarket_recommendations 메서드 실행
        success = await scheduler._run_korean_premarket_recommendations()
        
        if success:
            print("   ✅ 스케줄러 프리마켓 메서드 성공")
        else:
            print("   ❌ 스케줄러 프리마켓 메서드 실패")
            return False
        
        # 5. 알림 전송 테스트 (실제 전송 안 함)
        print("5️⃣ 알림 전송 시뮬레이션...")
        
        if alert:
            # Discord 웹훅 URL 확인
            from app.config.settings import settings
            
            discord_webhook = getattr(settings, 'discord_webhook_url', None)
            telegram_token = getattr(settings, 'telegram_bot_token', None)
            
            print(f"   📱 Discord 웹훅: {'설정됨' if discord_webhook else '미설정'}")
            print(f"   📱 Telegram 토큰: {'설정됨' if telegram_token else '미설정'}")
            
            if discord_webhook or telegram_token:
                print("   ✅ 알림 전송 준비 완료")
            else:
                print("   ⚠️ 알림 채널 미설정 (테스트 환경)")
        
        print("\n✅ 한국 프리마켓 추천 기능 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_korean_premarket())
    sys.exit(0 if success else 1)