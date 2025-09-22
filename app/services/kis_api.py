"""
KIS (Korea Investment & Securities) API client for stock data.
"""
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


class KISAPIClient:
    """KIS Open API client for fetching stock data."""
    
    def __init__(self, app_key: str = None, app_secret: str = None):
        self.app_key = app_key or settings.kis_app_key
        self.app_secret = app_secret or settings.kis_app_secret
        self.base_url = settings.kis_base_url
        self.access_token = None
        self.token_expires_at = None
        
        if not self.app_key or not self.app_secret:
            logger.warning("KIS API credentials not provided")
    
    def get_access_token(self) -> str:
        """
        Get access token from KIS API.
        Spring Boot manages token, but we implement backup logic.
        """
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"Content-Type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            self.access_token = result["access_token"]
            expires_in = result.get("expires_in", 86400)  # Default 24 hours
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5min buffer
            
            logger.info("KIS access token obtained successfully")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get KIS access token: {e}")
            raise
    
    def _make_request(self, method: str, endpoint: str, headers: Dict = None, params: Dict = None) -> Dict:
        """Make authenticated request to KIS API."""
        if not self.access_token:
            self.get_access_token()
        
        url = f"{self.base_url}{endpoint}"
        
        default_headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=default_headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=default_headers, json=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"KIS API request failed: {e}")
            raise
    
    def get_stock_price_daily(self, stock_code: str, start_date: str, end_date: str, 
                             market: str = "J") -> List[Dict]:
        """
        Get daily stock price data.
        
        Args:
            stock_code: Stock code (e.g., "005930" for Samsung)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            market: Market type (J: KOSPI/KOSDAQ, N: NASDAQ, etc.)
        
        Returns:
            List of daily price data
        """
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        
        headers = {"tr_id": "FHKST03010100"}
        params = {
            "fid_cond_mrkt_div_code": market,
            "fid_input_iscd": stock_code,
            "fid_input_date_1": start_date,
            "fid_input_date_2": end_date,
            "fid_period_div_code": "D",  # Daily
            "fid_org_adj_prc": "0"  # Original price
        }
        
        try:
            result = self._make_request("GET", endpoint, headers, params)
            
            if result.get("rt_cd") == "0":  # Success
                return result.get("output2", [])
            else:
                logger.error(f"KIS API error: {result.get('msg1', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get stock price data for {stock_code}: {e}")
            return []
    
    def get_stock_info(self, stock_code: str, market: str = "J") -> Dict:
        """
        Get basic stock information.
        
        Args:
            stock_code: Stock code
            market: Market type
        
        Returns:
            Stock information dict
        """
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
        
        headers = {"tr_id": "FHKST01010100"}
        params = {
            "fid_cond_mrkt_div_code": market,
            "fid_input_iscd": stock_code
        }
        
        try:
            result = self._make_request("GET", endpoint, headers, params)
            
            if result.get("rt_cd") == "0":
                return result.get("output", {})
            else:
                logger.error(f"KIS API error: {result.get('msg1', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get stock info for {stock_code}: {e}")
            return {}
    
    def get_market_cap_ranking(self, market: str = "J", count: int = 100) -> List[Dict]:
        """
        Get market capitalization ranking.
        
        Args:
            market: Market type
            count: Number of stocks to retrieve
        
        Returns:
            List of stock ranking data
        """
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-market-cap"
        
        headers = {"tr_id": "FHKST03030100"}
        params = {
            "fid_cond_mrkt_div_code": market,
            "fid_cond_scr_div_code": "20171",
            "fid_div_cls_code": "0",
            "fid_input_cnt_1": str(count)
        }
        
        try:
            result = self._make_request("GET", endpoint, headers, params)
            
            if result.get("rt_cd") == "0":
                return result.get("output", [])
            else:
                logger.error(f"KIS API error: {result.get('msg1', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get market cap ranking: {e}")
            return []
    
    def get_stock_financials(self, stock_code: str) -> Dict:
        """
        Get stock financial information.
        
        Args:
            stock_code: Stock code
        
        Returns:
            Financial data dict
        """
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        
        headers = {"tr_id": "FHKST01010400"}
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code
        }
        
        try:
            result = self._make_request("GET", endpoint, headers, params)
            
            if result.get("rt_cd") == "0":
                return result.get("output", {})
            else:
                logger.error(f"KIS API error: {result.get('msg1', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get stock financials for {stock_code}: {e}")
            return {}
    
    def bulk_stock_prices(self, stock_codes: List[str], start_date: str, end_date: str,
                         delay: float = 0.1) -> Dict[str, List[Dict]]:
        """
        Get stock prices for multiple stocks with rate limiting.
        
        Args:
            stock_codes: List of stock codes
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            delay: Delay between requests in seconds
        
        Returns:
            Dict mapping stock code to price data
        """
        results = {}
        
        for i, stock_code in enumerate(stock_codes):
            try:
                logger.info(f"Fetching price data for {stock_code} ({i+1}/{len(stock_codes)})")
                
                price_data = self.get_stock_price_daily(stock_code, start_date, end_date)
                results[stock_code] = price_data
                
                # Rate limiting
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to fetch data for {stock_code}: {e}")
                results[stock_code] = []
        
        return results
