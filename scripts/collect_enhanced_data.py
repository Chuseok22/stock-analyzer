#!/usr/bin/env python3
"""
새로운 스키마에 맞는 주식 데이터 수집 및 처리
최적화된 데이터 수집으로 ML 학습 데이터 품질 향상
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import json

# Add app directory to path  
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import (
    StockMaster, StockDailyPrice, StockTechnicalIndicator,
    TradingUniverse, TradingUniverseItem, MarketRegion
)
from app.services.kis_api import KISAPIClient
from app.database.redis_client import redis_client
from app.config.settings import settings


class EnhancedDataCollector:
    """향상된 데이터 수집기"""
    
    def __init__(self):
        self.kis_service = KISAPIClient()
        
        # 한국 주요 종목 리스트 (확장됨)
        self.korean_major_stocks = [
            {"code": "005930", "name": "삼성전자", "sector": "TECHNOLOGY"},
            {"code": "000660", "name": "SK하이닉스", "sector": "TECHNOLOGY"},
            {"code": "373220", "name": "LG에너지솔루션", "sector": "TECHNOLOGY"},
            {"code": "207940", "name": "삼성바이오로직스", "sector": "HEALTHCARE"},
            {"code": "005380", "name": "현대차", "sector": "CONSUMER_DISCRETIONARY"},
            {"code": "006400", "name": "삼성SDI", "sector": "TECHNOLOGY"},
            {"code": "051910", "name": "LG화학", "sector": "MATERIALS"},
            {"code": "035420", "name": "NAVER", "sector": "TECHNOLOGY"},
            {"code": "005490", "name": "POSCO홀딩스", "sector": "MATERIALS"},
            {"code": "068270", "name": "셀트리온", "sector": "HEALTHCARE"},
            {"code": "035720", "name": "카카오", "sector": "TECHNOLOGY"},
            {"code": "003670", "name": "포스코퓨처엠", "sector": "MATERIALS"},
            {"code": "000270", "name": "기아", "sector": "CONSUMER_DISCRETIONARY"},
            {"code": "096770", "name": "SK이노베이션", "sector": "ENERGY"},
            {"code": "323410", "name": "카카오뱅크", "sector": "FINANCE"},
            {"code": "066570", "name": "LG전자", "sector": "TECHNOLOGY"},
            {"code": "003550", "name": "LG", "sector": "INDUSTRIALS"},
            {"code": "017670", "name": "SK텔레콤", "sector": "TELECOMMUNICATIONS"},
            {"code": "034020", "name": "두산에너빌리티", "sector": "INDUSTRIALS"},
            {"code": "018260", "name": "삼성물산", "sector": "INDUSTRIALS"},
            {"code": "259960", "name": "크래프톤", "sector": "TECHNOLOGY"},
            {"code": "009150", "name": "삼성전기", "sector": "TECHNOLOGY"},
            {"code": "012330", "name": "현대모비스", "sector": "CONSUMER_DISCRETIONARY"},
            {"code": "028260", "name": "삼성물산우", "sector": "INDUSTRIALS"},
            {"code": "086790", "name": "하나금융지주", "sector": "FINANCE"},
            {"code": "015760", "name": "한국전력", "sector": "UTILITIES"},
            {"code": "316140", "name": "우리금융지주", "sector": "FINANCE"},
            {"code": "030200", "name": "KT", "sector": "TELECOMMUNICATIONS"},
            {"code": "011200", "name": "HMM", "sector": "INDUSTRIALS"},
            {"code": "105560", "name": "KB금융", "sector": "FINANCE"}
        ]
    
    def verify_kis_token(self) -> bool:
        """KIS 토큰 확인"""
        try:
            token = redis_client.get("kis:access_token")
            if token:
                ttl = redis_client.get_ttl("kis:access_token")
                print(f"✅ KIS 토큰 확인: TTL {ttl/3600:.1f}시간")
                return True
            else:
                print("❌ KIS 토큰이 없습니다!")
                return False
        except Exception as e:
            print(f"❌ KIS 토큰 확인 실패: {e}")
            return False
    
    def create_or_update_stock_master(self, stock_info: Dict[str, Any]) -> Optional[int]:
        """주식 마스터 정보 생성 또는 업데이트"""
        try:
            with get_db_session() as db:
                # 기존 종목 확인
                existing_stock = db.query(StockMaster).filter(
                    StockMaster.market_region == "KR",
                    StockMaster.stock_code == stock_info["code"]
                ).first()
                
                if existing_stock:
                    # 기존 종목 업데이트
                    existing_stock.stock_name = stock_info["name"]
                    existing_stock.sector_classification = stock_info.get("sector")
                    existing_stock.market_name = "KOSPI"  # 기본값
                    existing_stock.last_updated = datetime.now()
                    existing_stock.updated_at = datetime.now()
                    
                    db.commit()
                    return existing_stock.stock_id
                else:
                    # 새로운 종목 생성
                    new_stock = StockMaster(
                        market_region="KR",
                        stock_code=stock_info["code"],
                        stock_name=stock_info["name"],
                        sector_classification=stock_info.get("sector"),
                        market_name="KOSPI",
                        is_active=True,
                        data_provider="KIS",
                        last_updated=datetime.now()
                    )
                    
                    db.add(new_stock)
                    db.commit()
                    return new_stock.stock_id
                    
        except Exception as e:
            print(f"❌ 주식 마스터 처리 실패 ({stock_info['code']}): {e}")
            return None
    
    def collect_daily_price_data(self, stock_id: int, stock_code: str, days: int = 30) -> int:
        """일일 주가 데이터 수집"""
        try:
            # KIS API에서 주가 데이터 가져오기
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            price_data = self.kis_service.get_stock_price_daily(
                stock_code=stock_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            
            if not price_data:
                print(f"⚠️ {stock_code} 주가 데이터 없음")
                return 0
            
            collected_count = 0
            
            with get_db_session() as db:
                for data in price_data:
                    try:
                        trade_date = datetime.strptime(data['stck_bsop_date'], "%Y%m%d").date()
                        
                        # 기존 데이터 확인
                        existing_price = db.query(StockDailyPrice).filter(
                            StockDailyPrice.stock_id == stock_id,
                            StockDailyPrice.trade_date == trade_date
                        ).first()
                        
                        if existing_price:
                            continue  # 이미 존재하는 데이터는 스킵
                        
                        # OHLCV 데이터 처리
                        open_price = Decimal(str(data['stck_oprc']))
                        high_price = Decimal(str(data['stck_hgpr']))
                        low_price = Decimal(str(data['stck_lwpr']))
                        close_price = Decimal(str(data['stck_clpr']))
                        volume = int(data['acml_vol'])
                        
                        # 파생 지표 계산
                        if len(price_data) > 1:
                            # 이전 날짜 데이터 찾기
                            prev_close = None
                            current_date = data['stck_bsop_date']
                            for prev_data in price_data:
                                if prev_data['stck_bsop_date'] < current_date:
                                    prev_close = Decimal(str(prev_data['stck_clpr']))
                                    break
                            
                            if prev_close:
                                price_change = close_price - prev_close
                                price_change_pct = float((price_change / prev_close) * 100)
                                daily_return_pct = price_change_pct
                            else:
                                price_change = Decimal('0')
                                price_change_pct = 0.0
                                daily_return_pct = 0.0
                        else:
                            price_change = Decimal('0')
                            price_change_pct = 0.0
                            daily_return_pct = 0.0
                        
                        # VWAP 계산 (단순화)
                        vwap = close_price  # 실제로는 더 복잡한 계산 필요
                        
                        # Typical Price 계산
                        typical_price = (high_price + low_price + close_price) / 3
                        
                        # True Range 계산 (단순화)
                        true_range = high_price - low_price
                        
                        # 거래대금 (KIS에서 제공)
                        volume_value = Decimal(str(data['acml_tr_pbmn']))
                        
                        # 새로운 주가 데이터 생성
                        new_price = StockDailyPrice(
                            stock_id=stock_id,
                            trade_date=trade_date,
                            open_price=open_price,
                            high_price=high_price,
                            low_price=low_price,
                            close_price=close_price,
                            volume=volume,
                            volume_value=volume_value,
                            daily_return_pct=daily_return_pct,
                            price_change=price_change,
                            price_change_pct=price_change_pct,
                            vwap=vwap,
                            typical_price=typical_price,
                            true_range=true_range,
                            data_source="KIS"
                        )
                        
                        db.add(new_price)
                        collected_count += 1
                        
                    except Exception as e:
                        print(f"⚠️ 개별 주가 데이터 처리 실패: {e}")
                        continue
                
                db.commit()
            
            return collected_count
            
        except Exception as e:
            print(f"❌ 주가 데이터 수집 실패 ({stock_code}): {e}")
            return 0
    
    def calculate_technical_indicators(self, stock_id: int, stock_code: str) -> int:
        """기술적 지표 계산"""
        try:
            with get_db_session() as db:
                # 최근 200일 주가 데이터 가져오기 (이동평균 계산용)
                price_data = db.query(StockDailyPrice).filter(
                    StockDailyPrice.stock_id == stock_id
                ).order_by(StockDailyPrice.trade_date.desc()).limit(200).all()
                
                if len(price_data) < 20:
                    print(f"⚠️ {stock_code} 기술적 지표 계산용 데이터 부족 ({len(price_data)}개)")
                    return 0
                
                # 날짜순으로 정렬 (오래된 것부터)
                price_data = sorted(price_data, key=lambda x: x.trade_date)
                
                calculated_count = 0
                
                # 각 날짜에 대해 기술적 지표 계산
                for i, current_price in enumerate(price_data):
                    if i < 19:  # 최소 20개 데이터 필요
                        continue
                    
                    # 기존 지표 데이터 확인
                    existing_indicator = db.query(StockTechnicalIndicator).filter(
                        StockTechnicalIndicator.stock_id == stock_id,
                        StockTechnicalIndicator.calculation_date == current_price.trade_date
                    ).first()
                    
                    if existing_indicator:
                        continue  # 이미 존재하는 데이터는 스킵
                    
                    # 이동평균 계산
                    closes = [float(p.close_price) for p in price_data[max(0, i-199):i+1]]
                    
                    sma_5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else None
                    sma_10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else None
                    sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
                    sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
                    sma_100 = sum(closes[-100:]) / 100 if len(closes) >= 100 else None
                    sma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
                    
                    # EMA 계산 (단순화)
                    ema_12 = self._calculate_ema(closes, 12) if len(closes) >= 12 else None
                    ema_26 = self._calculate_ema(closes, 26) if len(closes) >= 26 else None
                    
                    # RSI 계산
                    rsi_14 = self._calculate_rsi(closes, 14) if len(closes) >= 15 else None
                    
                    # MACD 계산
                    if ema_12 and ema_26:
                        macd_line = ema_12 - ema_26
                        macd_signal = macd_line * 0.9  # 단순화
                        macd_histogram = macd_line - macd_signal
                    else:
                        macd_line = macd_signal = macd_histogram = None
                    
                    # 볼린저 밴드 계산
                    if sma_20 and len(closes) >= 20:
                        recent_closes = closes[-20:]
                        std_dev = (sum([(x - sma_20) ** 2 for x in recent_closes]) / 20) ** 0.5
                        bb_upper_20_2 = sma_20 + (2 * std_dev)
                        bb_lower_20_2 = sma_20 - (2 * std_dev)
                        bb_width = bb_upper_20_2 - bb_lower_20_2
                        bb_percent = (float(current_price.close_price) - bb_lower_20_2) / bb_width if bb_width > 0 else None
                    else:
                        bb_upper_20_2 = bb_lower_20_2 = bb_width = bb_percent = None
                    
                    # 볼륨 지표
                    volumes = [float(p.volume) for p in price_data[max(0, i-19):i+1]]
                    volume_sma_20 = sum(volumes) / len(volumes) if volumes else None
                    volume_ratio = float(current_price.volume) / volume_sma_20 if volume_sma_20 else None
                    
                    # 변동성 계산
                    if len(closes) >= 20:
                        returns = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(1, len(closes))]
                        volatility_20 = (sum([r**2 for r in returns[-20:]]) / 20) ** 0.5 if len(returns) >= 20 else None
                    else:
                        volatility_20 = None
                    
                    # 새로운 기술적 지표 생성
                    new_indicator = StockTechnicalIndicator(
                        stock_id=stock_id,
                        calculation_date=current_price.trade_date,
                        sma_5=sma_5,
                        sma_10=sma_10,
                        sma_20=sma_20,
                        sma_50=sma_50,
                        sma_100=sma_100,
                        sma_200=sma_200,
                        ema_12=ema_12,
                        ema_26=ema_26,
                        rsi_14=rsi_14,
                        macd_line=macd_line,
                        macd_signal=macd_signal,
                        macd_histogram=macd_histogram,
                        bb_upper_20_2=bb_upper_20_2,
                        bb_middle_20=sma_20,
                        bb_lower_20_2=bb_lower_20_2,
                        bb_width=bb_width,
                        bb_percent=bb_percent,
                        volume_sma_20=volume_sma_20,
                        volume_ratio=volume_ratio,
                        volatility_20=volatility_20,
                        calculation_version="v1.0"
                    )
                    
                    db.add(new_indicator)
                    calculated_count += 1
                
                db.commit()
                return calculated_count
                
        except Exception as e:
            print(f"❌ 기술적 지표 계산 실패 ({stock_code}): {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """EMA 계산"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """RSI 계산"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def add_stocks_to_universe(self, universe_id: int, stock_ids: List[int]) -> int:
        """유니버스에 종목 추가"""
        try:
            added_count = 0
            
            with get_db_session() as db:
                for rank, stock_id in enumerate(stock_ids, 1):
                    # 기존 항목 확인
                    existing_item = db.query(TradingUniverseItem).filter(
                        TradingUniverseItem.universe_id == universe_id,
                        TradingUniverseItem.stock_id == stock_id
                    ).first()
                    
                    if existing_item:
                        # 기존 항목 업데이트
                        existing_item.rank = rank
                        existing_item.is_active = True
                        existing_item.updated_at = datetime.now()
                    else:
                        # 새로운 항목 추가
                        new_item = TradingUniverseItem(
                            universe_id=universe_id,
                            stock_id=stock_id,
                            rank=rank,
                            weight=1.0 / len(stock_ids),  # 균등 가중
                            added_date=date.today(),
                            selection_reason="Korean major stock"
                        )
                        db.add(new_item)
                        added_count += 1
                
                db.commit()
            
            return added_count
            
        except Exception as e:
            print(f"❌ 유니버스 종목 추가 실패: {e}")
            return 0


