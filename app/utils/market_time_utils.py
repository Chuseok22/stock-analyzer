"""
시장 시간 관리 유틸리티
- 동적 서머타임 계산
- 시장 운영 시간 정보
- 시간대 변환 및 검증
"""
from datetime import datetime, time, timedelta
from typing import Tuple, Dict, Optional
from enum import Enum
import pytz
from dataclasses import dataclass


class MarketRegion(Enum):
    """시장 지역"""
    KR = "KR"
    US = "US"


@dataclass
class MarketHours:
    """시장 운영 시간 정보"""
    region: MarketRegion
    premarket_start: time
    premarket_end: time
    regular_start: time
    regular_end: time
    aftermarket_start: time
    aftermarket_end: time
    timezone: str
    local_name: str


@dataclass
class MarketTimeInfo:
    """시장 시간 정보 (한국 시간 기준)"""
    region: MarketRegion
    premarket_kr: Tuple[int, int]  # (hour, minute)
    regular_start_kr: Tuple[int, int]
    regular_end_kr: Tuple[int, int]
    aftermarket_end_kr: Tuple[int, int]
    local_hours: MarketHours
    is_dst_active: bool
    formatted_schedule: str


class MarketTimeManager:
    """시장 시간 관리자"""
    
    def __init__(self):
        self.kr_timezone = pytz.timezone('Asia/Seoul')
        self.us_timezone = pytz.timezone('America/New_York')
        
        # 기본 시장 운영 시간 (현지 시간 기준)
        self.market_hours = {
            MarketRegion.KR: MarketHours(
                region=MarketRegion.KR,
                premarket_start=time(8, 0),   # 08:00
                premarket_end=time(9, 0),     # 09:00
                regular_start=time(9, 0),     # 09:00
                regular_end=time(15, 30),     # 15:30
                aftermarket_start=time(15, 30), # 15:30
                aftermarket_end=time(18, 0),  # 18:00
                timezone="Asia/Seoul",
                local_name="한국"
            ),
            MarketRegion.US: MarketHours(
                region=MarketRegion.US,
                premarket_start=time(4, 0),   # 04:00 ET
                premarket_end=time(9, 30),    # 09:30 ET
                regular_start=time(9, 30),    # 09:30 ET
                regular_end=time(16, 0),      # 16:00 ET
                aftermarket_start=time(16, 0), # 16:00 ET
                aftermarket_end=time(20, 0),  # 20:00 ET
                timezone="America/New_York",
                local_name="미국"
            )
        }
    
    def _is_dst_active(self) -> bool:
        """현재 서머타임 적용 여부 확인"""
        now_us = datetime.now(self.us_timezone)
        return now_us.dst() != timedelta(0)
    
    def _convert_us_time_to_kr(self, us_hour: int, us_minute: int = 0) -> Tuple[int, int]:
        """미국 현지 시간을 한국 시간으로 동적 변환 (서머타임 자동 고려)"""
        # 현재 날짜 기준으로 미국 시간 생성
        now_us = datetime.now(self.us_timezone)
        us_time = now_us.replace(hour=us_hour, minute=us_minute, second=0, microsecond=0)
        
        # 한국 시간으로 변환
        kr_time = us_time.astimezone(self.kr_timezone)
        
        return kr_time.hour, kr_time.minute
    
    def get_market_time_info(self, region: MarketRegion) -> MarketTimeInfo:
        """시장 시간 정보 조회 (한국 시간 기준)"""
        local_hours = self.market_hours[region]
        
        if region == MarketRegion.KR:
            # 한국은 변환 불필요
            return MarketTimeInfo(
                region=region,
                premarket_kr=(local_hours.premarket_start.hour, local_hours.premarket_start.minute),
                regular_start_kr=(local_hours.regular_start.hour, local_hours.regular_start.minute),
                regular_end_kr=(local_hours.regular_end.hour, local_hours.regular_end.minute),
                aftermarket_end_kr=(local_hours.aftermarket_end.hour, local_hours.aftermarket_end.minute),
                local_hours=local_hours,
                is_dst_active=False,
                formatted_schedule=self._format_kr_schedule(local_hours)
            )
        
        elif region == MarketRegion.US:
            # 미국 시간을 한국 시간으로 변환
            is_dst = self._is_dst_active()
            
            premarket_kr = self._convert_us_time_to_kr(
                local_hours.premarket_start.hour, 
                local_hours.premarket_start.minute
            )
            regular_start_kr = self._convert_us_time_to_kr(
                local_hours.regular_start.hour,
                local_hours.regular_start.minute
            )
            regular_end_kr = self._convert_us_time_to_kr(
                local_hours.regular_end.hour,
                local_hours.regular_end.minute
            )
            aftermarket_end_kr = self._convert_us_time_to_kr(
                local_hours.aftermarket_end.hour,
                local_hours.aftermarket_end.minute
            )
            
            return MarketTimeInfo(
                region=region,
                premarket_kr=premarket_kr,
                regular_start_kr=regular_start_kr,
                regular_end_kr=regular_end_kr,
                aftermarket_end_kr=aftermarket_end_kr,
                local_hours=local_hours,
                is_dst_active=is_dst,
                formatted_schedule=self._format_us_schedule(local_hours, is_dst)
            )
    
    def _format_kr_schedule(self, hours: MarketHours) -> str:
        """한국 시장 스케줄 포맷팅"""
        return f"""📅 **한국 시장 운영 시간** (KST)
🌅 프리마켓: {hours.premarket_start.strftime('%H:%M')} - {hours.premarket_end.strftime('%H:%M')}
📈 정규장: {hours.regular_start.strftime('%H:%M')} - {hours.regular_end.strftime('%H:%M')}
🌙 애프터마켓: {hours.aftermarket_start.strftime('%H:%M')} - {hours.aftermarket_end.strftime('%H:%M')}"""
    
    def _format_us_schedule(self, hours: MarketHours, is_dst: bool) -> str:
        """미국 시장 스케줄 포맷팅"""
        timezone_name = "EDT" if is_dst else "EST"
        dst_status = "서머타임" if is_dst else "표준시"
        
        # 한국 시간으로 변환된 시간들
        premarket_kr = self._convert_us_time_to_kr(hours.premarket_start.hour, hours.premarket_start.minute)
        regular_start_kr = self._convert_us_time_to_kr(hours.regular_start.hour, hours.regular_start.minute)
        regular_end_kr = self._convert_us_time_to_kr(hours.regular_end.hour, hours.regular_end.minute)
        aftermarket_end_kr = self._convert_us_time_to_kr(hours.aftermarket_end.hour, hours.aftermarket_end.minute)
        
        return f"""📅 **미국 시장 운영 시간** ({timezone_name} - {dst_status})
🌅 프리마켓: {hours.premarket_start.strftime('%H:%M')} - {hours.premarket_end.strftime('%H:%M')} ET
   → 한국시간: {premarket_kr[0]:02d}:{premarket_kr[1]:02d} - {regular_start_kr[0]:02d}:{regular_start_kr[1]:02d}
📈 정규장: {hours.regular_start.strftime('%H:%M')} - {hours.regular_end.strftime('%H:%M')} ET
   → 한국시간: {regular_start_kr[0]:02d}:{regular_start_kr[1]:02d} - {regular_end_kr[0]:02d}:{regular_end_kr[1]:02d}
🌙 애프터마켓: {hours.aftermarket_start.strftime('%H:%M')} - {hours.aftermarket_end.strftime('%H:%M')} ET
   → 한국시간: {regular_end_kr[0]:02d}:{regular_end_kr[1]:02d} - {aftermarket_end_kr[0]:02d}:{aftermarket_end_kr[1]:02d}"""
    
    def get_market_status(self, region: MarketRegion) -> Dict[str, any]:
        """현재 시장 상태 조회"""
        time_info = self.get_market_time_info(region)
        now = datetime.now(self.kr_timezone)
        
        # 현재 시간을 시:분으로 변환
        current_time = now.hour * 60 + now.minute
        
        if region == MarketRegion.KR:
            premarket_start = time_info.premarket_kr[0] * 60 + time_info.premarket_kr[1]
            regular_start = time_info.regular_start_kr[0] * 60 + time_info.regular_start_kr[1]
            regular_end = time_info.regular_end_kr[0] * 60 + time_info.regular_end_kr[1]
            aftermarket_end = time_info.aftermarket_end_kr[0] * 60 + time_info.aftermarket_end_kr[1]
        
        else:  # US
            premarket_start = time_info.premarket_kr[0] * 60 + time_info.premarket_kr[1]
            regular_start = time_info.regular_start_kr[0] * 60 + time_info.regular_start_kr[1]
            regular_end = time_info.regular_end_kr[0] * 60 + time_info.regular_end_kr[1]
            aftermarket_end = time_info.aftermarket_end_kr[0] * 60 + time_info.aftermarket_end_kr[1]
            
            # 다음날로 넘어가는 경우 처리
            if aftermarket_end < premarket_start:
                if current_time < 12 * 60:  # 오전이면 다음날 계산
                    current_time += 24 * 60
                aftermarket_end += 24 * 60
                regular_end += 24 * 60 if regular_end < premarket_start else 0
                regular_start += 24 * 60 if regular_start < premarket_start else 0
        
        # 시장 상태 판단
        if current_time < premarket_start:
            status = "CLOSED"
            next_event = "PREMARKET_OPEN"
        elif premarket_start <= current_time < regular_start:
            status = "PREMARKET"
            next_event = "MARKET_OPEN"
        elif regular_start <= current_time < regular_end:
            status = "OPEN"
            next_event = "MARKET_CLOSE"
        elif regular_end <= current_time < aftermarket_end:
            status = "AFTERMARKET"
            next_event = "MARKET_CLOSED"
        else:
            status = "CLOSED"
            next_event = "PREMARKET_OPEN"
        
        return {
            "status": status,
            "next_event": next_event,
            "time_info": time_info,
            "current_time_kr": now.strftime("%H:%M"),
            "is_trading_day": True  # TODO: 휴일 체크 로직 추가
        }
    
    def get_next_market_event(self, region: MarketRegion) -> Dict[str, any]:
        """다음 시장 이벤트 정보"""
        market_status = self.get_market_status(region)
        time_info = market_status["time_info"]
        
        event_times = {
            "PREMARKET_OPEN": time_info.premarket_kr,
            "MARKET_OPEN": time_info.regular_start_kr,
            "MARKET_CLOSE": time_info.regular_end_kr,
            "MARKET_CLOSED": time_info.aftermarket_end_kr
        }
        
        next_event = market_status["next_event"]
        next_time = event_times.get(next_event)
        
        if next_time:
            now = datetime.now(self.kr_timezone)
            next_datetime = now.replace(
                hour=next_time[0], 
                minute=next_time[1], 
                second=0, 
                microsecond=0
            )
            
            # 다음날인 경우
            if next_datetime <= now:
                next_datetime += timedelta(days=1)
            
            time_until = next_datetime - now
            
            return {
                "event": next_event,
                "time": f"{next_time[0]:02d}:{next_time[1]:02d}",
                "time_until": time_until,
                "hours_until": int(time_until.total_seconds() / 3600),
                "minutes_until": int((time_until.total_seconds() % 3600) / 60)
            }
        
        return None


