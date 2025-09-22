-- Initial database schema for Stock Analyzer
-- Optimized for large-scale stock analysis and ML training
-- Author: AI Assistant
-- Date: 2025-09-22

-- ============================================================================
-- STOCK MASTER TABLE
-- ============================================================================
CREATE TABLE stock_master (
    stock_id BIGSERIAL PRIMARY KEY,
    market_region VARCHAR(2) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(200) NOT NULL,
    stock_name_en VARCHAR(200),
    
    -- Market information
    market_name VARCHAR(50),
    sector_classification VARCHAR(50),
    industry_classification VARCHAR(100),
    
    -- Company fundamentals
    market_capitalization NUMERIC(20, 2),
    shares_outstanding BIGINT,
    listing_date DATE,
    
    -- Status flags
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_delisted BOOLEAN NOT NULL DEFAULT FALSE,
    is_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Metadata
    data_provider VARCHAR(50),
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_stock_master_region_code UNIQUE (market_region, stock_code)
);

-- Indexes for stock_master
CREATE INDEX ix_stock_master_active ON stock_master (is_active);
CREATE INDEX ix_stock_master_sector ON stock_master (sector_classification);
CREATE INDEX ix_stock_master_market ON stock_master (market_name);
CREATE INDEX ix_stock_master_region ON stock_master (market_region);

