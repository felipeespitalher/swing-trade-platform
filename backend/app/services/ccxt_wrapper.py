"""
CCXT Exchange Abstraction Layer.

Provides:
- ExchangeAdapter: Abstract base class defining the exchange interface
- BinanceAdapter: Binance implementation using ccxt.async_support
- CCXTWrapper: Factory function for creating exchange adapters

Design principles:
- enableRateLimit=True: CCXT handles rate limiting automatically
- Async context manager: ensures exchange.close() is always called
- Retry logic: handles NetworkError, RateLimitExceeded, ExchangeNotAvailable
- Testnet support: BinanceAdapter can target testnet.binance.vision
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import ccxt.async_support as ccxt
from ccxt.base.errors import (
    NetworkError,
    RateLimitExceeded,
    ExchangeNotAvailable,
    BadSymbol,
    ExchangeError,
)

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds (exponential backoff multiplier)

# Supported timeframes for Phase 2
SUPPORTED_TIMEFRAMES = {"1h", "4h", "1d"}

# Supported symbols for Phase 2
SUPPORTED_SYMBOLS = {"BTC/USDT", "ETH/USDT"}


class ExchangeAdapter(ABC):
    """Abstract base class defining the exchange interface."""

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        since: Optional[int] = None,
    ) -> List[list]:
        """
        Fetch OHLCV candlestick data.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe ('1h', '4h', '1d')
            limit: Number of candles to fetch (max 1000)
            since: Start timestamp in milliseconds (for pagination)

        Returns:
            List of [timestamp_ms, open, high, low, close, volume]
        """
        ...

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> dict:
        """
        Fetch current ticker data.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')

        Returns:
            Dict with 'last', 'bid', 'ask', 'volume', 'timestamp'
        """
        ...

    @abstractmethod
    async def fetch_balance(self) -> dict:
        """
        Fetch account balance.

        Returns:
            Dict with currency balances (free, used, total)
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the exchange connection and release resources."""
        ...

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False


class BinanceAdapter(ExchangeAdapter):
    """
    Binance exchange adapter using ccxt.async_support.

    Supports both production and testnet environments.
    Implements exponential backoff retry for transient errors.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """
        Initialize Binance adapter.

        Args:
            api_key: Binance API key (optional for public endpoints)
            api_secret: Binance API secret (optional for public endpoints)
            testnet: If True, use testnet.binance.vision
            max_retries: Maximum retry attempts for transient errors
        """
        self.max_retries = max_retries
        self.testnet = testnet
        self.exchange_id = "binance"

        exchange_config = {
            "enableRateLimit": True,  # CCXT handles 6,000 weight/min automatically
            "options": {
                "defaultType": "spot",
            },
        }

        if api_key and api_secret:
            exchange_config["apiKey"] = api_key
            exchange_config["secret"] = api_secret

        if testnet:
            exchange_config["urls"] = {
                "api": {
                    "public": "https://testnet.binance.vision/api",
                    "private": "https://testnet.binance.vision/api",
                }
            }

        self._exchange = ccxt.binance(exchange_config)

        logger.info(
            f"BinanceAdapter initialized (testnet={testnet}, "
            f"authenticated={bool(api_key)})"
        )

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        since: Optional[int] = None,
    ) -> List[list]:
        """
        Fetch OHLCV candlestick data with retry logic.

        Returns list of [timestamp_ms, open, high, low, close, volume].
        """
        for attempt in range(self.max_retries + 1):
            try:
                params = {}
                candles = await self._exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=since,
                    limit=limit,
                    params=params,
                )
                logger.debug(
                    f"Fetched {len(candles)} candles for {symbol} {timeframe}"
                )
                return candles

            except RateLimitExceeded as e:
                wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    f"Rate limit exceeded for {symbol} {timeframe}, "
                    f"attempt {attempt + 1}/{self.max_retries + 1}, "
                    f"waiting {wait_time:.1f}s: {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except (NetworkError, ExchangeNotAvailable) as e:
                wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    f"Network error for {symbol} {timeframe}, "
                    f"attempt {attempt + 1}/{self.max_retries + 1}, "
                    f"waiting {wait_time:.1f}s: {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except BadSymbol as e:
                logger.error(f"Invalid symbol {symbol}: {e}")
                raise

            except ExchangeError as e:
                logger.error(f"Exchange error for {symbol} {timeframe}: {e}")
                raise

        # Should not reach here (loop exits via return or raise)
        raise ExchangeError(f"Failed to fetch OHLCV after {self.max_retries} retries")

    async def fetch_ticker(self, symbol: str) -> dict:
        """Fetch current ticker data with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                ticker = await self._exchange.fetch_ticker(symbol)
                return ticker

            except RateLimitExceeded as e:
                wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                if attempt < self.max_retries:
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except (NetworkError, ExchangeNotAvailable) as e:
                wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                if attempt < self.max_retries:
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise ExchangeError(f"Failed to fetch ticker after {self.max_retries} retries")

    async def fetch_balance(self) -> dict:
        """Fetch account balance with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                balance = await self._exchange.fetch_balance()
                return balance

            except RateLimitExceeded as e:
                wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                if attempt < self.max_retries:
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except (NetworkError, ExchangeNotAvailable) as e:
                wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                if attempt < self.max_retries:
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise ExchangeError(f"Failed to fetch balance after {self.max_retries} retries")

    async def close(self) -> None:
        """Close the exchange connection."""
        try:
            await self._exchange.close()
            logger.debug("BinanceAdapter exchange connection closed")
        except Exception as e:
            logger.warning(f"Error closing exchange connection: {e}")


