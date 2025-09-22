"""
Database models optimized for large-scale stock analysis and ML training.
Designed for maximum data collection and high-quality ML features.
"""
from enum import Enum
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Boolean, Float, Date, Text, ForeignKey, Index, DateTime, Numeric, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class MarketRegion(str, Enum):
    """Market region enum for global stock markets."""
    KR = "KR"  # South Korea
    US = "US"  # United States
    JP = "JP"  # Japan
    CN = "CN"  # China
    HK = "HK"  # Hong Kong


class StockSector(str, Enum):
    """Stock sector classification for industry analysis."""
    TECHNOLOGY = "TECHNOLOGY"
    FINANCE = "FINANCE"
    HEALTHCARE = "HEALTHCARE"
    ENERGY = "ENERGY"
    MATERIALS = "MATERIALS"
    INDUSTRIALS = "INDUSTRIALS"
    CONSUMER_DISCRETIONARY = "CONSUMER_DISCRETIONARY"
    CONSUMER_STAPLES = "CONSUMER_STAPLES"
    UTILITIES = "UTILITIES"
    REAL_ESTATE = "REAL_ESTATE"
    TELECOMMUNICATIONS = "TELECOMMUNICATIONS"


class StockMaster(Base):
    """Master stock information with comprehensive metadata for ML."""
    __tablename__ = "stock_master"

    stock_id = Column(BigInteger, primary_key=True, autoincrement=True)
    market_region = Column(String(2), nullable=False)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(200), nullable=False)
    stock_name_en = Column(String(200), nullable=True)
    
    # Market information
    market_name = Column(String(50), nullable=True)  # KOSPI, KOSDAQ, NYSE, NASDAQ
    sector_classification = Column(String(50), nullable=True)
    industry_classification = Column(String(100), nullable=True)
    
    # Company fundamentals
    market_capitalization = Column(Numeric(20, 2), nullable=True)
    shares_outstanding = Column(BigInteger, nullable=True)
    listing_date = Column(Date, nullable=True)
    
    # Status flags
    is_active = Column(Boolean, nullable=False, default=True)
    is_delisted = Column(Boolean, nullable=False, default=False)
    is_suspended = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    data_provider = Column(String(50), nullable=True)  # KIS, Yahoo, Alpha Vantage
    last_updated = Column(DateTime, nullable=False, default=func.now())
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    daily_prices = relationship("StockDailyPrice", back_populates="stock_master")
    technical_indicators = relationship("StockTechnicalIndicator", back_populates="stock_master")
    fundamental_data = relationship("StockFundamentalData", back_populates="stock_master")
    market_data = relationship("StockMarketData", back_populates="stock_master")
    universe_items = relationship("TradingUniverseItem", back_populates="stock_master")

    __table_args__ = (
        Index('uq_stock_master_region_code', 'market_region', 'stock_code', unique=True),
        Index('ix_stock_master_active', 'is_active'),
        Index('ix_stock_master_sector', 'sector_classification'),
        Index('ix_stock_master_market', 'market_name'),
    )


class StockDailyPrice(Base):
    """Daily OHLCV data with enhanced volume and price analytics."""
    __tablename__ = "stock_daily_price"

    price_id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_id = Column(BigInteger, ForeignKey("stock_master.stock_id"), nullable=False)
    trade_date = Column(Date, nullable=False)
    
    # OHLCV data with high precision
    open_price = Column(Numeric(15, 4), nullable=False)
    high_price = Column(Numeric(15, 4), nullable=False)
    low_price = Column(Numeric(15, 4), nullable=False)
    close_price = Column(Numeric(15, 4), nullable=False)
    adjusted_close_price = Column(Numeric(15, 4), nullable=True)
    
    # Volume data
    volume = Column(BigInteger, nullable=False)
    volume_value = Column(Numeric(20, 2), nullable=True)  # Trading value in currency
    
    # Derived price metrics
    daily_return_pct = Column(Float, nullable=True)
    price_change = Column(Numeric(15, 4), nullable=True)
    price_change_pct = Column(Float, nullable=True)
    
    # Advanced metrics
    vwap = Column(Numeric(15, 4), nullable=True)  # Volume Weighted Average Price
    typical_price = Column(Numeric(15, 4), nullable=True)  # (H+L+C)/3
    true_range = Column(Numeric(15, 4), nullable=True)
    
    # Quality flags
    is_adjusted = Column(Boolean, nullable=False, default=False)
    has_split = Column(Boolean, nullable=False, default=False)
    has_dividend = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    data_source = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    stock_master = relationship("StockMaster", back_populates="daily_prices")

    __table_args__ = (
        Index('uq_daily_price_stock_date', 'stock_id', 'trade_date', unique=True),
        Index('ix_daily_price_date', 'trade_date'),
        Index('ix_daily_price_volume', 'volume'),
    )


