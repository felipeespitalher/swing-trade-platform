"""
TDD stub tests for ohlcv_service module.
All tests are skipped until implementation is complete (Wave 1).
"""
import pytest


@pytest.mark.skip(reason="not implemented")
def test_upsert_batch_idempotent_no_duplicate_errors():
    """upsert_batch called twice with same data does not raise duplicate key errors."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_upsert_batch_persists_all_candles():
    """upsert_batch stores all candles from the input list."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_upsert_batch_uses_on_conflict_do_nothing():
    """upsert_batch uses ON CONFLICT DO NOTHING to handle duplicates gracefully."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_get_candles_returns_sorted_by_timestamp_ascending():
    """get_candles returns candles sorted by timestamp in ascending order."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_get_candles_respects_limit_parameter():
    """get_candles returns at most limit candles."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_get_candles_filters_by_symbol_and_timeframe():
    """get_candles returns only candles matching the given symbol and timeframe."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_get_closes_array_shape_matches_limit():
    """get_closes_array returns np.ndarray with shape (limit,) containing close prices."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_get_closes_array_values_match_close_prices():
    """get_closes_array values correspond to the close price of each candle."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_empty_db_returns_empty_list_for_get_candles():
    """get_candles on empty database returns empty list, not None or error."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_empty_db_returns_empty_array_for_get_closes_array():
    """get_closes_array on empty database returns empty np.ndarray, not None or error."""
    pass
