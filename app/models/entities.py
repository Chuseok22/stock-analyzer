"""
Database models that match Spring Boot JPA entities.
"""
from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, Float, Date, Text, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class Region(str, Enum):
  """Region enum matching Spring Boot enum."""
  KR = "KR"
  US = "US"


class Stock(Base):
  """Stock entity matching Spring Boot JPA entity."""
  __tablename__ = "stock"

  id = Column(Integer, primary_key=True, autoincrement=True)
  region = Column(String(2), nullable=False)  # KR, US
  code = Column(String(20), nullable=False)
  name = Column(String(100), nullable=False)
  active = Column(Boolean, nullable=False, default=True)

  # Audit fields (matching BasePostgresEntity)
  created_date = Column(DateTime, nullable=False, default=func.now())
  updated_date = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

  # Relationships
  universe_items = relationship("UniverseItem", back_populates="stock")
  recommendations = relationship("Recommendation", back_populates="stock")

  __table_args__ = (
    Index('ix_stock_region_active_code', 'region', 'active', 'code'),
    Index('uq_stock_region_code', 'region', 'code', unique=True),
  )


class Universe(Base):
  """Universe entity matching Spring Boot JPA entity."""
  __tablename__ = "universe"

  id = Column(Integer, primary_key=True, autoincrement=True)
  region = Column(String(2), nullable=False)
  size = Column(Integer, nullable=False)
  snapshot_date = Column(Date, nullable=False)
  rule_version = Column(String(50), nullable=False)

  # Audit fields
  created_date = Column(DateTime, nullable=False, default=func.now())
  updated_date = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

  # Relationships
  universe_items = relationship("UniverseItem", back_populates="universe")
  recommendations = relationship("Recommendation", back_populates="universe")

  __table_args__ = (
    Index('uq_universe_region_date', 'region', 'snapshot_date', unique=True),
  )


class UniverseItem(Base):
  """UniverseItem entity matching Spring Boot JPA entity."""
  __tablename__ = "universe_item"

  id = Column(Integer, primary_key=True, autoincrement=True)
  universe_id = Column(Integer, ForeignKey("universe.id"), nullable=False)
  stock_id = Column(Integer, ForeignKey("stock.id"), nullable=False)

  # Audit fields
  created_date = Column(DateTime, nullable=False, default=func.now())
  updated_date = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

  # Relationships
  universe = relationship("Universe", back_populates="universe_items")
  stock = relationship("Stock", back_populates="universe_items")

  __table_args__ = (
    Index('uq_universe_item', 'universe_id', 'stock_id', unique=True),
  )


class Recommendation(Base):
  """Recommendation entity matching Spring Boot JPA entity."""
  __tablename__ = "recommendation"

  id = Column(Integer, primary_key=True, autoincrement=True)
  stock_id = Column(Integer, ForeignKey("stock.id"), nullable=False)
  universe_id = Column(Integer, ForeignKey("universe.id"), nullable=False)
  for_date = Column(Date, nullable=False)
  score = Column(Float, nullable=False)
  rank = Column(Integer, nullable=True)
  reason_json = Column(Text, nullable=True)  # JSON string

  # Audit fields
  created_date = Column(DateTime, nullable=False, default=func.now())
  updated_date = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

  # Relationships
  stock = relationship("Stock", back_populates="recommendations")
  universe = relationship("Universe", back_populates="recommendations")

  __table_args__ = (
    Index('uq_reco_date_stock', 'for_date', 'stock_id', unique=True),
    Index('ix_reco_date_score', 'for_date', 'score'),
  )


# Additional table for storing stock price data (not in Spring Boot yet)
class StockPrice(Base):
  """Stock price data for ML training."""
  __tablename__ = "stock_price"

  id = Column(Integer, primary_key=True, autoincrement=True)
  stock_id = Column(Integer, ForeignKey("stock.id"), nullable=False)
  trade_date = Column(Date, nullable=False)
  open_price = Column(Float, nullable=False)
  high_price = Column(Float, nullable=False)
  low_price = Column(Float, nullable=False)
  close_price = Column(Float, nullable=False)
  volume = Column(Integer, nullable=False)
  adjusted_close = Column(Float, nullable=True)

  # Audit fields
  created_date = Column(DateTime, nullable=False, default=func.now())
  updated_date = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

  # Relationships
  stock = relationship("Stock")

  __table_args__ = (
    Index('uq_stock_price_date', 'stock_id', 'trade_date', unique=True),
    Index('ix_stock_price_date', 'trade_date'),
  )


class StockIndicator(Base):
  """Technical indicators for ML features."""
  __tablename__ = "stock_indicator"

  id = Column(Integer, primary_key=True, autoincrement=True)
  stock_id = Column(Integer, ForeignKey("stock.id"), nullable=False)
  trade_date = Column(Date, nullable=False)

  # Technical indicators
  sma_5 = Column(Float, nullable=True)
  sma_10 = Column(Float, nullable=True)
  sma_20 = Column(Float, nullable=True)
  sma_60 = Column(Float, nullable=True)
  ema_12 = Column(Float, nullable=True)
  ema_26 = Column(Float, nullable=True)
  rsi_14 = Column(Float, nullable=True)
  macd = Column(Float, nullable=True)
  macd_signal = Column(Float, nullable=True)
  bb_upper = Column(Float, nullable=True)
  bb_middle = Column(Float, nullable=True)
  bb_lower = Column(Float, nullable=True)

  # Volume indicators
  volume_sma_20 = Column(Float, nullable=True)
  volume_ratio = Column(Float, nullable=True)

  # Price patterns
  daily_return = Column(Float, nullable=True)
  volatility_20 = Column(Float, nullable=True)

  # Audit fields
  created_date = Column(DateTime, nullable=False, default=func.now())
  updated_date = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

  # Relationships
  stock = relationship("Stock")

  __table_args__ = (
    Index('uq_stock_indicator_date', 'stock_id', 'trade_date', unique=True),
    Index('ix_stock_indicator_date', 'trade_date'),
  )
