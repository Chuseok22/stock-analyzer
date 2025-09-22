"""
API utilities for stock analysis application.
"""
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class APIUtils:
    """Utility functions for API operations."""
    
    @staticmethod
    def create_session_with_retries(retries: int = 3, 
                                  backoff_factor: float = 0.3,
                                  status_forcelist: List[int] = None) -> requests.Session:
        """
        Create a requests session with retry strategy.
        
        Args:
            retries: Number of retries
            backoff_factor: Backoff factor for retries
            status_forcelist: HTTP status codes to retry on
            
        Returns:
            Configured requests session
        """
        if status_forcelist is None:
            status_forcelist = [500, 502, 503, 504]
        
        session = requests.Session()
        
        retry_strategy = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    @staticmethod
    def rate_limited_request(delay: float = 0.1):
        """
        Decorator for rate-limited API requests.
        
        Args:
            delay: Delay between requests in seconds
        """
        def decorator(func: Callable):
            last_called = [0.0]
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                elapsed = time.time() - last_called[0]
                left_to_wait = delay - elapsed
                if left_to_wait > 0:
                    time.sleep(left_to_wait)
                
                ret = func(*args, **kwargs)
                last_called[0] = time.time()
                return ret
            
            return wrapper
        return decorator
    
    @staticmethod
    def validate_api_response(response: Dict, required_fields: List[str] = None) -> bool:
        """
        Validate API response structure.
        
        Args:
            response: API response dictionary
            required_fields: List of required fields
            
        Returns:
            True if response is valid
        """
        if not isinstance(response, dict):
            logger.warning("API response is not a dictionary")
            return False
        
        if required_fields:
            for field in required_fields:
                if field not in response:
                    logger.warning(f"Required field '{field}' missing from API response")
                    return False
        
        return True
    
    @staticmethod
    def extract_error_message(response: Dict) -> str:
        """
        Extract error message from API response.
        
        Args:
            response: API response dictionary
            
        Returns:
            Error message string
        """
        # Common error message fields in various APIs
        error_fields = ['error', 'message', 'msg', 'error_message', 'msg1', 'error_desc']
        
        for field in error_fields:
            if field in response and response[field]:
                return str(response[field])
        
        return "Unknown API error"
    
    @staticmethod
    def safe_api_call(func: Callable, *args, max_retries: int = 3, 
                     retry_delay: float = 1.0, **kwargs) -> Optional[Any]:
        """
        Safely execute API call with retry logic.
        
        Args:
            func: Function to call
            args: Function arguments
            max_retries: Maximum number of retries
            retry_delay: Delay between retries
            kwargs: Function keyword arguments
            
        Returns:
            Function result or None if all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"API call attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in API call: {e}")
                break
        
        logger.error(f"API call failed after {max_retries + 1} attempts. Last error: {last_exception}")
        return None


class KISAPIUtils:
    """Utility functions specific to KIS API."""
    
    @staticmethod
    def parse_kis_price_data(raw_data: Dict) -> Optional[Dict]:
        """
        Parse KIS API price data response.
        
        Args:
            raw_data: Raw KIS API response
            
        Returns:
            Parsed price data or None
        """
        try:
            if not APIUtils.validate_api_response(raw_data, ['stck_bsop_date']):
                return None
            
            return {
                'trade_date': raw_data.get('stck_bsop_date', ''),
                'open_price': float(raw_data.get('stck_oprc', 0)),
                'high_price': float(raw_data.get('stck_hgpr', 0)),
                'low_price': float(raw_data.get('stck_lwpr', 0)),
                'close_price': float(raw_data.get('stck_clpr', 0)),
                'volume': int(raw_data.get('acml_vol', 0)),
                'trading_value': float(raw_data.get('acml_tr_pbmn', 0))
            }
            
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Failed to parse KIS price data: {e}")
            return None
    
    @staticmethod
    def parse_kis_stock_info(raw_data: Dict) -> Optional[Dict]:
        """
        Parse KIS API stock info response.
        
        Args:
            raw_data: Raw KIS API response
            
        Returns:
            Parsed stock info or None
        """
        try:
            return {
                'stock_code': raw_data.get('mksc_shrn_iscd', ''),
                'stock_name': raw_data.get('hts_kor_isnm', ''),
                'market_cap': float(raw_data.get('lstg_stqt', 0)),
                'current_price': float(raw_data.get('stck_prpr', 0)),
                'change_rate': float(raw_data.get('prdy_ctrt', 0)),
                'volume': int(raw_data.get('acml_vol', 0))
            }
            
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Failed to parse KIS stock info: {e}")
            return None
    
    @staticmethod
    def is_kis_response_successful(response: Dict) -> bool:
        """
        Check if KIS API response indicates success.
        
        Args:
            response: KIS API response
            
        Returns:
            True if successful
        """
        return response.get('rt_cd') == '0' or response.get('rt_cd') == 0
    
    @staticmethod
    def extract_kis_error_message(response: Dict) -> str:
        """
        Extract error message from KIS API response.
        
        Args:
            response: KIS API response
            
        Returns:
            Error message
        """
        error_msg = response.get('msg1', response.get('msg', 'Unknown KIS API error'))
        error_code = response.get('rt_cd', 'Unknown')
        
        return f"KIS API Error [{error_code}]: {error_msg}"


class AlphaVantageAPIUtils:
    """Utility functions specific to Alpha Vantage API."""
    
    @staticmethod
    def parse_alpha_vantage_daily_data(raw_data: Dict) -> Optional[List[Dict]]:
        """
        Parse Alpha Vantage daily price data.
        
        Args:
            raw_data: Raw Alpha Vantage API response
            
        Returns:
            List of parsed daily data or None
        """
        try:
            time_series = raw_data.get('Time Series (Daily)', {})
            
            if not time_series:
                logger.warning("No time series data found in Alpha Vantage response")
                return None
            
            parsed_data = []
            for date_str, data in time_series.items():
                try:
                    parsed_entry = {
                        'trade_date': date_str,
                        'open_price': float(data.get('1. open', 0)),
                        'high_price': float(data.get('2. high', 0)),
                        'low_price': float(data.get('3. low', 0)),
                        'close_price': float(data.get('4. close', 0)),
                        'volume': int(data.get('5. volume', 0))
                    }
                    parsed_data.append(parsed_entry)
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse Alpha Vantage data for {date_str}: {e}")
                    continue
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Failed to parse Alpha Vantage daily data: {e}")
            return None
    
    @staticmethod
    def is_alpha_vantage_rate_limited(response: Dict) -> bool:
        """
        Check if Alpha Vantage response indicates rate limiting.
        
        Args:
            response: Alpha Vantage API response
            
        Returns:
            True if rate limited
        """
        error_message = response.get('Error Message', '')
        note = response.get('Note', '')
        
        rate_limit_indicators = [
            'API call frequency',
            'rate limit',
            'premium',
            'calls per minute'
        ]
        
        full_response = f"{error_message} {note}".lower()
        
        return any(indicator in full_response for indicator in rate_limit_indicators)
    
    @staticmethod
    def extract_alpha_vantage_error(response: Dict) -> str:
        """
        Extract error message from Alpha Vantage response.
        
        Args:
            response: Alpha Vantage API response
            
        Returns:
            Error message
        """
        if 'Error Message' in response:
            return response['Error Message']
        
        if 'Note' in response:
            return response['Note']
        
        return "Unknown Alpha Vantage API error"


class APIResponseValidator:
    """Validator for API responses."""
    
    @staticmethod
    def validate_price_data_response(response: Dict, 
                                   api_type: str = 'kis') -> Dict[str, Any]:
        """
        Validate price data API response.
        
        Args:
            response: API response
            api_type: Type of API ('kis' or 'alpha_vantage')
            
        Returns:
            Validation result dictionary
        """
        validation_result = {
            'is_valid': False,
            'error_message': None,
            'parsed_data': None,
            'record_count': 0
        }
        
        try:
            if api_type.lower() == 'kis':
                if not KISAPIUtils.is_kis_response_successful(response):
                    validation_result['error_message'] = KISAPIUtils.extract_kis_error_message(response)
                    return validation_result
                
                # Parse KIS data
                output_data = response.get('output2', response.get('output', []))
                if not output_data:
                    validation_result['error_message'] = "No data in KIS response"
                    return validation_result
                
                parsed_records = []
                for record in output_data:
                    parsed = KISAPIUtils.parse_kis_price_data(record)
                    if parsed:
                        parsed_records.append(parsed)
                
                validation_result['parsed_data'] = parsed_records
                validation_result['record_count'] = len(parsed_records)
                validation_result['is_valid'] = len(parsed_records) > 0
                
            elif api_type.lower() == 'alpha_vantage':
                if AlphaVantageAPIUtils.is_alpha_vantage_rate_limited(response):
                    validation_result['error_message'] = "Alpha Vantage API rate limited"
                    return validation_result
                
                parsed_data = AlphaVantageAPIUtils.parse_alpha_vantage_daily_data(response)
                if not parsed_data:
                    validation_result['error_message'] = AlphaVantageAPIUtils.extract_alpha_vantage_error(response)
                    return validation_result
                
                validation_result['parsed_data'] = parsed_data
                validation_result['record_count'] = len(parsed_data)
                validation_result['is_valid'] = True
            
            else:
                validation_result['error_message'] = f"Unsupported API type: {api_type}"
            
        except Exception as e:
            validation_result['error_message'] = f"Validation error: {e}"
            logger.error(f"Failed to validate API response: {e}")
        
        return validation_result


class APIRateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum calls per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_called = 0.0
    
    def wait_if_needed(self) -> None:
        """Wait if needed to respect rate limit."""
        elapsed = time.time() - self.last_called
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_called = time.time()
    
    def __call__(self, func: Callable):
        """Use as decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper