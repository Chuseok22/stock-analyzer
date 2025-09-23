#!/usr/bin/env python3
"""
성능 최적화 서비스
- 비동기 데이터 수집 및 처리
- 다층 캐싱 시스템
- DB 쿼리 최적화
- 메모리 관리 및 리소스 최적화
- 배치 처리 및 병렬 처리
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple, Callable
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# 선택적 의존성
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("⚠️ aiohttp 미설치 - 동기 HTTP 클라이언트 사용")

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except (ImportError, Exception) as e:
    AIOREDIS_AVAILABLE = False
    print(f"⚠️ aioredis 호환성 문제 - 기본 redis 클라이언트 사용: {e}")
import functools
import time
import gc
from dataclasses import dataclass
import json
import pickle
import hashlib

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))

from app.database.connection import get_db_session
from app.models.entities import StockMaster, StockDailyPrice, MarketRegion
from app.database.redis_client import redis_client
from app.utils.structured_logger import StructuredLogger


@dataclass
class CacheConfig:
    """캐시 설정"""
    ttl: int = 300              # 기본 TTL (5분)
    max_size: int = 1000        # 최대 캐시 크기
    compression: bool = True    # 압축 사용
    serialization: str = "json" # 직렬화 방식 (json, pickle)


@dataclass
class PerformanceMetrics:
    """성능 지표"""
    execution_time: float
    cache_hit_rate: float
    memory_usage_mb: float
    db_query_count: int
    api_call_count: int
    error_count: int


class AsyncCache:
    """비동기 캐시 시스템"""
    
    def __init__(self, redis_client, config: CacheConfig = None):
        self.redis = redis_client
        self.config = config or CacheConfig()
        self.local_cache = {}  # L1 캐시 (메모리)
        self.cache_stats = {'hits': 0, 'misses': 0}
        
    async def get(self, key: str, default=None) -> Any:
        """캐시에서 값 조회 (L1 -> L2 순서)"""
        try:
            # L1 캐시 (메모리) 확인
            if key in self.local_cache:
                entry = self.local_cache[key]
                if entry['expires'] > time.time():
                    self.cache_stats['hits'] += 1
                    return entry['value']
                else:
                    del self.local_cache[key]
            
            # L2 캐시 (Redis) 확인
            cached_data = self.redis.get(key)
            if cached_data:
                if self.config.serialization == "pickle":
                    value = pickle.loads(cached_data)
                else:
                    value = json.loads(cached_data)
                
                # L1 캐시에도 저장
                self.local_cache[key] = {
                    'value': value,
                    'expires': time.time() + min(self.config.ttl, 60)  # L1은 최대 1분
                }
                
                self.cache_stats['hits'] += 1
                return value
            
            self.cache_stats['misses'] += 1
            return default
            
        except Exception as e:
            print(f"캐시 조회 실패 {key}: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """캐시에 값 저장"""
        try:
            cache_ttl = ttl or self.config.ttl
            
            # 직렬화
            if self.config.serialization == "pickle":
                serialized_value = pickle.dumps(value)
            else:
                serialized_value = json.dumps(value, default=str)
            
            # L2 캐시 (Redis) 저장
            success = self.redis.set(key, serialized_value, cache_ttl)
            
            # L1 캐시 (메모리) 저장
            if len(self.local_cache) < self.config.max_size:
                self.local_cache[key] = {
                    'value': value,
                    'expires': time.time() + min(cache_ttl, 60)
                }
            
            return success
            
        except Exception as e:
            print(f"캐시 저장 실패 {key}: {e}")
            return False
    
    def get_hit_rate(self) -> float:
        """캐시 히트율 반환"""
        total = self.cache_stats['hits'] + self.cache_stats['misses']
        return self.cache_stats['hits'] / total if total > 0 else 0.0
    
    def clear_local_cache(self):
        """L1 캐시 정리"""
        current_time = time.time()
        expired_keys = [k for k, v in self.local_cache.items() if v['expires'] <= current_time]
        for key in expired_keys:
            del self.local_cache[key]


def cache_result(ttl: int = 300, key_prefix: str = ""):
    """결과 캐싱 데코레이터"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"
            
            # 캐시에서 조회
            cache = AsyncCache(redis_client)
            cached_result = await cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # 캐시 미스 - 함수 실행
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 결과 캐싱
            await cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


