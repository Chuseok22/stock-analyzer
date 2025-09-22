"""
US 주식 데이터 수집을 위한 Alpha Vantage API 클라이언트
"""
import logging
import time
from typing import Dict, List, Optional
import requests
import pandas as pd
from datetime import datetime, timedelta

from app.config.settings import settings
from app.database.redis_client import redis_client
from app.utils.api_utils import APIUtils, AlphaVantageAPIUtils
from app.utils.data_utils import DataValidationUtils, DateUtils

logger = logging.getLogger(__name__)

# Redis keys for US market data
US_TOKEN_REDIS_KEY = "us:alpha_vantage_token"
US_RATE_LIMIT_KEY = "us:rate_limit"


class AlphaVantageAPIClient:
    """Alpha Vantage API client for US stock data."""

    def __init__(self):
        """Initialize Alpha Vantage API client."""
        self.api_key = settings.alpha_vantage_api_key
        self.base_url = "https://www.alphavantage.co/query"
        
        # Rate limiting: 5 calls per minute for free tier
        self.rate_limiter = APIUtils.APIRateLimiter(
            calls_per_minute=5,
            redis_key_prefix="alpha_vantage"
        )
        
        if not self.api_key:
            logger.warning("Alpha Vantage API key not provided")

    def _make_request(self, params: Dict) -> Dict:
        """Make rate-limited request to Alpha Vantage API."""
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        params['apikey'] = self.api_key
        
        try:
            with APIUtils.create_session_with_retries() as session:
                response = session.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for Alpha Vantage specific errors
                error_msg = AlphaVantageAPIUtils.extract_error_message(data)
                if error_msg:
                    logger.error(f"Alpha Vantage API error: {error_msg}")
                    return {}
                
                return data
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpha Vantage API request failed: {e}")
            return {}

    def get_daily_prices(self, symbol: str, outputsize: str = "compact") -> List[Dict]:
        """
        Get daily stock prices for US stocks.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL", "MSFT")
            outputsize: "compact" (100 days) or "full" (20+ years)
        
        Returns:
            List of daily price data
        """
        if not DataValidationUtils.is_valid_stock_symbol(symbol):
            logger.error(f"Invalid stock symbol: {symbol}")
            return []
            
        params = {
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': symbol,
            'outputsize': outputsize
        }
        
        try:
            data = self._make_request(params)
            
            if not data or "Time Series (Daily)" not in data:
                logger.error(f"No daily data for {symbol}")
                return []
            
            time_series = data["Time Series (Daily)"]
            metadata = data.get("Meta Data", {})
            
            prices = []
            for date_str, price_data in time_series.items():
                # Validate date format
                if not DataValidationUtils.is_valid_date_format(date_str):
                    logger.warning(f"Invalid date format in response: {date_str}")
                    continue
                    
                try:
                    prices.append({
                        'symbol': symbol,
                        'date': date_str,
                        'open': DataValidationUtils.safe_float(price_data['1. open']),
                        'high': DataValidationUtils.safe_float(price_data['2. high']),
                        'low': DataValidationUtils.safe_float(price_data['3. low']),
                        'close': DataValidationUtils.safe_float(price_data['4. close']),
                        'adjusted_close': DataValidationUtils.safe_float(price_data['5. adjusted close']),
                        'volume': DataValidationUtils.safe_int(price_data['6. volume']),
                        'dividend_amount': DataValidationUtils.safe_float(price_data['7. dividend amount']),
                        'split_coefficient': DataValidationUtils.safe_float(price_data['8. split coefficient'])
                    })
                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parsing price data for {symbol} on {date_str}: {e}")
                    continue
            
            # Sort by date (newest first)
            prices.sort(key=lambda x: x['date'], reverse=True)
            
            logger.info(f"Retrieved {len(prices)} days of data for {symbol}")
            return prices
            
        except Exception as e:
            logger.error(f"Failed to get daily prices for {symbol}: {e}")
            return []

    def get_company_overview(self, symbol: str) -> Dict:
        """Get company fundamental data."""
        if not DataValidationUtils.is_valid_stock_symbol(symbol):
            logger.error(f"Invalid stock symbol: {symbol}")
            return {}
            
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }
        
        try:
            data = self._make_request(params)
            
            if not data or "Symbol" not in data:
                logger.error(f"No company data for {symbol}")
                return {}
            
            return {
                'symbol': data.get('Symbol', ''),
                'name': data.get('Name', ''),
                'description': data.get('Description', ''),
                'exchange': data.get('Exchange', ''),
                'currency': data.get('Currency', 'USD'),
                'country': data.get('Country', 'USA'),
                'sector': data.get('Sector', ''),
                'industry': data.get('Industry', ''),
                'market_cap': DataValidationUtils.safe_float(data.get('MarketCapitalization')),
                'pe_ratio': DataValidationUtils.safe_float(data.get('PERatio')),
                'peg_ratio': DataValidationUtils.safe_float(data.get('PEGRatio')),
                'book_value': DataValidationUtils.safe_float(data.get('BookValue')),
                'dividend_per_share': DataValidationUtils.safe_float(data.get('DividendPerShare')),
                'dividend_yield': DataValidationUtils.safe_float(data.get('DividendYield')),
                'eps': DataValidationUtils.safe_float(data.get('EPS')),
                'revenue_per_share_ttm': DataValidationUtils.safe_float(data.get('RevenuePerShareTTM')),
                'profit_margin': DataValidationUtils.safe_float(data.get('ProfitMargin')),
                'operating_margin_ttm': DataValidationUtils.safe_float(data.get('OperatingMarginTTM')),
                'return_on_assets_ttm': DataValidationUtils.safe_float(data.get('ReturnOnAssetsTTM')),
                'return_on_equity_ttm': DataValidationUtils.safe_float(data.get('ReturnOnEquityTTM')),
                'revenue_ttm': DataValidationUtils.safe_float(data.get('RevenueTTM')),
                'gross_profit_ttm': DataValidationUtils.safe_float(data.get('GrossProfitTTM')),
                'diluted_eps_ttm': DataValidationUtils.safe_float(data.get('DilutedEPSTTM')),
                'quarterly_earnings_growth_yoy': DataValidationUtils.safe_float(data.get('QuarterlyEarningsGrowthYOY')),
                'quarterly_revenue_growth_yoy': DataValidationUtils.safe_float(data.get('QuarterlyRevenueGrowthYOY')),
                'analyst_target_price': DataValidationUtils.safe_float(data.get('AnalystTargetPrice')),
                'trailing_pe': DataValidationUtils.safe_float(data.get('TrailingPE')),
                'forward_pe': DataValidationUtils.safe_float(data.get('ForwardPE')),
                'price_to_sales_ratio_ttm': DataValidationUtils.safe_float(data.get('PriceToSalesRatioTTM')),
                'price_to_book_ratio': DataValidationUtils.safe_float(data.get('PriceToBookRatio')),
                'ev_to_revenue': DataValidationUtils.safe_float(data.get('EVToRevenue')),
                'ev_to_ebitda': DataValidationUtils.safe_float(data.get('EVToEBITDA')),
                'beta': DataValidationUtils.safe_float(data.get('Beta')),
                '52_week_high': DataValidationUtils.safe_float(data.get('52WeekHigh')),
                '52_week_low': DataValidationUtils.safe_float(data.get('52WeekLow')),
                '50_day_ma': DataValidationUtils.safe_float(data.get('50DayMovingAverage')),
                '200_day_ma': DataValidationUtils.safe_float(data.get('200DayMovingAverage')),
                'shares_outstanding': DataValidationUtils.safe_float(data.get('SharesOutstanding')),
                'shares_float': DataValidationUtils.safe_float(data.get('SharesFloat')),
                'shares_short': DataValidationUtils.safe_float(data.get('SharesShort')),
                'shares_short_prior_month': DataValidationUtils.safe_float(data.get('SharesShortPriorMonth')),
                'short_ratio': DataValidationUtils.safe_float(data.get('ShortRatio')),
                'short_percent_outstanding': DataValidationUtils.safe_float(data.get('ShortPercentOutstanding')),
                'short_percent_float': DataValidationUtils.safe_float(data.get('ShortPercentFloat')),
                'percent_insiders': DataValidationUtils.safe_float(data.get('PercentInsiders')),
                'percent_institutions': DataValidationUtils.safe_float(data.get('PercentInstitutions')),
            }
            
        except Exception as e:
            logger.error(f"Failed to get company overview for {symbol}: {e}")
            return {}

    def get_technical_indicators(self, symbol: str, indicator: str, interval: str = "daily", 
                                time_period: int = 14, series_type: str = "close") -> Dict:
        """
        Get technical indicators for US stocks.
        
        Args:
            symbol: Stock symbol
            indicator: Technical indicator (RSI, SMA, EMA, MACD, etc.)
            interval: daily, weekly, monthly
            time_period: Time period for calculation
            series_type: close, open, high, low
        """
        indicator_map = {
            'RSI': 'RSI',
            'SMA': 'SMA',
            'EMA': 'EMA',
            'MACD': 'MACD',
            'BBANDS': 'BBANDS',
            'ADX': 'ADX',
            'CCI': 'CCI',
            'STOCH': 'STOCH'
        }
        
        if indicator not in indicator_map:
            logger.error(f"Unsupported indicator: {indicator}")
            return {}
        
        params = {
            'function': indicator_map[indicator],
            'symbol': symbol,
            'interval': interval,
            'time_period': time_period,
            'series_type': series_type
        }
        
        try:
            data = self._make_request(params)
            
            if not data:
                return {}
            
            # Different indicators have different response structures
            if indicator == 'MACD':
                tech_data = data.get('Technical Analysis: MACD', {})
            elif indicator == 'BBANDS':
                tech_data = data.get('Technical Analysis: BBANDS', {})
            elif indicator == 'STOCH':
                tech_data = data.get('Technical Analysis: STOCH', {})
            else:
                tech_data = data.get(f'Technical Analysis: {indicator}', {})
            
            return tech_data
            
        except Exception as e:
            logger.error(f"Failed to get {indicator} for {symbol}: {e}")
            return {}

    def get_market_indices(self) -> Dict[str, float]:
        """Get major US market indices."""
        indices = {
            'SPY': 'S&P 500',
            'QQQ': 'NASDAQ 100', 
            'DIA': 'Dow Jones',
            'IWM': 'Russell 2000',
            'VIX': 'Volatility Index'
        }
        
        results = {}
        
        for symbol, name in indices.items():
            try:
                prices = self.get_daily_prices(symbol, "compact")
                if prices:
                    latest = prices[0]
                    results[name] = {
                        'symbol': symbol,
                        'price': latest['close'],
                        'date': latest['date']
                    }
            except Exception as e:
                logger.error(f"Failed to get index data for {symbol}: {e}")
                continue
        
        return results

    def bulk_stock_data(self, symbols: List[str], delay: float = 12.0) -> Dict[str, Dict]:
        """
        Get stock data for multiple symbols with rate limiting.
        Free tier allows 5 calls per minute.
        
        Args:
            symbols: List of stock symbols
            delay: Delay between requests in seconds (minimum 12s for free tier)
        """
        if not symbols:
            logger.warning("No symbols provided for bulk data collection")
            return {}
            
        results = {}
        
        for i, symbol in enumerate(symbols):
            if not DataValidationUtils.is_valid_stock_symbol(symbol):
                logger.warning(f"Skipping invalid symbol: {symbol}")
                continue
                
            try:
                logger.info(f"Fetching data for {symbol} ({i + 1}/{len(symbols)})")
                
                # Get price data
                prices = self.get_daily_prices(symbol)
                
                # Get company overview
                overview = self.get_company_overview(symbol)
                
                results[symbol] = {
                    'prices': prices,
                    'overview': overview,
                    'timestamp': DateUtils.get_current_datetime().isoformat()
                }
                
                # Rate limiting - use the built-in rate limiter
                if i < len(symbols) - 1:  # Don't wait after the last request
                    self.rate_limiter.wait_if_needed()
                
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                results[symbol] = {
                    'prices': [],
                    'overview': {},
                    'error': str(e),
                    'timestamp': DateUtils.get_current_datetime().isoformat()
                }
        
        return results

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Safely convert string to float."""
        # Deprecated: Use DataValidationUtils.safe_float instead
        return DataValidationUtils.safe_float(value)

    def get_sp500_symbols(self) -> List[str]:
        """Get S&P 500 stock symbols (top 100 for now due to API limits)."""
        # Top 100 S&P 500 stocks by market cap
        return [
            # Technology
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'CRM',
            'ADBE', 'NFLX', 'AMD', 'INTC', 'CSCO', 'PYPL', 'QCOM', 'IBM', 'UBER', 'SNOW',
            
            # Healthcare
            'UNH', 'JNJ', 'PFE', 'ABT', 'TMO', 'ABBV', 'MRK', 'DHR', 'BMY', 'AMGN',
            'GILD', 'CVS', 'MDT', 'ISRG', 'VRTX', 'ZTS', 'SYK', 'BDX', 'REGN', 'CI',
            
            # Financial
            'BRK.B', 'JPM', 'BAC', 'WFC', 'GS', 'MS', 'AXP', 'BLK', 'SPGI', 'CB',
            'MMC', 'ICE', 'PGR', 'TFC', 'USB', 'PNC', 'COF', 'AON', 'CME', 'MCO',
            
            # Consumer
            'AMZN', 'TSLA', 'HD', 'WMT', 'PG', 'KO', 'PEP', 'COST', 'MCD', 'NKE',
            'SBUX', 'TGT', 'LOW', 'TJX', 'EL', 'DIS', 'BKNG', 'ABNB', 'GM', 'F',
            
            # Industrial
            'BA', 'CAT', 'GE', 'RTX', 'HON', 'UPS', 'LMT', 'DE', 'MMM', 'UNP',
            'NSC', 'CSX', 'NOC', 'FDX', 'WM', 'ITW', 'EMR', 'ETN', 'CARR', 'OTIS',
            
            # Energy & Materials
            'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'KMI', 'OXY', 'MPC', 'VLO',
            'LIN', 'APD', 'ECL', 'DD', 'PPG', 'SHW', 'FCX', 'NEM', 'FMC', 'CE'
        ]
