-- Swing Trade Platform - Row-Level Security (RLS) Policies
-- Enables PostgreSQL RLS to enforce multi-tenant data isolation at the database level
--
-- Purpose:
-- - Each user can only see and modify their own data
-- - RLS policies work in conjunction with application-level filters
-- - Defense-in-depth: If app filter is bypassed, database policies prevent data leaks

-- ============================================================================
-- RLS CONTEXT FUNCTIONS
-- ============================================================================

-- Create a simple function to get the current user ID from application context
-- The app must SET LOCAL app.current_user_id before each transaction
CREATE OR REPLACE FUNCTION current_user_id() RETURNS UUID AS $$
BEGIN
  RETURN current_setting('app.current_user_id')::UUID;
EXCEPTION WHEN OTHERS THEN
  RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION current_user_id() IS
  'Get the current user ID from application context (set via SET LOCAL app.current_user_id)';

-- ============================================================================
-- ENABLE RLS ON ALL USER-OWNED TABLES
-- ============================================================================

-- USERS table: Users can only see/modify themselves
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- EXCHANGE_KEYS table: Users can only access their own keys
ALTER TABLE exchange_keys ENABLE ROW LEVEL SECURITY;

-- STRATEGIES table: Users can only access their own strategies
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;

-- TRADES table: Users can only access their own trades
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;

-- AUDIT_LOGS table: Users can only access their own logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- USERS TABLE RLS POLICIES
-- ============================================================================
-- Each user only sees themselves. Cannot edit/delete others.

CREATE POLICY users_isolation_select ON users
  FOR SELECT
  USING (id = current_user_id());

CREATE POLICY users_isolation_update ON users
  FOR UPDATE
  USING (id = current_user_id())
  WITH CHECK (id = current_user_id());

CREATE POLICY users_isolation_delete ON users
  FOR DELETE
  USING (id = current_user_id());

-- INSERT policy: Users can only create records for themselves
CREATE POLICY users_isolation_insert ON users
  FOR INSERT
  WITH CHECK (id = current_user_id());

COMMENT ON POLICY users_isolation_select ON users IS
  'Users can only SELECT their own user record';
COMMENT ON POLICY users_isolation_insert ON users IS
  'Users can only INSERT (create account for) themselves';
COMMENT ON POLICY users_isolation_update ON users IS
  'Users can only UPDATE their own user record';
COMMENT ON POLICY users_isolation_delete ON users IS
  'Users can only DELETE their own user record';

-- ============================================================================
-- EXCHANGE_KEYS TABLE RLS POLICIES
-- ============================================================================
-- Each user only sees and manages their own exchange keys.

CREATE POLICY exchange_keys_select ON exchange_keys
  FOR SELECT
  USING (user_id = current_user_id());

CREATE POLICY exchange_keys_insert ON exchange_keys
  FOR INSERT
  WITH CHECK (user_id = current_user_id());

CREATE POLICY exchange_keys_update ON exchange_keys
  FOR UPDATE
  USING (user_id = current_user_id())
  WITH CHECK (user_id = current_user_id());

CREATE POLICY exchange_keys_delete ON exchange_keys
  FOR DELETE
  USING (user_id = current_user_id());

COMMENT ON POLICY exchange_keys_select ON exchange_keys IS
  'Users can only SELECT exchange keys they own (user_id matches)';
COMMENT ON POLICY exchange_keys_insert ON exchange_keys IS
  'Users can only INSERT exchange keys for themselves';
COMMENT ON POLICY exchange_keys_update ON exchange_keys IS
  'Users can only UPDATE their own exchange keys';
COMMENT ON POLICY exchange_keys_delete ON exchange_keys IS
  'Users can only DELETE their own exchange keys';

-- ============================================================================
-- STRATEGIES TABLE RLS POLICIES
-- ============================================================================
-- Each user only sees and manages their own strategies.

CREATE POLICY strategies_select ON strategies
  FOR SELECT
  USING (user_id = current_user_id());

CREATE POLICY strategies_insert ON strategies
  FOR INSERT
  WITH CHECK (user_id = current_user_id());

CREATE POLICY strategies_update ON strategies
  FOR UPDATE
  USING (user_id = current_user_id())
  WITH CHECK (user_id = current_user_id());

