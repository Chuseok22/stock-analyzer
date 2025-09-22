"""
텔레그램 알림 시스템
실시간 주식 분석 결과를 텔레그램으로 전송
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import requests
from pathlib import Path
import os
import sys

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

try:
    from app.config.settings import settings
except ImportError:
    # 개발 환경에서 설정이 없을 경우 기본값 사용
    class MockSettings:
        telegram_enabled = False
        telegram_bot_token = ""
        telegram_chat_id = ""
    settings = MockSettings()

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """텔레그램 알림 발송 클래스"""
    
    def __init__(self):
        self.enabled = getattr(settings, 'telegram_enabled', False)
        self.bot_token = getattr(settings, 'telegram_bot_token', '')
        self.chat_id = getattr(settings, 'telegram_chat_id', '')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if self.enabled and not self.bot_token:
            logger.warning("텔레그램이 활성화되었지만 봇 토큰이 설정되지 않았습니다")
            self.enabled = False
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        텔레그램 메시지 전송
        
        Args:
            message: 전송할 메시지
            parse_mode: 메시지 파싱 모드 (Markdown, HTML)
            
        Returns:
            성공 여부
        """
        if not self.enabled:
            return False
            
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info("텔레그램 메시지 전송 성공")
                return True
            else:
                logger.error(f"텔레그램 메시지 전송 실패: {result.get('description')}")
                return False
                
        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 중 오류: {e}")
            return False
    
    def send_stock_alert(self, stock_info: Dict[str, Any]) -> bool:
        """
        주식 알림 메시지 전송
        
        Args:
            stock_info: 주식 정보 딕셔너리
        """
        try:
            symbol = stock_info.get('symbol', 'Unknown')
            name = stock_info.get('name', symbol)
            price = stock_info.get('current_price', 0)
            change = stock_info.get('change_percent', 0)
            signal = stock_info.get('signal', 'HOLD')
            confidence = stock_info.get('confidence', 0)
            
            # 이모지 설정
            signal_emoji = {
                'BUY': '🟢',
                'SELL': '🔴', 
                'HOLD': '🟡'
            }.get(signal, '⚪')
            
            change_emoji = '📈' if change > 0 else '📉' if change < 0 else '➡️'
            
            message = f"""
{signal_emoji} *주식 알림* {signal_emoji}

📊 *종목*: {name} ({symbol})
💰 *현재가*: {price:,.0f}원
{change_emoji} *변동률*: {change:+.2f}%
🎯 *신호*: {signal}
🔍 *신뢰도*: {confidence:.1%}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"주식 알림 전송 중 오류: {e}")
            return False
    
    def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """
        일일 요약 리포트 전송
        
        Args:
            summary_data: 요약 데이터
        """
        try:
            date = summary_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            total_stocks = summary_data.get('total_stocks', 0)
            buy_signals = summary_data.get('buy_signals', 0)
            sell_signals = summary_data.get('sell_signals', 0)
            avg_accuracy = summary_data.get('avg_accuracy', 0)
            top_picks = summary_data.get('top_picks', [])
            
            message = f"""
📊 *일일 주식 분석 요약* 📊

📅 *날짜*: {date}
🔍 *분석 종목*: {total_stocks}개
🟢 *매수 신호*: {buy_signals}개
🔴 *매도 신호*: {sell_signals}개
🎯 *평균 정확도*: {avg_accuracy:.1%}

🏆 *오늘의 추천 종목*:
            """.strip()
            
            for i, stock in enumerate(top_picks[:5], 1):
                name = stock.get('name', stock.get('symbol', 'Unknown'))
                expected_return = stock.get('expected_return', 0)
                confidence = stock.get('confidence', 0)
                message += f"\n{i}. {name} (기대수익률: {expected_return:+.1%}, 신뢰도: {confidence:.1%})"
            
            message += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"일일 요약 전송 중 오류: {e}")
            return False
    
    def send_market_status(self, market_data: Dict[str, Any]) -> bool:
        """
        시장 현황 알림 전송
        
        Args:
            market_data: 시장 데이터
        """
        try:
            market = market_data.get('market', 'KR')
            status = market_data.get('status', 'UNKNOWN')
            indices = market_data.get('indices', {})
            
            market_name = {'KR': '🇰🇷 한국', 'US': '🇺🇸 미국'}.get(market, market)
            status_emoji = {
                'OPEN': '🟢',
                'CLOSED': '🔴',
                'PRE_MARKET': '🟡',
                'AFTER_HOURS': '🟠'
            }.get(status, '⚪')
            
            message = f"""
{status_emoji} *{market_name} 시장 현황* {status_emoji}

📊 *상태*: {status}
            """.strip()
            
            # 주요 지수 정보 추가
            for index_name, index_data in indices.items():
                value = index_data.get('value', 0)
                change = index_data.get('change_percent', 0)
                change_emoji = '📈' if change > 0 else '📉' if change < 0 else '➡️'
                message += f"\n{change_emoji} *{index_name}*: {value:,.2f} ({change:+.2f}%)"
            
            message += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"시장 현황 전송 중 오류: {e}")
            return False
    
    def send_error_alert(self, error_info: Dict[str, Any]) -> bool:
        """
        시스템 오류 알림 전송
        
        Args:
            error_info: 오류 정보
        """
        try:
            component = error_info.get('component', 'Unknown')
            error_type = error_info.get('error_type', 'Error')
            message_text = error_info.get('message', 'Unknown error')
            
            message = f"""
🚨 *시스템 오류 알림* 🚨

🔧 *컴포넌트*: {component}
⚠️ *오류 유형*: {error_type}
📝 *메시지*: {message_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

관리자 확인이 필요합니다.
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"오류 알림 전송 중 오류: {e}")
            return False

# 전역 텔레그램 알림 인스턴스
telegram_notifier = TelegramNotifier()

async def send_telegram_notification(message_type: str, data: Dict[str, Any]) -> bool:
    """
    비동기 텔레그램 알림 전송
    
    Args:
        message_type: 메시지 타입 (stock_alert, daily_summary, market_status, error_alert)
        data: 전송할 데이터
        
    Returns:
        성공 여부
    """
    try:
        if message_type == 'stock_alert':
            return telegram_notifier.send_stock_alert(data)
        elif message_type == 'daily_summary':
            return telegram_notifier.send_daily_summary(data)
        elif message_type == 'market_status':
            return telegram_notifier.send_market_status(data)
        elif message_type == 'error_alert':
            return telegram_notifier.send_error_alert(data)
        else:
            logger.warning(f"알 수 없는 메시지 타입: {message_type}")
            return False
            
    except Exception as e:
        logger.error(f"텔레그램 알림 전송 실패: {e}")
        return False

# 테스트 함수
def test_telegram_integration():
    """텔레그램 연동 테스트"""
    print("📱 텔레그램 연동 테스트 시작...")
    
    # 테스트 메시지
    test_message = f"""
🧪 *테스트 메시지* 🧪

주식 분석 시스템 텔레그램 연동 테스트입니다.

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """.strip()
    
    success = telegram_notifier.send_message(test_message)
    
    if success:
        print("✅ 텔레그램 연동 테스트 성공!")
        
        # 주식 알림 테스트
        test_stock = {
            'symbol': 'TEST',
            'name': '테스트 종목',
            'current_price': 50000,
            'change_percent': 2.5,
            'signal': 'BUY',
            'confidence': 0.85
        }
        telegram_notifier.send_stock_alert(test_stock)
        
    else:
        print("❌ 텔레그램 연동 테스트 실패")
    
    return success

if __name__ == "__main__":
    # 직접 실행 시 테스트
    test_telegram_integration()