class AsyncAPIClient:
    """비동기 API 클라이언트"""
    
    def __init__(self, max_concurrent: int = 10, rate_limit: float = 0.1):
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        self.last_request_time = 0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=self.max_concurrent)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """비동기 HTTP 요청"""
        async with self.semaphore:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.rate_limit:
                await asyncio.sleep(self.rate_limit - time_since_last)
            
            self.last_request_time = time.time()
            
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"API 요청 실패 {url}: {response.status}")
                        return {}
            except Exception as e:
                print(f"API 요청 오류 {url}: {e}")
                return {}


class BatchProcessor:
    """배치 처리기"""
    
    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    async def process_in_batches(self, items: List[Any], processor: Callable, 
                               *args, **kwargs) -> List[Any]:
        """아이템들을 배치로 나누어 병렬 처리"""
        results = []
        
        # 배치로 분할
        batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        
        # 병렬 처리
        tasks = []
        for batch in batches:
            if asyncio.iscoroutinefunction(processor):
                task = processor(batch, *args, **kwargs)
            else:
                # CPU 집약적 작업은 별도 스레드에서 실행
                loop = asyncio.get_event_loop()
                task = loop.run_in_executor(self.executor, processor, batch, *args, **kwargs)
            tasks.append(task)
        
        # 모든 배치 완료 대기
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 취합
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                print(f"배치 처리 오류: {batch_result}")
                continue
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        
        return results
    
    def __del__(self):
        self.executor.shutdown(wait=False)


class DatabaseOptimizer:
    """데이터베이스 최적화"""
    
    @staticmethod
    def bulk_insert_optimized(session, model_class, data_list: List[Dict], 
                            batch_size: int = 1000):
        """최적화된 대량 삽입"""
        try:
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                session.bulk_insert_mappings(model_class, batch)
                
                # 메모리 관리
                if i % (batch_size * 5) == 0:
                    session.flush()
                    gc.collect()
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"대량 삽입 실패: {e}")
            return False
    
    @staticmethod
    def get_optimized_query_builder():
        """최적화된 쿼리 빌더"""
        return {
            'select_related': True,      # 관련 객체 미리 로드
            'batch_size': 1000,          # 배치 크기
            'use_index': True,           # 인덱스 힌트 사용
            'read_only': True            # 읽기 전용 최적화
        }


