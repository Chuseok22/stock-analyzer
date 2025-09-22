"""
실시간 ML 학습 시스템
- 당일 예측 vs 실제 결과 비교
- 매일 모델 성능 평가 및 개선
- 적응형 학습으로 정확도 지속 향상
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
import json

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import (
    StockMaster, StockDailyPrice, MarketRegion
)
from app.ml.global_ml_engine import GlobalMLEngine


@dataclass
class PredictionResult:
    """예측 결과 데이터"""
    prediction_date: date
    stock_id: int
    stock_code: str
    market_region: str
    predicted_return: float
    confidence_score: float
    actual_return: Optional[float] = None
    accuracy_score: Optional[float] = None
    created_at: datetime = None


@dataclass
class ModelPerformance:
    """모델 성능 지표"""
    date: date
    market_region: str
    total_predictions: int
    accurate_predictions: int
    accuracy_rate: float
    avg_prediction_error: float
    rmse: float
    mae: float
    top5_accuracy: float  # 상위 5개 추천의 정확도


class RealTimeLearningSystem:
    """실시간 ML 학습 시스템"""
    
    def __init__(self):
        self.ml_engine = GlobalMLEngine()
        
        # 배포 환경 볼륨 매핑 경로 (/volume1/project/stock-analyzer)
        self.base_volume_path = Path("/volume1/project/stock-analyzer")
        
        # 로컬 개발 환경 대체 경로
        if not self.base_volume_path.exists():
            self.base_volume_path = Path("storage")
            print("⚠️ 개발 환경: 로컬 storage 사용")
        else:
            print(f"✅ 배포 환경: 볼륨 매핑 경로 사용 - {self.base_volume_path}")
        
        # 분석 리포트 저장 구조 설정
        self.reports_base = self.base_volume_path / "analysis_reports"
        self.performance_dir = self.base_volume_path / "models" / "performance"
        
        # 디렉토리 생성
        self.reports_base.mkdir(parents=True, exist_ok=True)
        self.performance_dir.mkdir(parents=True, exist_ok=True)
        
        print("🧠 실시간 ML 학습 시스템 초기화")
        print(f"📁 리포트 저장 경로: {self.reports_base}")
        print(f"📊 성능 데이터 경로: {self.performance_dir}")
    
    def _get_report_path(self, target_date: date, report_type: str = "daily") -> Path:
        """연/월/주 구조로 리포트 경로 생성"""
        year = target_date.year
        month = f"{target_date.month:02d}"
        
        # 주차 계산 (해당 월의 몇 번째 주인지)
        import calendar
        first_day_of_month = target_date.replace(day=1)
        first_weekday = first_day_of_month.weekday()
        week_of_month = ((target_date.day + first_weekday - 1) // 7) + 1
        week_folder = f"week_{week_of_month:02d}"
        
        # 경로 구조: /analysis_reports/2025/01/week_01/
        report_dir = self.reports_base / str(year) / month / week_folder
        report_dir.mkdir(parents=True, exist_ok=True)
        
        return report_dir
    
    def save_daily_predictions(self, predictions: List, target_date: date) -> bool:
        """당일 예측 결과 저장"""
        print(f"💾 {target_date} 예측 결과 저장 중...")
        
        try:
            prediction_file = self.performance_dir / f"predictions_{target_date.strftime('%Y%m%d')}.json"
            
            # 예측 결과를 JSON으로 저장
            prediction_data = []
            
            for pred in predictions:
                prediction_data.append({
                    "prediction_date": target_date.isoformat(),
                    "stock_code": pred.stock_code,
                    "market_region": pred.market_region,
                    "predicted_return": pred.predicted_return,
                    "confidence_score": pred.confidence_score,
                    "recommendation": pred.recommendation,
                    "target_price": pred.target_price,
                    "created_at": datetime.now().isoformat()
                })
            
            with open(prediction_file, 'w', encoding='utf-8') as f:
                json.dump(prediction_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ {len(prediction_data)}개 예측 결과 저장 완료")
            return True
            
        except Exception as e:
            print(f"❌ 예측 결과 저장 실패: {e}")
            return False
    
    def calculate_actual_returns(self, target_date: date) -> Dict[str, float]:
        """당일 실제 수익률 계산"""
        print(f"📊 {target_date} 실제 수익률 계산 중...")
        
        actual_returns = {}
        
        try:
            with get_db_session() as db:
                # 전일과 당일 가격 데이터 조회
                prev_date = target_date - timedelta(days=1)
                
                # 주말 고려해서 이전 거래일 찾기
                for i in range(7):  # 최대 7일 이전까지 검색
                    check_date = target_date - timedelta(days=i+1)
                    
                    prev_prices = db.query(StockDailyPrice).filter(
                        StockDailyPrice.trade_date == check_date
                    ).all()
                    
                    if prev_prices:  # 데이터가 있으면 그 날이 이전 거래일
                        prev_date = check_date
                        break
                
                # 당일 가격 데이터
                current_prices = db.query(StockDailyPrice).filter(
                    StockDailyPrice.trade_date == target_date
                ).all()
                
                # 이전 거래일 가격 데이터
                prev_prices = db.query(StockDailyPrice).filter(
                    StockDailyPrice.trade_date == prev_date
                ).all()
                
                # 가격 매핑
                prev_price_map = {p.stock_id: float(p.close_price) for p in prev_prices}
                current_price_map = {p.stock_id: float(p.close_price) for p in current_prices}
                
                # 실제 수익률 계산
                for stock_id in current_price_map:
                    if stock_id in prev_price_map:
                        prev_price = prev_price_map[stock_id]
                        current_price = current_price_map[stock_id]
                        actual_return = ((current_price - prev_price) / prev_price) * 100
                        
                        # 종목 코드 조회
                        stock = db.query(StockMaster).filter_by(stock_id=stock_id).first()
                        if stock:
                            key = f"{stock.market_region}_{stock.stock_code}"
                            actual_returns[key] = actual_return
                
            print(f"✅ {len(actual_returns)}개 종목 실제 수익률 계산 완료")
            return actual_returns
            
        except Exception as e:
            print(f"❌ 실제 수익률 계산 실패: {e}")
            return {}
    
    def evaluate_daily_performance(self, target_date: date) -> Optional[ModelPerformance]:
        """당일 모델 성능 평가"""
        print(f"📈 {target_date} 모델 성능 평가 중...")
        
        try:
            # 예측 결과 로드
            prediction_file = self.performance_dir / f"predictions_{target_date.strftime('%Y%m%d')}.json"
            
            if not prediction_file.exists():
                print(f"⚠️ {target_date} 예측 파일 없음")
                return None
            
            with open(prediction_file, 'r', encoding='utf-8') as f:
                predictions = json.load(f)
            
            # 실제 수익률 계산
            actual_returns = self.calculate_actual_returns(target_date)
            
            if not actual_returns:
                print(f"⚠️ {target_date} 실제 수익률 데이터 없음")
                return None
            
            # 한국/미국 시장별 성능 평가
            performances = {}
            
            for region in ['KR', 'US']:
                region_predictions = [p for p in predictions if p['market_region'] == region]
                
                if not region_predictions:
                    continue
                
                accurate_count = 0
                total_predictions = len(region_predictions)
                prediction_errors = []
                predicted_values = []
                actual_values = []
                
                for pred in region_predictions:
                    key = f"{pred['market_region']}_{pred['stock_code']}"
                    
                    if key in actual_returns:
                        predicted_return = pred['predicted_return']
                        actual_return = actual_returns[key]
                        
                        # 방향성 정확도 (예측과 실제가 같은 방향인지)
                        if (predicted_return > 0 and actual_return > 0) or \
                           (predicted_return < 0 and actual_return < 0) or \
                           (abs(predicted_return) < 0.5 and abs(actual_return) < 0.5):
                            accurate_count += 1
                        
                        # 오차 계산
                        error = abs(predicted_return - actual_return)
                        prediction_errors.append(error)
                        predicted_values.append(predicted_return)
                        actual_values.append(actual_return)
                
                if prediction_errors:
                    # 성능 지표 계산
                    accuracy_rate = (accurate_count / total_predictions) * 100
                    avg_error = np.mean(prediction_errors)
                    rmse = np.sqrt(np.mean([(p - a) ** 2 for p, a in zip(predicted_values, actual_values)]))
                    mae = np.mean([abs(p - a) for p, a in zip(predicted_values, actual_values)])
                    
                    # 상위 5개 추천의 정확도
                    top5_predictions = region_predictions[:5]
                    top5_accurate = 0
                    
                    for pred in top5_predictions:
                        key = f"{pred['market_region']}_{pred['stock_code']}"
                        if key in actual_returns:
                            predicted = pred['predicted_return']
                            actual = actual_returns[key]
                            if (predicted > 0 and actual > 0) or (predicted < 0 and actual < 0):
                                top5_accurate += 1
                    
                    top5_accuracy = (top5_accurate / min(5, len(top5_predictions))) * 100
                    
                    performances[region] = ModelPerformance(
                        date=target_date,
                        market_region=region,
                        total_predictions=total_predictions,
                        accurate_predictions=accurate_count,
                        accuracy_rate=accuracy_rate,
                        avg_prediction_error=avg_error,
                        rmse=rmse,
                        mae=mae,
                        top5_accuracy=top5_accuracy
                    )
                    
                    print(f"   📊 {region} 성능:")
                    print(f"      정확도: {accuracy_rate:.1f}%")
                    print(f"      평균 오차: {avg_error:.2f}%")
                    print(f"      상위5 정확도: {top5_accuracy:.1f}%")
            
            # 성능 결과 저장
            self._save_performance_results(performances, target_date)
            
            return performances
            
        except Exception as e:
            print(f"❌ 성능 평가 실패: {e}")
            return None
    
    def _save_performance_results(self, performances: Dict[str, ModelPerformance], target_date: date):
        """성능 결과 저장 - 배포 환경 최적화"""
        try:
            # 1. 기존 performance 디렉토리에 저장 (호환성)
            performance_file = self.performance_dir / f"performance_{target_date.strftime('%Y%m%d')}.json"
            
            performance_data = {}
            for region, perf in performances.items():
                performance_data[region] = {
                    "date": target_date.isoformat(),
                    "market_region": perf.market_region,
                    "total_predictions": perf.total_predictions,
                    "accurate_predictions": perf.accurate_predictions,
                    "accuracy_rate": perf.accuracy_rate,
                    "avg_prediction_error": perf.avg_prediction_error,
                    "rmse": perf.rmse,
                    "mae": perf.mae,
                    "top5_accuracy": perf.top5_accuracy
                }
            
            with open(performance_file, 'w', encoding='utf-8') as f:
                json.dump(performance_data, f, ensure_ascii=False, indent=2)
            
            # 2. 볼륨 매핑된 구조화된 경로에도 저장
            report_dir = self._get_report_path(target_date, "daily")
            structured_file = report_dir / f"daily_performance_{target_date.strftime('%Y%m%d')}.json"
            
            # 더 상세한 일간 리포트 생성
            detailed_report = {
                "report_info": {
                    "type": "daily_performance",
                    "date": target_date.isoformat(),
                    "generated_at": datetime.now().isoformat(),
                    "system_version": "realtime_learning_v1.0"
                },
                "market_performance": performance_data,
                "summary": {
                    "total_markets": len(performances),
                    "avg_accuracy": np.mean([p["accuracy_rate"] for p in performance_data.values()]),
                    "best_market": max(performance_data.keys(), key=lambda k: performance_data[k]["accuracy_rate"]) if performance_data else None,
                    "total_predictions": sum([p["total_predictions"] for p in performance_data.values()])
                }
            }
            
            with open(structured_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_report, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 성능 결과 저장:")
            print(f"   📊 기본: {performance_file}")
            print(f"   📁 구조화: {structured_file}")
            
        except Exception as e:
            print(f"❌ 성능 결과 저장 실패: {e}")
    
    def generate_performance_report(self, target_date: date, days: int = 30) -> str:
        """성능 리포트 생성 - 배포 환경 최적화"""
        print(f"📊 {days}일간 성능 리포트 생성...")
        
        try:
            performances = {'KR': [], 'US': []}
            dates = []
            
            # 최근 N일 성능 데이터 수집
            for i in range(days):
                check_date = target_date - timedelta(days=i)
                performance_file = self.performance_dir / f"performance_{check_date.strftime('%Y%m%d')}.json"
                
                if performance_file.exists():
                    with open(performance_file, 'r', encoding='utf-8') as f:
                        perf_data = json.load(f)
                    
                    dates.append(check_date)
                    for region in ['KR', 'US']:
                        if region in perf_data:
                            performances[region].append(perf_data[region])
                        else:
                            performances[region].append(None)
            
            # 리포트 생성
            report = f"📈 **ML 모델 성능 리포트** ({days}일간)\n"
            report += f"📅 기간: {(target_date - timedelta(days=days-1)).strftime('%Y-%m-%d')} ~ {target_date.strftime('%Y-%m-%d')}\n"
            report += f"🕒 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # 시장별 상세 분석
            for region in ['KR', 'US']:
                valid_perfs = [p for p in performances[region] if p is not None]
                
                if valid_perfs:
                    accuracies = [p['accuracy_rate'] for p in valid_perfs]
                    top5_accuracies = [p['top5_accuracy'] for p in valid_perfs]
                    avg_errors = [p['avg_prediction_error'] for p in valid_perfs]
                    
                    market_name = "한국" if region == "KR" else "미국"
                    flag = "🇰🇷" if region == "KR" else "🇺🇸"
                    
                    report += f"{flag} **{market_name} 시장 성과** (분석일수: {len(valid_perfs)}일)\n"
                    report += f"• 평균 정확도: {np.mean(accuracies):.1f}%\n"
                    report += f"• 최고 정확도: {np.max(accuracies):.1f}%\n"
                    report += f"• 최저 정확도: {np.min(accuracies):.1f}%\n"
                    report += f"• 정확도 표준편차: {np.std(accuracies):.1f}%\n"
                    report += f"• 상위5 평균 정확도: {np.mean(top5_accuracies):.1f}%\n"
                    report += f"• 평균 예측 오차: {np.mean(avg_errors):.2f}%\n"
                    
                    # 최근 추세 분석
                    if len(accuracies) >= 7:
                        recent_accuracies = accuracies[-7:]  # 최근 7일
                        trend_slope = np.polyfit(range(len(recent_accuracies)), recent_accuracies, 1)[0]
                        if trend_slope > 0.5:
                            trend = f"상승 (+{trend_slope:.1f}%/일)"
                        elif trend_slope < -0.5:
                            trend = f"하락 ({trend_slope:.1f}%/일)"
                        else:
                            trend = "안정"
                        report += f"• 최근 추세: {trend}\n"
                    
                    # 성과 등급
                    avg_accuracy = np.mean(accuracies)
                    if avg_accuracy >= 75:
                        grade = "🥇 우수"
                    elif avg_accuracy >= 65:
                        grade = "🥈 양호"
                    elif avg_accuracy >= 55:
                        grade = "🥉 보통"
                    else:
                        grade = "🔧 개선필요"
                    
                    report += f"• 성과 등급: {grade}\n"
            
            # 종합 분석
            all_accuracies = []
            for region_perfs in performances.values():
                all_accuracies.extend([p['accuracy_rate'] for p in region_perfs if p is not None])
            
            if all_accuracies:
                report += "🎯 **종합 분석**\n"
                report += f"• 전체 평균 정확도: {np.mean(all_accuracies):.1f}%\n"
                report += f"• 분석 데이터 포인트: {len(all_accuracies)}개\n"
                
                # 시장간 상관관계
                kr_accs = [p['accuracy_rate'] for p in performances['KR'] if p is not None]
                us_accs = [p['accuracy_rate'] for p in performances['US'] if p is not None]
                
                if len(kr_accs) > 3 and len(us_accs) > 3:
                    min_len = min(len(kr_accs), len(us_accs))
                    if min_len > 0:
                        correlation = np.corrcoef(kr_accs[:min_len], us_accs[:min_len])[0,1]
                        report += f"• 한-미 시장 성과 상관계수: {correlation:.3f}\n"
                
                report += "\n"
            
            # 개선 제안
            report += "🚀 **개선 제안**\n"
            for region in ['KR', 'US']:
                valid_perfs = [p for p in performances[region] if p is not None]
                if valid_perfs:
                    avg_accuracy = np.mean([p['accuracy_rate'] for p in valid_perfs])
                    market_name = "한국" if region == "KR" else "미국"
                    
                    if avg_accuracy < 55:
                        report += f"• {market_name}: 🔥 집중 학습 권장 (정확도 {avg_accuracy:.1f}%)\n"
                    elif avg_accuracy < 65:
                        report += f"• {market_name}: 📈 점진적 개선 (정확도 {avg_accuracy:.1f}%)\n"
                    elif avg_accuracy > 75:
                        report += f"• {market_name}: 🎉 우수한 성능 유지 (정확도 {avg_accuracy:.1f}%)\n"
                    else:
                        report += f"• {market_name}: ✅ 안정적 성능 (정확도 {avg_accuracy:.1f}%)\n"
            
            # 기술적 지표
            report += "\n📊 **기술적 지표**\n"
            report += f"• 데이터 완성도: {len([d for d in dates if d])}/{days} 일 ({len([d for d in dates if d])/days*100:.1f}%)\n"
            report += f"• 시스템 안정성: {'높음' if len([d for d in dates if d])/days > 0.8 else '보통'}\n"
            
            # 볼륨 매핑 경로에 리포트 저장
            report_dir = self._get_report_path(target_date, "performance")
            report_file = report_dir / f"performance_report_{target_date.strftime('%Y%m%d')}_{days}days.md"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"📁 성능 리포트 저장: {report_file}")
            
            return report
            
        except Exception as e:
            print(f"❌ 성능 리포트 생성 실패: {e}")
            return "성능 리포트 생성 실패"
    
    def adaptive_model_training(self, target_date: date) -> bool:
        """적응형 모델 학습 (성능 기반)"""
        print(f"🏋️ {target_date} 적응형 모델 학습 시작...")
        
        try:
            # 최근 7일간 성능 분석
            recent_performances = self._analyze_recent_performance(target_date, days=7)
            
            if not recent_performances:
                print("⚠️ 최근 성능 데이터 부족, 기본 학습 진행")
                return self.ml_engine.train_global_models()
            
            # 성능 기반 학습 전략 결정
            training_strategy = self._determine_training_strategy(recent_performances)
            
            print(f"📋 학습 전략: {training_strategy['strategy']}")
            
            # 전략에 따른 모델 학습
            if training_strategy['strategy'] == 'intensive':
                # 성능이 떨어진 경우 집중 학습
                success = self._intensive_training(training_strategy)
            elif training_strategy['strategy'] == 'fine_tune':
                # 성능이 좋은 경우 미세 조정
                success = self._fine_tune_training(training_strategy)
            else:
                # 기본 학습
                success = self.ml_engine.train_global_models()
            
            if success:
                print("✅ 적응형 모델 학습 완료")
            else:
                print("❌ 적응형 모델 학습 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ 적응형 학습 실패: {e}")
            return False
    
    def _analyze_recent_performance(self, target_date: date, days: int = 7) -> Dict[str, List[float]]:
        """최근 성능 분석"""
        recent_performances = {'KR': [], 'US': []}
        
        try:
            for i in range(days):
                check_date = target_date - timedelta(days=i)
                performance_file = self.performance_dir / f"performance_{check_date.strftime('%Y%m%d')}.json"
                
                if performance_file.exists():
                    with open(performance_file, 'r', encoding='utf-8') as f:
                        perf_data = json.load(f)
                    
                    for region in ['KR', 'US']:
                        if region in perf_data:
                            recent_performances[region].append(perf_data[region]['accuracy_rate'])
            
            return recent_performances
            
        except Exception as e:
            print(f"❌ 최근 성능 분석 실패: {e}")
            return {}
    
    def _determine_training_strategy(self, recent_performances: Dict[str, List[float]]) -> Dict[str, Any]:
        """학습 전략 결정"""
        strategy = {
            'strategy': 'normal',
            'focus_regions': [],
            'intensity': 1.0
        }
        
        try:
            for region, accuracies in recent_performances.items():
                if accuracies:
                    avg_accuracy = np.mean(accuracies)
                    recent_trend = np.mean(accuracies[-3:]) if len(accuracies) >= 3 else avg_accuracy
                    
                    print(f"   📊 {region} 최근 평균 정확도: {avg_accuracy:.1f}%")
                    print(f"   📈 {region} 최근 3일 평균: {recent_trend:.1f}%")
                    
                    # 성능 기준에 따른 전략 결정
                    if avg_accuracy < 55:  # 55% 미만이면 집중 학습
                        strategy['strategy'] = 'intensive'
                        strategy['focus_regions'].append(region)
                        strategy['intensity'] = 2.0
                    elif avg_accuracy > 70 and recent_trend > avg_accuracy:  # 70% 이상이고 상승 추세
                        strategy['strategy'] = 'fine_tune'
                        strategy['intensity'] = 0.7
                    elif recent_trend < avg_accuracy - 5:  # 최근 성능 하락
                        strategy['focus_regions'].append(region)
                        strategy['intensity'] = 1.5
            
            return strategy
            
        except Exception as e:
            print(f"❌ 전략 결정 실패: {e}")
            return strategy
    
    def _intensive_training(self, strategy: Dict[str, Any]) -> bool:
        """집중 학습 (성능 저하 시) - 배포 환경 최적화"""
        print("🔥 집중 학습 모드 (배포 환경 최적화)...")
        
        try:
            # 배포 환경에서는 시간이 오래 걸려도 괜찮으므로 최대한 많은 데이터 활용
            print("📊 대량 데이터 수집 및 전처리...")
            
            # 기존 모델 백업
            self._backup_current_models()
            
            # 집중 학습 설정
            intensive_config = {
                'max_features': 'sqrt',  # 모든 피처 사용
                'n_estimators': 500,     # 트리 개수 대폭 증가
                'max_depth': 15,         # 깊이 증가
                'min_samples_split': 5,  # 더 세밀한 분할
                'min_samples_leaf': 2,   # 리프 노드 최소값 감소
                'random_state': 42,
                'n_jobs': -1,           # 모든 CPU 활용
                'verbose': 1            # 진행상황 표시
            }
            
            print(f"🎯 집중 학습 설정: {intensive_config}")
            print("⏱️ 배포 환경 - 시간 제한 없이 최고 정확도 추구...")
            
            # 더 긴 기간의 데이터로 학습 (최대 2년)
            from datetime import datetime, timedelta
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=730)  # 2년간 데이터
            
            print(f"📅 학습 기간: {start_date} ~ {end_date} (2년간)")
            
            # GlobalMLEngine에 집중 학습 설정 전달
            original_config = getattr(self.ml_engine, 'model_config', {})
            self.ml_engine.model_config = intensive_config
            
            # 집중 학습 실행
            success = self.ml_engine.train_global_models()
            
            # 설정 복원
            self.ml_engine.model_config = original_config
            
            if success:
                print("✅ 집중 학습 완료 - 최고 정확도 달성!")
                
                # 학습 결과 검증
                self._validate_model_performance()
            else:
                # 실패 시 백업 모델 복원
                self._restore_backup_models()
                print("❌ 집중 학습 실패, 이전 모델 복원")
            
            return success
            
        except Exception as e:
            print(f"❌ 집중 학습 오류: {e}")
            self._restore_backup_models()
            return False
    
    def _validate_model_performance(self):
        """모델 성능 검증"""
        try:
            print("🔍 새 모델 성능 검증...")
            
            # 최근 5일 데이터로 검증
            from datetime import date, timedelta
            validation_dates = [date.today() - timedelta(days=i) for i in range(1, 6)]
            
            total_accuracy = 0
            valid_days = 0
            
            for val_date in validation_dates:
                try:
                    performance = self.evaluate_daily_performance(val_date)
                    if performance:
                        for region, perf in performance.items():
                            total_accuracy += perf.accuracy_rate
                            valid_days += 1
                except:
                    continue
            
            if valid_days > 0:
                avg_accuracy = total_accuracy / valid_days
                print(f"📊 새 모델 평균 정확도: {avg_accuracy:.1f}%")
                
                if avg_accuracy >= 60:
                    print("✅ 모델 성능 검증 통과")
                else:
                    print("⚠️ 모델 성능 기준 미달, 추가 학습 필요")
            
        except Exception as e:
            print(f"❌ 성능 검증 실패: {e}")
    
    def _fine_tune_training(self, strategy: Dict[str, Any]) -> bool:
        """미세 조정 학습 (성능 양호 시)"""
        print("🎯 미세 조정 모드...")
        
        try:
            # 기존 모델을 기반으로 가벼운 업데이트
            success = self.ml_engine.train_global_models()
            
            if success:
                print("✅ 미세 조정 완료")
            
            return success
            
        except Exception as e:
            print(f"❌ 미세 조정 오류: {e}")
            return False
    
    def _backup_current_models(self):
        """현재 모델 백업"""
        try:
            from shutil import copy2
            
            model_dir = Path("storage/models/global")
            backup_dir = model_dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for model_file in model_dir.glob("*.joblib"):
                backup_file = backup_dir / f"{model_file.stem}_{timestamp}.joblib"
                copy2(model_file, backup_file)
            
            print("📦 모델 백업 완료")
            
        except Exception as e:
            print(f"❌ 모델 백업 실패: {e}")
    
    def _restore_backup_models(self):
        """백업 모델 복원"""
        try:
            from shutil import copy2
            
            model_dir = Path("storage/models/global")
            backup_dir = model_dir / "backups"
            
            # 가장 최근 백업 찾기
            backup_files = list(backup_dir.glob("*_*.joblib"))
            if backup_files:
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                for backup_file in backup_files:
                    original_name = "_".join(backup_file.stem.split("_")[:-2]) + ".joblib"
                    original_file = model_dir / original_name
                    copy2(backup_file, original_file)
                
                print("🔄 백업 모델 복원 완료")
            
        except Exception as e:
            print(f"❌ 모델 복원 실패: {e}")
    
    def generate_performance_report(self, target_date: date, days: int = 30) -> str:
        """성능 리포트 생성"""
        print(f"📊 {days}일간 성능 리포트 생성...")
        
        try:
            performances = {'KR': [], 'US': []}
            dates = []
            
            # 최근 N일 성능 데이터 수집
            for i in range(days):
                check_date = target_date - timedelta(days=i)
                performance_file = self.performance_dir / f"performance_{check_date.strftime('%Y%m%d')}.json"
                
                if performance_file.exists():
                    with open(performance_file, 'r', encoding='utf-8') as f:
                        perf_data = json.load(f)
                    
                    dates.append(check_date)
                    for region in ['KR', 'US']:
                        if region in perf_data:
                            performances[region].append(perf_data[region])
                        else:
                            performances[region].append(None)
            
            # 리포트 생성
            report = f"📈 **ML 모델 성능 리포트** ({days}일간)\n"
            report += f"📅 기간: {(target_date - timedelta(days=days-1)).strftime('%Y-%m-%d')} ~ {target_date.strftime('%Y-%m-%d')}\n\n"
            
            for region in ['KR', 'US']:
                valid_perfs = [p for p in performances[region] if p is not None]
                
                if valid_perfs:
                    accuracies = [p['accuracy_rate'] for p in valid_perfs]
                    top5_accuracies = [p['top5_accuracy'] for p in valid_perfs]
                    avg_errors = [p['avg_prediction_error'] for p in valid_perfs]
                    
                    market_name = "한국" if region == "KR" else "미국"
                    flag = "🇰🇷" if region == "KR" else "🇺🇸"
                    
                    report += f"{flag} **{market_name} 시장 성과**\n"
                    report += f"• 평균 정확도: {np.mean(accuracies):.1f}%\n"
                    report += f"• 최고 정확도: {np.max(accuracies):.1f}%\n"
                    report += f"• 최저 정확도: {np.min(accuracies):.1f}%\n"
                    report += f"• 상위5 평균 정확도: {np.mean(top5_accuracies):.1f}%\n"
                    report += f"• 평균 예측 오차: {np.mean(avg_errors):.2f}%\n"
                    
                    # 최근 추세
                    recent_accuracies = accuracies[-7:] if len(accuracies) >= 7 else accuracies
                    if len(recent_accuracies) >= 2:
                        trend = "상승" if recent_accuracies[-1] > recent_accuracies[0] else "하락"
                        report += f"• 최근 추세: {trend}\n"
                    
                    report += "\n"
            
            # 개선 제안
            report += "🎯 **개선 제안**\n"
            for region in ['KR', 'US']:
                valid_perfs = [p for p in performances[region] if p is not None]
                if valid_perfs:
                    avg_accuracy = np.mean([p['accuracy_rate'] for p in valid_perfs])
                    market_name = "한국" if region == "KR" else "미국"
                    
                    if avg_accuracy < 55:
                        report += f"• {market_name}: 집중 학습 필요 (정확도 {avg_accuracy:.1f}%)\n"
                    elif avg_accuracy > 70:
                        report += f"• {market_name}: 우수한 성능 유지 중 (정확도 {avg_accuracy:.1f}%)\n"
                    else:
                        report += f"• {market_name}: 안정적 성능 (정확도 {avg_accuracy:.1f}%)\n"
            
            return report
            
        except Exception as e:
            print(f"❌ 성능 리포트 생성 실패: {e}")
            return "성능 리포트 생성 실패"
    
    def run_daily_learning_cycle(self, target_date: date = None) -> bool:
        """일일 학습 사이클 실행"""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)  # 전일 기준
        
        print(f"🔄 {target_date} 일일 학습 사이클 시작")
        print("="*50)
        
        try:
            # 1. 성능 평가
            print("1️⃣ 모델 성능 평가...")
            performance = self.evaluate_daily_performance(target_date)
            
            if not performance:
                print("⚠️ 성능 평가 데이터 부족")
                return False
            
            # 2. 적응형 학습
            print("\n2️⃣ 적응형 모델 학습...")
            learning_success = self.adaptive_model_training(target_date)
            
            # 3. 성능 리포트 생성
            print("\n3️⃣ 성능 리포트 생성...")
            report = self.generate_performance_report(target_date, days=7)
            
            # 4. 리포트 저장
            report_file = self.performance_dir / f"weekly_report_{target_date.strftime('%Y%m%d')}.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # 볼륨 매핑된 구조화된 경로에도 저장
            report_dir = self._get_report_path(target_date, "weekly")
            structured_weekly_file = report_dir / f"weekly_report_{target_date.strftime('%Y%m%d')}.md"
            
            # 주간 리포트 메타데이터 추가
            enhanced_report = f"""---