class StockTechnicalIndicator(Base):
    """Comprehensive technical indicators for ML feature engineering."""
    __tablename__ = "stock_technical_indicator"

    indicator_id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_id = Column(BigInteger, ForeignKey("stock_master.stock_id"), nullable=False)
    calculation_date = Column(Date, nullable=False)
    
    # Moving Averages
    sma_5 = Column(Float, nullable=True)
    sma_10 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_100 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)
    
    ema_5 = Column(Float, nullable=True)
    ema_10 = Column(Float, nullable=True)
    ema_12 = Column(Float, nullable=True)
    ema_20 = Column(Float, nullable=True)
    ema_26 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    
    # Oscillators
    rsi_9 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    rsi_21 = Column(Float, nullable=True)
    
    stochastic_k = Column(Float, nullable=True)
    stochastic_d = Column(Float, nullable=True)
    
    williams_r = Column(Float, nullable=True)
    cci_14 = Column(Float, nullable=True)
    
    # MACD indicators
    macd_line = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    
    # Bollinger Bands
    bb_upper_20_2 = Column(Float, nullable=True)
    bb_middle_20 = Column(Float, nullable=True)
    bb_lower_20_2 = Column(Float, nullable=True)
    bb_width = Column(Float, nullable=True)
    bb_percent = Column(Float, nullable=True)
    
    # Volume indicators
    volume_sma_10 = Column(Float, nullable=True)
    volume_sma_20 = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    obv = Column(BigInteger, nullable=True)  # On Balance Volume
    
    # Volatility indicators
    atr_14 = Column(Float, nullable=True)  # Average True Range
    volatility_10 = Column(Float, nullable=True)
    volatility_20 = Column(Float, nullable=True)
    volatility_30 = Column(Float, nullable=True)
    
    # Trend indicators
    adx_14 = Column(Float, nullable=True)  # Average Directional Index
    di_plus_14 = Column(Float, nullable=True)
    di_minus_14 = Column(Float, nullable=True)
    
    # Price patterns
    support_level = Column(Float, nullable=True)
    resistance_level = Column(Float, nullable=True)
    trend_direction = Column(String(10), nullable=True)  # UP, DOWN, SIDEWAYS
    
    # Custom indicators
    momentum_5 = Column(Float, nullable=True)
    momentum_10 = Column(Float, nullable=True)
    price_position = Column(Float, nullable=True)  # Position within daily range
    
    # Metadata
    calculation_version = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    stock_master = relationship("StockMaster", back_populates="technical_indicators")

    __table_args__ = (
        Index('uq_technical_indicator_stock_date', 'stock_id', 'calculation_date', unique=True),
        Index('ix_technical_indicator_date', 'calculation_date'),
        Index('ix_technical_indicator_rsi', 'rsi_14'),
        Index('ix_technical_indicator_macd', 'macd_line'),
    )


class StockFundamentalData(Base):
    """Fundamental analysis data for comprehensive stock evaluation."""
    __tablename__ = "stock_fundamental_data"

    fundamental_id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_id = Column(BigInteger, ForeignKey("stock_master.stock_id"), nullable=False)
    report_date = Column(Date, nullable=False)
    fiscal_period = Column(String(10), nullable=True)  # Q1, Q2, Q3, Q4, Annual
    
    # Financial ratios
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    ps_ratio = Column(Float, nullable=True)
    pcf_ratio = Column(Float, nullable=True)
    
    # Profitability ratios
    roe = Column(Float, nullable=True)  # Return on Equity
    roa = Column(Float, nullable=True)  # Return on Assets
    gross_margin = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    net_margin = Column(Float, nullable=True)
    
    # Growth metrics
    revenue_growth_yoy = Column(Float, nullable=True)
    eps_growth_yoy = Column(Float, nullable=True)
    
    # Financial health
    debt_to_equity = Column(Float, nullable=True)
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    
    # Per share metrics
    eps = Column(Float, nullable=True)
    bps = Column(Float, nullable=True)  # Book value per share
    dividend_per_share = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    
    # Metadata
    data_source = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    stock_master = relationship("StockMaster", back_populates="fundamental_data")

    __table_args__ = (
        Index('uq_fundamental_stock_date', 'stock_id', 'report_date', unique=True),
        Index('ix_fundamental_pe_ratio', 'pe_ratio'),
        Index('ix_fundamental_roe', 'roe'),
    )


