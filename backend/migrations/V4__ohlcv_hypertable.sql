-- V4__ohlcv_hypertable.sql
-- Create OHLCV hypertable for TimescaleDB
-- This migration assumes TimescaleDB extension is already enabled (see V1)

-- Create base table (if not created by SQLAlchemy ORM)
CREATE TABLE IF NOT EXISTS ohlcv (
    timestamp    BIGINT        NOT NULL,
    exchange     VARCHAR(50)   NOT NULL,
    symbol       VARCHAR(20)   NOT NULL,
    timeframe    VARCHAR(10)   NOT NULL,
    open         NUMERIC(20,8) NOT NULL,
    high         NUMERIC(20,8) NOT NULL,
    low          NUMERIC(20,8) NOT NULL,
    close        NUMERIC(20,8) NOT NULL,
    volume       NUMERIC(30,8) NOT NULL,
    CONSTRAINT uq_ohlcv_pk UNIQUE (timestamp, exchange, symbol, timeframe)
);

-- Convert to TimescaleDB hypertable (idempotent)
-- Uses timestamp as partition column with 7-day chunks
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'ohlcv'
    ) THEN
        PERFORM create_hypertable(
            'ohlcv',
            'timestamp',
            chunk_time_interval => 604800000,  -- 7 days in milliseconds
            if_not_exists => TRUE
        );
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_ohlcv_symbol_timeframe_ts
    ON ohlcv (symbol, timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_ohlcv_exchange_symbol
    ON ohlcv (exchange, symbol);

-- Enable compression
ALTER TABLE ohlcv SET (
    timescaledb.compress = true,
    timescaledb.compress_segmentby = 'symbol, timeframe, exchange',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Auto-compress chunks older than 7 days
SELECT add_compression_policy('ohlcv', INTERVAL '7 days', if_not_exists => TRUE);

-- Retain 180 days of data (Phase 3 backtesting requirement)
SELECT add_retention_policy('ohlcv', INTERVAL '180 days', if_not_exists => TRUE);

-- Comment for documentation
COMMENT ON TABLE ohlcv IS 'TimescaleDB hypertable for OHLCV candlestick data. Partitioned by timestamp (7-day chunks). Compressed after 7 days, retained for 180 days.';
