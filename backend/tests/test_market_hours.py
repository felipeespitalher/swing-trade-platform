"""
Unit tests for MarketHoursService.

Covers:
- B3 market hours (open/closed by time, weekend, holidays)
- Crypto exchanges (24/7, always open)
- Unknown exchanges (assumed open)
- get_market_status() return structure
- assert_market_open() raising ValueError when closed
"""

import pytest
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

from app.services.market_hours import MarketHoursService


TZ_BRT = ZoneInfo("America/Sao_Paulo")
TZ_UTC = ZoneInfo("UTC")

# Monday April 6, 2026 — not a holiday
monday_noon = datetime(2026, 4, 6, 12, 0, 0, tzinfo=TZ_BRT)
monday_9am = datetime(2026, 4, 6, 9, 0, 0, tzinfo=TZ_BRT)
monday_10am = datetime(2026, 4, 6, 10, 0, 0, tzinfo=TZ_BRT)
monday_1755 = datetime(2026, 4, 6, 17, 55, 0, tzinfo=TZ_BRT)
monday_1756 = datetime(2026, 4, 6, 17, 56, 0, tzinfo=TZ_BRT)
monday_6pm = datetime(2026, 4, 6, 18, 0, 0, tzinfo=TZ_BRT)
saturday_noon = datetime(2026, 4, 4, 12, 0, 0, tzinfo=TZ_BRT)
sunday_noon = datetime(2026, 4, 5, 12, 0, 0, tzinfo=TZ_BRT)

# B3 holidays
new_year_2026 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=TZ_BRT)
carnival_monday_2026 = datetime(2026, 2, 16, 12, 0, 0, tzinfo=TZ_BRT)


class TestB3MarketHours:
    """Tests for B3 (Bolsa de Valores Brasileira) market hours."""

    def test_b3_open_during_trading_hours(self):
        """Monday at 12:00 BRT is within B3 trading hours."""
        assert MarketHoursService.is_market_open("b3", monday_noon) is True

    def test_b3_closed_before_open(self):
        """Monday at 09:00 BRT is before B3 opens at 10:00."""
        assert MarketHoursService.is_market_open("b3", monday_9am) is False

    def test_b3_closed_after_close(self):
        """Monday at 18:00 BRT is after B3 closes at 17:55."""
        assert MarketHoursService.is_market_open("b3", monday_6pm) is False

    def test_b3_closed_on_saturday(self):
        """Saturday at 12:00 BRT — B3 is closed on weekends."""
        assert MarketHoursService.is_market_open("b3", saturday_noon) is False

    def test_b3_closed_on_sunday(self):
        """Sunday at 12:00 BRT — B3 is closed on weekends."""
        assert MarketHoursService.is_market_open("b3", sunday_noon) is False

    def test_b3_closed_on_new_year(self):
        """Jan 1, 2026 at 12:00 BRT is a B3 holiday."""
        assert MarketHoursService.is_market_open("b3", new_year_2026) is False

    def test_b3_closed_on_carnival(self):
        """Feb 16, 2026 (Carnival Monday) at 12:00 BRT is a B3 holiday."""
        assert MarketHoursService.is_market_open("b3", carnival_monday_2026) is False

    def test_b3_open_at_exactly_open_time(self):
        """Monday at exactly 10:00:00 BRT — B3 is open (inclusive boundary)."""
        assert MarketHoursService.is_market_open("b3", monday_10am) is True

    def test_b3_open_at_close_time(self):
        """Monday at exactly 17:55:00 BRT — B3 is still open (inclusive boundary)."""
        assert MarketHoursService.is_market_open("b3", monday_1755) is True

    def test_b3_closed_after_close_boundary(self):
        """Monday at 17:56:00 BRT — B3 is closed (one minute past close)."""
        assert MarketHoursService.is_market_open("b3", monday_1756) is False


