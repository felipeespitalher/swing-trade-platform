"""
Tests for FundamentalService.

Uses unittest.mock to patch yfinance.Ticker so tests run without network access.

Coverage:
- Correct field mapping from yfinance info dict
- Percentage conversions (ROE, dividend yield, revenue growth)
- Score within [0, 100] for valid and empty data
- In-memory cache: second call skips yfinance fetch
- Cache expiry is NOT tested here (would require time mocking)
- Graceful handling when yfinance returns empty info dict
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.fundamental_service import FundamentalService


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

def _mock_info(overrides=None):
    """Return a realistic yfinance info dict."""
    data = {
        "marketCap": 500_000_000_000,
        "trailingPE": 15.0,
        "priceToBook": 2.5,
        "returnOnEquity": 0.18,
        "dividendYield": 0.035,
        "revenueGrowth": 0.12,
        "debtToEquity": 0.5,
        "currentRatio": 2.0,
        "fiftyTwoWeekHigh": 200.0,
        "fiftyTwoWeekLow": 100.0,
        "currentPrice": 150.0,
    }
    if overrides:
        data.update(overrides)
    return data


@pytest.fixture
def svc():
    service = FundamentalService()
    service._cache.clear()
    return service


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

class TestFieldMapping:

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_symbol_returned(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        result = svc.get_fundamentals("AAPL")
        assert result["symbol"] == "AAPL"

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_market_cap(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        result = svc.get_fundamentals("AAPL")
        assert result["market_cap"] == 500_000_000_000

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_pe_ratio(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        result = svc.get_fundamentals("AAPL")
        assert result["pe_ratio"] == pytest.approx(15.0)

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_price_to_book(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        result = svc.get_fundamentals("AAPL")
        assert result["price_to_book"] == pytest.approx(2.5)

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_roe_converted_to_percentage(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info({"returnOnEquity": 0.18})
        result = svc.get_fundamentals("AAPL")
        assert result["roe"] == pytest.approx(18.0)

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_dividend_yield_converted_to_percentage(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info({"dividendYield": 0.035})
        result = svc.get_fundamentals("AAPL")
        assert result["dividend_yield"] == pytest.approx(3.5)

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_revenue_growth_converted_to_percentage(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info({"revenueGrowth": 0.12})
        result = svc.get_fundamentals("AAPL")
        assert result["revenue_growth"] == pytest.approx(12.0)

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_debt_to_equity(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        result = svc.get_fundamentals("AAPL")
        assert result["debt_to_equity"] == pytest.approx(0.5)

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_52_week_range(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        result = svc.get_fundamentals("AAPL")
        assert result["week_52_high"] == pytest.approx(200.0)
        assert result["week_52_low"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Fundamental score
# ---------------------------------------------------------------------------

class TestFundamentalScore:

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_score_between_0_and_100(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        result = svc.get_fundamentals("MSFT")
        assert 0 <= result["score"] <= 100

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_empty_info_score_is_zero(self, mock_cls, svc):
        mock_cls.return_value.info = {}
        result = svc.get_fundamentals("UNKNOWN")
        assert result["score"] == 0

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_high_quality_company_scores_above_50(self, mock_cls, svc):
        # Very attractive fundamentals should score above 50
        info = _mock_info({
            "trailingPE": 10.0,       # good P/E
            "priceToBook": 1.0,       # good P/B
            "returnOnEquity": 0.30,   # excellent ROE
            "dividendYield": 0.04,    # sweet spot
            "revenueGrowth": 0.25,    # strong growth
            "debtToEquity": 0.2,      # low debt
            "currentRatio": 3.0,      # strong liquidity
        })
        mock_cls.return_value.info = info
        result = svc.get_fundamentals("QUALITY")
        assert result["score"] > 50

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_poor_company_scores_below_50(self, mock_cls, svc):
        info = _mock_info({
            "trailingPE": 50.0,       # expensive
            "priceToBook": 8.0,       # very expensive
            "returnOnEquity": 0.02,   # poor ROE
            "dividendYield": 0.0,
            "revenueGrowth": -0.10,   # declining revenue
            "debtToEquity": 3.0,      # high debt
            "currentRatio": 0.5,      # poor liquidity
        })
        mock_cls.return_value.info = info
        result = svc.get_fundamentals("POOR")
        assert result["score"] < 50


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class TestCache:

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_second_call_uses_cache(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        svc.get_fundamentals("TSLA")
        svc.get_fundamentals("TSLA")
        assert mock_cls.call_count == 1

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_different_symbols_fetch_separately(self, mock_cls, svc):
        mock_cls.return_value.info = _mock_info()
        svc.get_fundamentals("AAPL")
        svc.get_fundamentals("MSFT")
        assert mock_cls.call_count == 2


# ---------------------------------------------------------------------------
# Graceful handling of missing fields
# ---------------------------------------------------------------------------

class TestMissingFields:

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_none_when_field_missing(self, mock_cls, svc):
        mock_cls.return_value.info = {}
        result = svc.get_fundamentals("NODATA")
        assert result["pe_ratio"] is None
        assert result["price_to_book"] is None
        assert result["roe"] is None
        assert result["dividend_yield"] is None

    @patch("app.services.fundamental_service.yf.Ticker")
    def test_partial_data_does_not_raise(self, mock_cls, svc):
        mock_cls.return_value.info = {"marketCap": 1_000_000, "trailingPE": 20.0}
        result = svc.get_fundamentals("PARTIAL")
        assert result["market_cap"] == 1_000_000
        assert result["pe_ratio"] == pytest.approx(20.0)
        assert result["roe"] is None