CREATE POLICY strategies_delete ON strategies
  FOR DELETE
  USING (user_id = current_user_id());

COMMENT ON POLICY strategies_select ON strategies IS
  'Users can only SELECT strategies they own';
COMMENT ON POLICY strategies_insert ON strategies IS
  'Users can only INSERT strategies for themselves';
COMMENT ON POLICY strategies_update ON strategies IS
  'Users can only UPDATE their own strategies';
COMMENT ON POLICY strategies_delete ON strategies IS
  'Users can only DELETE their own strategies';

-- ============================================================================
-- TRADES TABLE RLS POLICIES
-- ============================================================================
-- Trades reference strategies which reference users.
-- Need to join through strategy to get user_id for RLS.

-- First, we need a function to get the user_id from a trade via its strategy
CREATE OR REPLACE FUNCTION get_trade_user_id(trade_id UUID) RETURNS UUID AS $$
  SELECT COALESCE(s.user_id, NULL)
  FROM trades t
  LEFT JOIN strategies s ON t.strategy_id = s.id
  WHERE t.id = trade_id;
$$ LANGUAGE SQL;

CREATE POLICY trades_select ON trades
  FOR SELECT
  USING (
    -- Allow access if strategy belongs to current user
    COALESCE(
      (SELECT user_id FROM strategies WHERE id = strategy_id),
      NULL
    ) = current_user_id()
  );

CREATE POLICY trades_insert ON trades
  FOR INSERT
  WITH CHECK (
    -- Can only insert trades for strategies we own
    COALESCE(
      (SELECT user_id FROM strategies WHERE id = strategy_id),
      NULL
    ) = current_user_id()
  );

CREATE POLICY trades_update ON trades
  FOR UPDATE
  USING (
    COALESCE(
      (SELECT user_id FROM strategies WHERE id = strategy_id),
      NULL
    ) = current_user_id()
  )
  WITH CHECK (
    COALESCE(
      (SELECT user_id FROM strategies WHERE id = strategy_id),
      NULL
    ) = current_user_id()
  );

CREATE POLICY trades_delete ON trades
  FOR DELETE
  USING (
    COALESCE(
      (SELECT user_id FROM strategies WHERE id = strategy_id),
      NULL
    ) = current_user_id()
  );

COMMENT ON POLICY trades_select ON trades IS
  'Users can only SELECT trades from their own strategies';
COMMENT ON POLICY trades_insert ON trades IS
  'Users can only INSERT trades for their own strategies';
COMMENT ON POLICY trades_update ON trades IS
  'Users can only UPDATE trades from their own strategies';
COMMENT ON POLICY trades_delete ON trades IS
  'Users can only DELETE trades from their own strategies';

-- ============================================================================
-- AUDIT_LOGS TABLE RLS POLICIES
-- ============================================================================
-- Users can only see logs of their own actions.

CREATE POLICY audit_logs_select ON audit_logs
  FOR SELECT
  USING (user_id = current_user_id());

-- INSERT: Application inserts logs for the current user
CREATE POLICY audit_logs_insert ON audit_logs
  FOR INSERT
  WITH CHECK (user_id = current_user_id());

-- NOTE: audit_logs is append-only, so no UPDATE or DELETE policies
-- If needed in future, add them here

COMMENT ON POLICY audit_logs_select ON audit_logs IS
  'Users can only SELECT their own audit logs';
COMMENT ON POLICY audit_logs_insert ON audit_logs IS
  'Application can only INSERT audit logs for the current user';

-- ============================================================================
-- GRANT PRIVILEGES
-- ============================================================================
-- Ensure the application user has appropriate privileges
-- (Adjust app_user if your app role has a different name)

-- If using a specific application role, uncomment and modify:
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- These are for testing RLS policies:
--
-- SET LOCAL app.current_user_id = 'user-id-uuid';
-- SELECT * FROM users;  -- Should see only the user
-- SELECT * FROM exchange_keys;  -- Should see only user's keys
--
-- RESET app.current_user_id;
-- SELECT * FROM users;  -- Should see nothing (if RLS is enforced)

COMMENT ON SCHEMA public IS 'Public schema with RLS enabled for multi-tenant isolation';