class TestCryptoMarketHours:
    """Tests for 24/7 crypto exchanges."""

    def test_binance_always_open(self):
        """Binance is open 24/7 — any datetime returns True."""
        assert MarketHoursService.is_market_open("binance", saturday_noon) is True

    def test_coinbase_always_open(self):
        """Coinbase is open 24/7 — Saturday midnight returns True."""
        saturday_midnight = datetime(2026, 4, 4, 0, 0, 0, tzinfo=TZ_UTC)
        assert MarketHoursService.is_market_open("coinbase", saturday_midnight) is True

    def test_kraken_always_open(self):
        """Kraken is open 24/7 — Sunday 03:00 UTC returns True."""
        sunday_3am = datetime(2026, 4, 5, 3, 0, 0, tzinfo=TZ_UTC)
        assert MarketHoursService.is_market_open("kraken", sunday_3am) is True


class TestUnknownExchange:
    """Tests for exchanges not in the registry."""

    def test_unknown_exchange_assumed_open(self):
        """Unknown exchanges are assumed open (fail-open behavior)."""
        assert MarketHoursService.is_market_open("unknown_broker", monday_noon) is True


class TestGetMarketStatus:
    """Tests for MarketHoursService.get_market_status()."""

    def test_status_has_required_fields_when_open(self):
        """B3 during trading hours returns dict with is_open=True, market_name, reason."""
        status = MarketHoursService.get_market_status("b3", monday_noon)
        assert status["is_open"] is True
        assert "market_name" in status
        assert "reason" in status
        assert status["reason"] == "open"

    def test_status_has_required_fields_when_closed(self):
        """B3 on weekend returns is_open=False, reason='weekend'."""
        status = MarketHoursService.get_market_status("b3", saturday_noon)
        assert status["is_open"] is False
        assert "reason" in status
        assert status["reason"] == "weekend"

    def test_status_24h_market(self):
        """Binance status returns is_open=True with reason='24h_market'."""
        status = MarketHoursService.get_market_status("binance", saturday_noon)
        assert status["is_open"] is True
        assert status["reason"] == "24h_market"

    def test_status_holiday_reason(self):
        """B3 on a holiday returns reason='holiday'."""
        status = MarketHoursService.get_market_status("b3", new_year_2026)
        assert status["is_open"] is False
        assert status["reason"] == "holiday"

    def test_status_outside_trading_hours_reason(self):
        """B3 before open returns reason='outside_trading_hours'."""
        status = MarketHoursService.get_market_status("b3", monday_9am)
        assert status["is_open"] is False
        assert status["reason"] == "outside_trading_hours"

    def test_status_includes_market_name_for_b3(self):
        """B3 status includes the market_name field."""
        status = MarketHoursService.get_market_status("b3", monday_noon)
        assert status.get("market_name") == "B3"


class TestAssertMarketOpen:
    """Tests for MarketHoursService.assert_market_open()."""

    def test_assert_raises_on_weekend(self):
        """assert_market_open raises ValueError when B3 is closed on Saturday."""
        with pytest.raises(ValueError):
            MarketHoursService.assert_market_open("b3", saturday_noon)

    def test_assert_raises_on_holiday(self):
        """assert_market_open raises ValueError on New Year 2026 (B3 holiday)."""
        with pytest.raises(ValueError):
            MarketHoursService.assert_market_open("b3", new_year_2026)

    def test_assert_raises_outside_hours(self):
        """assert_market_open raises ValueError when B3 is before open time."""
        with pytest.raises(ValueError):
            MarketHoursService.assert_market_open("b3", monday_9am)

    def test_assert_does_not_raise_when_open(self):
        """assert_market_open does NOT raise when B3 is open at 12:00 Monday."""
        MarketHoursService.assert_market_open("b3", monday_noon)

    def test_assert_crypto_never_raises(self):
        """assert_market_open does NOT raise for binance (24/7 exchange)."""
        MarketHoursService.assert_market_open("binance", saturday_noon)
        MarketHoursService.assert_market_open("binance", sunday_noon)
        MarketHoursService.assert_market_open("binance", new_year_2026)