class StockMarketData(Base):
    """Market-wide data and stock correlations for macro analysis."""
    __tablename__ = "stock_market_data"

    market_data_id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_id = Column(BigInteger, ForeignKey("stock_master.stock_id"), nullable=False)
    data_date = Column(Date, nullable=False)
    
    # Market metrics
    market_index_value = Column(Float, nullable=True)
    market_index_change_pct = Column(Float, nullable=True)
    sector_index_value = Column(Float, nullable=True)
    sector_index_change_pct = Column(Float, nullable=True)
    
    # Relative performance
    stock_vs_market_performance = Column(Float, nullable=True)
    stock_vs_sector_performance = Column(Float, nullable=True)
    
    # Market sentiment
    foreign_buying_volume = Column(BigInteger, nullable=True)
    institutional_buying_volume = Column(BigInteger, nullable=True)
    individual_buying_volume = Column(BigInteger, nullable=True)
    
    # Economic indicators (for correlation analysis)
    interest_rate = Column(Float, nullable=True)
    exchange_rate_usd = Column(Float, nullable=True)
    vix_level = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    stock_master = relationship("StockMaster", back_populates="market_data")

    __table_args__ = (
        Index('uq_market_data_stock_date', 'stock_id', 'data_date', unique=True),
        Index('ix_market_data_date', 'data_date'),
    )


class TradingUniverse(Base):
    """Trading universe definition for stock selection strategies."""
    __tablename__ = "trading_universe"

    universe_id = Column(BigInteger, primary_key=True, autoincrement=True)
    universe_name = Column(String(100), nullable=False)
    universe_description = Column(Text, nullable=True)
    market_region = Column(String(2), nullable=False)
    
    # Universe criteria
    min_market_cap = Column(Numeric(20, 2), nullable=True)
    max_market_cap = Column(Numeric(20, 2), nullable=True)
    min_daily_volume = Column(BigInteger, nullable=True)
    allowed_sectors = Column(Text, nullable=True)  # JSON array
    
    # Universe metadata
    creation_date = Column(Date, nullable=False)
    last_rebalance_date = Column(Date, nullable=True)
    rebalance_frequency = Column(String(20), nullable=True)  # DAILY, WEEKLY, MONTHLY
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Metadata
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    universe_items = relationship("TradingUniverseItem", back_populates="trading_universe")
    recommendations = relationship("StockRecommendation", back_populates="trading_universe")

    __table_args__ = (
        Index('uq_universe_name_region', 'universe_name', 'market_region', unique=True),
        Index('ix_universe_active', 'is_active'),
    )


class TradingUniverseItem(Base):
    """Items in a trading universe with weights and metadata."""
    __tablename__ = "trading_universe_item"

    universe_item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    universe_id = Column(BigInteger, ForeignKey("trading_universe.universe_id"), nullable=False)
    stock_id = Column(BigInteger, ForeignKey("stock_master.stock_id"), nullable=False)
    
    # Item properties
    weight = Column(Float, nullable=True, default=1.0)
    rank = Column(Integer, nullable=True)
    
    # Selection criteria
    selection_score = Column(Float, nullable=True)
    selection_reason = Column(Text, nullable=True)
    
    # Dates
    added_date = Column(Date, nullable=False)
    removed_date = Column(Date, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    trading_universe = relationship("TradingUniverse", back_populates="universe_items")
    stock_master = relationship("StockMaster", back_populates="universe_items")

    __table_args__ = (
        Index('uq_universe_item_stock', 'universe_id', 'stock_id', unique=True),
        Index('ix_universe_item_active', 'is_active'),
        Index('ix_universe_item_rank', 'rank'),
    )


class StockRecommendation(Base):
    """ML-generated stock recommendations with detailed scoring."""
    __tablename__ = "stock_recommendation"

    recommendation_id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_id = Column(BigInteger, ForeignKey("stock_master.stock_id"), nullable=False)
    universe_id = Column(BigInteger, ForeignKey("trading_universe.universe_id"), nullable=False)
    
    # Recommendation details
    recommendation_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    
    # Scoring
    ml_score = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    
    # Rankings
    universe_rank = Column(Integer, nullable=True)
    sector_rank = Column(Integer, nullable=True)
    
    # Price targets and predictions
    predicted_return_1d = Column(Float, nullable=True)
    predicted_return_5d = Column(Float, nullable=True)
    predicted_return_20d = Column(Float, nullable=True)
    
    target_price = Column(Numeric(15, 4), nullable=True)
    stop_loss_price = Column(Numeric(15, 4), nullable=True)
    
    # Model information
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    feature_importance = Column(Text, nullable=True)  # JSON
    
    # Recommendation reasoning
    recommendation_reason = Column(Text, nullable=True)
    key_factors = Column(Text, nullable=True)  # JSON array
    
    # Performance tracking
    actual_return_1d = Column(Float, nullable=True)
    actual_return_5d = Column(Float, nullable=True)
    actual_return_20d = Column(Float, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    stock_master = relationship("StockMaster")
    trading_universe = relationship("TradingUniverse", back_populates="recommendations")

    __table_args__ = (
        Index('uq_recommendation_stock_date', 'stock_id', 'recommendation_date', unique=True),
        Index('ix_recommendation_target_date', 'target_date'),
        Index('ix_recommendation_score', 'ml_score'),
        Index('ix_recommendation_rank', 'universe_rank'),
    )
