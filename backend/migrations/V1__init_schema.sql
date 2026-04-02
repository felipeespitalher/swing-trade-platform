-- Swing Trade Platform - Initial Database Schema
-- Created with PostgreSQL 15 + TimescaleDB extension
-- Database: swing_trade

-- ============================================================================
-- EXTENSIONS
-- ============================================================================
-- Enable UUID support (UUID v4 generation)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for encryption functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable TimescaleDB for time-series data (OHLCV)
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
-- Core user accounts for the platform
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR NOT NULL,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  timezone VARCHAR(50) DEFAULT 'UTC',
  risk_limit_pct DECIMAL(5,2) DEFAULT 2.0,
  is_email_verified BOOLEAN DEFAULT FALSE,
  email_verification_token VARCHAR UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CHECK (risk_limit_pct > 0 AND risk_limit_pct <= 100)
);

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at DESC);

-- ============================================================================
-- EXCHANGE KEYS TABLE
-- ============================================================================
-- API keys for exchanges (encrypted at application layer)
CREATE TABLE IF NOT EXISTS exchange_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  exchange VARCHAR(50) NOT NULL,
  api_key_encrypted TEXT NOT NULL,
  api_secret_encrypted TEXT NOT NULL,
  encryption_iv VARCHAR NOT NULL,
  is_testnet BOOLEAN DEFAULT TRUE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, exchange, is_testnet)
);

-- Indexes for exchange_keys table
CREATE INDEX IF NOT EXISTS idx_exchange_keys_user ON exchange_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_exchange_keys_active ON exchange_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_exchange_keys_user_active ON exchange_keys(user_id, is_active);

-- ============================================================================
-- AUDIT LOGS TABLE (Append-only)
-- ============================================================================
-- Immutable audit trail of all user actions
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action VARCHAR(100) NOT NULL,
  resource_type VARCHAR(50),
  resource_id UUID,
  old_values JSONB,
  new_values JSONB,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit_logs (no update/delete, append-only design)
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_created ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_created ON audit_logs(action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- ============================================================================
-- STRATEGIES TABLE
-- ============================================================================
-- Trading strategies with JSON configuration
CREATE TABLE IF NOT EXISTS strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  type VARCHAR(50) NOT NULL,
  config JSONB NOT NULL,
  is_active BOOLEAN DEFAULT FALSE,
  version INT DEFAULT 1,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for strategies table
CREATE INDEX IF NOT EXISTS idx_strategies_user ON strategies(user_id);
CREATE INDEX IF NOT EXISTS idx_strategies_user_active ON strategies(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_strategies_created ON strategies(created_at DESC);

-- ============================================================================
-- OHLCV TABLE (TimescaleDB Hypertable)
-- ============================================================================
-- Time-series candlestick data (Open, High, Low, Close, Volume)
-- Optimized for time-series queries with TimescaleDB compression
CREATE TABLE IF NOT EXISTS ohlcv (
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  exchange VARCHAR(50) NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  timeframe VARCHAR(10) NOT NULL,
  open DECIMAL(20,8) NOT NULL,
  high DECIMAL(20,8) NOT NULL,
  low DECIMAL(20,8) NOT NULL,
  close DECIMAL(20,8) NOT NULL,
  volume DECIMAL(20,8) NOT NULL
);

-- Convert to hypertable (idempotent in TimescaleDB 2.0+)
SELECT create_hypertable('ohlcv', 'timestamp', if_not_exists => TRUE);

-- Indexes for ohlcv hypertable
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_time ON ohlcv(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_exchange_symbol_time ON ohlcv(exchange, symbol, timestamp DESC);

-- Enable compression policy for older data (older than 7 days)
-- This reduces storage but maintains query performance
SELECT add_compression_policy('ohlcv', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================================================
-- TRADES TABLE
-- ============================================================================
-- Historical trades and paper trading records
CREATE TABLE IF NOT EXISTS trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
  symbol VARCHAR(20) NOT NULL,
  entry_date TIMESTAMP WITH TIME ZONE NOT NULL,
  exit_date TIMESTAMP WITH TIME ZONE,
  entry_price DECIMAL(20,8) NOT NULL,
  exit_price DECIMAL(20,8),
  quantity DECIMAL(20,8) NOT NULL,
  pnl DECIMAL(20,8),
  pnl_pct DECIMAL(10,4),
  reason VARCHAR(100),
  is_paper_trade BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CHECK (quantity > 0)
);

-- Indexes for trades table
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol_date ON trades(symbol, entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_entry_date ON trades(entry_date DESC);

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE users IS 'Core user accounts with authentication and preferences';
COMMENT ON TABLE exchange_keys IS 'Encrypted API credentials for exchange integrations';
COMMENT ON TABLE audit_logs IS 'Append-only audit trail of all user actions (no updates/deletes)';
COMMENT ON TABLE strategies IS 'User-defined trading strategies with JSON configuration';
COMMENT ON TABLE ohlcv IS 'Time-series candlestick data (TimescaleDB hypertable for compression)';
COMMENT ON TABLE trades IS 'Historical and paper trades with P&L calculations';

COMMENT ON COLUMN users.email IS 'Unique email address for login and recovery';
COMMENT ON COLUMN users.risk_limit_pct IS 'Maximum risk per trade as percentage (0.01-100)';
COMMENT ON COLUMN exchange_keys.is_testnet IS 'Boolean: TRUE=testnet, FALSE=live trading';
COMMENT ON COLUMN audit_logs.created_at IS 'Timestamp is immutable - append-only table';
COMMENT ON COLUMN ohlcv.timestamp IS 'OHLCV timestamp (indexed by TimescaleDB hypertable)';
COMMENT ON COLUMN trades.is_paper_trade IS 'Paper trade = simulation, FALSE = live or backtested';

-- ============================================================================
-- INITIAL DATA (optional reference data)
-- ============================================================================
-- Insert reference timezones (optional, for future UI dropdowns)
-- This section is intentionally empty - timezones are user-defined

-- ============================================================================
-- MIGRATION TRACKING
-- ============================================================================
-- Flyway automatically creates flyway_schema_history table
-- It will track all migrations applied in sequence
-- Do not manually alter this table
