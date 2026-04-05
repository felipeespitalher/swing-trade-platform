"""
Unit tests for OHLCVService — persistence and query operations.
Uses SQLite test database via conftest.py `db` fixture.
"""
import pytest
import numpy as np
from app.services.ohlcv_service import OHLCVService
from app.models.ohlcv import OHLCV

# Sample OHLCV data in CCXT format: [timestamp_ms, open, high, low, close, volume]
SAMPLE_CANDLES = [
    [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 1250.5],
    [1704070800000, 42300.0, 43000.0, 42200.0, 42800.0, 980.2],
    [1704074400000, 42800.0, 43200.0, 42600.0, 43100.0, 1100.0],
]

EXCHANGE = "binance"
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"


def test_upsert_batch_inserts_candles(db):
    """upsert_batch stores all candles from the input list and count_candles returns 3."""
    inserted = OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, TIMEFRAME)

    assert inserted == 3
    count = OHLCVService.count_candles(db, SYMBOL, TIMEFRAME, EXCHANGE)
    assert count == 3


def test_upsert_batch_idempotent(db):
    """upsert_batch called twice with same data does not create duplicates."""
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, TIMEFRAME)
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, TIMEFRAME)

    count = OHLCVService.count_candles(db, SYMBOL, TIMEFRAME, EXCHANGE)
    assert count == 3


def test_upsert_batch_empty_list(db):
    """upsert_batch with empty list returns 0 and does not raise any error."""
    result = OHLCVService.upsert_batch(db, [], EXCHANGE, SYMBOL, TIMEFRAME)

    assert result == 0
    count = OHLCVService.count_candles(db, SYMBOL, TIMEFRAME, EXCHANGE)
    assert count == 0


def test_get_candles_returns_sorted_ascending(db):
    """get_candles returns candles sorted ascending by timestamp even when inserted in reverse."""
    reversed_candles = list(reversed(SAMPLE_CANDLES))
    OHLCVService.upsert_batch(db, reversed_candles, EXCHANGE, SYMBOL, TIMEFRAME)

    candles = OHLCVService.get_candles(db, SYMBOL, TIMEFRAME, EXCHANGE)

    timestamps = [c[0] for c in candles]
    assert timestamps == sorted(timestamps), "Candles must be sorted ascending by timestamp"
    assert timestamps[0] == SAMPLE_CANDLES[0][0]
    assert timestamps[-1] == SAMPLE_CANDLES[-1][0]


def test_get_candles_respects_limit(db):
    """get_candles with limit=2 returns only 2 candles from a set of 3."""
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, TIMEFRAME)

    candles = OHLCVService.get_candles(db, SYMBOL, TIMEFRAME, EXCHANGE, limit=2)

    assert len(candles) == 2


def test_get_candles_filters_by_symbol(db):
    """get_candles('BTC/USDT', ...) returns only BTC candles, not ETH candles."""
    eth_candles = [
        [1704067200000, 2200.0, 2250.0, 2180.0, 2230.0, 5000.0],
        [1704070800000, 2230.0, 2280.0, 2210.0, 2260.0, 4800.0],
    ]
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, "BTC/USDT", TIMEFRAME)
    OHLCVService.upsert_batch(db, eth_candles, EXCHANGE, "ETH/USDT", TIMEFRAME)

    btc_candles = OHLCVService.get_candles(db, "BTC/USDT", TIMEFRAME, EXCHANGE)
    eth_result = OHLCVService.get_candles(db, "ETH/USDT", TIMEFRAME, EXCHANGE)

    assert len(btc_candles) == 3
    assert len(eth_result) == 2
    # BTC close prices should not match ETH close prices
    btc_closes = {c[4] for c in btc_candles}
    eth_closes = {c[4] for c in eth_result}
    assert btc_closes.isdisjoint(eth_closes)