# 전역 인스턴스
market_time_manager = MarketTimeManager()


def get_market_schedule_message(region: MarketRegion) -> str:
    """시장 스케줄 메시지 생성"""
    time_info = market_time_manager.get_market_time_info(region)
    return time_info.formatted_schedule


def get_market_status_message(region: MarketRegion) -> str:
    """시장 상태 메시지 생성"""
    status = market_time_manager.get_market_status(region)
    time_info = status["time_info"]
    
    status_names = {
        "CLOSED": "⏰ 시장 마감",
        "PREMARKET": "🌅 프리마켓 진행중",
        "OPEN": "📈 정규장 진행중", 
        "AFTERMARKET": "🌙 애프터마켓 진행중"
    }
    
    current_status = status_names.get(status["status"], "알 수 없음")
    current_time = status["current_time_kr"]
    
    message = f"🕐 **현재 시간**: {current_time} (한국시간)\n"
    message += f"📊 **시장 상태**: {current_status}\n\n"
    
    # 다음 이벤트 정보
    next_event = market_time_manager.get_next_market_event(region)
    if next_event:
        event_names = {
            "PREMARKET_OPEN": "🌅 프리마켓 시작",
            "MARKET_OPEN": "📈 정규장 시작",
            "MARKET_CLOSE": "📊 정규장 마감",
            "MARKET_CLOSED": "🌙 시장 완전 마감"
        }
        
        event_name = event_names.get(next_event["event"], next_event["event"])
        message += f"⏰ **다음 이벤트**: {event_name}\n"
        message += f"🕐 **시간**: {next_event['time']} ({next_event['hours_until']}시간 {next_event['minutes_until']}분 후)\n\n"
    
    message += time_info.formatted_schedule
    
    return message


if __name__ == "__main__":
    # 테스트
    manager = MarketTimeManager()
    
    print("=== 한국 시장 ===")
    kr_info = manager.get_market_time_info(MarketRegion.KR)
    print(kr_info.formatted_schedule)
    print()
    
    print("=== 미국 시장 ===")
    us_info = manager.get_market_time_info(MarketRegion.US)
    print(us_info.formatted_schedule)
    print()
    
    print("=== 현재 상태 ===")
    print(get_market_status_message(MarketRegion.US))