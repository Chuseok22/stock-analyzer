"""
Data collection and preprocessing service for stock analysis.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.entities import Stock, StockPrice, StockIndicator, Universe, UniverseItem
from app.database.connection import get_db_session
from app.services.kis_api import KISAPIClient

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
        
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        
        logger.info(f"Collecting stock prices from {start_date_str} to {end_date_str}")
        
        try:
            # Get stock price data from KIS API
            price_data = self.kis_client.bulk_stock_prices(
                stock_codes, start_date_str, end_date_str
            )
            
            # Save to database
            with get_db_session() as db:
                for stock_code, daily_data in price_data.items():
                    stock = self._get_stock_by_code(db, stock_code)
                    if not stock:
                        logger.warning(f"Stock not found: {stock_code}")
                        continue
                    
                    self._save_price_data(db, stock.id, daily_data)
                
                logger.info(f"Successfully collected price data for {len(price_data)} stocks")
                return True
                
        except Exception as e:
            logger.error(f"Failed to collect stock prices: {e}")
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
        Calculate technical indicators for stocks.
        
        Args:
            stock_id: Specific stock ID (None for all active stocks)
            days: Number of recent days to calculate
        
        Returns:
            Success status
        """
        try:
            with get_db_session() as db:
                if stock_id:
                    stock_ids = [stock_id]
                else:
                    # Get all active stocks
                    stocks = db.query(Stock).filter(Stock.active == True).all()
                    stock_ids = [stock.id for stock in stocks]
                
                for sid in stock_ids:
                    self._calculate_stock_indicators(db, sid, days)
                
                logger.info(f"Calculated indicators for {len(stock_ids)} stocks")
                return True
                
        except Exception as e:
            logger.error(f"Failed to calculate technical indicators: {e}")
            return False
    
    def _calculate_stock_indicators(self, db: Session, stock_id: int, days: int) -> None:
        """Calculate technical indicators for a single stock."""
        # Get recent price data
        prices_query = db.query(StockPrice).filter(
            StockPrice.stock_id == stock_id
        ).order_by(StockPrice.trade_date.desc()).limit(days * 2)  # Extra data for indicators
        
        prices = prices_query.all()
        if len(prices) < 20:  # Need minimum data for indicators
            logger.warning(f"Insufficient price data for stock {stock_id}")
            return
        
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
        
        # Calculate indicators
        indicators_df = self._compute_technical_indicators(df)
        
        # Save indicators to database
        for _, row in indicators_df.iterrows():
            if pd.isna(row['date']):
                continue
                
            # Check if indicator data already exists
            existing = db.query(StockIndicator).filter(
                and_(
                    StockIndicator.stock_id == stock_id,
                    StockIndicator.trade_date == row['date']
                )
            ).first()
            
            if existing:
                # Update existing record
                self._update_indicator_record(existing, row)
            else:
                # Create new record
                indicator = StockIndicator(
                    stock_id=stock_id,
                    trade_date=row['date']
                )
                self._update_indicator_record(indicator, row)
                db.add(indicator)
    
    def _compute_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute technical indicators from price data."""
        result = df.copy()
        
        # Simple Moving Averages
        result['sma_5'] = df['close'].rolling(window=5).mean()
        result['sma_10'] = df['close'].rolling(window=10).mean()
        result['sma_20'] = df['close'].rolling(window=20).mean()
        result['sma_60'] = df['close'].rolling(window=60).mean()
        
        # Exponential Moving Averages
        result['ema_12'] = df['close'].ewm(span=12).mean()
        result['ema_26'] = df['close'].ewm(span=26).mean()
        
        # RSI (Relative Strength Index)
        result['rsi_14'] = self._calculate_rsi(df['close'], 14)
        
        # MACD
        result['macd'] = result['ema_12'] - result['ema_26']
        result['macd_signal'] = result['macd'].ewm(span=9).mean()
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        bb_middle = df['close'].rolling(window=bb_period).mean()
        bb_std_dev = df['close'].rolling(window=bb_period).std()
        result['bb_upper'] = bb_middle + (bb_std_dev * bb_std)
        result['bb_middle'] = bb_middle
        result['bb_lower'] = bb_middle - (bb_std_dev * bb_std)
        
        # Volume indicators
        result['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        result['volume_ratio'] = df['volume'] / result['volume_sma_20']
        
        # Price patterns
        result['daily_return'] = df['close'].pct_change()
        result['volatility_20'] = result['daily_return'].rolling(window=20).std()
        
        return result
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _update_indicator_record(self, indicator: StockIndicator, row: pd.Series) -> None:
        """Update indicator record with calculated values."""
        indicator.sma_5 = self._safe_float(row.get('sma_5'))
        indicator.sma_10 = self._safe_float(row.get('sma_10'))
        indicator.sma_20 = self._safe_float(row.get('sma_20'))
        indicator.sma_60 = self._safe_float(row.get('sma_60'))
        indicator.ema_12 = self._safe_float(row.get('ema_12'))
        indicator.ema_26 = self._safe_float(row.get('ema_26'))
        indicator.rsi_14 = self._safe_float(row.get('rsi_14'))
        indicator.macd = self._safe_float(row.get('macd'))
        indicator.macd_signal = self._safe_float(row.get('macd_signal'))
        indicator.bb_upper = self._safe_float(row.get('bb_upper'))
        indicator.bb_middle = self._safe_float(row.get('bb_middle'))
        indicator.bb_lower = self._safe_float(row.get('bb_lower'))
        indicator.volume_sma_20 = self._safe_float(row.get('volume_sma_20'))
        indicator.volume_ratio = self._safe_float(row.get('volume_ratio'))
        indicator.daily_return = self._safe_float(row.get('daily_return'))
        indicator.volatility_20 = self._safe_float(row.get('volatility_20'))
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float, handling NaN."""
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    def get_training_data(self, universe_id: int, lookback_days: int = 252) -> pd.DataFrame:
        """
        Get training data for machine learning model.
        
        Args:
            universe_id: Universe ID to get stocks from
            lookback_days: Number of days to look back
        
        Returns:
            Training dataset as DataFrame
        """
        try:
            with get_db_session() as db:
                # Get stocks in universe
                universe_stocks = db.query(UniverseItem).filter(
                    UniverseItem.universe_id == universe_id
                ).all()
                
                stock_ids = [item.stock_id for item in universe_stocks]
                
                if not stock_ids:
                    logger.warning(f"No stocks found in universe {universe_id}")
                    return pd.DataFrame()
                
                # Get cutoff date
                cutoff_date = datetime.now().date() - timedelta(days=lookback_days)
                
                # Query training data
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
                
                # Calculate target variable (next day return)
                df['next_day_return'] = df.groupby('stock_id')['daily_return'].shift(-1)
                df['target'] = (df['next_day_return'] > 0).astype(int)  # Binary classification
                
                # Remove rows with missing target
                df = df.dropna(subset=['target'])
                
                logger.info(f"Generated training data: {len(df)} samples")
                return df
                
        except Exception as e:
            logger.error(f"Failed to get training data: {e}")
            return pd.DataFrame()
    
    def update_universe_stocks(self, region: str = "KR", top_n: int = 200) -> Optional[int]:
        """
        Update universe with top market cap stocks.
        
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
            
            with get_db_session() as db:
                # Create new universe
                universe = Universe(
                    region=region,
                    size=len(top_stocks),
                    snapshot_date=date.today(),
                    rule_version="market_cap_top_" + str(top_n)
                )
                db.add(universe)
                db.flush()  # Get universe ID
                
                # Add stocks to universe
                for stock_data in top_stocks:
                    stock_code = stock_data.get("mksc_shrn_iscd", "")
                    
                    # Find or create stock
                    stock = self._get_stock_by_code(db, stock_code)
                    if not stock:
                        # Create new stock if not exists
                        stock = Stock(
                            region=region,
                            code=stock_code,
                            name=stock_data.get("hts_kor_isnm", ""),
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
                
                logger.info(f"Created universe {universe.id} with {len(top_stocks)} stocks")
                return universe.id
                
        except Exception as e:
            logger.error(f"Failed to update universe: {e}")
            return None
