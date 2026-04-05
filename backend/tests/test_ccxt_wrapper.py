"""
Unit tests for CCXT wrapper (BinanceAdapter, ExchangeAdapter, fetch_ohlcv_paginated).
All exchange calls are mocked — no real network requests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ccxt.base.errors import NetworkError, RateLimitExceeded, ExchangeNotAvailable, BadSymbol

from app.services.ccxt_wrapper import (
    BinanceAdapter,
    ExchangeAdapter,
    create_exchange_adapter,
    fetch_ohlcv_paginated,
    SUPPORTED_TIMEFRAMES,
    SUPPORTED_SYMBOLS,
)

# Sample OHLCV fixture data (CCXT format: [timestamp_ms, open, high, low, close, volume])
SAMPLE_CANDLES = [
    [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 1250.5],
    [1704070800000, 42300.0, 43000.0, 42200.0, 42800.0, 980.2],
    [1704074400000, 42800.0, 43200.0, 42600.0, 43100.0, 1100.0],
]

SAMPLE_TICKER = {
    "symbol": "BTC/USDT",
    "last": 42300.0,
    "bid": 42280.0,
    "ask": 42320.0,
    "volume": 15000.0,
    "timestamp": 1704067200000,
}

SAMPLE_BALANCE = {
    "USDT": {"free": 10000.0, "used": 0.0, "total": 10000.0},
    "BTC": {"free": 0.5, "used": 0.0, "total": 0.5},
}


def _make_mock_exchange():
    """Create a fully async-mocked ccxt exchange object."""
    mock = MagicMock()
    mock.fetch_ohlcv = AsyncMock()
    mock.fetch_ticker = AsyncMock()
    mock.fetch_balance = AsyncMock()
    mock.close = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# fetch_ohlcv tests
# ---------------------------------------------------------------------------


async def test_fetch_ohlcv_returns_candles(mocker):
    """fetch_ohlcv returns the candle list from the underlying exchange."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter()
    mock_exchange = _make_mock_exchange()
    mock_exchange.fetch_ohlcv.return_value = SAMPLE_CANDLES
    adapter._exchange = mock_exchange

    result = await adapter.fetch_ohlcv("BTC/USDT", "1h", limit=3)

    assert result == SAMPLE_CANDLES
    mock_exchange.fetch_ohlcv.assert_awaited_once()


async def test_fetch_ohlcv_with_since_parameter(mocker):
    """fetch_ohlcv passes the 'since' timestamp to the exchange call."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter()
    mock_exchange = _make_mock_exchange()
    mock_exchange.fetch_ohlcv.return_value = SAMPLE_CANDLES
    adapter._exchange = mock_exchange

    since_ts = 1704067200000
    await adapter.fetch_ohlcv("BTC/USDT", "1h", since=since_ts)

    call_kwargs = mock_exchange.fetch_ohlcv.call_args
    assert call_kwargs.kwargs.get("since") == since_ts or (
        len(call_kwargs.args) >= 3 and call_kwargs.args[2] == since_ts
    )


async def test_fetch_ohlcv_retries_on_network_error(mocker):
    """NetworkError causes retries; succeeds on the third attempt."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter(max_retries=3)
    mock_exchange = _make_mock_exchange()
    mock_exchange.fetch_ohlcv.side_effect = [
        NetworkError("timeout"),
        NetworkError("timeout"),
        SAMPLE_CANDLES,
    ]
    adapter._exchange = mock_exchange

    result = await adapter.fetch_ohlcv("BTC/USDT", "1h")

    assert result == SAMPLE_CANDLES
    assert mock_exchange.fetch_ohlcv.await_count == 3


async def test_fetch_ohlcv_raises_after_max_retries(mocker):
    """NetworkError propagates after max_retries+1 total attempts are exhausted."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    max_retries = 2
    adapter = BinanceAdapter(max_retries=max_retries)
    mock_exchange = _make_mock_exchange()
    mock_exchange.fetch_ohlcv.side_effect = NetworkError("persistent error")
    adapter._exchange = mock_exchange

    with pytest.raises(NetworkError):
        await adapter.fetch_ohlcv("BTC/USDT", "1h")

    # max_retries=2 means 3 total attempts (attempts 0, 1, 2)
    assert mock_exchange.fetch_ohlcv.await_count == max_retries + 1


async def test_fetch_ohlcv_retries_on_rate_limit_exceeded(mocker):
    """RateLimitExceeded triggers a retry and succeeds on the second call."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter(max_retries=3)
    mock_exchange = _make_mock_exchange()
    mock_exchange.fetch_ohlcv.side_effect = [
        RateLimitExceeded("rate limit"),
        SAMPLE_CANDLES,
    ]
    adapter._exchange = mock_exchange

    result = await adapter.fetch_ohlcv("BTC/USDT", "1h")

    assert result == SAMPLE_CANDLES
    assert mock_exchange.fetch_ohlcv.await_count == 2


async def test_fetch_ohlcv_raises_on_bad_symbol(mocker):
    """BadSymbol is not a transient error — it raises immediately without retrying."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter(max_retries=3)
    mock_exchange = _make_mock_exchange()
    mock_exchange.fetch_ohlcv.side_effect = BadSymbol("INVALID/PAIR")
    adapter._exchange = mock_exchange

    with pytest.raises(BadSymbol):
        await adapter.fetch_ohlcv("INVALID/PAIR", "1h")

    # No retries — only one attempt
    assert mock_exchange.fetch_ohlcv.await_count == 1


# ---------------------------------------------------------------------------
# fetch_ticker / fetch_balance tests
# ---------------------------------------------------------------------------


async def test_fetch_ticker_returns_data(mocker):
    """fetch_ticker returns the ticker dict from the underlying exchange."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter()
    mock_exchange = _make_mock_exchange()
    mock_exchange.fetch_ticker.return_value = SAMPLE_TICKER
    adapter._exchange = mock_exchange

    result = await adapter.fetch_ticker("BTC/USDT")

    assert result == SAMPLE_TICKER
    mock_exchange.fetch_ticker.assert_awaited_once_with("BTC/USDT")


