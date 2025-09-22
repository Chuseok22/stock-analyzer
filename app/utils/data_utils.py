"""
Data processing utilities for stock analysis.
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DateUtils:
    """Utility functions for date operations."""
    
    @staticmethod
    def get_previous_trading_day(target_date: date) -> date:
        """
        Get the previous trading day (excluding weekends).
        
        Args:
            target_date: Target date
            
        Returns:
            Previous trading day
        """
        previous_date = target_date - timedelta(days=1)
        
        # If previous day is weekend, go back to Friday
        while previous_date.weekday() > 4:  # Monday=0, Sunday=6
            previous_date -= timedelta(days=1)
            
        return previous_date
    
    @staticmethod
    def get_next_trading_day(target_date: date) -> date:
        """
        Get the next trading day (excluding weekends).
        
        Args:
            target_date: Target date
            
        Returns:
            Next trading day
        """
        next_date = target_date + timedelta(days=1)
        
        # If next day is weekend, go to Monday
        while next_date.weekday() > 4:  # Monday=0, Sunday=6
            next_date += timedelta(days=1)
            
        return next_date
    
    @staticmethod
    def get_trading_days_between(start_date: date, end_date: date) -> List[date]:
        """
        Get list of trading days between two dates (excluding weekends).
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of trading days
        """
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                trading_days.append(current_date)
            current_date += timedelta(days=1)
            
        return trading_days
    
    @staticmethod
    def parse_date_string(date_str: str, format_str: str = "%Y%m%d") -> Optional[date]:
        """
        Parse date string with error handling.
        
        Args:
            date_str: Date string
            format_str: Date format
            
        Returns:
            Parsed date or None if parsing fails
        """
        try:
            return datetime.strptime(date_str, format_str).date()
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse date string '{date_str}': {e}")
            return None
    
    @staticmethod
    def format_date_for_api(target_date: date, format_str: str = "%Y%m%d") -> str:
        """
        Format date for API calls.
        
        Args:
            target_date: Date to format
            format_str: Format string
            
        Returns:
            Formatted date string
        """
        return target_date.strftime(format_str)


class DataValidationUtils:
    """Utility functions for data validation."""
    
    @staticmethod
    def safe_float(value: Any) -> Optional[float]:
        """
        Safely convert value to float, handling NaN and None.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None
        """
        if pd.isna(value) or value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    @staticmethod
    def safe_int(value: Any) -> Optional[int]:
        """
        Safely convert value to int, handling NaN and None.
        
        Args:
            value: Value to convert
            
        Returns:
            Int value or None
        """
        if pd.isna(value) or value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    
    @staticmethod
    def validate_stock_code(stock_code: str) -> bool:
        """
        Validate stock code format.
        
        Args:
            stock_code: Stock code to validate
            
        Returns:
            True if valid
        """
        if not stock_code or not isinstance(stock_code, str):
            return False
        
        # Korean stock codes are typically 6 digits
        if len(stock_code) == 6 and stock_code.isdigit():
            return True
        
        # US stock codes are typically alphabetic
        if stock_code.isalpha() and 1 <= len(stock_code) <= 5:
            return True
        
        return False
    
    @staticmethod
    def validate_price_data(price_data: Dict) -> bool:
        """
        Validate price data dictionary.
        
        Args:
            price_data: Price data to validate
            
        Returns:
            True if valid
        """
        required_fields = ['open_price', 'high_price', 'low_price', 'close_price', 'volume']
        
        for field in required_fields:
            if field not in price_data:
                return False
            
            value = price_data[field]
            if value is None or (isinstance(value, str) and not value.strip()):
                return False
        
        # Validate price relationships
        try:
            open_price = float(price_data['open_price'])
            high_price = float(price_data['high_price'])
            low_price = float(price_data['low_price'])
            close_price = float(price_data['close_price'])
            volume = int(price_data['volume'])
            
            # High should be highest, low should be lowest
            if high_price < max(open_price, close_price, low_price):
                return False
            
            if low_price > min(open_price, close_price, high_price):
                return False
            
            # Volume should be non-negative
            if volume < 0:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False


class DataFrameUtils:
    """Utility functions for DataFrame operations."""
    
    @staticmethod
    def safe_merge_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, 
                            on: List[str], how: str = 'inner') -> pd.DataFrame:
        """
        Safely merge DataFrames with error handling.
        
        Args:
            df1: First DataFrame
            df2: Second DataFrame
            on: Columns to merge on
            how: Merge type
            
        Returns:
            Merged DataFrame
        """
        try:
            # Check if merge columns exist
            for col in on:
                if col not in df1.columns:
                    logger.warning(f"Column '{col}' not found in first DataFrame")
                    return pd.DataFrame()
                if col not in df2.columns:
                    logger.warning(f"Column '{col}' not found in second DataFrame")
                    return pd.DataFrame()
            
            return pd.merge(df1, df2, on=on, how=how)
            
        except Exception as e:
            logger.error(f"Failed to merge DataFrames: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add common technical analysis features to DataFrame.
        
        Args:
            df: DataFrame with price data
            
        Returns:
            DataFrame with additional features
        """
        result = df.copy()
        
        try:
            # Price relative to moving averages
            if 'close_price' in df.columns and 'sma_20' in df.columns:
                result['price_to_sma_20'] = df['close_price'] / df['sma_20'] - 1
            
            # RSI levels categorization
            if 'rsi_14' in df.columns:
                result['rsi_level'] = pd.cut(df['rsi_14'],
                                           bins=[0, 30, 70, 100],
                                           labels=[0, 1, 2]).astype(float)
            
            # MACD histogram
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                result['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Band position
            if all(col in df.columns for col in ['close_price', 'bb_upper', 'bb_lower']):
                bb_range = df['bb_upper'] - df['bb_lower']
                bb_range = bb_range.replace(0, 1)  # Avoid division by zero
                result['bb_position'] = (df['close_price'] - df['bb_lower']) / bb_range
            
            # Volume surge indicator
            if 'volume_ratio' in df.columns:
                result['volume_surge'] = (df['volume_ratio'] > 1.5).astype(int)
            
            logger.debug(f"Added technical features to DataFrame with {len(result)} rows")
            
        except Exception as e:
            logger.error(f"Failed to add technical features: {e}")
            
        return result
    
    @staticmethod
    def clean_dataframe(df: pd.DataFrame, 
                       numeric_columns: List[str] = None,
                       drop_na_threshold: float = 0.5) -> pd.DataFrame:
        """
        Clean DataFrame by handling missing values and invalid data.
        
        Args:
            df: DataFrame to clean
            numeric_columns: List of columns that should be numeric
            drop_na_threshold: Drop rows with more than this proportion of NaN values
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        result = df.copy()
        
        try:
            # Convert specified columns to numeric
            if numeric_columns:
                for col in numeric_columns:
                    if col in result.columns:
                        result[col] = pd.to_numeric(result[col], errors='coerce')
            
            # Drop rows with too many NaN values
            na_threshold = int(len(result.columns) * drop_na_threshold)
            result = result.dropna(thresh=na_threshold)
            
            # Replace infinite values with NaN
            result = result.replace([float('inf'), float('-inf')], pd.NA)
            
            logger.debug(f"Cleaned DataFrame: {len(df)} -> {len(result)} rows")
            
        except Exception as e:
            logger.error(f"Failed to clean DataFrame: {e}")
            
        return result


class TechnicalIndicatorUtils:
    """Utility functions for technical indicator calculations."""
    
    @staticmethod
    def calculate_sma(prices: pd.Series, window: int) -> pd.Series:
        """
        Calculate Simple Moving Average.
        
        Args:
            prices: Price series
            window: Window size
            
        Returns:
            SMA series
        """
        try:
            return prices.rolling(window=window, min_periods=1).mean()
        except Exception as e:
            logger.error(f"Failed to calculate SMA: {e}")
            return pd.Series(index=prices.index, dtype=float)
    
    @staticmethod
    def calculate_ema(prices: pd.Series, span: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.
        
        Args:
            prices: Price series
            span: Span for EMA
            
        Returns:
            EMA series
        """
        try:
            return prices.ewm(span=span, min_periods=1).mean()
        except Exception as e:
            logger.error(f"Failed to calculate EMA: {e}")
            return pd.Series(index=prices.index, dtype=float)
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index).
        
        Args:
            prices: Price series
            period: RSI period
            
        Returns:
            RSI series
        """
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
            
            # Avoid division by zero
            loss = loss.replace(0, 0.000001)
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
            
        except Exception as e:
            logger.error(f"Failed to calculate RSI: {e}")
            return pd.Series(index=prices.index, dtype=float)
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, window: int = 20, 
                                num_std: float = 2) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Args:
            prices: Price series
            window: Window size
            num_std: Number of standard deviations
            
        Returns:
            Dictionary with upper, middle, and lower bands
        """
        try:
            middle = prices.rolling(window=window, min_periods=1).mean()
            std_dev = prices.rolling(window=window, min_periods=1).std()
            
            upper = middle + (std_dev * num_std)
            lower = middle - (std_dev * num_std)
            
            return {
                'upper': upper,
                'middle': middle,
                'lower': lower
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate Bollinger Bands: {e}")
            return {
                'upper': pd.Series(index=prices.index, dtype=float),
                'middle': pd.Series(index=prices.index, dtype=float),
                'lower': pd.Series(index=prices.index, dtype=float)
            }
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, 
                      signal: int = 9) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: Price series
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line EMA period
            
        Returns:
            Dictionary with MACD line and signal line
        """
        try:
            ema_fast = prices.ewm(span=fast, min_periods=1).mean()
            ema_slow = prices.ewm(span=slow, min_periods=1).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, min_periods=1).mean()
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': macd_line - signal_line
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate MACD: {e}")
            return {
                'macd': pd.Series(index=prices.index, dtype=float),
                'signal': pd.Series(index=prices.index, dtype=float),
                'histogram': pd.Series(index=prices.index, dtype=float)
            }