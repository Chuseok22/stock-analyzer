#!/usr/bin/env python3
"""
운영환경용 완전한 ML 주식 추천 시스템
- 현재가, 예상 수익률, 투자 이유 포함
- 하락장 대응 inverse 전략
- 대규모 종목 데이터 처리
- 강화된 알림 시스템
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import pickle

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockRecommendation, StockMaster
from app.services.kis_api import KISAPIClient
from app.services.notification import NotificationService
from sqlalchemy import text


class ProductionMLSystem:
    """운영환경용 ML 추천 시스템"""
    
    def __init__(self):
        self.universe_id = 1
        self.kis_client = KISAPIClient()
        self.notification = NotificationService()
        self.model_dir = Path(__file__).parent.parent / "storage" / "models"
        self.model_dir.mkdir(exist_ok=True)
        
        # 시장 지수 종목 코드 (하락장 판단용)
        self.market_indices = {
            'KOSPI': '001',  # KOSPI 200
            'KOSDAQ': '229180'  # KODEX KOSDAQ 150
        }
        
        # Inverse ETF 코드들
        self.inverse_etfs = {
            'KODEX 인버스': '114800',
            'TIGER 인버스': '225500', 
            'KODEX 레버리지': '122630',
            'TIGER 2X 인버스': '252670'
        }
    
    def check_market_trend(self) -> Dict[str, any]:
        """시장 트렌드 분석 (상승장/하락장 판단)"""
        print("📊 시장 트렌드 분석 중...")
        
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
            
            market_data = {}
            
            for market_name, code in self.market_indices.items():
                try:
                    price_data = self.kis_client.get_stock_price_daily(code, start_date, end_date)
                    
                    if price_data and len(price_data) >= 2:
                        # 최근 5일 평균 vs 이전 5일 평균
                        recent_prices = [float(d['stck_clpr']) for d in price_data[-5:]]
                        previous_prices = [float(d['stck_clpr']) for d in price_data[-10:-5]]
                        
                        recent_avg = np.mean(recent_prices)
                        previous_avg = np.mean(previous_prices)
                        
                        trend_pct = ((recent_avg - previous_avg) / previous_avg) * 100
                        
                        market_data[market_name] = {
                            'current_price': recent_prices[-1],
                            'trend_pct': trend_pct,
                            'trend': 'bullish' if trend_pct > 1 else 'bearish' if trend_pct < -1 else 'neutral'
                        }
                        
                        print(f"   {market_name}: {trend_pct:.2f}% ({'상승' if trend_pct > 0 else '하락'})")
                        
                except Exception as e:
                    print(f"   ⚠️ {market_name} 데이터 오류: {e}")
                    continue
            
            # 전체 시장 트렌드 결정
            if market_data:
                avg_trend = np.mean([d['trend_pct'] for d in market_data.values()])
                overall_trend = 'bullish' if avg_trend > 1 else 'bearish' if avg_trend < -1 else 'neutral'
                
                result = {
                    'overall_trend': overall_trend,
                    'avg_trend_pct': avg_trend,
                    'market_data': market_data,
                    'is_bear_market': avg_trend < -2  # 2% 이상 하락 시 하락장
                }
                
                print(f"✅ 전체 시장 트렌드: {overall_trend} ({avg_trend:.2f}%)")
                return result
            
            return {'overall_trend': 'neutral', 'avg_trend_pct': 0, 'market_data': {}, 'is_bear_market': False}
            
        except Exception as e:
            print(f"❌ 시장 트렌드 분석 실패: {e}")
            return {'overall_trend': 'neutral', 'avg_trend_pct': 0, 'market_data': {}, 'is_bear_market': False}
    
    def get_expanded_stock_universe(self) -> List[Dict]:
        """확장된 종목 유니버스 가져오기"""
        print("🌍 종목 유니버스 확장 중...")
        
        try:
            # 시가총액 상위 종목 가져오기
            kospi_stocks = self.kis_client.get_market_cap_ranking("J", 200)  # KOSPI 200개
            kosdaq_stocks = self.kis_client.get_market_cap_ranking("Q", 100)  # KOSDAQ 100개
            
            all_stocks = []
            
            # KOSPI 종목 처리
            for stock in kospi_stocks:
                if stock.get('mksc_shrn_iscd'):  # 종목코드가 있는 경우만
                    all_stocks.append({
                        'stock_code': stock['mksc_shrn_iscd'],
                        'stock_name': stock.get('hts_kor_isnm', ''),
                        'market': 'KOSPI',
                        'market_cap': stock.get('lstg_stqt', 0)
                    })
            
            # KOSDAQ 종목 처리  
            for stock in kosdaq_stocks:
                if stock.get('mksc_shrn_iscd'):
                    all_stocks.append({
                        'stock_code': stock['mksc_shrn_iscd'],
                        'stock_name': stock.get('hts_kor_isnm', ''),
                        'market': 'KOSDAQ', 
                        'market_cap': stock.get('lstg_stqt', 0)
                    })
            
            print(f"✅ {len(all_stocks)}개 종목 수집 완료")
            print(f"   KOSPI: {len([s for s in all_stocks if s['market'] == 'KOSPI'])}개")
            print(f"   KOSDAQ: {len([s for s in all_stocks if s['market'] == 'KOSDAQ'])}개")
            
            return all_stocks
            
        except Exception as e:
            print(f"❌ 종목 유니버스 확장 실패: {e}")
            # 기존 데이터베이스 종목 사용
            return self.get_existing_stocks()
    
    def get_existing_stocks(self) -> List[Dict]:
        """기존 데이터베이스의 종목 가져오기"""
        try:
            with get_db_session() as db:
                query = text("""
                    SELECT DISTINCT sm.stock_code, sm.stock_name, 'DB' as market, 0 as market_cap
                    FROM stock_master sm
                    INNER JOIN trading_universe_item tui ON sm.stock_id = tui.stock_id
                    WHERE tui.universe_id = :universe_id AND tui.is_active = true
                """)
                
                result = db.execute(query, {"universe_id": self.universe_id}).fetchall()
                
                # SQLAlchemy Row 객체를 딕셔너리로 변환
                return [{'stock_code': row[0], 'stock_name': row[1], 'market': row[2], 'market_cap': row[3]} 
                       for row in result]
                
        except Exception as e:
            print(f"❌ 기존 종목 로드 실패: {e}")
            return []
    
    def get_comprehensive_data(self, stock_codes: List[str]) -> pd.DataFrame:
        """포괄적인 데이터 수집"""
        print(f"📊 {len(stock_codes)}개 종목 데이터 수집 중...")
        
        try:
            # 데이터베이스에서 기존 데이터 로드
            with get_db_session() as db:
                # 종목코드를 문자열로 변환하여 조인
                codes_str = "','".join(stock_codes)
                
                query = text(f"""
                    SELECT 
                        sm.stock_id,
                        sm.stock_code,
                        sm.stock_name,
                        sp.trade_date,
                        sp.close_price,
                        sp.open_price,
                        sp.high_price,
                        sp.low_price,
                        sp.volume,
                        sp.daily_return_pct,
                        sp.price_change_pct,
                        sti.sma_5,
                        sti.sma_20,
                        sti.sma_50,
                        sti.ema_12,
                        sti.ema_26,
                        sti.rsi_14,
                        sti.bb_upper_20_2 as bb_upper,
                        sti.bb_middle_20 as bb_middle,
                        sti.bb_lower_20_2 as bb_lower,
                        sti.bb_percent,
                        sti.volume_ratio,
                        sti.macd_line,
                        sti.macd_signal,
                        sti.macd_histogram
                    FROM stock_master sm
                    INNER JOIN stock_daily_price sp ON sm.stock_id = sp.stock_id
                    LEFT JOIN stock_technical_indicator sti ON sm.stock_id = sti.stock_id 
                        AND sp.trade_date = sti.calculation_date
                    WHERE sm.stock_code IN ('{codes_str}')
                    ORDER BY sm.stock_id, sp.trade_date DESC
                """)
                
                result = db.execute(query).fetchall()
                
                if not result:
                    print("❌ 데이터베이스에서 데이터 없음")
                    return pd.DataFrame()
                
                df = pd.DataFrame(result, columns=[
                    'stock_id', 'stock_code', 'stock_name', 'trade_date', 'close_price',
                    'open_price', 'high_price', 'low_price', 'volume', 'daily_return_pct',
                    'price_change_pct', 'sma_5', 'sma_20', 'sma_50', 'ema_12', 'ema_26',
                    'rsi_14', 'bb_upper', 'bb_middle', 'bb_lower', 'bb_percent', 'volume_ratio',
                    'macd_line', 'macd_signal', 'macd_histogram'
                ])
                
                print(f"✅ {len(df)}개 레코드 로드")
                
                # 데이터 타입 변환
                numeric_cols = ['close_price', 'open_price', 'high_price', 'low_price', 'volume',
                               'daily_return_pct', 'price_change_pct',
                               'sma_5', 'sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi_14',
                               'bb_upper', 'bb_middle', 'bb_lower', 'bb_percent', 'volume_ratio',
                               'macd_line', 'macd_signal', 'macd_histogram']
                
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                return df
                
        except Exception as e:
            print(f"❌ 데이터 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def create_advanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """고급 피처 생성"""
        print("🔧 고급 피처 생성 중...")
        
        try:
            df_features = df.copy()
            
            # 기본 피처들 (가능한 컬럼만 사용)
            if 'sma_20' in df_features.columns and 'close_price' in df_features.columns:
                df_features['price_momentum'] = df_features['close_price'] / df_features['sma_20'] - 1
            else:
                df_features['price_momentum'] = 0
                
            if 'volume_ratio' in df_features.columns:
                df_features['volume_momentum'] = df_features['volume_ratio'] - 1
            else:
                df_features['volume_momentum'] = 0
            
            # RSI 기반 피처
            if 'rsi_14' in df_features.columns:
                df_features['rsi_oversold'] = (df_features['rsi_14'] < 30).astype(int)
                df_features['rsi_overbought'] = (df_features['rsi_14'] > 70).astype(int)
                df_features['rsi_neutral'] = ((df_features['rsi_14'] >= 30) & (df_features['rsi_14'] <= 70)).astype(int)
            else:
                df_features['rsi_oversold'] = 0
                df_features['rsi_overbought'] = 0
                df_features['rsi_neutral'] = 1
            
            # 볼린저 밴드 피처
            if 'bb_percent' in df_features.columns:
                df_features['bb_position'] = df_features['bb_percent']
            else:
                df_features['bb_position'] = 0.5
                
            if all(col in df_features.columns for col in ['bb_upper', 'bb_lower', 'bb_middle']):
                df_features['bb_squeeze'] = ((df_features['bb_upper'] - df_features['bb_lower']) / df_features['bb_middle']).fillna(0)
            else:
                df_features['bb_squeeze'] = 0
            
            # 이동평균 피처
            if all(col in df_features.columns for col in ['sma_5', 'sma_20']):
                df_features['sma_cross'] = (df_features['sma_5'] > df_features['sma_20']).astype(int)
            else:
                df_features['sma_cross'] = 0
                
            if all(col in df_features.columns for col in ['close_price', 'sma_20']):
                df_features['price_above_sma20'] = (df_features['close_price'] > df_features['sma_20']).astype(int)
            else:
                df_features['price_above_sma20'] = 0
            
            # MACD 피처 (null 값 처리)
            if 'macd_line' in df_features.columns:
                df_features['macd_positive'] = (df_features['macd_line'] > 0).fillna(False).astype(int)
            else:
                df_features['macd_positive'] = 0
                
            if all(col in df_features.columns for col in ['macd_line', 'macd_signal']):
                df_features['macd_signal_cross'] = (df_features['macd_line'] > df_features['macd_signal']).fillna(False).astype(int)
            else:
                df_features['macd_signal_cross'] = 0
            
            # 변동성 피처
            if all(col in df_features.columns for col in ['high_price', 'low_price', 'close_price']):
                df_features['volatility'] = ((df_features['high_price'] - df_features['low_price']) / df_features['close_price']).fillna(0)
            else:
                df_features['volatility'] = 0
                
            if 'volume_ratio' in df_features.columns:
                df_features['volume_spike'] = (df_features['volume_ratio'] > 2.0).astype(int)
            else:
                df_features['volume_spike'] = 0
            
            # 타겟 변수 생성 (다음날 수익률 예측)
            df_features = df_features.sort_values(['stock_id', 'trade_date'])
            if 'daily_return_pct' in df_features.columns:
                df_features['next_day_return'] = df_features.groupby('stock_id')['daily_return_pct'].shift(-1)
                df_features['target'] = (df_features['next_day_return'] > 0).astype(int)
            else:
                df_features['target'] = 0
            
            # NaN 값 처리
            df_features = df_features.fillna(0)
            
            print(f"✅ {len(df_features)}개 레코드 피처 생성 완료")
            
            return df_features
            
        except Exception as e:
            print(f"❌ 피처 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def train_production_model(self, df: pd.DataFrame, market_trend: Dict) -> Dict:
        """운영환경용 모델 학습"""
        print("🤖 운영환경용 모델 학습 시작...")
        
        try:
            if len(df) < 50:
                return {"success": False, "error": f"학습 데이터 부족: {len(df)}개"}
            
            # 피처 선택
            feature_cols = [
                'rsi_14', 'bb_position', 'volume_ratio', 'price_momentum', 'volume_momentum',
                'rsi_oversold', 'rsi_overbought', 'bb_squeeze', 'sma_cross', 'price_above_sma20',
                'macd_positive', 'macd_signal_cross', 'volatility', 'volume_spike'
            ]
            
            # 사용 가능한 피처만 선택
            available_features = [col for col in feature_cols if col in df.columns]
            print(f"📊 사용 피처: {available_features}")
            
            # 유효한 데이터만 사용
            df_train = df[df['target'].notna()].copy()
            
            if len(df_train) < 20:
                return {"success": False, "error": f"유효한 학습 데이터 부족: {len(df_train)}개"}
            
            X = df_train[available_features]
            y = df_train['target']
            
            print(f"✅ 학습 데이터: {len(X)}개")
            print(f"   상승: {y.sum()}개 ({y.mean()*100:.1f}%)")
            print(f"   하락: {len(y) - y.sum()}개 ({(1-y.mean())*100:.1f}%)")
            
            # 모델 학습 (하락장/상승장에 따라 파라미터 조정)
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.metrics import accuracy_score, classification_report
            
            if market_trend.get('is_bear_market', False):
                # 하락장: 보수적인 예측
                model = RandomForestClassifier(
                    n_estimators=100, 
                    max_depth=5, 
                    min_samples_split=10,
                    random_state=42,
                    class_weight='balanced'
                )
                model_type = "bear_market"
            else:
                # 상승장/중립: 일반적인 예측
                model = RandomForestClassifier(
                    n_estimators=50,
                    max_depth=7,
                    min_samples_split=5,
                    random_state=42
                )
                model_type = "bull_market"
            
            model.fit(X, y)
            
            # 예측 및 평가
            y_pred = model.predict(X)
            accuracy = accuracy_score(y, y_pred)
            
            print(f"✅ 모델 정확도: {accuracy:.4f}")
            print(f"📊 모델 타입: {model_type}")
            
            # 피처 중요도
            feature_importance = dict(zip(available_features, model.feature_importances_))
            print(f"📊 피처 중요도 (상위 5개):")
            for feat, imp in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   {feat}: {imp:.4f}")
            
            # 모델 저장
            model_data = {
                'model': model,
                'features': available_features,
                'model_type': model_type,
                'market_trend': market_trend,
                'training_date': datetime.now(),
                'accuracy': accuracy,
                'feature_importance': feature_importance
            }
            
            with open(self.model_dir / "production_model.pkl", "wb") as f:
                pickle.dump(model_data, f)
            
            print(f"✅ 모델 저장 완료: production_model.pkl")
            
            return {
                "success": True,
                "accuracy": accuracy,
                "model_type": model_type,
                "training_samples": len(X),
                "features": available_features,
                "feature_importance": feature_importance
            }
            
        except Exception as e:
            print(f"❌ 모델 학습 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def generate_detailed_predictions(self, market_trend: Dict) -> List[Dict]:
        """상세한 예측 생성 (현재가, 예상 수익률, 이유 포함)"""
        print("📈 상세 예측 생성 중...")
        
        try:
            # 모델 로드
            with open(self.model_dir / "production_model.pkl", "rb") as f:
                model_data = pickle.load(f)
            
            model = model_data['model']
            features = model_data['features']
            
            # 최신 데이터 가져오기
            stock_universe = self.get_existing_stocks()  # 일단 기존 종목으로
            stock_codes = [s['stock_code'] for s in stock_universe]
            
            df = self.get_comprehensive_data(stock_codes)
            if df.empty:
                print("❌ 데이터 없음")
                return []
            
            df = self.create_advanced_features(df)
            if df.empty:
                print("❌ 피처 생성 실패")
                return []
            
            # 최신 날짜 데이터만 사용
            latest_date = df['trade_date'].max()
            latest_df = df[df['trade_date'] == latest_date].copy()
            
            if len(latest_df) == 0:
                print("❌ 최신 데이터 없음")
                return []
            
            print(f"📅 예측 기준일: {latest_date.date()}")
            print(f"📊 예측 대상: {len(latest_df)}개 종목")
            
            # 예측 실행
            X = latest_df[features]
            
            # 상승 확률과 예상 수익률 계산
            proba_scores = model.predict_proba(X)[:, 1]  # 상승 확률
            
            results = []
            for i, (_, row) in enumerate(latest_df.iterrows()):
                # 현재가 정보
                current_price = float(row['close_price'])
                
                # 예상 수익률 계산 (확률 * 기대 수익률)
                rsi = float(row['rsi_14'])
                bb_pos = float(row['bb_position'])
                vol_ratio = float(row['volume_ratio'])
                
                # 간단한 수익률 추정 (RSI와 볼린저밴드 기반)
                expected_return = 0
                if rsi < 30 and bb_pos < 0.2:  # 과매도 + 하단
                    expected_return = 3.0  # 3% 기대
                elif rsi > 70 and bb_pos > 0.8:  # 과매수 + 상단
                    expected_return = -2.0  # -2% 기대
                elif 40 <= rsi <= 60 and 0.3 <= bb_pos <= 0.7:  # 중립
                    expected_return = 1.0  # 1% 기대
                else:
                    expected_return = 0.5  # 0.5% 기대
                
                # 확률 가중 수익률
                prob_weighted_return = proba_scores[i] * expected_return
                
                # 투자 이유 생성
                reasons = []
                if rsi < 30:
                    reasons.append(f"RSI 과매도({rsi:.1f})")
                elif rsi > 70:
                    reasons.append(f"RSI 과매수({rsi:.1f})")
                
                if bb_pos < 0.2:
                    reasons.append("볼린저밴드 하단")
                elif bb_pos > 0.8:
                    reasons.append("볼린저밴드 상단")
                
                if vol_ratio > 1.5:
                    reasons.append(f"거래량 급증({vol_ratio:.1f}x)")
                
                if row['sma_cross'] == 1:
                    reasons.append("단기평균선 돌파")
                
                if not reasons:
                    reasons.append("기술적 중립")
                
                investment_reason = ", ".join(reasons)
                
                # 결과 저장
                results.append({
                    'stock_id': int(row['stock_id']),
                    'stock_code': row['stock_code'],
                    'stock_name': row['stock_name'],
                    'current_price': current_price,
                    'ml_score': float(proba_scores[i]),
                    'expected_return_pct': round(prob_weighted_return, 2),
                    'investment_reason': investment_reason,
                    'rsi': rsi,
                    'bb_position': bb_pos,
                    'volume_ratio': vol_ratio,
                    'prediction_date': latest_date.date()
                })
            
            # 점수순 정렬
            results.sort(key=lambda x: x['ml_score'], reverse=True)
            
            print(f"✅ {len(results)}개 상세 예측 완료")
            return results
            
        except Exception as e:
            print(f"❌ 상세 예측 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def handle_inverse_strategy(self, market_trend: Dict, predictions: List[Dict]) -> List[Dict]:
        """하락장 대응 inverse 전략 처리"""
        print("🔄 Inverse 전략 처리 중...")
        
        if not market_trend.get('is_bear_market', False):
            print("   상승장/중립장 - inverse 전략 불필요")
            return predictions
        
        print(f"   하락장 감지 ({market_trend['avg_trend_pct']:.2f}%) - inverse 전략 적용")
        
        try:
            # Inverse ETF 데이터 수집
            inverse_predictions = []
            
            for etf_name, etf_code in self.inverse_etfs.items():
                try:
                    # Inverse ETF 현재가 조회
                    etf_info = self.kis_client.get_stock_info(etf_code)
                    
                    if etf_info and etf_info.get('stck_prpr'):
                        current_price = float(etf_info['stck_prpr'])
                        
                        # 하락장에서 inverse ETF는 상승 기대
                        market_decline = abs(market_trend['avg_trend_pct'])
                        expected_return = market_decline * 0.8  # 시장 하락의 80% 수익 기대
                        
                        inverse_predictions.append({
                            'stock_id': 0,  # ETF는 별도 ID
                            'stock_code': etf_code,
                            'stock_name': etf_name,
                            'current_price': current_price,
                            'ml_score': 0.85,  # 하락장에서 높은 점수
                            'expected_return_pct': round(expected_return, 2),
                            'investment_reason': f"하락장 대응 inverse 전략, 시장 하락률 {market_decline:.1f}%",
                            'rsi': 50.0,
                            'bb_position': 0.5,
                            'volume_ratio': 1.0,
                            'prediction_date': datetime.now().date(),
                            'strategy_type': 'inverse'
                        })
                        
                        print(f"   ✅ {etf_name}: {expected_return:.1f}% 기대수익")
                        
                except Exception as e:
                    print(f"   ⚠️ {etf_name} 처리 실패: {e}")
                    continue
            
            # 기존 예측과 inverse 전략 결합
            if inverse_predictions:
                # 하락장에서는 inverse ETF를 상위에 배치
                combined_predictions = inverse_predictions + predictions
                combined_predictions.sort(key=lambda x: x['ml_score'], reverse=True)
                
                print(f"✅ Inverse 전략 {len(inverse_predictions)}개 추가")
                return combined_predictions
            
            return predictions
            
        except Exception as e:
            print(f"❌ Inverse 전략 처리 실패: {e}")
            return predictions
    
    def save_production_recommendations(self, predictions: List[Dict], top_n: int = 20) -> int:
        """운영환경용 추천 저장"""
        print(f"💾 상위 {top_n}개 추천 저장...")
        
        try:
            saved = 0
            today = datetime.now().date()
            
            with get_db_session() as db:
                # 오늘 날짜의 기존 추천 삭제
                db.execute(text("""
                    DELETE FROM stock_recommendation 
                    WHERE recommendation_date = :today AND universe_id = :universe_id
                """), {"today": today, "universe_id": self.universe_id})
                
                for rank, pred in enumerate(predictions[:top_n], 1):
                    # inverse ETF는 별도 처리
                    if pred.get('strategy_type') == 'inverse':
                        continue  # 별도 테이블에 저장하거나 로그만 남김
                    
                    new_rec = StockRecommendation(
                        stock_id=pred['stock_id'],
                        universe_id=self.universe_id,
                        recommendation_date=pred['prediction_date'],
                        target_date=(pred['prediction_date'] + timedelta(days=1)),
                        ml_score=pred['ml_score'],
                        universe_rank=rank,
                        model_name="Production ML System",
                        model_version="v2.0",
                        recommendation_reason=f"{pred['investment_reason']} | 예상수익률: {pred['expected_return_pct']}%"
                    )
                    
                    db.add(new_rec)
                    saved += 1
                
                db.commit()
            
            print(f"✅ {saved}개 추천 저장 (기존 추천 삭제 후)")
            return saved
            
        except Exception as e:
            print(f"❌ 추천 저장 실패: {e}")
            return 0
    
    def send_enhanced_notification(self, predictions: List[Dict], market_trend: Dict, model_result: Dict):
        """강화된 알림 발송"""
        print("📱 강화된 알림 발송 중...")
        
        try:
            # 상위 5개 추천 형식화
            top_5_detailed = []
            for i, pred in enumerate(predictions[:5], 1):
                strategy_mark = "🔄" if pred.get('strategy_type') == 'inverse' else "📈"
                
                detail_text = (
                    f"{strategy_mark} **{i}. {pred['stock_code']} ({pred['stock_name']})**\n"
                    f"   💰 현재가: {pred['current_price']:,.0f}원\n"
                    f"   🎯 예상수익률: **{pred['expected_return_pct']:+.1f}%**\n"
                    f"   🤖 ML점수: {pred['ml_score']:.3f}\n"
                    f"   📋 이유: {pred['investment_reason']}\n"
                )
                top_5_detailed.append(detail_text)
            
            # 시장 상황 분석
            market_status = "📈 상승장" if market_trend['overall_trend'] == 'bullish' else "📉 하락장" if market_trend['overall_trend'] == 'bearish' else "➡️ 중립장"
            market_color = "🟢" if market_trend['avg_trend_pct'] > 0 else "🔴" if market_trend['avg_trend_pct'] < 0 else "🟡"
            
            # 전체 메시지 구성
            message = (
                f"🚀 **운영환경 ML 주식 추천 시스템**\n\n"
                f"📅 **분석 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🎯 **모델 정확도**: {model_result.get('accuracy', 0):.3f} ({model_result.get('model_type', 'unknown')})\n"
                f"📊 **학습 샘플**: {model_result.get('training_samples', 0):,}개\n\n"
                f"📈 **시장 현황**: {market_status} {market_color}\n"
                f"📊 **시장 트렌드**: {market_trend['avg_trend_pct']:+.2f}%\n"
            )
            
            # 시장별 상세 정보
            if market_trend.get('market_data'):
                message += f"\n📊 **지수별 현황**:\n"
                for market, data in market_trend['market_data'].items():
                    trend_emoji = "📈" if data['trend_pct'] > 0 else "📉" if data['trend_pct'] < 0 else "➡️"
                    message += f"   {trend_emoji} {market}: {data['trend_pct']:+.2f}%\n"
            
            # 하락장 경고
            if market_trend.get('is_bear_market'):
                message += f"\n⚠️ **하락장 감지** - Inverse 전략 적용됨\n"
            
            # 상위 추천 종목
            message += f"\n🏆 **오늘의 TOP 5 추천**:\n\n"
            message += "\n".join(top_5_detailed)
            
            # 주의사항
            message += (
                f"\n⚠️ **투자 주의사항**:\n"
                f"- 이 추천은 AI 모델 기반 분석입니다\n"
                f"- 투자 결정은 본인의 판단과 책임하에 진행하세요\n"
                f"- 손실 위험을 고려한 적절한 자금 관리가 필요합니다\n\n"
                f"💪 **Happy Trading!** 🎯"
            )
            
            # Discord 알림 발송
            self.notification._send_simple_slack_message(message)
            print("✅ Discord 알림 전송 완료")
            
        except Exception as e:
            print(f"❌ 알림 발송 실패: {e}")


def main():
    """메인 실행 함수"""
    print("🚀 운영환경 ML 주식 추천 시스템 시작")
    print("="*80)
    
    system = ProductionMLSystem()
    
    try:
        # 1. 시장 트렌드 분석
        print("\n1️⃣ 시장 트렌드 분석")
        market_trend = system.check_market_trend()
        
        # 2. 종목 데이터 수집
        print("\n2️⃣ 종목 데이터 수집")
        stock_universe = system.get_existing_stocks()  # 확장은 나중에
        stock_codes = [s['stock_code'] for s in stock_universe[:50]]  # 일단 50개로 제한
        
        df = system.get_comprehensive_data(stock_codes)
        if df.empty:
            print("❌ 데이터 수집 실패")
            return False
        
        # 3. 피처 생성
        print("\n3️⃣ 고급 피처 생성")
        df_features = system.create_advanced_features(df)
        if df_features.empty:
            print("❌ 피처 생성 실패")
            return False
        
        # 4. 모델 학습
        print("\n4️⃣ 운영환경용 모델 학습")
        model_result = system.train_production_model(df_features, market_trend)
        if not model_result["success"]:
            print(f"❌ 모델 학습 실패: {model_result['error']}")
            return False
        
        # 5. 상세 예측 생성
        print("\n5️⃣ 상세 예측 생성")
        predictions = system.generate_detailed_predictions(market_trend)
        if not predictions:
            print("❌ 예측 생성 실패")
            return False
        
        # 6. Inverse 전략 적용
        print("\n6️⃣ Inverse 전략 적용")
        final_predictions = system.handle_inverse_strategy(market_trend, predictions)
        
        # 7. 추천 저장
        print("\n7️⃣ 추천 저장")
        saved = system.save_production_recommendations(final_predictions)
        
        # 8. 강화된 알림 발송
        print("\n8️⃣ 강화된 알림 발송")
        system.send_enhanced_notification(final_predictions, market_trend, model_result)
        
        print(f"\n✅ 운영환경 ML 시스템 실행 완료!")
        print(f"📊 총 {len(final_predictions)}개 예측 생성")
        print(f"💾 {saved}개 추천 저장")
        print(f"🎯 모델 정확도: {model_result['accuracy']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 시스템 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
