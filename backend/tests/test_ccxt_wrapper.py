"""
TDD stub tests for ccxt_wrapper module.
All tests are skipped until implementation is complete (Wave 1).
"""
import pytest


@pytest.mark.skip(reason="not implemented")
def test_fetch_ohlcv_returns_expected_candle_count():
    """fetch_ohlcv('BTC/USDT', '1h', limit=100) returns list of 100 candles."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_fetch_ohlcv_candle_fields_are_complete():
    """Each candle has timestamp, open, high, low, close, volume fields."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_fetch_ohlcv_pagination_fetches_180_days():
    """fetch_ohlcv_paginated paginates with since cursor to cover 180 days."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_fetch_ohlcv_pagination_does_not_hit_rate_limit():
    """Paginated fetch respects rate limit delays between requests."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_retry_on_network_error():
    """NetworkError triggers exponential backoff retry up to max attempts."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_retry_exhausted_raises_after_max_attempts():
    """After max retry attempts, the original exception is re-raised."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_rate_limit_exceeded_triggers_backoff():
    """RateLimitExceeded exception triggers wait and retry."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_exchange_not_available_triggers_backoff():
    """ExchangeNotAvailable exception triggers wait and retry."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_close_called_on_context_manager_exit():
    """exchange.close() is always called when async context manager exits normally."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_close_called_on_context_manager_exception():
    """exchange.close() is always called when async context manager exits via exception."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_testnet_support_uses_testnet_url():
    """When testnet=True, adapter connects to testnet.binance.vision endpoint."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_enable_rate_limit_is_true():
    """Adapter always initializes CCXT exchange with enableRateLimit=True."""
    pass
