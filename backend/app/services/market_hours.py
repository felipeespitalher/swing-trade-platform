"""
Market Hours Service.

Validates whether a given market is open for trading at a given time.
Supports:
- B3 (Bolsa de Valores Brasileira): Mon-Fri 10:00-17:55 BRT
- NYSE/NASDAQ: Mon-Fri 09:30-16:00 ET
- Crypto (Binance etc.): 24/7

B3 holidays for 2025-2026 are hardcoded. For production, integrate with
a financial calendar API (e.g., Brasil API, Nelogica calendar).
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Timezone definitions
TZ_BRT = ZoneInfo("America/Sao_Paulo")
TZ_ET = ZoneInfo("America/New_York")
TZ_UTC = ZoneInfo("UTC")


@dataclass
class MarketSchedule:
    """Daily open/close times for a market."""
    market: str
    timezone: ZoneInfo
    open_time: time
    close_time: time
    is_24h: bool = False


# Market schedules
MARKET_SCHEDULES: dict[str, MarketSchedule] = {
    "b3": MarketSchedule(
        market="B3",
        timezone=TZ_BRT,
        open_time=time(10, 0),
        close_time=time(17, 55),
    ),
    "clear_xp": MarketSchedule(
        market="B3",
        timezone=TZ_BRT,
        open_time=time(10, 0),
        close_time=time(17, 55),
    ),
    "profit_pro": MarketSchedule(
        market="B3",
        timezone=TZ_BRT,
        open_time=time(10, 0),
        close_time=time(17, 55),
    ),
    "nyse": MarketSchedule(
        market="NYSE",
        timezone=TZ_ET,
        open_time=time(9, 30),
        close_time=time(16, 0),
    ),
    "binance": MarketSchedule(
        market="Binance",
        timezone=TZ_UTC,
        open_time=time(0, 0),
        close_time=time(23, 59),
        is_24h=True,
    ),
    "coinbase": MarketSchedule(
        market="Coinbase",
        timezone=TZ_UTC,
        open_time=time(0, 0),
        close_time=time(23, 59),
        is_24h=True,
    ),
    "kraken": MarketSchedule(
        market="Kraken",
        timezone=TZ_UTC,
        open_time=time(0, 0),
        close_time=time(23, 59),
        is_24h=True,
    ),
}

# B3 holidays (YYYY-MM-DD format)
# Source: B3 official calendar
B3_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 1, 1),   # New Year
    date(2025, 3, 3),   # Carnival Monday
    date(2025, 3, 4),   # Carnival Tuesday
    date(2025, 4, 18),  # Good Friday
    date(2025, 4, 21),  # Tiradentes
    date(2025, 5, 1),   # Labor Day
    date(2025, 6, 19),  # Corpus Christi
    date(2025, 9, 7),   # Independence Day
    date(2025, 10, 12),  # Nossa Sra Aparecida
    date(2025, 11, 2),  # Finados
    date(2025, 11, 15),  # Proclamacao da Republica
    date(2025, 11, 20),  # Consciencia Negra
    date(2025, 12, 25),  # Christmas
    date(2025, 12, 31),  # New Year's Eve (early close, treated as holiday)
    # 2026
    date(2026, 1, 1),   # New Year
    date(2026, 2, 16),  # Carnival Monday
    date(2026, 2, 17),  # Carnival Tuesday
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 21),  # Tiradentes
    date(2026, 5, 1),   # Labor Day
    date(2026, 6, 4),   # Corpus Christi
    date(2026, 9, 7),   # Independence Day
    date(2026, 10, 12),  # Nossa Sra Aparecida
    date(2026, 11, 2),  # Finados
    date(2026, 11, 15),  # Proclamacao da Republica
    date(2026, 11, 20),  # Consciencia Negra
    date(2026, 12, 25),  # Christmas
    date(2026, 12, 31),  # New Year's Eve
}

# NYSE/US holidays 2025-2026
NYSE_HOLIDAYS: set[date] = {
    date(2025, 1, 1),   # New Year
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27),  # Thanksgiving
    date(2025, 12, 25),  # Christmas
    date(2026, 1, 1),   # New Year
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas
}

HOLIDAYS_BY_MARKET: dict[str, set[date]] = {
    "b3": B3_HOLIDAYS,
    "clear_xp": B3_HOLIDAYS,
    "profit_pro": B3_HOLIDAYS,
    "nyse": NYSE_HOLIDAYS,
}


class MarketHoursService:
    """
    Service to check market open/close status for any supported exchange.
    """

    @classmethod
    def get_schedule(cls, exchange_id: str) -> Optional[MarketSchedule]:
        """Get market schedule for a given exchange."""
        return MARKET_SCHEDULES.get(exchange_id.lower())

    @classmethod
    def is_market_open(
        cls,
        exchange_id: str,
        dt: Optional[datetime] = None,
    ) -> bool:
        """
        Check if the market is open at the given datetime.

        Args:
            exchange_id: Exchange/broker identifier (e.g., 'b3', 'binance', 'clear_xp')
            dt: UTC datetime to check (defaults to now)

        Returns:
            True if market is open for trading
        """
        schedule = cls.get_schedule(exchange_id)
        if schedule is None:
            # Unknown exchange — assume open (fail-open for crypto)
            logger.warning(f"Unknown exchange '{exchange_id}', assuming market open")
            return True

        if schedule.is_24h:
            return True

        if dt is None:
            dt = datetime.now(TZ_UTC)

        # Convert to market's local timezone
        local_dt = dt.astimezone(schedule.timezone)
        local_date = local_dt.date()
        local_time = local_dt.time()

        # Check weekend
        if local_dt.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Check holidays
        holidays = HOLIDAYS_BY_MARKET.get(exchange_id.lower(), set())
        if local_date in holidays:
            return False

        # Check trading hours
        return schedule.open_time <= local_time <= schedule.close_time

    @classmethod
    def get_market_status(
        cls,
        exchange_id: str,
        dt: Optional[datetime] = None,
    ) -> dict:
        """
        Get detailed market status information.

        Returns:
            Dict with: is_open, market_name, local_time, open_time, close_time, reason
        """
        schedule = cls.get_schedule(exchange_id)
        if dt is None:
            dt = datetime.now(TZ_UTC)

        if schedule is None:
            return {
                "is_open": True,
                "market_name": exchange_id,
                "reason": "unknown_exchange",
            }

        if schedule.is_24h:
            return {
                "is_open": True,
                "market_name": schedule.market,
                "reason": "24h_market",
            }

        local_dt = dt.astimezone(schedule.timezone)
        local_date = local_dt.date()
        is_weekend = local_dt.weekday() >= 5
        holidays = HOLIDAYS_BY_MARKET.get(exchange_id.lower(), set())
        is_holiday = local_date in holidays
        in_hours = schedule.open_time <= local_dt.time() <= schedule.close_time

        if is_weekend:
            reason = "weekend"
        elif is_holiday:
            reason = "holiday"
        elif not in_hours:
            reason = "outside_trading_hours"
        else:
            reason = "open"

        return {
            "is_open": not is_weekend and not is_holiday and in_hours,
            "market_name": schedule.market,
            "local_time": local_dt.strftime("%Y-%m-%d %H:%M %Z"),
            "open_time": schedule.open_time.strftime("%H:%M"),
            "close_time": schedule.close_time.strftime("%H:%M"),
            "timezone": str(schedule.timezone),
            "reason": reason,
        }

    @classmethod
    def assert_market_open(cls, exchange_id: str, dt: Optional[datetime] = None) -> None:
        """
        Raise ValueError if the market is closed.
        Use this before placing real orders.
        """
        status = cls.get_market_status(exchange_id, dt)
        if not status["is_open"]:
            market = status.get("market_name", exchange_id)
            reason = status.get("reason", "closed")
            reason_msg = {
                "weekend": "mercado fechado no fim de semana",
                "holiday": "feriado — mercado fechado",
                "outside_trading_hours": f"fora do horario de pregao ({status.get('open_time')}–{status.get('close_time')} {status.get('timezone', '')})",
            }.get(reason, "mercado fechado")
            raise ValueError(f"{market}: {reason_msg}")
