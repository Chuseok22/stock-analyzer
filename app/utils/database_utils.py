"""
Database utilities for stock analysis application.
"""
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
from datetime import date, datetime
import logging

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import get_db_session
from app.models.entities import Stock, StockPrice, StockIndicator, UniverseItem

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Utility functions for database operations."""
    
    @staticmethod
    @contextmanager
    def safe_db_session() -> Generator[Session, None, None]:
        """
        Context manager for safe database session handling with comprehensive error management.
        
        Yields:
            Database session
        """
        session = None
        try:
            with get_db_session() as session:
                yield session
        except SQLAlchemyError as e:
            logger.error(f"Database error occurred: {e}")
            if session:
                session.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error in database session: {e}")
            if session:
                session.rollback()
            raise
    
    @staticmethod
    def get_stock_by_code(db: Session, stock_code: str) -> Optional[Stock]:
        """
        Get stock entity by code with active status check.
        
        Args:
            db: Database session
            stock_code: Stock code
            
        Returns:
            Stock entity or None
        """
        try:
            return db.query(Stock).filter(
                and_(Stock.code == stock_code, Stock.active == True)
            ).first()
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
            universe_items = db.query(UniverseItem).filter(
                UniverseItem.universe_id == universe_id
            ).all()
            
            return [item.stock_id for item in universe_items]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get stock IDs for universe {universe_id}: {e}")
            return []
    
    @staticmethod
    def get_latest_price_data(db: Session, stock_id: int, 
                            days: int = 1) -> List[StockPrice]:
        """
        Get latest price data for a stock.
        
        Args:
            db: Database session
            stock_id: Stock ID
            days: Number of days to retrieve
            
        Returns:
            List of StockPrice entities
        """
        try:
            return db.query(StockPrice).filter(
                StockPrice.stock_id == stock_id
            ).order_by(desc(StockPrice.trade_date)).limit(days).all()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get latest price data for stock {stock_id}: {e}")
            return []
    
    @staticmethod
    def get_latest_indicator_data(db: Session, stock_id: int, 
                                trade_date: date = None) -> Optional[StockIndicator]:
        """
        Get latest indicator data for a stock.
        
        Args:
            db: Database session
            stock_id: Stock ID
            trade_date: Specific trade date (optional)
            
        Returns:
            StockIndicator entity or None
        """
        try:
            query = db.query(StockIndicator).filter(
                StockIndicator.stock_id == stock_id
            )
            
            if trade_date:
                query = query.filter(StockIndicator.trade_date == trade_date)
            else:
                query = query.order_by(desc(StockIndicator.trade_date))
            
            return query.first()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get indicator data for stock {stock_id}: {e}")
            return None
    
    @staticmethod
    def bulk_upsert_price_data(db: Session, stock_id: int, 
                             price_data_list: List[Dict]) -> int:
        """
        Bulk upsert price data with improved error handling.
        
        Args:
            db: Database session
            stock_id: Stock ID
            price_data_list: List of price data dictionaries
            
        Returns:
            Number of records processed
        """
        processed_count = 0
        
        try:
            for price_data in price_data_list:
                try:
                    # Validate data structure
                    if not isinstance(price_data, dict):
                        logger.warning(f"Invalid price data format: {type(price_data)}")
                        continue
                    
                    # Parse trade date
                    trade_date_str = price_data.get("stck_bsop_date", "")
                    if not trade_date_str:
                        logger.warning("Missing trade date in price data")
                        continue
                    
                    trade_date = datetime.strptime(trade_date_str, "%Y%m%d").date()
                    
                    # Check if record exists
                    existing = db.query(StockPrice).filter(
                        and_(
                            StockPrice.stock_id == stock_id,
                            StockPrice.trade_date == trade_date
                        )
                    ).first()
                    
                    # Parse price values
                    try:
                        open_price = float(price_data.get("stck_oprc", 0))
                        high_price = float(price_data.get("stck_hgpr", 0))
                        low_price = float(price_data.get("stck_lwpr", 0))
                        close_price = float(price_data.get("stck_clpr", 0))
                        volume = int(price_data.get("acml_vol", 0))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid price values in data: {e}")
                        continue
                    
                    if existing:
                        # Update existing record
                        existing.open_price = open_price
                        existing.high_price = high_price
                        existing.low_price = low_price
                        existing.close_price = close_price
                        existing.volume = volume
                    else:
                        # Create new record
                        price_record = StockPrice(
                            stock_id=stock_id,
                            trade_date=trade_date,
                            open_price=open_price,
                            high_price=high_price,
                            low_price=low_price,
                            close_price=close_price,
                            volume=volume
                        )
                        db.add(price_record)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process individual price record: {e}")
                    continue
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to bulk upsert price data: {e}")
            return processed_count
    
    @staticmethod
    def bulk_upsert_indicator_data(db: Session, stock_id: int, 
                                 indicator_data_list: List[Dict]) -> int:
        """
        Bulk upsert indicator data with improved error handling.
        
        Args:
            db: Database session
            stock_id: Stock ID
            indicator_data_list: List of indicator data dictionaries
            
        Returns:
            Number of records processed
        """
        processed_count = 0
        
        try:
            for indicator_data in indicator_data_list:
                try:
                    trade_date = indicator_data.get('trade_date')
                    if not trade_date:
                        continue
                    
                    # Check if record exists
                    existing = db.query(StockIndicator).filter(
                        and_(
                            StockIndicator.stock_id == stock_id,
                            StockIndicator.trade_date == trade_date
                        )
                    ).first()
                    
                    if existing:
                        # Update existing record
                        DatabaseUtils._update_indicator_fields(existing, indicator_data)
                    else:
                        # Create new record
                        indicator = StockIndicator(
                            stock_id=stock_id,
                            trade_date=trade_date
                        )
                        DatabaseUtils._update_indicator_fields(indicator, indicator_data)
                        db.add(indicator)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process individual indicator record: {e}")
                    continue
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to bulk upsert indicator data: {e}")
            return processed_count
    
    @staticmethod
    def _update_indicator_fields(indicator: StockIndicator, data: Dict) -> None:
        """
        Update indicator fields from data dictionary.
        
        Args:
            indicator: StockIndicator entity
            data: Data dictionary
        """
        # Define field mappings
        field_mappings = {
            'sma_5': 'sma_5',
            'sma_10': 'sma_10',
            'sma_20': 'sma_20',
            'sma_60': 'sma_60',
            'ema_12': 'ema_12',
            'ema_26': 'ema_26',
            'rsi_14': 'rsi_14',
            'macd': 'macd',
            'macd_signal': 'macd_signal',
            'bb_upper': 'bb_upper',
            'bb_middle': 'bb_middle',
            'bb_lower': 'bb_lower',
            'volume_sma_20': 'volume_sma_20',
            'volume_ratio': 'volume_ratio',
            'daily_return': 'daily_return',
            'volatility_20': 'volatility_20'
        }
        
        for field_name, data_key in field_mappings.items():
            if data_key in data:
                value = DatabaseUtils._safe_float_conversion(data[data_key])
                setattr(indicator, field_name, value)
    
    @staticmethod
    def _safe_float_conversion(value: Any) -> Optional[float]:
        """
        Safely convert value to float with NaN/None handling.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None
        """
        if value is None:
            return None
        
        try:
            import pandas as pd
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError, ImportError):
            return None
    
    @staticmethod
    def check_data_availability(db: Session, stock_id: int, 
                              start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Check data availability for a stock in a date range.
        
        Args:
            db: Database session
            stock_id: Stock ID
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with availability information
        """
        try:
            # Count price records
            price_count = db.query(StockPrice).filter(
                and_(
                    StockPrice.stock_id == stock_id,
                    StockPrice.trade_date >= start_date,
                    StockPrice.trade_date <= end_date
                )
            ).count()
            
            # Count indicator records
            indicator_count = db.query(StockIndicator).filter(
                and_(
                    StockIndicator.stock_id == stock_id,
                    StockIndicator.trade_date >= start_date,
                    StockIndicator.trade_date <= end_date
                )
            ).count()
            
            # Get date range of available data
            first_price = db.query(StockPrice).filter(
                StockPrice.stock_id == stock_id
            ).order_by(StockPrice.trade_date).first()
            
            last_price = db.query(StockPrice).filter(
                StockPrice.stock_id == stock_id
            ).order_by(desc(StockPrice.trade_date)).first()
            
            return {
                'price_records': price_count,
                'indicator_records': indicator_count,
                'first_available_date': first_price.trade_date if first_price else None,
                'last_available_date': last_price.trade_date if last_price else None,
                'has_sufficient_data': price_count > 0 and indicator_count > 0
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to check data availability: {e}")
            return {
                'price_records': 0,
                'indicator_records': 0,
                'first_available_date': None,
                'last_available_date': None,
                'has_sufficient_data': False
            }
    
    @staticmethod
    def cleanup_old_data(db: Session, cutoff_date: date, 
                       stock_id: int = None) -> Dict[str, int]:
        """
        Clean up old data before a cutoff date.
        
        Args:
            db: Database session
            cutoff_date: Date before which to delete data
            stock_id: Specific stock ID (optional)
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            deleted_prices = 0
            deleted_indicators = 0
            
            # Delete old price data
            price_query = db.query(StockPrice).filter(
                StockPrice.trade_date < cutoff_date
            )
            if stock_id:
                price_query = price_query.filter(StockPrice.stock_id == stock_id)
            
            deleted_prices = price_query.delete()
            
            # Delete old indicator data
            indicator_query = db.query(StockIndicator).filter(
                StockIndicator.trade_date < cutoff_date
            )
            if stock_id:
                indicator_query = indicator_query.filter(StockIndicator.stock_id == stock_id)
            
            deleted_indicators = indicator_query.delete()
            
            logger.info(f"Cleaned up {deleted_prices} price records and {deleted_indicators} indicator records")
            
            return {
                'deleted_prices': deleted_prices,
                'deleted_indicators': deleted_indicators
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return {
                'deleted_prices': 0,
                'deleted_indicators': 0
            }