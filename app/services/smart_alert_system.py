"""
스마트 알림 시스템
- US 프리마켓 알림 (장 시작 30분 전)
- 하락장 경고 알림 
- 글로벌 시장 동향 알림
- 위험 관리 알림
"""
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import List, Dict, Any, Optional
import asyncio
from dataclasses import dataclass
from enum import Enum
import pytz
import json

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockMaster, MarketRegion
from app.ml.global_ml_engine import GlobalMLEngine, MarketRegime, GlobalPrediction
from app.services.notification import NotificationService
from app.utils.market_time_utils import MarketTimeManager
from app.config.settings import settings


class AlertType(Enum):
    """알림 유형"""
    PREMARKET_RECOMMENDATIONS = "premarket_recommendations"
    BEAR_MARKET_WARNING = "bear_market_warning"
    MARKET_REGIME_CHANGE = "market_regime_change"
    HIGH_RISK_ALERT = "high_risk_alert"
    PROFIT_OPPORTUNITY = "profit_opportunity"
    CRISIS_MODE_ALERT = "crisis_mode_alert"


class MarketTime(Enum):
    """시장 시간대"""
    KR_MARKET_OPEN = "09:00"  # 한국 시장 개장
    KR_MARKET_CLOSE = "15:30"  # 한국 시장 마감
    US_PREMARKET = "06:00"    # 미국 프리마켓 알림 (동부시간 20:00 = 한국시간 06:00)
    US_MARKET_OPEN = "09:30"  # 미국 시장 개장 (동부시간)
    US_MARKET_CLOSE = "16:00"  # 미국 시장 마감 (동부시간)


@dataclass
class SmartAlert:
    """스마트 알림 데이터"""
    alert_type: AlertType
    market_region: str
    title: str
    message: str
    stocks: List[Dict[str, Any]]
    urgency_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    action_required: bool
    recommendations: List[str]
    created_at: datetime