-- ============================================================================
-- STOCK DAILY PRICE TABLE
-- ============================================================================
CREATE TABLE stock_daily_price (
    price_id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stock_master(stock_id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    
    -- OHLCV data with high precision
    open_price NUMERIC(15, 4) NOT NULL,
    high_price NUMERIC(15, 4) NOT NULL,
    low_price NUMERIC(15, 4) NOT NULL,
    close_price NUMERIC(15, 4) NOT NULL,
    adjusted_close_price NUMERIC(15, 4),
    
    -- Volume data
    volume BIGINT NOT NULL,
    volume_value NUMERIC(20, 2),
    
    -- Derived price metrics
    daily_return_pct FLOAT,
    price_change NUMERIC(15, 4),
    price_change_pct FLOAT,
    
    -- Advanced metrics
    vwap NUMERIC(15, 4),
    typical_price NUMERIC(15, 4),
    true_range NUMERIC(15, 4),
    
    -- Quality flags
    is_adjusted BOOLEAN NOT NULL DEFAULT FALSE,
    has_split BOOLEAN NOT NULL DEFAULT FALSE,
    has_dividend BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Metadata
    data_source VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_daily_price_stock_date UNIQUE (stock_id, trade_date)
);

-- Indexes for stock_daily_price
CREATE INDEX ix_daily_price_date ON stock_daily_price (trade_date);
CREATE INDEX ix_daily_price_volume ON stock_daily_price (volume);
CREATE INDEX ix_daily_price_stock_id ON stock_daily_price (stock_id);

-- ============================================================================
-- STOCK TECHNICAL INDICATOR TABLE
-- ============================================================================
CREATE TABLE stock_technical_indicator (
    indicator_id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stock_master(stock_id) ON DELETE CASCADE,
    calculation_date DATE NOT NULL,
    
    -- Moving Averages
    sma_5 FLOAT,
    sma_10 FLOAT,
    sma_20 FLOAT,
    sma_50 FLOAT,
    sma_100 FLOAT,
    sma_200 FLOAT,
    
    ema_5 FLOAT,
    ema_10 FLOAT,
    ema_12 FLOAT,
    ema_20 FLOAT,
    ema_26 FLOAT,
    ema_50 FLOAT,
    
    -- Oscillators
    rsi_9 FLOAT,
    rsi_14 FLOAT,
    rsi_21 FLOAT,
    
    stochastic_k FLOAT,
    stochastic_d FLOAT,
    
    williams_r FLOAT,
    cci_14 FLOAT,
    
    -- MACD indicators
    macd_line FLOAT,
    macd_signal FLOAT,
    macd_histogram FLOAT,
    
    -- Bollinger Bands
    bb_upper_20_2 FLOAT,
    bb_middle_20 FLOAT,
    bb_lower_20_2 FLOAT,
    bb_width FLOAT,
    bb_percent FLOAT,
    
    -- Volume indicators
    volume_sma_10 FLOAT,
    volume_sma_20 FLOAT,
    volume_ratio FLOAT,
    obv BIGINT,
    
    -- Volatility indicators
    atr_14 FLOAT,
    volatility_10 FLOAT,
    volatility_20 FLOAT,
    volatility_30 FLOAT,
    
    -- Trend indicators
    adx_14 FLOAT,
    di_plus_14 FLOAT,
    di_minus_14 FLOAT,
    
    -- Price patterns
    support_level FLOAT,
    resistance_level FLOAT,
    trend_direction VARCHAR(10),
    
    -- Custom indicators
    momentum_5 FLOAT,
    momentum_10 FLOAT,
    price_position FLOAT,
    
    -- Metadata
    calculation_version VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_technical_indicator_stock_date UNIQUE (stock_id, calculation_date)
);

-- Indexes for stock_technical_indicator
CREATE INDEX ix_technical_indicator_date ON stock_technical_indicator (calculation_date);
CREATE INDEX ix_technical_indicator_rsi ON stock_technical_indicator (rsi_14);
CREATE INDEX ix_technical_indicator_macd ON stock_technical_indicator (macd_line);
CREATE INDEX ix_technical_indicator_stock_id ON stock_technical_indicator (stock_id);

-- ============================================================================
-- STOCK FUNDAMENTAL DATA TABLE
-- ============================================================================
CREATE TABLE stock_fundamental_data (
    fundamental_id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stock_master(stock_id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    fiscal_period VARCHAR(10),
    
    -- Financial ratios
    pe_ratio FLOAT,
    pb_ratio FLOAT,
    ps_ratio FLOAT,
    pcf_ratio FLOAT,
    
    -- Profitability ratios
    roe FLOAT,
    roa FLOAT,
    gross_margin FLOAT,
    operating_margin FLOAT,
    net_margin FLOAT,
    
    -- Growth metrics
    revenue_growth_yoy FLOAT,
    eps_growth_yoy FLOAT,
    
    -- Financial health
    debt_to_equity FLOAT,
    current_ratio FLOAT,
    quick_ratio FLOAT,
    
    -- Per share metrics
    eps FLOAT,
    bps FLOAT,
    dividend_per_share FLOAT,
    dividend_yield FLOAT,
    
    -- Metadata
    data_source VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_fundamental_stock_date UNIQUE (stock_id, report_date)
);

-- Indexes for stock_fundamental_data
CREATE INDEX ix_fundamental_pe_ratio ON stock_fundamental_data (pe_ratio);
CREATE INDEX ix_fundamental_roe ON stock_fundamental_data (roe);
CREATE INDEX ix_fundamental_stock_id ON stock_fundamental_data (stock_id);

-- ============================================================================
-- STOCK MARKET DATA TABLE
-- ============================================================================
CREATE TABLE stock_market_data (
    market_data_id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stock_master(stock_id) ON DELETE CASCADE,
    data_date DATE NOT NULL,
    
    -- Market metrics
    market_index_value FLOAT,
    market_index_change_pct FLOAT,
    sector_index_value FLOAT,
    sector_index_change_pct FLOAT,
    
    -- Relative performance
    stock_vs_market_performance FLOAT,
    stock_vs_sector_performance FLOAT,
    
    -- Market sentiment
    foreign_buying_volume BIGINT,
    institutional_buying_volume BIGINT,
    individual_buying_volume BIGINT,
    
    -- Economic indicators
    interest_rate FLOAT,
    exchange_rate_usd FLOAT,
    vix_level FLOAT,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_market_data_stock_date UNIQUE (stock_id, data_date)
);

-- Indexes for stock_market_data
CREATE INDEX ix_market_data_date ON stock_market_data (data_date);
CREATE INDEX ix_market_data_stock_id ON stock_market_data (stock_id);

-- ============================================================================
-- TRADING UNIVERSE TABLE
-- ============================================================================
CREATE TABLE trading_universe (
    universe_id BIGSERIAL PRIMARY KEY,
    universe_name VARCHAR(100) NOT NULL,
    universe_description TEXT,
    market_region VARCHAR(2) NOT NULL,
    
    -- Universe criteria
    min_market_cap NUMERIC(20, 2),
    max_market_cap NUMERIC(20, 2),
    min_daily_volume BIGINT,
    allowed_sectors TEXT,
    
    -- Universe metadata
    creation_date DATE NOT NULL,
    last_rebalance_date DATE,
    rebalance_frequency VARCHAR(20),
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Metadata
    created_by VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_universe_name_region UNIQUE (universe_name, market_region)
);

-- Indexes for trading_universe
CREATE INDEX ix_universe_active ON trading_universe (is_active);
CREATE INDEX ix_universe_region ON trading_universe (market_region);

-- ============================================================================
-- TRADING UNIVERSE ITEM TABLE
-- ============================================================================
CREATE TABLE trading_universe_item (
    universe_item_id BIGSERIAL PRIMARY KEY,
    universe_id BIGINT NOT NULL REFERENCES trading_universe(universe_id) ON DELETE CASCADE,
    stock_id BIGINT NOT NULL REFERENCES stock_master(stock_id) ON DELETE CASCADE,
    
    -- Item properties
    weight FLOAT DEFAULT 1.0,
    rank INTEGER,
    
    -- Selection criteria
    selection_score FLOAT,
    selection_reason TEXT,
    
    -- Dates
    added_date DATE NOT NULL,
    removed_date DATE,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_universe_item_stock UNIQUE (universe_id, stock_id)
);

-- Indexes for trading_universe_item
CREATE INDEX ix_universe_item_active ON trading_universe_item (is_active);
CREATE INDEX ix_universe_item_rank ON trading_universe_item (rank);
CREATE INDEX ix_universe_item_universe_id ON trading_universe_item (universe_id);
CREATE INDEX ix_universe_item_stock_id ON trading_universe_item (stock_id);

-- ============================================================================
-- STOCK RECOMMENDATION TABLE
-- ============================================================================
CREATE TABLE stock_recommendation (
    recommendation_id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stock_master(stock_id) ON DELETE CASCADE,
    universe_id BIGINT NOT NULL REFERENCES trading_universe(universe_id) ON DELETE CASCADE,
    
    -- Recommendation details
    recommendation_date DATE NOT NULL,
    target_date DATE NOT NULL,
    
    -- Scoring
    ml_score FLOAT NOT NULL,
    confidence_score FLOAT,
    risk_score FLOAT,
    
    -- Rankings
    universe_rank INTEGER,
    sector_rank INTEGER,
    
    -- Price targets and predictions
    predicted_return_1d FLOAT,
    predicted_return_5d FLOAT,
    predicted_return_20d FLOAT,
    
    target_price NUMERIC(15, 4),
    stop_loss_price NUMERIC(15, 4),
    
    -- Model information
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    feature_importance TEXT,
    
    -- Recommendation reasoning
    recommendation_reason TEXT,
    key_factors TEXT,
    
    -- Performance tracking
    actual_return_1d FLOAT,
    actual_return_5d FLOAT,
    actual_return_20d FLOAT,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_recommendation_stock_date UNIQUE (stock_id, recommendation_date)
);

-- Indexes for stock_recommendation
CREATE INDEX ix_recommendation_target_date ON stock_recommendation (target_date);
CREATE INDEX ix_recommendation_score ON stock_recommendation (ml_score);
CREATE INDEX ix_recommendation_rank ON stock_recommendation (universe_rank);
CREATE INDEX ix_recommendation_stock_id ON stock_recommendation (stock_id);
CREATE INDEX ix_recommendation_universe_id ON stock_recommendation (universe_id);

-- ============================================================================
-- COMMENTS AND DOCUMENTATION
-- ============================================================================

-- Add table comments for documentation
COMMENT ON TABLE stock_master IS 'Master stock information with comprehensive metadata for ML';
COMMENT ON TABLE stock_daily_price IS 'Daily OHLCV data with enhanced volume and price analytics';
COMMENT ON TABLE stock_technical_indicator IS 'Comprehensive technical indicators for ML feature engineering';
COMMENT ON TABLE stock_fundamental_data IS 'Fundamental analysis data for comprehensive stock evaluation';
COMMENT ON TABLE stock_market_data IS 'Market-wide data and stock correlations for macro analysis';
COMMENT ON TABLE trading_universe IS 'Trading universe definition for stock selection strategies';
COMMENT ON TABLE trading_universe_item IS 'Items in a trading universe with weights and metadata';
COMMENT ON TABLE stock_recommendation IS 'ML-generated stock recommendations with detailed scoring';

-- Add column comments for key fields
COMMENT ON COLUMN stock_master.stock_id IS 'Primary key for stock identification';
COMMENT ON COLUMN stock_master.market_region IS 'Market region (KR, US, JP, CN, HK)';
COMMENT ON COLUMN stock_master.stock_code IS 'Stock ticker symbol';
COMMENT ON COLUMN stock_master.market_capitalization IS 'Market cap in local currency';

COMMENT ON COLUMN stock_daily_price.vwap IS 'Volume Weighted Average Price';
COMMENT ON COLUMN stock_daily_price.typical_price IS 'Calculated as (High + Low + Close) / 3';
COMMENT ON COLUMN stock_daily_price.true_range IS 'True Range for volatility calculation';

COMMENT ON COLUMN stock_technical_indicator.obv IS 'On Balance Volume indicator';
COMMENT ON COLUMN stock_technical_indicator.atr_14 IS 'Average True Range over 14 periods';
COMMENT ON COLUMN stock_technical_indicator.adx_14 IS 'Average Directional Index over 14 periods';

COMMENT ON COLUMN stock_recommendation.ml_score IS 'Machine learning generated recommendation score';
COMMENT ON COLUMN stock_recommendation.feature_importance IS 'JSON string containing feature importance scores';

-- ============================================================================
-- INITIAL DATA SETUP
-- ============================================================================

-- Create a default Korean universe
INSERT INTO trading_universe (
    universe_name, 
    universe_description, 
    market_region, 
    creation_date, 
    rebalance_frequency,
    created_by
) VALUES (
    'Korean Major Stocks',
    'Top Korean stocks for ML training and recommendation',
    'KR',
    CURRENT_DATE,
    'DAILY',
    'System'
);

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stock_analyzer_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO stock_analyzer_user;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
