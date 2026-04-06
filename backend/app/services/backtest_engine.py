"""
Backtesting engine for swing trade strategy evaluation.

Runs a strategy against historical OHLCV data with:
- No lookahead bias: signal from candle N closes → fill at candle N+1 open
- 0.05% slippage + 0.1% commission (via PaperTradingEngine)
- Metrics: win_rate, profit_factor, sharpe_ratio, max_drawdown, total_return
"""

import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import numpy as np

from app.services.signal_generator import Signal, SignalGenerator, MIN_CANDLES
from app.services.paper_trading_engine import PaperPortfolio, PaperTradingEngine

logger = logging.getLogger(__name__)


def timestamp_to_date(ts_ms: int) -> str:
    """Convert millisecond timestamp to 'YYYY-MM-DD' string (UTC)."""
    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _date_to_ms(date_str: str) -> int:
    """Convert 'YYYY-MM-DD' string to millisecond timestamp (UTC start of day)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


@dataclass
class BacktestRequest:
    """Parameters for a single backtest run."""

    strategy_id: str
    strategy_type: str          # 'rsi_only', 'macd_only', 'rsi_macd'
    strategy_config: dict       # RSI / MACD params
    symbol: str                 # 'BTC/USDT'
    timeframe: str              # '1h', '4h', '1d'
    start_date: str             # ISO date 'YYYY-MM-DD'
    end_date: str               # ISO date 'YYYY-MM-DD'
    initial_capital: float = 10000.0


@dataclass
class BacktestResult:
    """Result of a completed (or failed) backtest run."""

    id: str
    strategy_id: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    status: str                             # 'completed' or 'failed'
    metrics: Optional[dict] = None          # computed metrics dict
    equity_curve: Optional[list] = None     # [{'date': str, 'value': float}, ...]
    trades: Optional[list] = None           # list of trade dicts from simulate_exit
    error: Optional[str] = None


def _compute_sharpe(equity_curve: list) -> float:
    """
    Compute annualised Sharpe ratio from equity curve.

    Uses simple daily returns between consecutive equity points.
    Annualises with sqrt(252). Returns 0.0 when fewer than 2 points
    or standard deviation is zero.
    """
    if len(equity_curve) < 2:
        return 0.0

    values = [pt["value"] for pt in equity_curve]
    returns = []
    for i in range(1, len(values)):
        prev = values[i - 1]
        if prev == 0:
            continue
        returns.append((values[i] - prev) / prev)

    if len(returns) < 2:
        return 0.0

    arr = np.array(returns, dtype=np.float64)
    std = float(np.std(arr, ddof=1))
    if std == 0.0:
        return 0.0
    mean_ret = float(np.mean(arr))
    return float((mean_ret / std) * math.sqrt(252))


def _compute_max_drawdown(equity_curve: list) -> float:
    """
    Compute maximum drawdown as a negative percentage.

    Returns 0.0 if curve is empty or has no drawdown.
    Result is <= 0 (e.g. -15.3 means 15.3 % peak-to-trough decline).
    """
    if not equity_curve:
        return 0.0

    values = [pt["value"] for pt in equity_curve]
    peak = values[0]
    max_dd = 0.0

    for v in values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak * 100.0
            if dd < max_dd:
                max_dd = dd

    return max_dd


class BacktestEngine:
    """
    Runs a strategy against a provided candle list and returns a BacktestResult.

    No lookahead bias guarantee:
        Signal is evaluated on closes[0..i] (candle i close is the last value).
        Any resulting BUY/SELL fills at candle[i+1] open price.
    """

    def run(self, request: BacktestRequest, candles: list) -> BacktestResult:
        """
        Execute a backtest.

        Args:
            request: BacktestRequest with strategy params and date range.
            candles: Raw OHLCV list [[ts_ms, open, high, low, close, volume], ...].

        Returns:
            BacktestResult with status='completed' or status='failed'.
        """
        result_id = str(uuid.uuid4())

        # --- 1. Filter candles to requested date range ---
        start_ms = _date_to_ms(request.start_date)
        end_ms = _date_to_ms(request.end_date) + 86_400_000 - 1  # inclusive end of day

        filtered = [c for c in candles if start_ms <= c[0] <= end_ms]

        # --- 2. Check minimum data requirement ---
        if len(filtered) < 30:
            return BacktestResult(
                id=result_id,
                strategy_id=request.strategy_id,
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_date=request.start_date,
                end_date=request.end_date,
                status="failed",
                error="Insufficient data: need at least 30 candles in the selected range",
            )

        # --- 3. Set up paper trading infrastructure ---
        initial_capital = Decimal(str(request.initial_capital))

        try:
            strategy_uuid = uuid.UUID(request.strategy_id)
        except (ValueError, AttributeError):
            strategy_uuid = uuid.uuid4()

        portfolio = PaperPortfolio(
            strategy_id=strategy_uuid,
            initial_balance=initial_capital,
        )
        engine = PaperTradingEngine(portfolio)
        generator = SignalGenerator()

        # Determine minimum candle index to start iterating
        min_candles = MIN_CANDLES.get(request.strategy_type, 26)

        equity_curve: list = []
        completed_trades: list = []
        config = request.strategy_config
        symbol = request.symbol

        # --- 4. Iterate over candles ---
        total = len(filtered)

        for i in range(min_candles, total):
            # Build closes array up to and including candle i (no lookahead)
            closes = np.array(
                [float(filtered[j][4]) for j in range(i + 1)],
                dtype=np.float64,
            )

            signal = generator.evaluate(request.strategy_type, config, closes)

            # Fill at next candle open (avoid lookahead bias)
            if i + 1 < total:
                next_open = Decimal(str(filtered[i + 1][1]))

                if signal == Signal.BUY and symbol not in portfolio.open_positions:
                    engine.simulate_entry(symbol, next_open)

                elif signal == Signal.SELL and symbol in portfolio.open_positions:
                    trade = engine.simulate_exit(symbol, next_open, reason="signal")
                    if trade is not None:
                        completed_trades.append(trade)

            # Record equity snapshot at current candle
            equity_curve.append({
                "date": timestamp_to_date(filtered[i][0]),
                "value": float(portfolio.total_equity),
            })

        # --- 5. Close any remaining open positions at last candle close ---
        if symbol in portfolio.open_positions:
            last_close = Decimal(str(filtered[-1][4]))
            trade = engine.simulate_exit(symbol, last_close, reason="end_of_backtest")
            if trade is not None:
                completed_trades.append(trade)
            # Update last equity point to reflect forced exit
            if equity_curve:
                equity_curve[-1]["value"] = float(portfolio.total_equity)

        # --- 6. Compute metrics ---
        final_equity = float(portfolio.total_equity)
        init_cap = float(initial_capital)
        total_return = ((final_equity - init_cap) / init_cap) * 100.0 if init_cap > 0 else 0.0

        winning = [t for t in completed_trades if t["pnl"] > 0]
        losing = [t for t in completed_trades if t["pnl"] < 0]
        n_trades = len(completed_trades)

        win_rate = len(winning) / n_trades if n_trades > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in winning)
        gross_loss = abs(sum(t["pnl"] for t in losing))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        sharpe_ratio = _compute_sharpe(equity_curve)
        max_drawdown = _compute_max_drawdown(equity_curve)

        metrics = {
            "total_return": round(total_return, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "max_drawdown": round(max_drawdown, 4),
            "total_trades": n_trades,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "final_equity": round(final_equity, 2),
        }

        logger.info(
            f"Backtest complete: strategy={request.strategy_id} "
            f"symbol={symbol} trades={n_trades} return={total_return:.2f}%"
        )

        return BacktestResult(
            id=result_id,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            status="completed",
            metrics=metrics,
            equity_curve=equity_curve,
            trades=completed_trades,
        )
