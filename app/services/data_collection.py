"""
Data collection and preprocessing service for stock analysis.
"""
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional

import pandas as pd
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database.connection import get_db_session
from app.models.entities import Stock, StockPrice, StockIndicator, Universe, UniverseItem
from app.services.kis_api import KISAPIClient
from app.utils.data_utils import DateUtils, DataValidationUtils, TechnicalIndicatorUtils
from app.utils.database_utils import DatabaseUtils
from app.utils.api_utils import APIResponseValidator

logger = logging.getLogger(__name__)


class DataCollectionService:
  """Service for collecting and preprocessing stock data."""

  def __init__(self):
    self.kis_client = KISAPIClient()

  def collect_stock_prices(self, stock_codes: List[str], days: int = 252) -> bool:
    """
    Collect stock price data for given stocks.

    Args:
        stock_codes: List of stock codes to collect
        days: Number of days to collect (default 1 year)

    Returns:
        Success status
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    start_date_str = DateUtils.format_date_for_api(start_date)
    end_date_str = DateUtils.format_date_for_api(end_date)

    logger.info(f"Collecting stock prices from {start_date_str} to {end_date_str}")

    try:
      # Validate stock codes
      valid_codes = [code for code in stock_codes if DataValidationUtils.validate_stock_code(code)]
      if not valid_codes:
        logger.error("No valid stock codes provided")
        return False

      # Get stock price data from KIS API
      price_data = self.kis_client.bulk_stock_prices(
          valid_codes, start_date_str, end_date_str
      )

      # Save to database using DatabaseUtils
      success_count = 0
      with DatabaseUtils.safe_db_session() as db:
        for stock_code, daily_data in price_data.items():
          stock = DatabaseUtils.get_stock_by_code(db, stock_code)
          if not stock:
            logger.warning(f"Stock not found: {stock_code}")
            continue

          # Validate and process price data
          validated_data = []
          for raw_record in daily_data:
            if self._validate_kis_price_record(raw_record):
              validated_data.append(raw_record)

          if validated_data:
            processed = DatabaseUtils.bulk_upsert_price_data(db, stock.id, validated_data)
            success_count += processed

        logger.info(f"Successfully collected price data: {success_count} records for {len(price_data)} stocks")
        return success_count > 0

    except Exception as e:
      logger.error(f"Failed to collect stock prices: {e}")
      return False

  def _validate_kis_price_record(self, record: Dict) -> bool:
    """Validate KIS price record."""
    try:
      # Check required fields
      required_fields = ["stck_bsop_date", "stck_oprc", "stck_hgpr", "stck_lwpr", "stck_clpr", "acml_vol"]
      for field in required_fields:
        if field not in record or not record[field]:
          return False

      # Validate date format
      date_str = record["stck_bsop_date"]
      if not DateUtils.parse_date_string(date_str):
        return False

      # Validate price values
      price_data = {
        'open_price': record["stck_oprc"],
        'high_price': record["stck_hgpr"],
        'low_price': record["stck_lwpr"],
        'close_price': record["stck_clpr"],
        'volume': record["acml_vol"]
      }

      return DataValidationUtils.validate_price_data(price_data)

    except Exception as e:
      logger.warning(f"Price record validation failed: {e}")
      return False

  def _get_stock_by_code(self, db: Session, stock_code: str) -> Optional[Stock]:
    """Get stock entity by code."""
    return db.query(Stock).filter(
        and_(Stock.code == stock_code, Stock.active == True)
    ).first()

  def _save_price_data(self, db: Session, stock_id: int, daily_data: List[Dict]) -> None:
    """Save daily price data to database."""
    for data in daily_data:
      try:
        # Parse KIS API response format
        trade_date = datetime.strptime(data["stck_bsop_date"], "%Y%m%d").date()

        # Check if data already exists
        existing = db.query(StockPrice).filter(
            and_(
                StockPrice.stock_id == stock_id,
                StockPrice.trade_date == trade_date
            )
        ).first()

        if existing:
          # Update existing record
          existing.open_price = float(data["stck_oprc"])
          existing.high_price = float(data["stck_hgpr"])
          existing.low_price = float(data["stck_lwpr"])
          existing.close_price = float(data["stck_clpr"])
          existing.volume = int(data["acml_vol"])
        else:
          # Create new record
          price_record = StockPrice(
              stock_id=stock_id,
              trade_date=trade_date,
              open_price=float(data["stck_oprc"]),
              high_price=float(data["stck_hgpr"]),
              low_price=float(data["stck_lwpr"]),
              close_price=float(data["stck_clpr"]),
              volume=int(data["acml_vol"])
          )
          db.add(price_record)

      except (KeyError, ValueError, TypeError) as e:
        logger.warning(f"Failed to parse price data: {e}")
        continue

  def calculate_technical_indicators(self, stock_id: int = None, days: int = 100) -> bool:
    """
    Calculate technical indicators for stocks using utility functions.

    Args:
        stock_id: Specific stock ID (None for all active stocks)
        days: Number of recent days to calculate

    Returns:
        Success status
    """
    try:
      with DatabaseUtils.safe_db_session() as db:
        if stock_id:
          stock_ids = [stock_id]
        else:
          # Get all active stocks
          stocks = db.query(Stock).filter(Stock.active == True).all()
          stock_ids = [stock.id for stock in stocks]

        success_count = 0
        for sid in stock_ids:
          if self._calculate_stock_indicators_optimized(db, sid, days):
            success_count += 1

        logger.info(f"Calculated indicators for {success_count}/{len(stock_ids)} stocks")
        return success_count > 0

    except Exception as e:
      logger.error(f"Failed to calculate technical indicators: {e}")
      return False

  def _calculate_stock_indicators_optimized(self, db: Session, stock_id: int, days: int) -> bool:
    """Calculate technical indicators for a single stock using utility functions."""
    try:
      # Get recent price data
      prices_query = db.query(StockPrice).filter(
          StockPrice.stock_id == stock_id
      ).order_by(StockPrice.trade_date.desc()).limit(days * 2)  # Extra data for indicators

      prices = prices_query.all()
      if len(prices) < 20:  # Need minimum data for indicators
        logger.warning(f"Insufficient price data for stock {stock_id}")
        return False

      # Convert to DataFrame for easier calculation
      df = pd.DataFrame([{
        'date': p.trade_date,
        'open': p.open_price,
        'high': p.high_price,
        'low': p.low_price,
        'close': p.close_price,
        'volume': p.volume
      } for p in reversed(prices)])

      df = df.sort_values('date')

      # Calculate indicators using utility functions
      indicators_df = self._compute_technical_indicators_optimized(df)

      # Prepare indicator data for bulk upsert
      indicator_data_list = []
      for _, row in indicators_df.iterrows():
        if pd.isna(row['date']):
          continue

        indicator_data = {
          'trade_date': row['date'],
          'sma_5': row.get('sma_5'),
          'sma_10': row.get('sma_10'),
          'sma_20': row.get('sma_20'),
          'sma_60': row.get('sma_60'),
          'ema_12': row.get('ema_12'),
          'ema_26': row.get('ema_26'),
          'rsi_14': row.get('rsi_14'),
          'macd': row.get('macd'),
          'macd_signal': row.get('macd_signal'),
          'bb_upper': row.get('bb_upper'),
          'bb_middle': row.get('bb_middle'),
          'bb_lower': row.get('bb_lower'),
          'volume_sma_20': row.get('volume_sma_20'),
          'volume_ratio': row.get('volume_ratio'),
          'daily_return': row.get('daily_return'),
          'volatility_20': row.get('volatility_20')
        }
        indicator_data_list.append(indicator_data)

      # Bulk upsert using DatabaseUtils
      processed = DatabaseUtils.bulk_upsert_indicator_data(db, stock_id, indicator_data_list)
      logger.debug(f"Processed {processed} indicator records for stock {stock_id}")

      return processed > 0

    except Exception as e:
      logger.error(f"Failed to calculate indicators for stock {stock_id}: {e}")
      return False

  def _compute_technical_indicators_optimized(self, df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical indicators using utility functions."""
    result = df.copy()

    try:
      # Simple Moving Averages using utility functions
      result['sma_5'] = TechnicalIndicatorUtils.calculate_sma(df['close'], 5)
      result['sma_10'] = TechnicalIndicatorUtils.calculate_sma(df['close'], 10)
      result['sma_20'] = TechnicalIndicatorUtils.calculate_sma(df['close'], 20)
      result['sma_60'] = TechnicalIndicatorUtils.calculate_sma(df['close'], 60)

      # Exponential Moving Averages
      result['ema_12'] = TechnicalIndicatorUtils.calculate_ema(df['close'], 12)
      result['ema_26'] = TechnicalIndicatorUtils.calculate_ema(df['close'], 26)

      # RSI
      result['rsi_14'] = TechnicalIndicatorUtils.calculate_rsi(df['close'], 14)

      # MACD
      macd_data = TechnicalIndicatorUtils.calculate_macd(df['close'])
      result['macd'] = macd_data['macd']
      result['macd_signal'] = macd_data['signal']

      # Bollinger Bands
      bb_data = TechnicalIndicatorUtils.calculate_bollinger_bands(df['close'])
      result['bb_upper'] = bb_data['upper']
      result['bb_middle'] = bb_data['middle']
      result['bb_lower'] = bb_data['lower']

      # Volume indicators
      result['volume_sma_20'] = TechnicalIndicatorUtils.calculate_sma(df['volume'], 20)
      result['volume_ratio'] = df['volume'] / result['volume_sma_20']

      # Price patterns
      result['daily_return'] = df['close'].pct_change()
      result['volatility_20'] = result['daily_return'].rolling(window=20).std()

      return result

    except Exception as e:
      logger.error(f"Failed to compute technical indicators: {e}")
      return df

  def get_training_data(self, universe_id: int, lookback_days: int = 252) -> pd.DataFrame:
    """
    Get training data for machine learning model with improved error handling.

    Args:
        universe_id: Universe ID to get stocks from
        lookback_days: Number of days to look back

    Returns:
        Training dataset as DataFrame
    """
    try:
      with DatabaseUtils.safe_db_session() as db:
        # Get stocks in universe using DatabaseUtils
        stock_ids = DatabaseUtils.get_stock_ids_in_universe(db, universe_id)

        if not stock_ids:
          logger.warning(f"No stocks found in universe {universe_id}")
          return pd.DataFrame()

        # Get cutoff date using DateUtils
        cutoff_date = datetime.now().date() - timedelta(days=lookback_days)

        # Query training data with improved joins
        query = db.query(
            StockIndicator.stock_id,
            StockIndicator.trade_date,
            Stock.code.label('stock_code'),
            StockIndicator.sma_5,
            StockIndicator.sma_10,
            StockIndicator.sma_20,
            StockIndicator.sma_60,
            StockIndicator.ema_12,
            StockIndicator.ema_26,
            StockIndicator.rsi_14,
            StockIndicator.macd,
            StockIndicator.macd_signal,
            StockIndicator.bb_upper,
            StockIndicator.bb_middle,
            StockIndicator.bb_lower,
            StockIndicator.volume_sma_20,
            StockIndicator.volume_ratio,
            StockIndicator.daily_return,
            StockIndicator.volatility_20,
            StockPrice.close_price
        ).join(
            Stock, StockIndicator.stock_id == Stock.id
        ).join(
            StockPrice, and_(
                StockIndicator.stock_id == StockPrice.stock_id,
                StockIndicator.trade_date == StockPrice.trade_date
            )
        ).filter(
            and_(
                StockIndicator.stock_id.in_(stock_ids),
                StockIndicator.trade_date >= cutoff_date
            )
        ).order_by(
            StockIndicator.stock_id,
            StockIndicator.trade_date
        )

        # Convert to DataFrame
        df = pd.read_sql(query.statement, db.bind)

        if df.empty:
          logger.warning("No training data found")
          return df

        # Calculate target variable (next day return)
        df['next_day_return'] = df.groupby('stock_id')['daily_return'].shift(-1)
        df['target'] = (df['next_day_return'] > 0).astype(int)  # Binary classification

        # Clean dataframe using utility functions
        numeric_columns = [
          'sma_5', 'sma_10', 'sma_20', 'sma_60', 'ema_12', 'ema_26', 'rsi_14',
          'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower',
          'volume_sma_20', 'volume_ratio', 'daily_return', 'volatility_20',
          'close_price', 'next_day_return'
        ]

        from app.utils.data_utils import DataFrameUtils
        df = DataFrameUtils.clean_dataframe(df, numeric_columns=numeric_columns)

        # Remove rows with missing target
        df = df.dropna(subset=['target'])

        logger.info(f"Generated training data: {len(df)} samples from {len(stock_ids)} stocks")
        return df

    except Exception as e:
      logger.error(f"Failed to get training data: {e}")
      return pd.DataFrame()

  def update_universe_stocks(self, region: str = "KR", top_n: int = 200) -> Optional[int]:
    """
    Update universe with top market cap stocks using improved validation.

    Args:
        region: Market region (KR/US)
        top_n: Number of top stocks to include

    Returns:
        Universe ID if successful
    """
    try:
      # Get top stocks by market cap from KIS API
      top_stocks = self.kis_client.get_market_cap_ranking(count=top_n)

      if not top_stocks:
        logger.error("Failed to get market cap ranking")
        return None

      with DatabaseUtils.safe_db_session() as db:
        # Create new universe
        universe = Universe(
            region=region,
            size=len(top_stocks),
            snapshot_date=date.today(),
            rule_version=f"market_cap_top_{top_n}_{datetime.now().strftime('%Y%m%d')}"
        )
        db.add(universe)
        db.flush()  # Get universe ID

        # Add stocks to universe with validation
        added_count = 0
        for stock_data in top_stocks:
          stock_code = stock_data.get("mksc_shrn_iscd", "")

          # Validate stock code
          if not DataValidationUtils.validate_stock_code(stock_code):
            logger.warning(f"Invalid stock code: {stock_code}")
            continue

          # Find or create stock
          stock = DatabaseUtils.get_stock_by_code(db, stock_code)
          if not stock:
            # Create new stock if not exists
            stock_name = stock_data.get("hts_kor_isnm", "").strip()
            if not stock_name:
              logger.warning(f"Missing stock name for {stock_code}")
              continue

            stock = Stock(
                region=region,
                code=stock_code,
                name=stock_name,
                active=True
            )
            db.add(stock)
            db.flush()

          # Add to universe
          universe_item = UniverseItem(
              universe_id=universe.id,
              stock_id=stock.id
          )
          db.add(universe_item)
          added_count += 1

        logger.info(f"Created universe {universe.id} with {added_count} stocks")
        return universe.id if added_count > 0 else None

    except Exception as e:
      logger.error(f"Failed to update universe: {e}")
      return None
