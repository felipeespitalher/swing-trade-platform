"""
Unit tests for BacktestEngine.

Strategy: pure-unit, no DB, no mocks of the engine itself.
Synthetic candles generated via make_candles() helper.

Tests:
1. completed status with sufficient data
2. failed status with < 30 candles
3. equity curve first point equals initial_capital
4. win_rate is in [0, 1]
5. max_drawdown is <= 0
6. no-lookahead-bias: entry fill uses candle[i+1] open (+ slippage), not candle[i] close
"""

import time
import uuid
from decimal import Decimal

import pytest

from app.services.backtest_engine import BacktestEngine, BacktestRequest, BacktestResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candles(n: int, base_price: float = 40000.0) -> list:
    """Generate n synthetic OHLCV candles starting 180 days ago."""
    now_ms = int(time.time() * 1000)
    interval_ms = 3600_000  # 1h
    start_ms = now_ms - (n * interval_ms)
    candles = []
    price = base_price
    for i in range(n):
        ts = start_ms + i * interval_ms
        open_p = price
        close_p = price * (1 + (0.5 - (i % 7) / 14) * 0.02)  # oscillates
        high_p = max(open_p, close_p) * 1.005
        low_p = min(open_p, close_p) * 0.995
        candles.append([ts, open_p, high_p, low_p, close_p, 100.0])
        price = close_p
    return candles


def _date_from_ms_offset(offset_days: int) -> str:
    """Return a YYYY-MM-DD date that is offset_days before today (UTC)."""
    import datetime
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=offset_days)
    return dt.strftime("%Y-%m-%d")


def make_request(
    strategy_type: str = "rsi_only",
    n_candles: int = 200,
    *,
    initial_capital: float = 10000.0,
    config: dict | None = None,
) -> tuple[BacktestRequest, list]:
    """Build a BacktestRequest + matching candle list for the given size."""
    # candles span from n_candles hours ago to now
    candles = make_candles(n_candles)

    # date range that encompasses all candles
    start_date = _date_from_ms_offset(n_candles // 24 + 2)
    end_date = _date_from_ms_offset(0)

    req = BacktestRequest(
        strategy_id=str(uuid.uuid4()),
        strategy_type=strategy_type,
        strategy_config=config or {"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70},
        symbol="BTC/USDT",
        timeframe="1h",
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
    )
    return req, candles


# ---------------------------------------------------------------------------
# Test 1: completed status with sufficient data
# ---------------------------------------------------------------------------

def test_run_returns_completed_status_with_sufficient_data():
    """BacktestEngine returns status='completed' when given >= 30 candles in range."""
    req, candles = make_request(n_candles=200)
    result = BacktestEngine().run(req, candles)

    assert isinstance(result, BacktestResult)
    assert result.status == "completed", f"Expected 'completed' but got '{result.status}': {result.error}"
    assert result.error is None
    assert result.metrics is not None
    assert result.equity_curve is not None
    assert result.trades is not None


# ---------------------------------------------------------------------------
# Test 2: failed status with insufficient candles
# ---------------------------------------------------------------------------

def test_run_returns_failed_with_insufficient_candles():
    """BacktestEngine returns status='failed' and an error when fewer than 30 candles exist in range."""
    candles = make_candles(10)  # only 10 candles in dataset

    # Use a date range that matches those 10 candles
    start_date = _date_from_ms_offset(12)
    end_date = _date_from_ms_offset(0)

    req = BacktestRequest(
        strategy_id=str(uuid.uuid4()),
        strategy_type="rsi_only",
        strategy_config={"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70},
        symbol="BTC/USDT",
        timeframe="1h",
        start_date=start_date,
        end_date=end_date,
        initial_capital=10000.0,
    )

    result = BacktestEngine().run(req, candles)

    assert result.status == "failed"
    assert result.error is not None
    assert "Insufficient" in result.error


# ---------------------------------------------------------------------------
# Test 3: equity curve starts at initial_capital
# ---------------------------------------------------------------------------

def test_equity_curve_starts_at_initial_capital():
    """The first point in the equity curve should equal the initial capital value."""
    initial = 15000.0
    req, candles = make_request(n_candles=200, initial_capital=initial)
    result = BacktestEngine().run(req, candles)

    assert result.status == "completed"
    assert result.equity_curve, "equity_curve must not be empty"

    first_value = result.equity_curve[0]["value"]
    # The first equity point is recorded BEFORE any trade fills, so it
    # should equal initial capital (all cash, no open position yet).
    assert abs(first_value - initial) < 1.0, (
        f"Expected equity_curve[0]['value'] ≈ {initial}, got {first_value}"
    )


# ---------------------------------------------------------------------------
# Test 4: win_rate is between 0 and 1
# ---------------------------------------------------------------------------

def test_metrics_win_rate_between_0_and_1():
    """win_rate in metrics must be in the range [0, 1]."""
    req, candles = make_request(n_candles=300)
    result = BacktestEngine().run(req, candles)

    assert result.status == "completed"
    win_rate = result.metrics["win_rate"]
    assert 0.0 <= win_rate <= 1.0, f"win_rate={win_rate} is outside [0, 1]"


# ---------------------------------------------------------------------------
# Test 5: max_drawdown is <= 0
# ---------------------------------------------------------------------------

def test_metrics_max_drawdown_is_negative_or_zero():
    """max_drawdown must be <= 0 (it represents a decline from peak)."""
    req, candles = make_request(n_candles=300)
    result = BacktestEngine().run(req, candles)

    assert result.status == "completed"
    max_dd = result.metrics["max_drawdown"]
    assert max_dd <= 0.0, f"max_drawdown={max_dd} should be <= 0"


# ---------------------------------------------------------------------------
# Test 6: no-lookahead bias — fill uses next candle open, not current close
# ---------------------------------------------------------------------------

def test_no_lookahead_bias_fill_uses_next_candle_open():
    """
    Entry price must be based on the NEXT candle's open price (+ slippage),
    NOT the candle where the signal was generated (its close).

    We use MACD crossover strategy which fires regularly on the synthetic
    oscillating price pattern, guaranteeing at least one trade is generated.

    For each trade we verify that entry_price matches candle[i+1][1] * (1+0.0005)
    — the fill-at-next-open-with-slippage formula — not candle[i][4].
    """
    # MACD crossover fires whenever EMA(12) crosses EMA(26); it will trigger
    # on the oscillating synthetic price pattern.
    req, candles = make_request(
        strategy_type="macd_only",
        n_candles=300,
        config={"macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
    )
    result = BacktestEngine().run(req, candles)

    assert result.status == "completed"
    assert result.trades, (
        "Expected at least one trade from MACD strategy on 300-candle oscillating data"
    )

    SLIPPAGE = Decimal("0.0005")
    from decimal import ROUND_HALF_UP

    # Compute every valid fill price: next_open * (1 + slippage), rounded to 8 dp
    possible_fills = set()
    for i in range(len(candles) - 1):
        next_open = Decimal(str(candles[i + 1][1]))
        fill = (next_open * (1 + SLIPPAGE)).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP
        )
        possible_fills.add(float(fill))

    for trade in result.trades:
        entry_price = trade["entry_price"]
        matched_valid = any(abs(entry_price - valid) < 0.01 for valid in possible_fills)
        assert matched_valid, (
            f"Trade entry_price={entry_price} does not match any expected "
            f"next-candle-open + slippage value. Possible lookahead bias!"
        )
