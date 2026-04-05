"""
TDD stub tests for paper_trading_engine module.
All tests are skipped until implementation is complete (Wave 4).
"""
import pytest


@pytest.mark.skip(reason="not implemented")
def test_entry_order_reduces_available_balance():
    """Executing a BUY entry order reduces the portfolio's available balance by the trade cost."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_exit_order_increases_available_balance():
    """Executing a SELL exit order increases the portfolio's available balance by the proceeds."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_slippage_is_applied_to_fill_price():
    """Fill price differs from signal price by the configured slippage percentage."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_slippage_adverse_for_buy_orders():
    """Slippage increases fill price for BUY orders (worse price for buyer)."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_slippage_adverse_for_sell_orders():
    """Slippage decreases fill price for SELL orders (worse price for seller)."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_risk_limit_blocks_oversized_position():
    """Order exceeding max_risk_per_trade_pct of portfolio is rejected."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_risk_limit_allows_compliant_position():
    """Order within max_risk_per_trade_pct of portfolio is accepted and filled."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_stop_and_restart_recovers_state_from_redis():
    """After engine stop and restart, portfolio state is fully recovered from Redis."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_open_position_tracked_in_portfolio():
    """After a BUY fill, the position appears in the portfolio's open positions."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_closed_position_recorded_in_trade_history():
    """After a SELL fill that closes a position, the trade is recorded with PnL."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_pnl_calculated_correctly_on_close():
    """PnL = (exit_price - entry_price) * quantity - fees; correct sign for long trades."""
    pass