def create_exchange_adapter(
    exchange_id: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    testnet: bool = False,
) -> ExchangeAdapter:
    """
    Factory function for creating exchange adapters.

    Args:
        exchange_id: Exchange identifier (e.g., 'binance')
        api_key: Exchange API key
        api_secret: Exchange API secret
        testnet: Use testnet if True

    Returns:
        ExchangeAdapter instance

    Raises:
        ValueError: If exchange_id is not supported
    """
    adapters = {
        "binance": BinanceAdapter,
    }

    adapter_class = adapters.get(exchange_id.lower())
    if not adapter_class:
        supported = ", ".join(adapters.keys())
        raise ValueError(
            f"Unsupported exchange: {exchange_id!r}. Supported: {supported}"
        )

    return adapter_class(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
    )


async def fetch_ohlcv_paginated(
    adapter: ExchangeAdapter,
    symbol: str,
    timeframe: str,
    since_ms: int,
    batch_size: int = 500,
    sleep_between_batches: float = 0.5,
) -> List[list]:
    """
    Fetch historical OHLCV data with pagination.

    Paginates using the 'since' cursor until no more data is returned
    or the current timestamp is reached. Fetches 180 days without
    hitting rate limits due to sleep_between_batches.

    Args:
        adapter: ExchangeAdapter instance
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Candlestick timeframe ('1h', '4h', '1d')
        since_ms: Start timestamp in milliseconds
        batch_size: Candles per request (max 1000)
        sleep_between_batches: Seconds to sleep between paginated requests

    Returns:
        List of all OHLCV candles from since_ms to now
    """
    import time

    all_candles = []
    current_since = since_ms
    now_ms = int(time.time() * 1000)

    logger.info(
        f"Starting paginated fetch for {symbol} {timeframe} "
        f"from {since_ms} to {now_ms}"
    )

    while current_since < now_ms:
        batch = await adapter.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=batch_size,
            since=current_since,
        )

        if not batch:
            logger.debug(f"No more candles returned for {symbol} {timeframe}")
            break

        all_candles.extend(batch)

        # Advance cursor to after last candle
        last_timestamp = batch[-1][0]
        if last_timestamp <= current_since:
            # No progress made, avoid infinite loop
            logger.warning(
                f"Pagination cursor did not advance for {symbol} {timeframe}, stopping"
            )
            break

        current_since = last_timestamp + 1

        logger.debug(
            f"Fetched batch of {len(batch)} candles, "
            f"total: {len(all_candles)}, cursor: {current_since}"
        )

        if len(batch) < batch_size:
            # Last batch (no more data)
            break

        # Polite delay to avoid rate limiting
        await asyncio.sleep(sleep_between_batches)

    logger.info(
        f"Paginated fetch complete: {len(all_candles)} total candles "
        f"for {symbol} {timeframe}"
    )
    return all_candles