def test_get_candles_filters_by_timeframe(db):
    """get_candles filters by timeframe so 1h and 4h candles are returned separately."""
    candles_4h = [
        [1704067200000, 42000.0, 43500.0, 41500.0, 43200.0, 5000.0],
        [1704081600000, 43200.0, 44000.0, 43000.0, 43800.0, 4500.0],
    ]
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, "1h")
    OHLCVService.upsert_batch(db, candles_4h, EXCHANGE, SYMBOL, "4h")

    candles_1h = OHLCVService.get_candles(db, SYMBOL, "1h", EXCHANGE)
    candles_4h_result = OHLCVService.get_candles(db, SYMBOL, "4h", EXCHANGE)

    assert len(candles_1h) == 3
    assert len(candles_4h_result) == 2


def test_get_candles_since_ms_filter(db):
    """get_candles with since_ms set to second candle timestamp returns only candles 2 and 3."""
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, TIMEFRAME)

    second_candle_ts = SAMPLE_CANDLES[1][0]
    candles = OHLCVService.get_candles(
        db, SYMBOL, TIMEFRAME, EXCHANGE, since_ms=second_candle_ts
    )

    assert len(candles) == 2
    assert candles[0][0] == second_candle_ts
    assert candles[1][0] == SAMPLE_CANDLES[2][0]


def test_get_candles_empty_db_returns_empty_list(db):
    """get_candles on empty database returns [] not None or an error."""
    candles = OHLCVService.get_candles(db, SYMBOL, TIMEFRAME, EXCHANGE)

    assert candles == []
    assert isinstance(candles, list)


def test_get_closes_array_shape(db):
    """get_closes_array returns a float64 ndarray with shape (3,) after inserting 3 candles."""
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, TIMEFRAME)

    closes = OHLCVService.get_closes_array(db, SYMBOL, TIMEFRAME, EXCHANGE)

    assert isinstance(closes, np.ndarray)
    assert closes.dtype == np.float64
    assert closes.shape == (3,)


def test_get_closes_array_values_correct(db):
    """get_closes_array returns close prices in the same order as inserted candles."""
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, TIMEFRAME)

    closes = OHLCVService.get_closes_array(db, SYMBOL, TIMEFRAME, EXCHANGE)

    expected_closes = [c[4] for c in SAMPLE_CANDLES]
    np.testing.assert_allclose(closes, expected_closes, rtol=1e-6)


def test_get_closes_array_empty_db_returns_empty(db):
    """get_closes_array on empty database returns np.array([], dtype=float64) with shape (0,)."""
    closes = OHLCVService.get_closes_array(db, SYMBOL, TIMEFRAME, EXCHANGE)

    assert isinstance(closes, np.ndarray)
    assert closes.dtype == np.float64
    assert closes.shape == (0,)
    assert len(closes) == 0


def test_count_candles_returns_correct_count(db):
    """count_candles returns 3 after inserting 3 candles."""
    OHLCVService.upsert_batch(db, SAMPLE_CANDLES, EXCHANGE, SYMBOL, TIMEFRAME)

    count = OHLCVService.count_candles(db, SYMBOL, TIMEFRAME, EXCHANGE)

    assert count == 3


def test_upsert_batch_different_exchanges_not_duplicate(db):
    """Same symbol/timeframe/timestamp for 'binance' and 'bybit' creates 2 separate rows."""
    single_candle = [SAMPLE_CANDLES[0]]
    OHLCVService.upsert_batch(db, single_candle, "binance", SYMBOL, TIMEFRAME)
    OHLCVService.upsert_batch(db, single_candle, "bybit", SYMBOL, TIMEFRAME)

    binance_count = OHLCVService.count_candles(db, SYMBOL, TIMEFRAME, "binance")
    bybit_count = OHLCVService.count_candles(db, SYMBOL, TIMEFRAME, "bybit")

    assert binance_count == 1
    assert bybit_count == 1

    total = db.query(OHLCV).count()
    assert total == 2
