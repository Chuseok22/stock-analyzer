#!/usr/bin/env python3
"""
텔레그램 봇 설정 및 테스트 스크립트
"""
import requests
import json

def get_telegram_chat_id(bot_token: str):
    """
    텔레그램 봇의 Chat ID를 확인하는 도구
    """
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data['ok'] and data['result']:
            print("📱 발견된 채팅:")
            for update in data['result']:
                if 'message' in update:
                    msg = update['message']
                    chat = msg['chat']
                    print(f"   Chat ID: {chat['id']}")
                    print(f"   이름: {chat.get('title', chat.get('first_name', 'Unknown'))}")
                    print(f"   타입: {chat['type']}")
                    print(f"   메시지: {msg.get('text', 'No text')}")
                    print("-" * 40)
                elif 'channel_post' in update:
                    post = update['channel_post']
                    chat = post['chat']
                    print(f"   채널 ID: {chat['id']}")
                    print(f"   채널명: {chat.get('title', 'Unknown')}")
                    print(f"   타입: {chat['type']}")
                    print("-" * 40)
        else:
            print("❌ 메시지를 찾을 수 없습니다. 봇과 대화하거나 채널에 메시지를 보내주세요.")
            
    except Exception as e:
        print(f"❌ 오류: {e}")

def test_telegram_message(bot_token: str, chat_id: str, message: str = "🧪 테스트 메시지"):
    """
    텔레그램 메시지 발송 테스트
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, data=payload)
        result = response.json()
        
        if result['ok']:
            print("✅ 텔레그램 메시지 전송 성공!")
        else:
            print(f"❌ 메시지 전송 실패: {result['description']}")
            
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    print("📱 텔레그램 봇 설정 도구")
    print("=" * 40)
    
    # 1. 봇 토큰 입력
    bot_token = input("🔑 봇 토큰을 입력하세요: ").strip()
    
    if not bot_token:
        print("❌ 봇 토큰이 필요합니다.")
        exit(1)
    
    # 2. Chat ID 확인
    print("\n📋 Chat ID 확인 중...")
    get_telegram_chat_id(bot_token)
    
    # 3. Chat ID 입력 및 테스트
    chat_id = input("\n💬 사용할 Chat ID를 입력하세요: ").strip()
    
    if chat_id:
        print("\n📤 테스트 메시지 전송 중...")
        test_telegram_message(bot_token, chat_id)
        
        print(f"\n✅ 설정 완료! .env 파일에 다음을 추가하세요:")
        print(f"TELEGRAM_ENABLED=true")
        print(f"TELEGRAM_BOT_TOKEN={bot_token}")
        print(f"TELEGRAM_CHAT_ID={chat_id}")
    else:
        print("\n⚠️ Chat ID가 입력되지 않았습니다.")
