-- Swing Trade Platform - Portfolio Management + B3 Exchange Support
-- V5: Portfolios table, portfolio_id on strategies, label on exchange_keys

-- ============================================================================
-- ADD LABEL TO EXCHANGE_KEYS
-- ============================================================================
ALTER TABLE exchange_keys ADD COLUMN IF NOT EXISTS label VARCHAR(100);

-- Backfill label with exchange name for existing records
UPDATE exchange_keys SET label = exchange WHERE label IS NULL;

-- ============================================================================
-- PORTFOLIOS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    capital_allocation NUMERIC(20, 2) NOT NULL DEFAULT 0,
    risk_profile VARCHAR(50) NOT NULL DEFAULT 'moderado',
    mode VARCHAR(20) NOT NULL DEFAULT 'paper',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK (mode IN ('paper', 'live')),
    CHECK (risk_profile IN ('conservador', 'moderado', 'agressivo'))
);

CREATE INDEX IF NOT EXISTS idx_portfolios_user ON portfolios(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_user_active ON portfolios(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_portfolios_mode ON portfolios(user_id, mode);

-- ============================================================================
-- ADD PORTFOLIO_ID TO STRATEGIES
-- ============================================================================
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS portfolio_id UUID REFERENCES portfolios(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_strategies_portfolio ON strategies(portfolio_id);

-- ============================================================================
-- RLS FOR PORTFOLIOS
-- ============================================================================
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;

CREATE POLICY portfolios_select ON portfolios
    FOR SELECT USING (user_id = current_user_id());

CREATE POLICY portfolios_insert ON portfolios
    FOR INSERT WITH CHECK (user_id = current_user_id());

CREATE POLICY portfolios_update ON portfolios
    FOR UPDATE USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());

CREATE POLICY portfolios_delete ON portfolios
    FOR DELETE USING (user_id = current_user_id());

COMMENT ON TABLE portfolios IS 'User portfolios grouping strategies with paper/live mode';
COMMENT ON COLUMN portfolios.mode IS 'paper = simulation mode, live = real money trading';
COMMENT ON COLUMN strategies.portfolio_id IS 'Optional portfolio grouping for this strategy';
COMMENT ON COLUMN exchange_keys.label IS 'User-defined label for this exchange connection';
