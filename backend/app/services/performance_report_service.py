"""
Performance report service for swing trade strategies.

Computes relative performance metrics comparing a strategy's equity curve
against an optional benchmark (e.g. IBOV, S&P 500, CDI):

- cumulative_return: total strategy return (%)
- benchmark_return: total benchmark return (%) — None if no benchmark provided
- alpha: strategy return minus benchmark return (%) — None if no benchmark
- rolling_sharpe: list of annualised Sharpe ratios for each point (rolling window)
- rolling_drawdown: list of max drawdown percentages for each point (rolling window)
"""

import math
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class PerformanceReportService:
    """
    Computes performance metrics for a strategy equity curve.

    Usage:
        svc = PerformanceReportService()
        report = svc.compute(equity_curve, benchmark_prices=benchmark, rolling_window=30)
    """

    def compute(
        self,
        equity_curve: list,
        benchmark_prices: Optional[list] = None,
        rolling_window: int = 30,
    ) -> dict:
        """
        Compute performance metrics.

        Args:
            equity_curve: List of dicts with keys 'date' and 'value'.
                          Must have at least 2 points.
            benchmark_prices: Optional list of dicts with keys 'date' and 'close'.
                              Must have at least 2 points if provided.
            rolling_window: Number of points for rolling Sharpe / drawdown windows.

        Returns:
            dict with keys:
                cumulative_return (float), benchmark_return (float|None),
                alpha (float|None), rolling_sharpe (list), rolling_drawdown (list)

        Raises:
            ValueError: If equity_curve has fewer than 2 points.
        """
        if len(equity_curve) < 2:
            raise ValueError("equity_curve must have at least 2 points")

        values = np.array([pt["value"] for pt in equity_curve], dtype=np.float64)
        cumulative_return = self._cumulative_return(values)

        benchmark_return: Optional[float] = None
        alpha: Optional[float] = None
        if benchmark_prices and len(benchmark_prices) >= 2:
            b_values = np.array([pt["close"] for pt in benchmark_prices], dtype=np.float64)
            benchmark_return = self._cumulative_return(b_values)
            alpha = round(cumulative_return - benchmark_return, 4)

        rolling_sharpe = self._rolling_sharpe(values, rolling_window)
        rolling_drawdown = self._rolling_drawdown(values, rolling_window)

        return {
            "cumulative_return": round(cumulative_return, 4),
            "benchmark_return": round(benchmark_return, 4) if benchmark_return is not None else None,
            "alpha": alpha,
            "rolling_sharpe": rolling_sharpe,
            "rolling_drawdown": rolling_drawdown,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cumulative_return(values: np.ndarray) -> float:
        init = float(values[0])
        final = float(values[-1])
        if init == 0:
            return 0.0
        return ((final - init) / init) * 100.0

    @staticmethod
    def _rolling_sharpe(values: np.ndarray, window: int) -> list:
        """
        Compute rolling annualised Sharpe ratio.

        Returns a list of length == len(values).
        Points with fewer than 2 returns in the window are None.
        """
        n = len(values)
        result = [None] * n

        for i in range(n):
            start = max(0, i - window + 1)
            window_vals = values[start : i + 1]

            if len(window_vals) < 2:
                continue

            returns = np.diff(window_vals) / window_vals[:-1]
            if len(returns) < 1:
                continue

            std = float(np.std(returns, ddof=1))
            if std == 0.0:
                result[i] = 0.0
            else:
                mean_ret = float(np.mean(returns))
                result[i] = round(float((mean_ret / std) * math.sqrt(252)), 4)

        return result

    @staticmethod
    def _rolling_drawdown(values: np.ndarray, window: int) -> list:
        """
        Compute rolling maximum drawdown (as a negative percentage).

        Returns a list of length == len(values).
        Points before the window fills (< 2 values) are None.
        """
        n = len(values)
        result = [None] * n

        for i in range(n):
            start = max(0, i - window + 1)
            window_vals = values[start : i + 1]

            if len(window_vals) < 2:
                continue

            peak = float(window_vals[0])
            max_dd = 0.0
            for v in window_vals:
                fv = float(v)
                if fv > peak:
                    peak = fv
                if peak > 0:
                    dd = (fv - peak) / peak * 100.0
                    if dd < max_dd:
                        max_dd = dd
            result[i] = round(max_dd, 4)

        return result
