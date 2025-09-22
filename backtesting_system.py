#!/usr/bin/env python3
"""
백테스팅 시스템
- 과거 추천의 성과 분석
- 모델 성능 평가
- 수익률 계산
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.database.connection import get_db_session
from app.services.notification import NotificationService
from sqlalchemy import text


class BacktestingSystem:
    """백테스팅 시스템"""
    
    def __init__(self):
        self.notification = NotificationService()
    
    def get_recommendations_history(self, days_back: int = 30) -> pd.DataFrame:
        """과거 추천 이력 가져오기"""
        print(f"📊 과거 {days_back}일 추천 이력 조회...")
        
        try:
            with get_db_session() as db:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days_back)
                
                query = text("""
                    SELECT 
                        sr.recommendation_id,
                        sr.stock_id,
                        sm.stock_code,
                        sm.stock_name,
                        sr.recommendation_date,
                        sr.target_date,
                        sr.ml_score,
                        sr.universe_rank,
                        sr.recommendation_reason,
                        sr.model_name,
                        sr.model_version
                    FROM stock_recommendation sr
                    INNER JOIN stock_master sm ON sr.stock_id = sm.stock_id
                    WHERE sr.recommendation_date >= :start_date 
                        AND sr.recommendation_date <= :end_date
                    ORDER BY sr.recommendation_date DESC, sr.universe_rank ASC
                """)
                
                result = db.execute(query, {
                    "start_date": start_date,
                    "end_date": end_date
                }).fetchall()
                
                if not result:
                    print("❌ 추천 이력 없음")
                    return pd.DataFrame()
                
                df = pd.DataFrame(result, columns=[
                    'recommendation_id', 'stock_id', 'stock_code', 'stock_name',
                    'recommendation_date', 'target_date', 'ml_score', 'universe_rank',
                    'recommendation_reason', 'model_name', 'model_version'
                ])
                
                print(f"✅ {len(df)}개 추천 이력 조회")
                return df
                
        except Exception as e:
            print(f"❌ 추천 이력 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_price_data_for_backtest(self, stock_ids: List[int], start_date, end_date) -> pd.DataFrame:
        """백테스트용 가격 데이터 조회"""
        print(f"💰 {len(stock_ids)}개 종목 가격 데이터 조회...")
        
        try:
            with get_db_session() as db:
                ids_str = ','.join(map(str, stock_ids))
                
                query = text(f"""
                    SELECT 
                        stock_id,
                        trade_date,
                        close_price,
                        daily_return_pct
                    FROM stock_daily_price
                    WHERE stock_id IN ({ids_str})
                        AND trade_date >= :start_date
                        AND trade_date <= :end_date
                    ORDER BY stock_id, trade_date
                """)
                
                result = db.execute(query, {
                    "start_date": start_date,
                    "end_date": end_date
                }).fetchall()
                
                if not result:
                    print("❌ 가격 데이터 없음")
                    return pd.DataFrame()
                
                df = pd.DataFrame(result, columns=['stock_id', 'trade_date', 'close_price', 'daily_return_pct'])
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
                df['daily_return_pct'] = pd.to_numeric(df['daily_return_pct'], errors='coerce')
                
                print(f"✅ {len(df)}개 가격 데이터 조회")
                return df
                
        except Exception as e:
            print(f"❌ 가격 데이터 조회 실패: {e}")
            return pd.DataFrame()
    
    def calculate_returns(self, recommendations_df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
        """수익률 계산"""
        print("📈 수익률 계산 중...")
        
        try:
            results = []
            
            for _, rec in recommendations_df.iterrows():
                stock_id = rec['stock_id']
                rec_date = pd.to_datetime(rec['recommendation_date'])
                target_date = pd.to_datetime(rec['target_date'])
                
                # 추천일과 타겟일의 가격 조회
                stock_prices = price_df[price_df['stock_id'] == stock_id].copy()
                stock_prices = stock_prices.sort_values('trade_date')
                
                # 추천일 가격 (매수가)
                rec_price_row = stock_prices[stock_prices['trade_date'] >= rec_date]
                if len(rec_price_row) == 0:
                    continue
                
                entry_price = rec_price_row.iloc[0]['close_price']
                entry_date = rec_price_row.iloc[0]['trade_date']
                
                # 1일 후 수익률
                return_1d = None
                price_1d_row = stock_prices[stock_prices['trade_date'] > entry_date]
                if len(price_1d_row) > 0:
                    price_1d = price_1d_row.iloc[0]['close_price']
                    return_1d = ((price_1d - entry_price) / entry_price) * 100
                
                # 5일 후 수익률
                return_5d = None
                price_5d_row = stock_prices[stock_prices['trade_date'] >= entry_date + pd.Timedelta(days=5)]
                if len(price_5d_row) > 0:
                    price_5d = price_5d_row.iloc[0]['close_price']
                    return_5d = ((price_5d - entry_price) / entry_price) * 100
                
                # 10일 후 수익률
                return_10d = None
                price_10d_row = stock_prices[stock_prices['trade_date'] >= entry_date + pd.Timedelta(days=10)]
                if len(price_10d_row) > 0:
                    price_10d = price_10d_row.iloc[0]['close_price']
                    return_10d = ((price_10d - entry_price) / entry_price) * 100
                
                results.append({
                    'recommendation_id': rec['recommendation_id'],
                    'stock_code': rec['stock_code'],
                    'stock_name': rec['stock_name'],
                    'recommendation_date': rec['recommendation_date'],
                    'ml_score': rec['ml_score'],
                    'universe_rank': rec['universe_rank'],
                    'entry_price': entry_price,
                    'entry_date': entry_date.date(),
                    'return_1d': return_1d,
                    'return_5d': return_5d,
                    'return_10d': return_10d
                })
            
            if not results:
                print("❌ 계산 가능한 수익률 없음")
                return pd.DataFrame()
            
            result_df = pd.DataFrame(results)
            print(f"✅ {len(result_df)}개 종목 수익률 계산 완료")
            return result_df
            
        except Exception as e:
            print(f"❌ 수익률 계산 실패: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def analyze_performance(self, backtest_df: pd.DataFrame) -> Dict:
        """성과 분석"""
        print("📊 성과 분석 중...")
        
        try:
            if backtest_df.empty:
                return {}
            
            # 기본 통계
            total_recommendations = len(backtest_df)
            
            # 1일 수익률 분석
            returns_1d = backtest_df['return_1d'].dropna()
            if len(returns_1d) > 0:
                avg_return_1d = returns_1d.mean()
                positive_1d = (returns_1d > 0).sum()
                win_rate_1d = (positive_1d / len(returns_1d)) * 100
            else:
                avg_return_1d = 0
                win_rate_1d = 0
            
            # 5일 수익률 분석
            returns_5d = backtest_df['return_5d'].dropna()
            if len(returns_5d) > 0:
                avg_return_5d = returns_5d.mean()
                positive_5d = (returns_5d > 0).sum()
                win_rate_5d = (positive_5d / len(returns_5d)) * 100
            else:
                avg_return_5d = 0
                win_rate_5d = 0
            
            # 10일 수익률 분석
            returns_10d = backtest_df['return_10d'].dropna()
            if len(returns_10d) > 0:
                avg_return_10d = returns_10d.mean()
                positive_10d = (returns_10d > 0).sum()
                win_rate_10d = (positive_10d / len(returns_10d)) * 100
            else:
                avg_return_10d = 0
                win_rate_10d = 0
            
            # 랭킹별 성과 (상위 5개 vs 전체)
            top5_df = backtest_df[backtest_df['universe_rank'] <= 5]
            if len(top5_df) > 0:
                top5_return_1d = top5_df['return_1d'].dropna().mean()
                top5_win_rate_1d = (top5_df['return_1d'].dropna() > 0).mean() * 100
            else:
                top5_return_1d = 0
                top5_win_rate_1d = 0
            
            # 최고/최악 성과
            if len(returns_1d) > 0:
                best_return = returns_1d.max()
                worst_return = returns_1d.min()
                best_stock = backtest_df.loc[returns_1d.idxmax(), 'stock_name'] if not returns_1d.empty else "N/A"
                worst_stock = backtest_df.loc[returns_1d.idxmin(), 'stock_name'] if not returns_1d.empty else "N/A"
            else:
                best_return = 0
                worst_return = 0
                best_stock = "N/A"
                worst_stock = "N/A"
            
            analysis = {
                'total_recommendations': total_recommendations,
                'avg_return_1d': avg_return_1d,
                'avg_return_5d': avg_return_5d,
                'avg_return_10d': avg_return_10d,
                'win_rate_1d': win_rate_1d,
                'win_rate_5d': win_rate_5d,
                'win_rate_10d': win_rate_10d,
                'top5_return_1d': top5_return_1d,
                'top5_win_rate_1d': top5_win_rate_1d,
                'best_return': best_return,
                'worst_return': worst_return,
                'best_stock': best_stock,
                'worst_stock': worst_stock
            }
            
            print(f"✅ 성과 분석 완료")
            return analysis
            
        except Exception as e:
            print(f"❌ 성과 분석 실패: {e}")
            return {}
    
    def send_backtest_report(self, analysis: Dict, backtest_df: pd.DataFrame):
        """백테스트 리포트 발송"""
        print("📱 백테스트 리포트 발송 중...")
        
        try:
            if not analysis:
                print("❌ 분석 데이터 없음")
                return
            
            # 상위 5개 종목 성과
            top_performers = backtest_df.nlargest(5, 'return_1d')[['stock_name', 'return_1d', 'ml_score']].to_dict('records')
            worst_performers = backtest_df.nsmallest(5, 'return_1d')[['stock_name', 'return_1d', 'ml_score']].to_dict('records')
            
            message = (
                f"📊 **ML 주식 추천 백테스트 리포트**\n\n"
                f"📅 **분석 기간**: 최근 30일\n"
                f"📈 **총 추천 종목**: {analysis['total_recommendations']}개\n\n"
                f"💰 **수익률 성과**:\n"
                f"   1일: {analysis['avg_return_1d']:+.2f}% (승률: {analysis['win_rate_1d']:.1f}%)\n"
                f"   5일: {analysis['avg_return_5d']:+.2f}% (승률: {analysis['win_rate_5d']:.1f}%)\n"
                f"   10일: {analysis['avg_return_10d']:+.2f}% (승률: {analysis['win_rate_10d']:.1f}%)\n\n"
                f"🏆 **TOP 5 성과**:\n"
                f"   평균 수익률: {analysis['top5_return_1d']:+.2f}%\n"
                f"   승률: {analysis['top5_win_rate_1d']:.1f}%\n\n"
                f"📈 **최고 성과**: {analysis['best_return']:+.2f}% ({analysis['best_stock']})\n"
                f"📉 **최악 성과**: {analysis['worst_return']:+.2f}% ({analysis['worst_stock']})\n\n"
            )
            
            # 상위 종목들
            if top_performers:
                message += f"🌟 **상위 성과 종목**:\n"
                for i, perf in enumerate(top_performers[:3], 1):
                    message += f"   {i}. {perf['stock_name']}: {perf['return_1d']:+.2f}% (ML점수: {perf['ml_score']:.3f})\n"
            
            message += f"\n📊 **모델 성능이 {'우수' if analysis['win_rate_1d'] > 55 else '보통' if analysis['win_rate_1d'] > 45 else '개선필요'}합니다**"
            
            if analysis['win_rate_1d'] < 45:
                message += f"\n⚠️ **개선 권장사항**: 승률이 낮습니다. 모델 재학습을 고려하세요."
            
            self.notification._send_simple_slack_message(message)
            print("✅ 백테스트 리포트 발송 완료")
            
        except Exception as e:
            print(f"❌ 리포트 발송 실패: {e}")
    
    def run_backtest(self, days_back: int = 30):
        """백테스트 실행"""
        print(f"🔍 백테스트 시작 (최근 {days_back}일)")
        print("="*60)
        
        try:
            # 1. 추천 이력 조회
            recommendations_df = self.get_recommendations_history(days_back)
            if recommendations_df.empty:
                print("❌ 백테스트할 데이터 없음")
                return
            
            # 2. 가격 데이터 조회
            stock_ids = recommendations_df['stock_id'].unique().tolist()
            start_date = recommendations_df['recommendation_date'].min()
            end_date = datetime.now().date()
            
            price_df = self.get_price_data_for_backtest(stock_ids, start_date, end_date)
            if price_df.empty:
                print("❌ 가격 데이터 없음")
                return
            
            # 3. 수익률 계산
            backtest_df = self.calculate_returns(recommendations_df, price_df)
            if backtest_df.empty:
                print("❌ 수익률 계산 실패")
                return
            
            # 4. 성과 분석
            analysis = self.analyze_performance(backtest_df)
            
            # 5. 리포트 출력
            print(f"\n📊 백테스트 결과:")
            print(f"   총 추천: {analysis.get('total_recommendations', 0)}개")
            print(f"   1일 평균 수익률: {analysis.get('avg_return_1d', 0):+.2f}%")
            print(f"   1일 승률: {analysis.get('win_rate_1d', 0):.1f}%")
            print(f"   TOP5 평균 수익률: {analysis.get('top5_return_1d', 0):+.2f}%")
            
            # 6. 알림 발송
            self.send_backtest_report(analysis, backtest_df)
            
            print(f"✅ 백테스트 완료")
            
        except Exception as e:
            print(f"❌ 백테스트 실패: {e}")
            import traceback
            traceback.print_exc()


def main():
    """메인 함수"""
    days = 30
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print("사용법: python backtesting_system.py [일수]")
            return
    
    backtest = BacktestingSystem()
    backtest.run_backtest(days)


if __name__ == "__main__":
    main()