class PerformanceOptimizer:
    """성능 최적화 메인 클래스"""
    
    def __init__(self):
        self.logger = StructuredLogger("performance_optimizer")
        self.cache = AsyncCache(redis_client)
        self.batch_processor = BatchProcessor()
        self.api_client = None
        self.metrics = PerformanceMetrics(
            execution_time=0.0,
            cache_hit_rate=0.0,
            memory_usage_mb=0.0,
            db_query_count=0,
            api_call_count=0,
            error_count=0
        )
        
        self.logger.info("성능 최적화 시스템 초기화")
    
    @cache_result(ttl=300, key_prefix="stock_data")
    async def get_stock_data_cached(self, stock_codes: List[str], 
                                  region: MarketRegion) -> List[Dict]:
        """캐시된 주식 데이터 조회"""
        self.logger.info(f"캐시된 주식 데이터 조회: {len(stock_codes)}개 종목")
        
        try:
            start_time = time.time()
            
            with get_db_session() as db:
                # 최적화된 쿼리
                stocks = db.query(StockMaster).filter(
                    StockMaster.market_region == region.value,
                    StockMaster.stock_code.in_(stock_codes),
                    StockMaster.is_active == True
                ).all()
                
                self.metrics.db_query_count += 1
                
                # 최근 30일 가격 데이터
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                
                stock_data = []
                for stock in stocks:
                    prices = db.query(StockDailyPrice).filter(
                        StockDailyPrice.stock_id == stock.stock_id,
                        StockDailyPrice.trade_date >= start_date,
                        StockDailyPrice.trade_date <= end_date
                    ).order_by(StockDailyPrice.trade_date.desc()).limit(30).all()
                    
                    if prices:
                        stock_info = {
                            'stock_code': stock.stock_code,
                            'stock_name': stock.stock_name,
                            'market_region': stock.market_region,
                            'current_price': float(prices[0].close_price),
                            'price_change_pct': float(prices[0].daily_return_pct) if prices[0].daily_return_pct else 0,
                            'volume': int(prices[0].volume) if prices[0].volume else 0,
                            'prices': [{
                                'date': p.trade_date.isoformat(),
                                'close': float(p.close_price),
                                'volume': int(p.volume) if p.volume else 0
                            } for p in prices[:10]]  # 최근 10일만
                        }
                        stock_data.append(stock_info)
                
                self.metrics.execution_time = time.time() - start_time
                self.logger.info(f"주식 데이터 조회 완료: {len(stock_data)}개, {self.metrics.execution_time:.2f}초")
                
                return stock_data
                
        except Exception as e:
            self.metrics.error_count += 1
            self.logger.error(f"캐시된 주식 데이터 조회 실패: {e}")
            return []
    
    async def parallel_api_calls(self, urls: List[str], headers: Dict = None) -> List[Dict]:
        """병렬 API 호출"""
        self.logger.info(f"병렬 API 호출: {len(urls)}개 URL")
        
        try:
            async with AsyncAPIClient(max_concurrent=5, rate_limit=0.2) as client:
                tasks = []
                for url in urls:
                    task = client.request('GET', url, headers=headers or {})
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 성공한 결과만 필터링
                valid_results = []
                for result in results:
                    if isinstance(result, Exception):
                        self.metrics.error_count += 1
                    elif isinstance(result, dict) and result:
                        valid_results.append(result)
                        self.metrics.api_call_count += 1
                
                self.logger.info(f"병렬 API 호출 완료: {len(valid_results)}/{len(urls)}개 성공")
                return valid_results
                
        except Exception as e:
            self.logger.error(f"병렬 API 호출 실패: {e}")
            return []
    
    async def optimized_data_collection(self, stock_codes: List[str], 
                                      region: MarketRegion) -> List[Dict]:
        """최적화된 데이터 수집"""
        self.logger.info(f"최적화된 데이터 수집: {region.value} {len(stock_codes)}개 종목")
        
        try:
            start_time = time.time()
            
            # 1. 캐시된 데이터 우선 조회
            cached_data = await self.get_stock_data_cached(stock_codes, region)
            
            # 2. 캐시 미스 종목들에 대해 배치 처리
            cached_codes = {item['stock_code'] for item in cached_data}
            missing_codes = [code for code in stock_codes if code not in cached_codes]
            
            if missing_codes:
                self.logger.info(f"캐시 미스 종목: {len(missing_codes)}개")
                
                # 배치 처리로 누락된 데이터 수집
                missing_data = await self.batch_processor.process_in_batches(
                    missing_codes,
                    self._collect_single_stock_data,
                    region
                )
                
                # 결과 병합
                cached_data.extend([item for item in missing_data if item])
            
            # 3. 성능 지표 업데이트
            self.metrics.execution_time = time.time() - start_time
            self.metrics.cache_hit_rate = len(cached_codes) / len(stock_codes) if stock_codes else 0
            
            self.logger.info(f"데이터 수집 완료: {len(cached_data)}개, 캐시 히트율: {self.metrics.cache_hit_rate:.1%}")
            
            return cached_data
            
        except Exception as e:
            self.logger.error(f"최적화된 데이터 수집 실패: {e}")
            return []
    
    async def _collect_single_stock_data(self, stock_codes: List[str], 
                                       region: MarketRegion) -> List[Dict]:
        """단일 종목 데이터 수집 (배치 처리용)"""
        results = []
        
        try:
            with get_db_session() as db:
                for code in stock_codes:
                    stock = db.query(StockMaster).filter_by(
                        market_region=region.value,
                        stock_code=code,
                        is_active=True
                    ).first()
                    
                    if not stock:
                        continue
                    
                    # 최근 데이터 조회
                    recent_price = db.query(StockDailyPrice).filter_by(
                        stock_id=stock.stock_id
                    ).order_by(StockDailyPrice.trade_date.desc()).first()
                    
                    if recent_price:
                        stock_info = {
                            'stock_code': stock.stock_code,
                            'stock_name': stock.stock_name,
                            'market_region': stock.market_region,
                            'current_price': float(recent_price.close_price),
                            'price_change_pct': float(recent_price.daily_return_pct) if recent_price.daily_return_pct else 0,
                            'volume': int(recent_price.volume) if recent_price.volume else 0
                        }
                        results.append(stock_info)
            
            return results
            
        except Exception as e:
            self.logger.error(f"단일 종목 데이터 수집 실패: {e}")
            return []
    
    def optimize_memory_usage(self):
        """메모리 사용량 최적화"""
        try:
            # L1 캐시 정리
            self.cache.clear_local_cache()
            
            # 가비지 컬렉션 강제 실행
            collected = gc.collect()
            
            # 메모리 사용량 측정
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.metrics.memory_usage_mb = memory_mb
            
            self.logger.info(f"메모리 최적화 완료: {collected}개 객체 정리, 현재 사용량: {memory_mb:.1f}MB")
            
        except Exception as e:
            self.logger.error(f"메모리 최적화 실패: {e}")
    
    async def batch_update_database(self, updates: List[Dict], 
                                  model_class, batch_size: int = 1000) -> bool:
        """배치 데이터베이스 업데이트"""
        self.logger.info(f"배치 DB 업데이트: {len(updates)}개 레코드")
        
        try:
            with get_db_session() as db:
                success = DatabaseOptimizer.bulk_insert_optimized(
                    db, model_class, updates, batch_size
                )
                
                if success:
                    self.metrics.db_query_count += len(updates) // batch_size + 1
                    self.logger.info("배치 DB 업데이트 성공")
                else:
                    self.metrics.error_count += 1
                    self.logger.error("배치 DB 업데이트 실패")
                
                return success
                
        except Exception as e:
            self.logger.error(f"배치 DB 업데이트 오류: {e}")
            return False
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        return {
            'execution_time': f"{self.metrics.execution_time:.2f}초",
            'cache_hit_rate': f"{self.metrics.cache_hit_rate:.1%}",
            'memory_usage': f"{self.metrics.memory_usage_mb:.1f}MB",
            'db_queries': self.metrics.db_query_count,
            'api_calls': self.metrics.api_call_count,
            'errors': self.metrics.error_count,
            'cache_stats': {
                'hits': self.cache.cache_stats['hits'],
                'misses': self.cache.cache_stats['misses'],
                'hit_rate': f"{self.cache.get_hit_rate():.1%}"
            }
        }
    
    async def run_performance_benchmark(self) -> Dict[str, Any]:
        """성능 벤치마크 실행"""
        self.logger.info("성능 벤치마크 시작")
        
        try:
            benchmark_results = {}
            
            # 1. 캐시 성능 테스트
            start_time = time.time()
            test_data = {'test': 'data', 'timestamp': datetime.now().isoformat()}
            
            for i in range(100):
                await self.cache.set(f"benchmark_key_{i}", test_data)
                retrieved = await self.cache.get(f"benchmark_key_{i}")
            
            cache_time = time.time() - start_time
            benchmark_results['cache_performance'] = f"{cache_time:.3f}초"
            
            # 2. DB 쿼리 성능 테스트
            start_time = time.time()
            
            with get_db_session() as db:
                stocks = db.query(StockMaster).filter_by(is_active=True).limit(100).all()
            
            db_time = time.time() - start_time
            benchmark_results['db_query_performance'] = f"{db_time:.3f}초"
            
            # 3. 메모리 사용량
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            benchmark_results['memory_usage'] = f"{memory_mb:.1f}MB"
            
            # 4. 전체 성능 점수 계산
            performance_score = 100 - min(cache_time * 10 + db_time * 5 + memory_mb * 0.1, 90)
            benchmark_results['performance_score'] = f"{performance_score:.1f}/100"
            
            self.logger.info(f"성능 벤치마크 완료: {performance_score:.1f}점")
            
            return benchmark_results
            
        except Exception as e:
            self.logger.error(f"성능 벤치마크 실패: {e}")
            return {'error': str(e)}