def main():
    """메인 실행 함수"""
    print("🚀 향상된 주식 데이터 수집 및 처리")
    print("="*70)
    print("📋 작업 순서:")
    print("1. KIS 토큰 확인")
    print("2. 주식 마스터 데이터 생성")
    print("3. 일일 주가 데이터 수집")
    print("4. 기술적 지표 계산")
    print("5. 유니버스 구성")
    print("="*70)
    
    collector = EnhancedDataCollector()
    
    # 1단계: KIS 토큰 확인
    print("\n1️⃣ KIS 토큰 확인")
    if not collector.verify_kis_token():
        print("❌ KIS 토큰 확인 실패. 프로세스를 중단합니다.")
        return False
    
    # 2단계: 주식 마스터 데이터 생성
    print("\n2️⃣ 주식 마스터 데이터 생성")
    stock_ids = []
    
    for stock_info in collector.korean_major_stocks:
        stock_id = collector.create_or_update_stock_master(stock_info)
        if stock_id:
            stock_ids.append(stock_id)
            print(f"✅ {stock_info['code']} ({stock_info['name']}) - ID: {stock_id}")
        else:
            print(f"❌ {stock_info['code']} 처리 실패")
    
    print(f"📊 총 {len(stock_ids)}개 종목 마스터 데이터 처리 완료")
    
    # 3단계: 일일 주가 데이터 수집
    print("\n3️⃣ 일일 주가 데이터 수집")
    total_price_count = 0
    
    for i, (stock_info, stock_id) in enumerate(zip(collector.korean_major_stocks, stock_ids)):
        print(f"🔄 [{i+1}/{len(stock_ids)}] {stock_info['code']} 주가 데이터 수집 중...")
        count = collector.collect_daily_price_data(stock_id, stock_info['code'])
        total_price_count += count
        print(f"   ✅ {count}개 데이터 수집")
    
    print(f"📈 총 {total_price_count}개 주가 데이터 수집 완료")
    
    # 4단계: 기술적 지표 계산
    print("\n4️⃣ 기술적 지표 계산")
    total_indicator_count = 0
    
    for i, (stock_info, stock_id) in enumerate(zip(collector.korean_major_stocks, stock_ids)):
        print(f"🔄 [{i+1}/{len(stock_ids)}] {stock_info['code']} 기술적 지표 계산 중...")
        count = collector.calculate_technical_indicators(stock_id, stock_info['code'])
        total_indicator_count += count
        print(f"   ✅ {count}개 지표 계산")
    
    print(f"🔧 총 {total_indicator_count}개 기술적 지표 계산 완료")
    
    # 5단계: 유니버스 구성
    print("\n5️⃣ 유니버스 구성")
    
    try:
        with get_db_session() as db:
            # 기본 한국 유니버스 찾기
            universe = db.query(TradingUniverse).filter(
                TradingUniverse.universe_name == "Korean Major Stocks",
                TradingUniverse.market_region == "KR"
            ).first()
            
            if universe:
                added_count = collector.add_stocks_to_universe(universe.universe_id, stock_ids)
                print(f"✅ {added_count}개 종목을 유니버스 ID {universe.universe_id}에 추가")
            else:
                print("❌ 기본 유니버스를 찾을 수 없습니다")
    
    except Exception as e:
        print(f"❌ 유니버스 구성 실패: {e}")
    
    # 성공 요약
    print("\n" + "="*70)
    print("🎉 향상된 데이터 수집 및 처리 완료!")
    print("="*70)
    print(f"✅ 종목 마스터: {len(stock_ids)}개")
    print(f"✅ 주가 데이터: {total_price_count}개")
    print(f"✅ 기술적 지표: {total_indicator_count}개")
    print("\n🚀 이제 ML 모델 학습을 진행할 수 있습니다!")
    
    # Discord 알림
    try:
        from app.services.notification import NotificationService
        notification = NotificationService()
        message = (
            f"📊 **향상된 데이터 수집 완료**\n\n"
            f"📅 수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🏢 종목 마스터: {len(stock_ids)}개\n"
            f"📈 주가 데이터: {total_price_count}개\n"
            f"🔧 기술적 지표: {total_indicator_count}개\n"
            f"🌌 유니버스: Korean Major Stocks\n\n"
            f"🚀 **ML 모델 학습 준비 완료!**"
        )
        notification._send_simple_slack_message(message)
        print("📱 Discord 알림 전송 완료")
    except Exception as e:
        print(f"⚠️ Discord 알림 전송 실패: {e}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