class SmartAlertSystem:
    """스마트 알림 시스템"""
    
    def __init__(self):
        self.ml_engine = GlobalMLEngine()
        self.notification_service = NotificationService()
        self.market_time_manager = MarketTimeManager()
        
        # 하락장 감지 시스템 통합
        try:
            from app.services.bear_market_detector import BearMarketDetector
            self.bear_detector = BearMarketDetector()
            print("🐻 하락장 감지 시스템 통합 완료")
        except Exception as e:
            print(f"⚠️ 하락장 감지 시스템 로드 실패: {e}")
            self.bear_detector = None
        
        # 시간대 설정
        self.kr_timezone = pytz.timezone('Asia/Seoul')
        self.us_timezone = pytz.timezone('America/New_York')
        
        # 마지막 알림 시간 추적
        self.last_alerts = {}
        
        print("📢 스마트 알림 시스템 초기화")
    
    def should_send_premarket_alert(self) -> bool:
        """프리마켓 알림 전송 시점 확인"""
        now_kr = datetime.now(self.kr_timezone)
        target_time = now_kr.replace(hour=6, minute=0, second=0, microsecond=0)
        
        # 06:00 ~ 06:30 사이에만 전송
        return target_time <= now_kr <= target_time + timedelta(minutes=30)
    
    def should_send_market_close_alert(self, region: MarketRegion) -> bool:
        """장 마감 후 알림 전송 시점 확인"""
        if region == MarketRegion.KR:
            now = datetime.now(self.kr_timezone)
            # 한국: 15:30 마감 후 16:00에 알림
            target_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
            return target_time <= now <= target_time + timedelta(minutes=30)
        
        elif region == MarketRegion.US:
            now = datetime.now(self.us_timezone)
            # 미국: 16:00 마감 후 16:30에 알림 (현지시간)
            target_time = now.replace(hour=16, minute=30, second=0, microsecond=0)
            return target_time <= now <= target_time + timedelta(minutes=30)
        
        return False
    
    def generate_premarket_alert(self) -> Optional[SmartAlert]:
        """미국 프리마켓 알림 생성"""
        print("🌅 US 프리마켓 알림 생성 중...")
        
        try:
            # 시장 체제 분석
            market_condition = self.ml_engine.detect_market_regime()
            
            # 미국 주식 예측
            us_predictions = self.ml_engine.predict_stocks(MarketRegion.US, top_n=5)
            
            if not us_predictions:
                print("   ⚠️ 미국 예측 데이터 없음")
                return None
            
            # 시장 시간 정보 가져오기
            market_schedule = self.market_time_manager.get_market_schedule_info()
            dst_status = self.market_time_manager.format_dst_status()
            
            # 알림 메시지 구성 (한국 시간대 명시)
            kr_time_str = datetime.now(self.kr_timezone).strftime('%m/%d %H:%M KST')
            title = f"🇺🇸 미국 프리마켓 추천 종목 ({kr_time_str})"
            
            # 시장 운영 시간 정보 추가
            time_info = f"🕐 **오늘 미국 시장 운영 시간**\n"
            time_info += f"📅 {market_schedule['today_date']}\n"
            time_info += f"🌍 {dst_status}\n"
            time_info += f"• 프리마켓: {market_schedule['premarket']['us_time']} (현지) / {market_schedule['premarket']['kr_time']} (한국)\n"
            time_info += f"• 정규장: {market_schedule['regular']['us_time']} (현지) / {market_schedule['regular']['kr_time']} (한국)\n"
            time_info += f"• 애프터마켓: {market_schedule['aftermarket']['us_time']} (현지) / {market_schedule['aftermarket']['kr_time']} (한국)\n\n"
            
            # 시장 상황 요약
            regime_emoji = {
                MarketRegime.BULL_MARKET: "🐂",
                MarketRegime.BEAR_MARKET: "🐻", 
                MarketRegime.SIDEWAYS_MARKET: "🦀",
                MarketRegime.HIGH_VOLATILITY: "⚡",
                MarketRegime.CRISIS_MODE: "🚨"
            }
            
            regime_name = {
                MarketRegime.BULL_MARKET: "강세장",
                MarketRegime.BEAR_MARKET: "약세장",
                MarketRegime.SIDEWAYS_MARKET: "횡보장", 
                MarketRegime.HIGH_VOLATILITY: "고변동성",
                MarketRegime.CRISIS_MODE: "위기상황"
            }
            
            market_summary = f"{regime_emoji.get(market_condition.regime, '📊')} **시장 체제 분석**\n"
            market_summary += f"• 현재 체제: {regime_name.get(market_condition.regime, '분석중')}\n"
            market_summary += f"• 변동성: {market_condition.volatility_level:.1%}\n"
            market_summary += f"• 공포/탐욕: {market_condition.fear_greed_index:.0f}/100\n"
            market_summary += f"• 리스크: {market_condition.risk_level}\n\n"
            
            # 추천 종목 정보
            stock_info = []
            message_lines = [time_info, market_summary, "🎯 **오늘의 추천 종목**"]
            
            for i, pred in enumerate(us_predictions[:5], 1):
                # 추천 등급 이모지
                rec_emoji = {
                    "STRONG_BUY": "🚀",
                    "BUY": "📈", 
                    "HOLD": "⏸️",
                    "SELL": "📉",
                    "STRONG_SELL": "🔻"
                }
                
                emoji = rec_emoji.get(pred.recommendation, "📊")
                
                stock_line = f"{i}. {emoji} **{pred.stock_code}** "
                stock_line += f"예상 수익률: **{pred.predicted_return:+.1f}%** "
                stock_line += f"({pred.recommendation})"
                
                if pred.target_price:
                    stock_line += f"\n   💰 목표가: ${pred.target_price:.2f}"
                
                if pred.reasoning:
                    main_reason = pred.reasoning[0] if pred.reasoning else "기술적 분석"
                    stock_line += f"\n   📝 {main_reason}"
                
                message_lines.append(stock_line)
                
                # 구조화된 데이터
                stock_info.append({
                    'code': pred.stock_code,
                    'predicted_return': pred.predicted_return,
                    'recommendation': pred.recommendation,
                    'confidence': pred.confidence_score,
                    'target_price': pred.target_price,
                    'reasoning': pred.reasoning
                })
            
            # 위험 관리 조언
            recommendations = []
            
            if market_condition.risk_level == "CRITICAL":
                recommendations.extend([
                    "🚨 극도로 위험한 시장 상황입니다",
                    "💰 포지션 크기를 최소화하세요",
                    "🛡️ 손절가를 엄격히 준수하세요"
                ])
            elif market_condition.risk_level == "HIGH":
                recommendations.extend([
                    "⚠️ 높은 리스크 환경입니다",
                    "📊 분할 매수를 고려하세요",
                    "🔍 시장 상황을 면밀히 모니터링하세요"
                ])
            else:
                recommendations.extend([
                    f"💡 미국 시장 개장까지 약 30분 남았습니다",
                    "📈 프리마켓 동향을 확인하세요",
                    "🎯 계획된 진입점을 준수하세요"
                ])
            
            # 최종 메시지
            message = "\n".join(message_lines)
            
            if recommendations:
                message += "\n\n🎯 **투자 조언**\n"
                message += "\n".join(f"• {rec}" for rec in recommendations)
            
            # 긴급도 결정
            urgency_level = "HIGH" if market_condition.risk_level in ["HIGH", "CRITICAL"] else "MEDIUM"
            
            alert = SmartAlert(
                alert_type=AlertType.PREMARKET_RECOMMENDATIONS,
                market_region="US",
                title=title,
                message=message,
                stocks=stock_info,
                urgency_level=urgency_level,
                action_required=True,
                recommendations=recommendations,
                created_at=datetime.now()
            )
            
            print("   ✅ 프리마켓 알림 생성 완료")
            return alert
            
        except Exception as e:
            print(f"   ❌ 프리마켓 알림 생성 실패: {e}")
            return None
    
    async def generate_korean_premarket_recommendations(self, predictions: List[GlobalPrediction]) -> Optional[SmartAlert]:
        """한국 프리마켓 추천 알림 생성 (08:30 - 장 시작 30분 전)"""
        print("🇰🇷 한국 프리마켓 추천 알림 생성 중...")
        
        try:
            if not predictions:
                print("   ⚠️ 예측 데이터 없음")
                return None
            
            # 시장 체제 분석
            market_condition = self.ml_engine.detect_market_regime()
            
            # 제목 생성 (한국 시간대 명시)
            kr_time_str = datetime.now(self.kr_timezone).strftime('%m/%d %H:%M KST')
            title = f"🇰🇷 한국 주식 프리마켓 추천 ({kr_time_str})"
            
            # 메시지 구성
            message_lines = [
                f"📊 **한국 시장 프리마켓 분석**",
                f"🕘 장 시작까지 30분 남음 (09:00 개장)",
                "",
                f"🎯 **시장 체제**: {market_condition.regime.value}",
                f"📈 **리스크 레벨**: {market_condition.risk_level}",
                f"💪 **트렌드 강도**: {market_condition.trend_strength:.2f}",
                "",
                "🏆 **오늘의 추천 종목**"
            ]
            
            # 상위 5개 종목 정보
            stock_info = []
            for i, pred in enumerate(predictions[:5], 1):
                symbol = pred.stock_code  # stock_code 속성 사용
                score = pred.predicted_return
                confidence = pred.confidence_score
                direction = "📈 상승" if score > 0 else "📉 하락"
                
                stock_info.append({
                    "symbol": symbol,
                    "score": score,
                    "confidence": confidence,
                    "direction": direction
                })
                
                message_lines.append(
                    f"{i}. **{symbol}** {direction} (신뢰도: {confidence:.1%})"
                )
            
            # 투자 조언 생성
            recommendations = []
            
            # 시장 상황에 따른 조언
            if market_condition.risk_level == "CRITICAL":
                recommendations.extend([
                    "🚨 극도로 위험한 시장 상황입니다",
                    "💰 포지션 크기를 최소화하세요", 
                    "🛡️ 손절가를 엄격히 준수하세요",
                    "📊 장 초반 30분은 관망하는 것을 권장합니다"
                ])
            elif market_condition.risk_level == "HIGH":
                recommendations.extend([
                    "⚠️ 높은 리스크 환경입니다",
                    "📊 분할 매수를 고려하세요",
                    "🔍 시장 상황을 면밀히 모니터링하세요",
                    "💡 개장 직후 급등락에 주의하세요"
                ])
            else:
                recommendations.extend([
                    "💡 한국 시장 개장까지 약 30분 남았습니다",
                    "📈 프리마켓 분석을 참고하세요",
                    "🎯 계획된 진입점을 준수하세요",
                    "📊 09:00 개장 후 첫 10분간 거래량을 확인하세요"
                ])
            
            # 최종 메시지
            message = "\n".join(message_lines)
            
            if recommendations:
                message += "\n\n🎯 **투자 조언**\n"
                message += "\n".join(f"• {rec}" for rec in recommendations)
            
            # 면책조항
            message += "\n\n⚠️ *본 정보는 투자 참고용이며, 투자 결정은 본인 책임입니다.*"
            
            # 긴급도 결정
            urgency_level = "HIGH" if market_condition.risk_level in ["HIGH", "CRITICAL"] else "MEDIUM"
            
            alert = SmartAlert(
                alert_type=AlertType.PREMARKET_RECOMMENDATIONS,
                market_region="KR",
                title=title,
                message=message,
                stocks=stock_info,
                urgency_level=urgency_level,
                action_required=True,
                recommendations=recommendations,
                created_at=datetime.now()
            )
            
            print("   ✅ 한국 프리마켓 알림 생성 완료")
            return alert
            
        except Exception as e:
            print(f"   ❌ 한국 프리마켓 알림 생성 실패: {e}")
            import traceback
            print(f"   상세 오류: {traceback.format_exc()}")
            return None
    
    async def generate_bear_market_warning(self) -> Optional[SmartAlert]:
        """하락장 경고 알림 생성 - 고도화된 감지 시스템 사용"""
        print("🐻 하락장 경고 알림 검사 중...")
        
        try:
            # 1. 고도화된 하락장 감지 시스템 사용
            if self.bear_detector:
                bear_alert = await self.bear_detector.generate_bear_market_alert()
                
                if bear_alert:
                    print(f"   🚨 고도화된 하락장 감지: {bear_alert['severity']}")
                    
                    # 하락장 알림을 SmartAlert 형식으로 변환
                    return SmartAlert(
                        alert_type=AlertType.BEAR_MARKET_WARNING,
                        market_region="GLOBAL",
                        title=bear_alert['title'],
                        message=bear_alert['message'],
                        stocks=[{
                            'code': rec.etf_code,
                            'name': rec.etf_name,
                            'expected_return': rec.expected_return,
                            'allocation': rec.target_allocation,
                            'risk_level': rec.risk_level
                        } for rec in bear_alert.get('recommendations', [])],
                        urgency_level=bear_alert['urgency_level'],
                        action_required=True,
                        recommendations=[
                            f"인버스 ETF 포지션 고려",
                            f"리스크 관리 강화",
                            f"포트폴리오 방어적 조정"
                        ],
                        created_at=datetime.now()
                    )
            
            # 2. 기본 하락장 감지 로직 (폴백)
            print("   🔄 기본 하락장 감지 로직 사용...")
            
            # 시장 체제 분석
            market_condition = self.ml_engine.detect_market_regime()
            
            # 하락장이 아니면 알림 없음
            if market_condition.regime not in [MarketRegime.BEAR_MARKET, MarketRegime.CRISIS_MODE]:
                return None
            
            # 한국/미국 시장 모두 분석
            kr_predictions = await self.ml_engine.predict_stocks(MarketRegion.KR, top_n=10)
            us_predictions = await self.ml_engine.predict_stocks(MarketRegion.US, top_n=10)
            
            # 전반적인 부정적 전망 체크
            kr_negative = sum(1 for p in kr_predictions if p.predicted_return < -2) / len(kr_predictions) if kr_predictions else 0
            us_negative = sum(1 for p in us_predictions if p.predicted_return < -2) / len(us_predictions) if us_predictions else 0
            
            overall_negative = (kr_negative + us_negative) / 2
            
            # 50% 이상이 부정적이면 경고 발송
            if overall_negative < 0.5:
                return None
            
            # 경고 메시지 구성 (한국 시간대 명시)
            kr_time_str = datetime.now(self.kr_timezone).strftime('%m/%d %H:%M KST')
            title = f"🚨 하락장 경고 - 포지션 정리 권고 ({kr_time_str})"
            
            severity_level = "위험" if market_condition.regime == MarketRegime.BEAR_MARKET else "심각"
            
            # 시장 시간 정보 추가
            market_schedule = self.market_time_manager.get_market_schedule_info()
            current_status = self.market_time_manager.get_current_market_status()
            
            time_info = f"⏰ **현재 시장 상황**\n"
            time_info += f"📅 {market_schedule['today_date']}\n"
            time_info += f"🔄 현재 상태: {current_status['status']}\n"
            
            if current_status['status'] == '정규장':
                time_info += f"⚠️ 현재 거래 시간 중입니다 - 즉시 대응 필요\n"
            elif current_status['status'] == '프리마켓':
                time_info += f"📈 프리마켓 시간 - 정규장 전 대응 준비\n"
            elif current_status['status'] == '애프터마켓':
                time_info += f"📉 애프터마켓 - 다음 거래일 대응 계획 수립\n"
            else:
                time_info += f"🛑 시장 마감 - 다음 거래일 대응 준비\n"
            
            time_info += f"• 다음 정규장: {market_schedule['regular']['us_time']} (미국) / {market_schedule['regular']['kr_time']} (한국)\n\n"
            
            message = f"⚠️ **{severity_level}한 시장 상황이 감지되었습니다**\n\n"
            message += time_info
            
            message += f"📊 **시장 분석 결과**\n"
            message += f"• 시장 체제: {market_condition.regime.value}\n"
            message += f"• 변동성 수준: {market_condition.volatility_level:.1%}\n"
            message += f"• 공포 지수: {market_condition.fear_greed_index:.0f}/100\n"
            message += f"• 리스크 레벨: {market_condition.risk_level}\n\n"
            
            message += f"📈 **시장 전망**\n"
            message += f"• 🇰🇷 한국 종목 부정적 비율: {kr_negative:.0%}\n"
            message += f"• 🇺🇸 미국 종목 부정적 비율: {us_negative:.0%}\n\n"
            
            # 권고사항
            recommendations = []
            
            if market_condition.regime == MarketRegime.CRISIS_MODE:
                recommendations.extend([
                    "🚨 즉시 모든 리스크 포지션 정리를 권합니다",
                    "💰 현금 비중을 80% 이상으로 늘리세요",
                    "📉 숏 포지션이나 인버스 ETF 고려",
                    "🛡️ 방어적 자산(금, 채권) 투자 검토"
                ])
            else:  # BEAR_MARKET
                recommendations.extend([
                    "⚠️ 포지션 크기를 50% 이상 줄이세요",
                    "💼 배당주나 방어주로 전환 고려",
                    "📊 분할 매도를 통한 점진적 정리",
                    "🎯 현금 확보로 향후 기회 대비"
                ])
            
            message += "🎯 **즉시 행동 권고**\n"
            message += "\n".join(f"• {rec}" for rec in recommendations)
            
            # 가장 위험한 종목들 표시
            all_predictions = (kr_predictions + us_predictions)
            risky_stocks = [p for p in all_predictions if p.predicted_return < -5][:5]
            
            if risky_stocks:
                message += "\n\n📉 **주의 종목 (5% 이상 하락 예상)**\n"
                for stock in risky_stocks:
                    flag = "🇰🇷" if stock.market_region == "KR" else "🇺🇸"
                    message += f"• {flag} {stock.stock_code}: {stock.predicted_return:+.1f}%\n"
            
            alert = SmartAlert(
                alert_type=AlertType.BEAR_MARKET_WARNING,
                market_region="GLOBAL",
                title=title,
                message=message,
                stocks=[],
                urgency_level="CRITICAL",
                action_required=True,
                recommendations=recommendations,
                created_at=datetime.now()
            )
            
            print(f"   🚨 하락장 경고 생성: {severity_level} 수준")
            return alert
            
        except Exception as e:
            print(f"   ❌ 하락장 경고 생성 실패: {e}")
            return None
    
    def generate_market_close_summary(self, region: MarketRegion) -> Optional[SmartAlert]:
        """장 마감 후 요약 알림 생성"""
        print(f"📊 {region.value} 장 마감 요약 생성 중...")
        
        try:
            # 해당 시장 예측 결과
            predictions = self.ml_engine.predict_stocks(region, top_n=10)
            
            if not predictions:
                return None
            
            # 시장 요약 통계
            total_stocks = len(predictions)
            positive_stocks = sum(1 for p in predictions if p.predicted_return > 0)
            negative_stocks = total_stocks - positive_stocks
            
            avg_return = sum(p.predicted_return for p in predictions) / total_stocks
            max_return = max(predictions, key=lambda x: x.predicted_return)
            min_return = min(predictions, key=lambda x: x.predicted_return)
            
            # 제목 및 시장 정보 (한국 시간대 명시)
            market_name = "한국" if region == MarketRegion.KR else "미국"
            kr_time_str = datetime.now(self.kr_timezone).strftime('%m/%d %H:%M KST')
            title = f"📊 {market_name} 시장 마감 후 분석 요약 ({kr_time_str})"
            
            # 내일 시장 시간 정보 (미국 시장용)
            time_info = ""
            if region == MarketRegion.US:
                tomorrow_schedule = self.market_time_manager.get_market_schedule_info(days_offset=1)
                dst_status = self.market_time_manager.format_dst_status()
                
                time_info = f"🕐 **내일 미국 시장 운영 시간**\n"
                time_info += f"📅 {tomorrow_schedule['today_date']}\n"
                time_info += f"🌍 {dst_status}\n"
                time_info += f"• 프리마켓: {tomorrow_schedule['premarket']['us_time']} (현지) / {tomorrow_schedule['premarket']['kr_time']} (한국)\n"
                time_info += f"• 정규장: {tomorrow_schedule['regular']['us_time']} (현지) / {tomorrow_schedule['regular']['kr_time']} (한국)\n"
                time_info += f"• 애프터마켓: {tomorrow_schedule['aftermarket']['us_time']} (현지) / {tomorrow_schedule['aftermarket']['kr_time']} (한국)\n\n"
            elif region == MarketRegion.KR:
                # 한국 시장은 고정 시간이므로 간단히 표시
                time_info = f"🕐 **내일 한국 시장 운영 시간**\n"
                time_info += f"• 정규장: 09:00 - 15:30 (한국시간)\n"
                time_info += f"• 동시호가: 08:30 - 09:00, 15:30 - 16:00\n\n"
            
            # 메시지 구성
            message = f"🏁 **{market_name} 시장 분석 완료**\n\n"
            
            if time_info:
                message += time_info
            
            message += f"📈 **시장 전망 요약**\n"
            message += f"• 전체 분석 종목: {total_stocks}개\n"
            message += f"• 상승 예상: {positive_stocks}개 ({positive_stocks/total_stocks:.0%})\n"
            message += f"• 하락 예상: {negative_stocks}개 ({negative_stocks/total_stocks:.0%})\n"
            message += f"• 평균 예상 수익률: {avg_return:+.1f}%\n\n"
            
            message += f"🎯 **주목 종목**\n"
            message += f"🔝 최고 기대: {max_return.stock_code} ({max_return.predicted_return:+.1f}%)\n"
            message += f"⚠️ 최대 리스크: {min_return.stock_code} ({min_return.predicted_return:+.1f}%)\n\n"
            
            # 상위 3개 추천
            top_3 = predictions[:3]
            message += f"🏆 **내일 상위 3개 추천**\n"
            for i, pred in enumerate(top_3, 1):
                rec_emoji = {"STRONG_BUY": "🚀", "BUY": "📈"}.get(pred.recommendation, "📊")
                message += f"{i}. {rec_emoji} {pred.stock_code}: {pred.predicted_return:+.1f}% ({pred.recommendation})\n"
            
            # 시장 조건에 따른 조언
            market_condition = self.ml_engine.market_condition
            recommendations = []
            
            if market_condition:
                if market_condition.risk_level == "LOW":
                    recommendations.append("💚 안정적인 시장 환경, 적극적 투자 고려")
                elif market_condition.risk_level == "HIGH":
                    recommendations.append("⚠️ 고위험 환경, 신중한 접근 필요")
                
                if avg_return > 2:
                    recommendations.append("📈 전반적 상승 모멘텀, 선별적 매수 기회")
                elif avg_return < -2:
                    recommendations.append("📉 조정 가능성, 현금 비중 확대 고려")
            
            if recommendations:
                message += "\n🎯 **내일 투자 전략**\n"
                message += "\n".join(f"• {rec}" for rec in recommendations)
            
            alert = SmartAlert(
                alert_type=AlertType.MARKET_REGIME_CHANGE,
                market_region=region.value,
                title=title,
                message=message,
                stocks=[{
                    'code': p.stock_code,
                    'predicted_return': p.predicted_return,
                    'recommendation': p.recommendation
                } for p in predictions[:5]],
                urgency_level="MEDIUM",
                action_required=False,
                recommendations=recommendations,
                created_at=datetime.now()
            )
            
            print(f"   ✅ {market_name} 마감 요약 생성 완료")
            return alert
            
        except Exception as e:
            print(f"   ❌ {region.value} 마감 요약 생성 실패: {e}")
            return None
    
    async def send_alert(self, alert: SmartAlert) -> bool:
        """알림 전송"""
        print(f"📢 알림 전송: {alert.title}")
        
        try:
            # Discord와 Telegram 동시 전송
            discord_success = await self._send_discord_message(alert)
            telegram_success = await self._send_telegram_message(alert)
            
            success_count = 0
            if discord_success:
                print(f"   ✅ Discord 전송 성공")
                success_count += 1
            else:
                print(f"   ❌ Discord 전송 실패")
                
            if telegram_success:
                print(f"   ✅ Telegram 전송 성공")
                success_count += 1
            else:
                print(f"   ❌ Telegram 전송 실패")
            
            # 하나라도 성공하면 성공으로 처리
            if success_count > 0:
                # 전송 기록 저장
                self.last_alerts[alert.alert_type.value] = datetime.now()
                print(f"   📊 알림 전송 완료: {success_count}/2 플랫폼")
                return True
            else:
                print(f"   ❌ 모든 플랫폼 전송 실패")
                return False
                
        except Exception as e:
            print(f"   ❌ 알림 전송 실패: {e}")
            return False
    
    async def _send_discord_message(self, alert: SmartAlert) -> bool:
        """Discord 메시지 전송"""
        try:
            # 기존 notification 서비스의 Discord 기능 활용
            from discord_webhook import DiscordWebhook, DiscordEmbed
            
            if not settings.discord_webhook_url:
                print("   ⚠️ Discord webhook URL 설정되지 않음")
                return False
            
            webhook = DiscordWebhook(url=settings.discord_webhook_url)
            
            # Embed 생성
            embed = DiscordEmbed(
                title=alert.title,
                description=alert.message[:2000],  # Discord 제한
                color=self._get_alert_color(alert.urgency_level)
            )
            
            # 추가 정보
            embed.add_embed_field(
                name="긴급도",
                value=alert.urgency_level,
                inline=True
            )
            
            embed.add_embed_field(
                name="시장",
                value=alert.market_region,
                inline=True
            )
            
            embed.add_embed_field(
                name="시간",
                value=alert.created_at.strftime("%Y-%m-%d %H:%M"),
                inline=True
            )
            
            webhook.add_embed(embed)
            response = webhook.execute()
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"   ❌ Discord 전송 에러: {e}")
            return False
    
    async def _send_telegram_message(self, alert: SmartAlert) -> bool:
        """Telegram 메시지 전송"""
        try:
            import requests
            
            # Telegram 설정 확인
            if not settings.telegram_bot_token or not settings.telegram_chat_id:
                print("   ⚠️ Telegram 설정이 완료되지 않음")
                return False
            
            # 안전한 텔레그램 메시지 형식 (마크다운 없이)
            message = f"""🚨 {alert.title}

긴급도: {alert.urgency_level}
시장: {alert.market_region}
시간: {alert.created_at.strftime("%Y-%m-%d %H:%M")}

{alert.message}"""
            
            # 추천사항이 있다면 추가
            if alert.recommendations:
                message += "\n\n📋 권장사항:\n"
                for i, rec in enumerate(alert.recommendations, 1):
                    message += f"{i}. {rec}\n"
            
            # Telegram API 호출 (마크다운 없이)
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": settings.telegram_chat_id,
                "text": message
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"   ❌ Telegram API 오류: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Telegram 전송 에러: {e}")
            return False
    
    def _get_alert_color(self, urgency_level: str) -> int:
        """긴급도별 색상 코드"""
        colors = {
            "LOW": 0x00FF00,      # 초록
            "MEDIUM": 0xFFFF00,   # 노랑  
            "HIGH": 0xFF8C00,     # 주황
            "CRITICAL": 0xFF0000  # 빨강
        }
        return colors.get(urgency_level, 0x808080)
    
    def should_send_alert(self, alert_type: AlertType, cooldown_hours: int = 1) -> bool:
        """알림 쿨다운 체크"""
        if alert_type.value not in self.last_alerts:
            return True
        
        last_sent = self.last_alerts[alert_type.value]
        cooldown_period = timedelta(hours=cooldown_hours)
        
        return datetime.now() - last_sent > cooldown_period
    
    async def run_alert_cycle(self):
        """알림 주기 실행"""
        print("🔄 스마트 알림 시스템 실행 중...")
        
        alerts_sent = 0
        
        try:
            # 1. 프리마켓 알림 체크 (미국)
            if self.should_send_premarket_alert():
                if self.should_send_alert(AlertType.PREMARKET_RECOMMENDATIONS, cooldown_hours=6):
                    premarket_alert = self.generate_premarket_alert()
                    if premarket_alert:
                        success = await self.send_alert(premarket_alert)
                        if success:
                            alerts_sent += 1
            
            # 2. 하락장 경고 체크
            if self.should_send_alert(AlertType.BEAR_MARKET_WARNING, cooldown_hours=4):
                bear_warning = self.generate_bear_market_warning()
                if bear_warning:
                    success = await self.send_alert(bear_warning)
                    if success:
                        alerts_sent += 1
            
            # 3. 한국 시장 마감 요약
            if self.should_send_market_close_alert(MarketRegion.KR):
                if self.should_send_alert(AlertType.MARKET_REGIME_CHANGE, cooldown_hours=8):
                    kr_summary = self.generate_market_close_summary(MarketRegion.KR)
                    if kr_summary:
                        success = await self.send_alert(kr_summary)
                        if success:
                            alerts_sent += 1
            
            # 4. 미국 시장 마감 요약 (한국 시간 새벽)
            if self.should_send_market_close_alert(MarketRegion.US):
                us_summary = self.generate_market_close_summary(MarketRegion.US)
                if us_summary:
                    success = await self.send_alert(us_summary)
                    if success:
                        alerts_sent += 1
            
            print(f"📊 알림 주기 완료: {alerts_sent}개 전송")
            return alerts_sent > 0
            
        except Exception as e:
            print(f"❌ 알림 주기 실행 실패: {e}")
            return False


async def main():
    """메인 실행"""
    alert_system = SmartAlertSystem()
    
    # 알림 주기 실행
    success = await alert_system.run_alert_cycle()
    
    if success:
        print("✅ 스마트 알림 시스템 실행 완료")
    else:
        print("⚠️ 전송된 알림 없음")
    
    return success


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