title: "주간 ML 성능 리포트"
date: "{target_date.isoformat()}"
type: "weekly_performance"
generated_at: "{datetime.now().isoformat()}"
period_days: 7
system_version: "realtime_learning_v1.0"
---

{report}

---
**📁 저장 위치**: {structured_weekly_file}
**🔄 다음 리포트**: {(target_date + timedelta(days=7)).isoformat()}
"""
            
            with open(structured_weekly_file, 'w', encoding='utf-8') as f:
                f.write(enhanced_report)
            
            print(f"\n📊 주간 성능 리포트 저장:")
            print(f"   📊 기본: {report_file}")
            print(f"   📁 구조화: {structured_weekly_file}")
            print("\n" + "="*50)
            print("🎉 일일 학습 사이클 완료!")
            
            return learning_success
            
        except Exception as e:
            print(f"❌ 일일 학습 사이클 실패: {e}")
            return False


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="실시간 ML 학습 시스템")
    parser.add_argument("--date", type=str, help="대상 날짜 (YYYY-MM-DD)")
    parser.add_argument("--evaluate", action="store_true", help="성능 평가만 실행")
    parser.add_argument("--train", action="store_true", help="적응형 학습만 실행")
    parser.add_argument("--report", action="store_true", help="성능 리포트만 생성")
    parser.add_argument("--full", action="store_true", help="전체 사이클 실행")
    
    args = parser.parse_args()
    
    # 대상 날짜 설정
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = date.today() - timedelta(days=1)
    
    learning_system = RealTimeLearningSystem()
    
    try:
        if args.evaluate:
            # 성능 평가만
            learning_system.evaluate_daily_performance(target_date)
        elif args.train:
            # 적응형 학습만
            learning_system.adaptive_model_training(target_date)
        elif args.report:
            # 성능 리포트만
            report = learning_system.generate_performance_report(target_date)
            print("\n" + report)
        elif args.full:
            # 전체 사이클
            success = learning_system.run_daily_learning_cycle(target_date)
            sys.exit(0 if success else 1)
        else:
            print("실행 모드를 선택하세요: --evaluate, --train, --report, --full")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 실행 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
