#!/usr/bin/env python3
"""
Discord webhook 알림 테스트 (KIS 토큰 재발급 없음)
"""
import sys
from pathlib import Path
import requests
import json
from datetime import datetime

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.config.settings import settings


def test_discord_webhook():
    """Discord 웹훅을 통한 알림 테스트"""
    print("🎮 Discord 웹훅 알림 테스트 시작...\n")
    
    # Discord 설정 확인
    if not settings.discord_enabled:
        print("❌ Discord 알림이 비활성화되어 있습니다.")
        return False
    
    if not settings.discord_webhook_url:
        print("❌ Discord 웹훅 URL이 설정되지 않았습니다.")
        return False
    
    print(f"✅ Discord 활성화 상태: {settings.discord_enabled}")
    print(f"✅ 웹훅 URL: {settings.discord_webhook_url[:50]}...")
    
    # 테스트 메시지 준비
    test_messages = [
        {
            "title": "🧪 Discord 알림 테스트",
            "description": "Stock Analyzer Discord 웹훅 연결 테스트입니다.",
            "color": 0x00ff00,  # 녹색
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "테스트 시간",
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "inline": True
                },
                {
                    "name": "상태",
                    "value": "✅ 정상 작동",
                    "inline": True
                }
            ]
        },
        {
            "title": "🚀 Redis & KIS 통합 완료",
            "description": "Redis 기반 KIS 토큰 관리 시스템이 성공적으로 구현되었습니다.",
            "color": 0x0099ff,  # 파란색
            "fields": [
                {
                    "name": "구현된 기능",
                    "value": "• Redis 토큰 캐싱\n• 일일 자동 갱신\n• 스케줄러 통합",
                    "inline": False
                },
                {
                    "name": "다음 토큰 갱신",
                    "value": "매일 자정 00:00",
                    "inline": True
                }
            ]
        }
    ]
    
    success_count = 0
    
    for i, embed_data in enumerate(test_messages, 1):
        print(f"\n📤 테스트 메시지 {i} 전송 중...")
        
        # Discord 웹훅 메시지 형식
        payload = {
            "embeds": [embed_data]
        }
        
        try:
            response = requests.post(
                settings.discord_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 204:
                print(f"✅ 메시지 {i} 전송 성공!")
                success_count += 1
            else:
                print(f"❌ 메시지 {i} 전송 실패: HTTP {response.status_code}")
                print(f"   응답: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 메시지 {i} 전송 중 오류: {e}")
    
    # 결과 요약
    print(f"\n📊 테스트 결과:")
    print(f"   전송 시도: {len(test_messages)}개")
    print(f"   성공: {success_count}개")
    print(f"   실패: {len(test_messages) - success_count}개")
    
    if success_count == len(test_messages):
        print("\n🎉 모든 Discord 알림 테스트가 성공했습니다!")
        return True
    else:
        print("\n⚠️ 일부 Discord 알림 전송에 실패했습니다.")
        return False


def test_simple_discord_message():
    """간단한 텍스트 메시지 테스트"""
    print("\n📝 간단한 텍스트 메시지 테스트...")
    
    simple_payload = {
        "content": "🔔 **Stock Analyzer 알림 테스트**\n\n"
                  "Redis 기반 KIS 토큰 관리 시스템이 성공적으로 구현되었습니다!\n"
                  f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    try:
        response = requests.post(
            settings.discord_webhook_url,
            json=simple_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 204:
            print("✅ 간단한 메시지 전송 성공!")
            return True
        else:
            print(f"❌ 간단한 메시지 전송 실패: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 간단한 메시지 전송 중 오류: {e}")
        return False


def main():
    """Discord 알림 테스트 실행"""
    print("🚀 Discord 웹훅 알림 테스트 시작\n")
    
    # 임베드 메시지 테스트
    embed_success = test_discord_webhook()
    
    # 간단한 텍스트 메시지 테스트
    simple_success = test_simple_discord_message()
    
    # 최종 결과
    print("\n" + "="*50)
    print("🎯 Discord 알림 테스트 최종 결과")
    print("="*50)
    print(f"임베드 메시지: {'✅ 성공' if embed_success else '❌ 실패'}")
    print(f"텍스트 메시지: {'✅ 성공' if simple_success else '❌ 실패'}")
    
    if embed_success and simple_success:
        print("\n🎉 Discord 웹훅이 정상적으로 작동합니다!")
        print("📱 이제 실시간 알림을 받을 수 있습니다.")
        return True
    else:
        print("\n❌ Discord 웹훅 설정을 확인해주세요.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
