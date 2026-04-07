"""
Fundamental analysis service using Yahoo Finance (yfinance).

Fetches key fundamental indicators for a given ticker symbol and computes
a composite score (0-100) based on value, profitability, growth, and safety metrics.

In-memory cache with 1-hour TTL avoids hammering the Yahoo Finance API.

Scoring criteria (0-100):
  - P/E ratio (20 pts): < 15 = 20, 15-25 = 12, 25-35 = 5
  - P/B ratio (15 pts): < 1.5 = 15, 1.5-3 = 8, 3-5 = 3
  - ROE       (20 pts): > 20% = 20, 10-20% = 12, 0-10% = 5
  - Div Yield (10 pts): 2-6% = 10, any positive = 5
  - Rev Growth(15 pts): > 20% = 15, 10-20% = 10, 0-10% = 5
  - Debt/Eq   (10 pts): < 0.5 = 10, 0.5-1 = 6, 1-2 = 2
  - Current R (10 pts): > 2 = 10, 1-2 = 6
"""

import logging
import time
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 3600  # 1 hour


class FundamentalService:
    """
    Fetches and scores fundamental data for equity symbols via Yahoo Finance.

    Usage:
        svc = FundamentalService()
        data = svc.get_fundamentals("AAPL")
        print(data["score"], data["pe_ratio"])
    """

    def __init__(self):
        # Cache: symbol -> (fetched_at_timestamp, data_dict)
        self._cache: dict = {}

    def get_fundamentals(self, symbol: str) -> dict:
        """
        Return fundamental data for the given symbol.

        Results are cached for 1 hour. Subsequent calls within the TTL
        return cached data without hitting Yahoo Finance.

        Args:
            symbol: Ticker symbol (e.g. 'AAPL', 'PETR4.SA', 'BTC-USD')

        Returns:
            dict with fields:
                symbol, market_cap, pe_ratio, price_to_book, roe (%),
                dividend_yield (%), revenue_growth (%), debt_to_equity,
                current_ratio, week_52_high, week_52_low, current_price, score
        """
        now = time.time()
        cached = self._cache.get(symbol)
        if cached is not None:
            fetched_at, data = cached
            if now - fetched_at < _CACHE_TTL_SECONDS:
                logger.debug(f"Cache hit for {symbol}")
                return data

        logger.debug(f"Fetching fundamentals for {symbol} from Yahoo Finance")
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
        except Exception as exc:
            logger.warning(f"yfinance fetch failed for {symbol}: {exc}")
            info = {}

        data = self._build_data(symbol, info)
        self._cache[symbol] = (now, data)
        return data

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_data(self, symbol: str, info: dict) -> dict:
        pe_ratio: Optional[float] = info.get("trailingPE")
        price_to_book: Optional[float] = info.get("priceToBook")

        # Yahoo Finance returns ROE, dividendYield, revenueGrowth as decimals (0.18 = 18%)
        roe_raw: Optional[float] = info.get("returnOnEquity")
        div_yield_raw: Optional[float] = info.get("dividendYield")
        rev_growth_raw: Optional[float] = info.get("revenueGrowth")

        roe_pct = round(roe_raw * 100, 4) if roe_raw is not None else None
        div_yield_pct = round(div_yield_raw * 100, 4) if div_yield_raw is not None else None
        rev_growth_pct = round(rev_growth_raw * 100, 4) if rev_growth_raw is not None else None

        score = self._compute_score(
            pe=pe_ratio,
            pb=price_to_book,
            roe=roe_raw,
            div_yield=div_yield_raw,
            rev_growth=rev_growth_raw,
            d_e=info.get("debtToEquity"),
            current_ratio=info.get("currentRatio"),
        )

        return {
            "symbol": symbol,
            "market_cap": info.get("marketCap"),
            "pe_ratio": pe_ratio,
            "price_to_book": price_to_book,
            "roe": roe_pct,
            "dividend_yield": div_yield_pct,
            "revenue_growth": rev_growth_pct,
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            "current_price": info.get("currentPrice"),
            "score": score,
        }

    @staticmethod
    def _compute_score(
        pe: Optional[float],
        pb: Optional[float],
        roe: Optional[float],
        div_yield: Optional[float],
        rev_growth: Optional[float],
        d_e: Optional[float],
        current_ratio: Optional[float],
    ) -> float:
        """
        Compute a 0-100 fundamental score.

        Each metric contributes to a weighted total.
        Final score = (points earned / max possible points) * 100.
        Returns 0 when no metrics are available.
        """
        earned = 0.0
        max_possible = 0.0

        # P/E ratio (20 pts)
        if pe is not None and pe > 0:
            max_possible += 20
            if pe < 15:
                earned += 20
            elif pe < 25:
                earned += 12
            elif pe < 35:
                earned += 5

        # P/B ratio (15 pts)
        if pb is not None and pb > 0:
            max_possible += 15
            if pb < 1.5:
                earned += 15
            elif pb < 3.0:
                earned += 8
            elif pb < 5.0:
                earned += 3

        # ROE (20 pts) — raw decimal expected (0.18 = 18%)
        if roe is not None:
            max_possible += 20
            if roe > 0.20:
                earned += 20
            elif roe > 0.10:
                earned += 12
            elif roe > 0:
                earned += 5

        # Dividend yield (10 pts) — raw decimal expected
        if div_yield is not None and div_yield > 0:
            max_possible += 10
            if 0.02 <= div_yield <= 0.06:
                earned += 10
            else:
                earned += 5

        # Revenue growth (15 pts) — raw decimal expected
        if rev_growth is not None:
            max_possible += 15
            if rev_growth > 0.20:
                earned += 15
            elif rev_growth > 0.10:
                earned += 10
            elif rev_growth > 0:
                earned += 5

        # Debt/Equity (10 pts)
        if d_e is not None:
            max_possible += 10
            if d_e < 0.5:
                earned += 10
            elif d_e < 1.0:
                earned += 6
            elif d_e < 2.0:
                earned += 2

        # Current ratio (10 pts)
        if current_ratio is not None:
            max_possible += 10
            if current_ratio > 2.0:
                earned += 10
            elif current_ratio > 1.0:
                earned += 6

        if max_possible == 0:
            return 0

        return round((earned / max_possible) * 100, 1)
