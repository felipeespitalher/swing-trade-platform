"""
TDD stub tests for market data API endpoints.
All tests are skipped until implementation is complete (Wave 1/3).
"""
import pytest


@pytest.mark.skip(reason="not implemented")
def test_ticker_returns_current_price():
    """GET /market-data/ticker?symbol=BTC/USDT returns last price for the symbol."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_ticker_price_is_numeric():
    """Ticker response price field is a positive numeric value."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_ticker_returns_404_for_unknown_symbol():
    """GET /market-data/ticker for an unsupported symbol returns 404."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_ohlcv_returns_candle_list():
    """GET /market-data/ohlcv returns list of OHLCV candles for symbol and timeframe."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_ohlcv_candle_count_respects_limit_param():
    """GET /market-data/ohlcv?limit=50 returns at most 50 candles."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_ohlcv_candles_sorted_ascending_by_timestamp():
    """OHLCV response candles are sorted in ascending chronological order."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_ohlcv_returns_404_for_unknown_symbol():
    """GET /market-data/ohlcv for an unsupported symbol returns 404."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_balance_returns_testnet_balances():
    """GET /market-data/balance returns asset balances from Binance Testnet."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_balance_requires_authenticated_user():
    """GET /market-data/balance returns 401 for unauthenticated requests."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_balance_response_includes_usdt_balance():
    """Balance response includes USDT balance as primary trading currency."""
    pass
