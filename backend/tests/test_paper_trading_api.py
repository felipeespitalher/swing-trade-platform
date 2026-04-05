"""
TDD stub tests for paper trading API endpoints.
All tests are skipped until implementation is complete (Wave 4).
"""
import pytest


@pytest.mark.skip(reason="not implemented")
def test_start_session_returns_201_with_session_id():
    """POST /paper-trading/sessions with valid strategy_id returns 201 and session ID."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_start_session_initializes_paper_balance():
    """Started session has initial_balance set from request and current_balance equal to initial."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_start_session_rejects_already_active_session():
    """Starting a second session for a strategy already running returns 409 Conflict."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_stop_session_sets_status_to_stopped():
    """POST /paper-trading/sessions/{id}/stop sets session status to stopped."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_stop_session_records_final_balance():
    """Stopping a session persists the final portfolio balance."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_status_returns_current_portfolio_snapshot():
    """GET /paper-trading/sessions/{id}/status returns open positions and current balance."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_status_returns_404_for_nonexistent_session():
    """GET /paper-trading/sessions/{id}/status returns 404 for unknown session ID."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_trade_history_returns_only_own_trades():
    """GET /paper-trading/sessions/{id}/trades returns only trades from this session."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_trade_history_isolated_between_users():
    """User A cannot access trade history from User B's session; returns 404."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_trade_history_includes_pnl_per_trade():
    """Each trade record in history includes realized PnL value."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_unauthenticated_request_returns_401():
    """All paper trading endpoints return 401 without a valid auth token."""
    pass
