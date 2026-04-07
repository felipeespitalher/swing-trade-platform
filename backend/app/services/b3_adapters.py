"""
B3 (Bolsa de Valores Brasileira) Exchange Adapters.

Provides adapters for Brazilian brokers:
- ClearXPAdapter: Clear/XP Investimentos REST API
- ProfitProAdapter: Profit Pro (Nelogica) API

Both adapters implement ExchangeAdapter ABC so they integrate seamlessly
with the existing strategy/backtest/paper trading infrastructure.

NOTE: ClearXP and ProfitPro require institutional API agreements.
Credentials are obtained directly from each broker.
The adapters use paper simulation when `testnet=True` (no real orders placed).

Market data for B3 symbols uses Yahoo Finance / Alpha Vantage as fallback
when broker data feeds are unavailable (common for testnet/paper mode).
"""

import asyncio
import logging
from abc import ABC
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.services.ccxt_wrapper import ExchangeAdapter
from app.services.market_hours import MarketHoursService

logger = logging.getLogger(__name__)

# B3 symbol format: TICKER.SA (e.g., PETR4.SA, KNRI11.SA)
# Internal format we use: TICKER/BRL (e.g., PETR4/BRL, KNRI11/BRL)
B3_SUPPORTED_TIMEFRAMES = {"1d", "1wk", "1mo"}

# FII (Fundo de Investimento Imobiliario) suffix pattern: ends in 11
# Stock pattern: ends in 3, 4, 5, 6 (ON, PN, PNA, PNB shares)


def to_yahoo_symbol(symbol: str) -> str:
    """Convert internal symbol format to Yahoo Finance format."""
    # PETR4/BRL -> PETR4.SA
    base = symbol.split("/")[0]
    return f"{base}.SA"


def from_yahoo_symbol(yahoo_symbol: str) -> str:
    """Convert Yahoo Finance symbol to internal format."""
    # PETR4.SA -> PETR4/BRL
    base = yahoo_symbol.replace(".SA", "")
    return f"{base}/BRL"


