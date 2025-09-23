#!/usr/bin/env python3
"""
텔레그램 연동 상세 테스트 스크립트
"""

import os
import sys
import traceback
from dotenv import load_dotenv
import requests

def test_telegram_detailed():
    """상세한 텔레그램 테스트"""
    
    # 환경 변수 로드
    load_dotenv()
    
    print("🔍 텔레그램 연동 상세 테스트")
    print("=" * 50)
    
    # 1. 환경 변수 확인
    telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print(f"📋 환경 변수 상태:")
    print(f"   TELEGRAM_ENABLED: {telegram_enabled}")
    print(f"   TELEGRAM_BOT_TOKEN: {'설정됨' if bot_token else '설정 안됨'}")
    print(f"   TELEGRAM_CHAT_ID: {chat_id}")
    print()
    
    # 2. 활성화 상태 확인
    if telegram_enabled.lower() != 'true':
        print("⚠️ 텔레그램이 비활성화되어 있습니다")
        return False
    
    # 3. 필수 설정 확인
    if not bot_token or not chat_id:
        print("❌ 봇 토큰 또는 Chat ID가 설정되지 않았습니다")
        return False
    
    # 4. 봇 정보 확인
    try:
        print("🤖 봇 정보 확인 중...")
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                print(f"   ✅ 봇 이름: {bot_info['result']['first_name']}")
                print(f"   ✅ 봇 사용자명: @{bot_info['result']['username']}")
            else:
                print(f"   ❌ 봇 API 오류: {bot_info.get('description')}")
                return False
        else:
            print(f"   ❌ HTTP 오류: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 봇 정보 확인 실패: {e}")
        return False
    
    # 5. 채팅 정보 확인
    try:
        print("\n💬 채팅 정보 확인 중...")
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        data = {'chat_id': chat_id}
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            chat_info = response.json()
            if chat_info.get('ok'):
                chat_result = chat_info['result']
                chat_type = chat_result['type']
                chat_title = chat_result.get('title', chat_result.get('first_name', 'Unknown'))
                print(f"   ✅ 채팅 타입: {chat_type}")
                print(f"   ✅ 채팅 이름: {chat_title}")
            else:
                print(f"   ❌ 채팅 정보 오류: {chat_info.get('description')}")
                return False
        else:
            print(f"   ❌ HTTP 오류: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 채팅 정보 확인 실패: {e}")
        return False
    
    # 6. 테스트 메시지 전송
    try:
        print("\n📤 테스트 메시지 전송 중...")
        
        test_message = """🎯 주식 분석기 텔레그램 연동 테스트 🎯

✅ 시스템 연결 성공!
📱 알림이 정상적으로 작동합니다.

🔔 앞으로 받을 수 있는 알림:
• 매수/매도 신호
• 일일 분석 요약  
• 시장 현황
• 시스템 알림

⏰ 테스트 시간: 지금"""

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': test_message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("   ✅ 테스트 메시지 전송 성공!")
                print("   📱 텔레그램을 확인해보세요!")
                return True
            else:
                print(f"   ❌ 메시지 전송 오류: {result.get('description')}")
                return False
        else:
            print(f"   ❌ HTTP 오류: {response.status_code}")
            print(f"   응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 메시지 전송 실패: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_telegram_detailed()
    print("\n" + "=" * 50)
    if success:
        print("🎉 텔레그램 연동 완료!")
    else:
        print("💥 텔레그램 연동 실패 - 설정을 확인해주세요")