async def test_fetch_balance_returns_data(mocker):
    """fetch_balance returns the balance dict from the underlying exchange."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter()
    mock_exchange = _make_mock_exchange()
    mock_exchange.fetch_balance.return_value = SAMPLE_BALANCE
    adapter._exchange = mock_exchange

    result = await adapter.fetch_balance()

    assert result == SAMPLE_BALANCE
    mock_exchange.fetch_balance.assert_awaited_once()


# ---------------------------------------------------------------------------
# Context manager / close() tests
# ---------------------------------------------------------------------------


async def test_close_called_on_context_manager_exit(mocker):
    """exchange.close() is called when exiting the async context manager normally."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter()
    mock_exchange = _make_mock_exchange()
    adapter._exchange = mock_exchange

    async with adapter:
        pass

    mock_exchange.close.assert_awaited_once()


async def test_close_called_even_on_exception(mocker):
    """exchange.close() is called even when the async with block raises an exception."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)
    adapter = BinanceAdapter()
    mock_exchange = _make_mock_exchange()
    adapter._exchange = mock_exchange

    with pytest.raises(RuntimeError):
        async with adapter:
            raise RuntimeError("something went wrong inside the block")

    mock_exchange.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Testnet / configuration tests
# ---------------------------------------------------------------------------


async def test_testnet_url_configured(mocker):
    """When testnet=True, the exchange is configured with the testnet base URL."""
    mock_binance_cls = MagicMock(return_value=_make_mock_exchange())
    mocker.patch("ccxt.async_support.binance", mock_binance_cls)

    BinanceAdapter(testnet=True)

    call_args = mock_binance_cls.call_args
    config = call_args[0][0] if call_args[0] else call_args.kwargs
    # Config may be passed as first positional or keyword — normalise
    if isinstance(config, dict):
        exchange_config = config
    else:
        exchange_config = call_args[0][0]

    assert "urls" in exchange_config
    api_urls = exchange_config["urls"]["api"]
    assert "testnet.binance.vision" in api_urls["public"]
    assert "testnet.binance.vision" in api_urls["private"]


# ---------------------------------------------------------------------------
# create_exchange_adapter factory tests
# ---------------------------------------------------------------------------


def test_create_exchange_adapter_binance(mocker):
    """create_exchange_adapter('binance') returns a BinanceAdapter instance."""
    mocker.patch("ccxt.async_support.binance", return_value=_make_mock_exchange())
    adapter = create_exchange_adapter("binance")
    assert isinstance(adapter, BinanceAdapter)


def test_create_exchange_adapter_unsupported():
    """create_exchange_adapter with an unsupported exchange raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported exchange"):
        create_exchange_adapter("kraken")


# ---------------------------------------------------------------------------
# fetch_ohlcv_paginated tests
# ---------------------------------------------------------------------------


async def test_fetch_ohlcv_paginated_returns_all_candles(mocker):
    """fetch_ohlcv_paginated combines multiple batches into a single list."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)

    # Two full batches of 3 candles each, then an empty batch to stop
    batch_1 = [
        [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 1250.5],
        [1704070800000, 42300.0, 43000.0, 42200.0, 42800.0, 980.2],
        [1704074400000, 42800.0, 43200.0, 42600.0, 43100.0, 1100.0],
    ]
    batch_2 = [
        [1704078000000, 43100.0, 43500.0, 43000.0, 43400.0, 900.0],
        [1704081600000, 43400.0, 43600.0, 43300.0, 43550.0, 850.0],
        [1704085200000, 43550.0, 43800.0, 43450.0, 43700.0, 1050.0],
    ]

    mock_adapter = MagicMock(spec=ExchangeAdapter)
    # Each batch has exactly batch_size=3 candles, then empty to terminate
    mock_adapter.fetch_ohlcv = AsyncMock(side_effect=[batch_1, batch_2, []])

    result = await fetch_ohlcv_paginated(
        adapter=mock_adapter,
        symbol="BTC/USDT",
        timeframe="1h",
        since_ms=1704067200000,
        batch_size=3,
        sleep_between_batches=0,
    )

    assert len(result) == 6
    assert result[:3] == batch_1
    assert result[3:] == batch_2


async def test_fetch_ohlcv_paginated_stops_on_empty_batch(mocker):
    """fetch_ohlcv_paginated stops immediately when the first batch is empty."""
    mocker.patch("app.services.ccxt_wrapper.asyncio.sleep", new_callable=AsyncMock)

    mock_adapter = MagicMock(spec=ExchangeAdapter)
    mock_adapter.fetch_ohlcv = AsyncMock(return_value=[])

    result = await fetch_ohlcv_paginated(
        adapter=mock_adapter,
        symbol="BTC/USDT",
        timeframe="1h",
        since_ms=1704067200000,
        batch_size=500,
        sleep_between_batches=0,
    )

    assert result == []
    mock_adapter.fetch_ohlcv.assert_awaited_once()