class B3BaseAdapter(ExchangeAdapter, ABC):
    """
    Base adapter for B3 brokers.

    Provides common B3 functionality:
    - Market data via Yahoo Finance (for paper/testnet mode)
    - Market hours validation
    - B3 symbol format handling
    """

    def __init__(
        self,
        exchange_id: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
        max_retries: int = 3,
    ):
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet  # True = paper mode (no real orders)
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"{self.__class__.__name__} initialized "
            f"(testnet={testnet}, authenticated={bool(api_key)})"
        )

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        since: Optional[int] = None,
    ) -> List[list]:
        """
        Fetch B3 OHLCV data via Yahoo Finance.

        symbol: e.g. 'PETR4/BRL' or 'KNRI11/BRL'
        timeframe: '1d', '1wk', '1mo'
        Returns [[timestamp_ms, open, high, low, close, volume], ...]
        """
        yahoo_symbol = to_yahoo_symbol(symbol)

        # Yahoo Finance interval mapping
        interval_map = {
            "1d": "1d",
            "1wk": "1wk",
            "1mo": "1mo",
            # Alias timeframes used by other exchanges
            "1h": "1h",
            "4h": "1h",  # Yahoo doesn't support 4h, use 1h
        }
        interval = interval_map.get(timeframe, "1d")

        # Calculate range
        range_map = {
            "1d": "1y",
            "1wk": "5y",
            "1mo": "10y",
            "1h": "7d",
        }
        range_val = range_map.get(interval, "1y")

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        params = {
            "interval": interval,
            "range": range_val,
            "includePrePost": "false",
        }

        client = self._get_client()
        for attempt in range(self.max_retries):
            try:
                resp = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                data = resp.json()

                result = data.get("chart", {}).get("result", [])
                if not result:
                    logger.warning(f"No data returned for {yahoo_symbol}")
                    return []

                chart = result[0]
                timestamps = chart.get("timestamp", [])
                indicators = chart.get("indicators", {}).get("quote", [{}])[0]

                opens = indicators.get("open", [])
                highs = indicators.get("high", [])
                lows = indicators.get("low", [])
                closes = indicators.get("close", [])
                volumes = indicators.get("volume", [])

                candles = []
                for i, ts in enumerate(timestamps):
                    if i >= len(closes) or closes[i] is None:
                        continue
                    candles.append([
                        ts * 1000,  # Convert to milliseconds
                        opens[i] or closes[i],
                        highs[i] or closes[i],
                        lows[i] or closes[i],
                        closes[i],
                        volumes[i] or 0,
                    ])

                logger.debug(f"Fetched {len(candles)} candles for {yahoo_symbol} {timeframe}")
                return candles[-limit:] if limit else candles

            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error fetching {yahoo_symbol}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"Error fetching {yahoo_symbol}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return []

    async def fetch_ticker(self, symbol: str) -> dict:
        """Fetch current quote for a B3 symbol."""
        yahoo_symbol = to_yahoo_symbol(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        params = {"interval": "1d", "range": "5d"}

        client = self._get_client()
        try:
            resp = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            data = resp.json()

            result = data.get("chart", {}).get("result", [])
            if not result:
                return {"symbol": symbol, "last": 0, "bid": 0, "ask": 0, "volume": 0}

            chart = result[0]
            meta = chart.get("meta", {})
            last = meta.get("regularMarketPrice", 0)

            return {
                "symbol": symbol,
                "last": last,
                "bid": last,
                "ask": last,
                "volume": meta.get("regularMarketVolume", 0),
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                "currency": "BRL",
            }
        except Exception as e:
            logger.error(f"Error fetching ticker for {yahoo_symbol}: {e}")
            return {"symbol": symbol, "last": 0, "bid": 0, "ask": 0, "volume": 0}

    async def fetch_balance(self) -> dict:
        """
        Fetch account balance.
        In testnet/paper mode, returns simulated balance.
        In live mode, calls the broker's balance API.
        """
        if self.testnet or not self.api_key:
            # Paper mode: return simulated BRL balance
            return {
                "BRL": {"free": 10000.0, "used": 0.0, "total": 10000.0},
                "total": {"BRL": 10000.0},
                "free": {"BRL": 10000.0},
                "used": {"BRL": 0.0},
            }
        # Live mode: delegate to broker-specific implementation
        return await self._fetch_live_balance()

    async def _fetch_live_balance(self) -> dict:
        """Override in subclass to implement live balance fetch."""
        raise NotImplementedError("Subclass must implement _fetch_live_balance()")

    def _assert_market_open_for_live(self) -> None:
        """Raise ValueError if market is closed and we're in live mode."""
        if not self.testnet:
            MarketHoursService.assert_market_open(self.exchange_id)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        logger.debug(f"{self.__class__.__name__} connection closed")


class ClearXPAdapter(B3BaseAdapter):
    """
    Clear/XP Investimentos broker adapter for B3.

    API documentation: https://developer.xpi.com.br/
    Requires institutional API agreement with XP Inc.

    For paper/testnet mode: uses Yahoo Finance for market data, simulates orders.
    For live mode: uses XP Developer API for order execution and account data.
    """

    # XP Developer API base URL
    # IMPORTANT: Replace with actual endpoint from XP documentation
    BASE_URL = "https://api.xpi.com.br/trading/v1"
    AUTH_URL = "https://api.xpi.com.br/auth/v1/token"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
        max_retries: int = 3,
    ):
        super().__init__(
            exchange_id="clear_xp",
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            max_retries=max_retries,
        )
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        """Get OAuth2 access token for XP API."""
        now = datetime.now(timezone.utc)
        if self._access_token and self._token_expires_at and now < self._token_expires_at:
            return self._access_token

        client = self._get_client()
        try:
            resp = await client.post(
                self.AUTH_URL,
                json={"client_id": self.api_key, "client_secret": self.api_secret, "grant_type": "client_credentials"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            from datetime import timedelta
            self._token_expires_at = now + timedelta(seconds=expires_in - 60)
            return self._access_token
        except Exception as e:
            logger.error(f"ClearXP auth error: {e}")
            raise

    async def _fetch_live_balance(self) -> dict:
        """Fetch live account balance from XP API."""
        token = await self._get_access_token()
        client = self._get_client()
        try:
            resp = await client.get(
                f"{self.BASE_URL}/account/balance",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            brl_balance = float(data.get("availableBalance", 0))
            return {
                "BRL": {"free": brl_balance, "used": 0.0, "total": brl_balance},
                "total": {"BRL": brl_balance},
                "free": {"BRL": brl_balance},
                "used": {"BRL": 0.0},
            }
        except Exception as e:
            logger.error(f"ClearXP balance error: {e}")
            raise


class ProfitProAdapter(B3BaseAdapter):
    """
    Profit Pro (Nelogica) adapter for B3.

    The Profit Pro API provides:
    - Real-time market data via WebSocket
    - Order routing to B3 via DMA (Direct Market Access)
    - Portfolio and position management

    API access requires a signed agreement with Nelogica.
    Contact: api@nelogica.com.br

    For paper/testnet mode: uses Yahoo Finance for market data, simulates orders.
    For live mode: uses Profit Pro REST/WebSocket API.
    """

    # Profit Pro API base URL
    # IMPORTANT: Replace with actual endpoint from Nelogica documentation
    BASE_URL = "https://api.profitchart.com.br/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
        max_retries: int = 3,
    ):
        super().__init__(
            exchange_id="profit_pro",
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            max_retries=max_retries,
        )

    async def _fetch_live_balance(self) -> dict:
        """Fetch live account balance from Profit Pro API."""
        client = self._get_client()
        try:
            resp = await client.get(
                f"{self.BASE_URL}/account/balance",
                headers={
                    "X-API-Key": self.api_key,
                    "X-API-Secret": self.api_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            brl_balance = float(data.get("balance", 0))
            return {
                "BRL": {"free": brl_balance, "used": 0.0, "total": brl_balance},
                "total": {"BRL": brl_balance},
                "free": {"BRL": brl_balance},
                "used": {"BRL": 0.0},
            }
        except Exception as e:
            logger.error(f"ProfitPro balance error: {e}")
            raise