# 글로벌 성능 최적화 인스턴스
performance_optimizer = PerformanceOptimizer()


# 사용 예시
async def main():
    """메인 테스트 함수"""
    print("⚡ 성능 최적화 시스템 테스트")
    print("="*60)
    
    optimizer = PerformanceOptimizer()
    
    try:
        # 1. 성능 벤치마크
        print("\n1️⃣ 성능 벤치마크 실행")
        benchmark = await optimizer.run_performance_benchmark()
        
        for key, value in benchmark.items():
            print(f"   {key}: {value}")
        
        # 2. 최적화된 데이터 수집 테스트
        print("\n2️⃣ 최적화된 데이터 수집 테스트")
        test_codes = ['005930', '000660', '035420', 'AAPL', 'MSFT']
        
        # 한국 종목
        kr_data = await optimizer.optimized_data_collection(
            test_codes[:3], MarketRegion.KR
        )
        print(f"   한국 데이터: {len(kr_data)}개 수집")
        
        # 3. 성능 리포트
        print("\n3️⃣ 성능 리포트")
        report = optimizer.get_performance_report()
        
        for key, value in report.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for sub_key, sub_value in value.items():
                    print(f"     {sub_key}: {sub_value}")
            else:
                print(f"   {key}: {value}")
        
        # 4. 메모리 최적화
        print("\n4️⃣ 메모리 최적화")
        optimizer.optimize_memory_usage()
        
        print("\n🎉 성능 최적화 시스템 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
