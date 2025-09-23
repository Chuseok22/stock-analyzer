"""
Database utilities for stock analysis application.
Updated to use correct entity names and improved functionality.
"""
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
from datetime import date, datetime
import logging

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import get_db_session
from app.models.entities import StockMaster, StockDailyPrice, StockTechnicalIndicator, TradingUniverseItem

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Utility functions for database operations."""
    
    @staticmethod
    def batch_insert(db: Session, records: List[Any]) -> bool:
        """
        Perform batch insert of records.
        
        Args:
            db: Database session
            records: List of model instances to insert
            
        Returns:
            Success status
        """
        try:
            db.add_all(records)
            db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Batch insert failed: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def get_stock_by_code(db: Session, stock_code: str, market_region: str = None) -> Optional[StockMaster]:
        """
        Get stock entity by code with optional market region filter.
        
        Args:
            db: Database session
            stock_code: Stock code
            market_region: Market region (KR, US, etc.)
            
        Returns:
            StockMaster entity or None
        """
        try:
            query = db.query(StockMaster).filter(
                and_(StockMaster.stock_code == stock_code, StockMaster.is_active == True)
            )
            
            if market_region:
                query = query.filter(StockMaster.market_region == market_region)
                
            return query.first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get stock by code '{stock_code}': {e}")
            return None
    
    @staticmethod
    def get_stock_ids_in_universe(db: Session, universe_id: int) -> List[int]:
        """
        Get list of stock IDs in a universe.
        
        Args:
            db: Database session
            universe_id: Universe ID
            
        Returns:
            List of stock IDs
        """
        try:
            universe_items = db.query(TradingUniverseItem).filter(
                TradingUniverseItem.universe_id == universe_id
            ).all()
            
            return [item.stock_id for item in universe_items]
        except SQLAlchemyError as e:
            logger.error(f"Failed to get stock IDs for universe '{universe_id}': {e}")
            return []
    
    @staticmethod
    def get_latest_prices(db: Session, stock_id: int, 
                         days: int = 1) -> List[StockDailyPrice]:
        """
        Get latest price records for a stock.
        
        Args:
            db: Database session
            stock_id: Stock ID
            days: Number of days to retrieve
            
        Returns:
            List of StockDailyPrice records
        """
        try:
            return db.query(StockDailyPrice).filter(
                StockDailyPrice.stock_id == stock_id
            ).order_by(desc(StockDailyPrice.trade_date)).limit(days).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get latest prices for stock '{stock_id}': {e}")
            return []
    
    @staticmethod
    def get_technical_indicators(db: Session, stock_id: int,
                               trade_date: date = None) -> Optional[StockTechnicalIndicator]:
        """
        Get technical indicators for a stock.
        
        Args:
            db: Database session
            stock_id: Stock ID
            trade_date: Specific trade date (optional)
            
        Returns:
            StockTechnicalIndicator record or None
        """
        try:
            query = db.query(StockTechnicalIndicator).filter(
                StockTechnicalIndicator.stock_id == stock_id
            )
            
            if trade_date:
                query = query.filter(StockTechnicalIndicator.calculation_date == trade_date)
            else:
                query = query.order_by(desc(StockTechnicalIndicator.calculation_date))
                
            return query.first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get technical indicators for stock '{stock_id}': {e}")
            return None
    
    @staticmethod
    def save_price_data(db: Session, stock_id: int, price_data: Dict[str, Any]) -> bool:
        """
        Save price data to database.
        
        Args:
            db: Database session
            stock_id: Stock ID
            price_data: Price data dictionary
            
        Returns:
            Success status
        """
        try:
            # Extract data from price_data dict
            trade_date = price_data.get('date')
            if isinstance(trade_date, str):
                trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
            elif isinstance(trade_date, datetime):
                trade_date = trade_date.date()
            
            # Check if record already exists
            existing = db.query(StockDailyPrice).filter(
                and_(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date == trade_date
                )
            ).first()
            
            if existing:
                # Update existing record
                existing.open_price = float(price_data.get('open', 0))
                existing.high_price = float(price_data.get('high', 0))
                existing.low_price = float(price_data.get('low', 0))
                existing.close_price = float(price_data.get('close', 0))
                existing.volume = int(price_data.get('volume', 0))
                existing.updated_at = datetime.now()
            else:
                # Create new record
                price_record = StockDailyPrice(
                    stock_id=stock_id,
                    trade_date=trade_date,
                    open_price=float(price_data.get('open', 0)),
                    high_price=float(price_data.get('high', 0)),
                    low_price=float(price_data.get('low', 0)),
                    close_price=float(price_data.get('close', 0)),
                    volume=int(price_data.get('volume', 0)),
                    data_source=price_data.get('source', 'api')
                )
                db.add(price_record)
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save price data for stock '{stock_id}': {e}")
            db.rollback()
            return False
    
    @staticmethod
    def get_price_history(db: Session, stock_id: int, 
                         start_date: date, end_date: date) -> List[StockDailyPrice]:
        """
        Get price history for a stock within date range.
        
        Args:
            db: Database session
            stock_id: Stock ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of StockDailyPrice records
        """
        try:
            return db.query(StockDailyPrice).filter(
                and_(
                    StockDailyPrice.stock_id == stock_id,
                    StockDailyPrice.trade_date >= start_date,
                    StockDailyPrice.trade_date <= end_date
                )
            ).order_by(StockDailyPrice.trade_date).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get price history for stock '{stock_id}': {e}")
            return []
    
    @staticmethod
    def get_active_stocks(db: Session, market_region: str = None) -> List[StockMaster]:
        """
        Get all active stocks, optionally filtered by market region.
        
        Args:
            db: Database session
            market_region: Market region filter (optional)
            
        Returns:
            List of StockMaster records
        """
        try:
            query = db.query(StockMaster).filter(StockMaster.is_active == True)
            
            if market_region:
                query = query.filter(StockMaster.market_region == market_region)
                
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get active stocks: {e}")
            return []


class DataValidationUtils:
    """Utilities for data validation."""
    
    @staticmethod
    def validate_price_data(price_data: Dict[str, Any]) -> bool:
        """
        Validate price data structure and values.
        
        Args:
            price_data: Price data dictionary
            
        Returns:
            Validation result
        """
        required_fields = ['date', 'open', 'high', 'low', 'close', 'volume']
        
        # Check required fields
        for field in required_fields:
            if field not in price_data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate numeric values
        try:
            open_price = float(price_data['open'])
            high_price = float(price_data['high'])
            low_price = float(price_data['low'])
            close_price = float(price_data['close'])
            volume = int(price_data['volume'])
            
            # Basic validation
            if any([open_price <= 0, high_price <= 0, low_price <= 0, close_price <= 0]):
                logger.warning("Invalid price values (non-positive)")
                return False
            
            if high_price < max(open_price, close_price, low_price):
                logger.warning("High price is not the highest")
                return False
            
            if low_price > min(open_price, close_price, high_price):
                logger.warning("Low price is not the lowest")
                return False
            
            if volume < 0:
                logger.warning("Invalid volume (negative)")
                return False
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid data types in price data: {e}")
            return False


# Legacy function wrappers for backward compatibility
def get_stock_by_code(db: Session, stock_code: str) -> Optional[StockMaster]:
    """Legacy wrapper function."""
    return DatabaseUtils.get_stock_by_code(db, stock_code)