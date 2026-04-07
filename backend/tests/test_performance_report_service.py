"""
Tests for PerformanceReportService.

Coverage:
- Cumulative return computation (positive, negative, flat)
- Benchmark comparison and alpha calculation
- Rolling Sharpe and rolling max drawdown lengths
- Edge cases: empty or single-point equity curves raise ValueError
"""

import math
import pytest

from app.services.performance_report_service import PerformanceReportService


def _equity(values):
    return [{"date": f"2024-01-{i+1:02d}", "value": float(v)} for i, v in enumerate(values)]


def _benchmark(values):
    return [{"date": f"2024-01-{i+1:02d}", "close": float(v)} for i, v in enumerate(values)]


@pytest.fixture
def svc():
    return PerformanceReportService()


# ---------------------------------------------------------------------------
# Cumulative return
# ---------------------------------------------------------------------------

class TestCumulativeReturn:

    def test_positive_return(self, svc):
        result = svc.compute(_equity([10000, 10500, 11000]))
        assert result["cumulative_return"] == pytest.approx(10.0, rel=1e-3)

    def test_negative_return(self, svc):
        result = svc.compute(_equity([10000, 9500, 9000]))
        assert result["cumulative_return"] == pytest.approx(-10.0, rel=1e-3)

    def test_flat_return(self, svc):
        result = svc.compute(_equity([10000, 10000, 10000]))
        assert result["cumulative_return"] == pytest.approx(0.0, abs=1e-6)

    def test_large_gain(self, svc):
        result = svc.compute(_equity([1000, 2000]))
        assert result["cumulative_return"] == pytest.approx(100.0, rel=1e-3)


# ---------------------------------------------------------------------------
# Benchmark & alpha
# ---------------------------------------------------------------------------

class TestBenchmarkAndAlpha:

    def test_benchmark_return_computed(self, svc):
        result = svc.compute(_equity([10000, 11000, 12000]), benchmark_prices=_benchmark([100, 105, 110]))
        assert result["benchmark_return"] == pytest.approx(10.0, rel=1e-3)

    def test_alpha_positive_when_outperforming(self, svc):
        # strategy +20%, benchmark +10% → alpha +10%
        result = svc.compute(_equity([10000, 11000, 12000]), benchmark_prices=_benchmark([100, 105, 110]))
        assert result["alpha"] == pytest.approx(10.0, rel=1e-2)

    def test_alpha_negative_when_underperforming(self, svc):
        # strategy +5%, benchmark +20% → alpha -15%
        result = svc.compute(_equity([10000, 10500]), benchmark_prices=_benchmark([100, 120]))
        assert result["alpha"] < 0

    def test_no_benchmark_returns_none(self, svc):
        result = svc.compute(_equity([10000, 10500]))
        assert result["benchmark_return"] is None
        assert result["alpha"] is None

    def test_empty_benchmark_treated_as_none(self, svc):
        result = svc.compute(_equity([10000, 10500]), benchmark_prices=[])
        assert result["benchmark_return"] is None
        assert result["alpha"] is None


# ---------------------------------------------------------------------------
# Rolling Sharpe
# ---------------------------------------------------------------------------

class TestRollingSharpe:

    def test_length_matches_equity_curve(self, svc):
        equity = _equity([10000 + i * 50 for i in range(50)])
        result = svc.compute(equity, rolling_window=10)
        assert len(result["rolling_sharpe"]) == 50

    def test_early_points_are_none_before_window(self, svc):
        equity = _equity([10000 + i * 50 for i in range(20)])
        result = svc.compute(equity, rolling_window=10)
        # Points before window fills may be None (not enough returns)
        assert result["rolling_sharpe"][0] is None

    def test_later_points_are_numeric(self, svc):
        equity = _equity([10000 + i * 50 for i in range(30)])
        result = svc.compute(equity, rolling_window=5)
        assert result["rolling_sharpe"][-1] is not None
        assert isinstance(result["rolling_sharpe"][-1], float)

    def test_flat_equity_has_zero_sharpe(self, svc):
        equity = _equity([10000] * 20)
        result = svc.compute(equity, rolling_window=5)
        last = result["rolling_sharpe"][-1]
        assert last == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Rolling Drawdown
# ---------------------------------------------------------------------------

class TestRollingDrawdown:

    def test_length_matches_equity_curve(self, svc):
        equity = _equity([10000 + i * 50 for i in range(50)])
        result = svc.compute(equity, rolling_window=10)
        assert len(result["rolling_drawdown"]) == 50

    def test_no_drawdown_on_monotonic_increase(self, svc):
        equity = _equity([10000 + i * 100 for i in range(20)])
        result = svc.compute(equity, rolling_window=5)
        # Monotonically increasing equity → no drawdown (0.0)
        assert result["rolling_drawdown"][-1] == pytest.approx(0.0, abs=1e-6)

    def test_drawdown_negative_on_decline(self, svc):
        equity = _equity([10000, 9500, 9000, 9500, 9000])
        result = svc.compute(equity, rolling_window=5)
        last = result["rolling_drawdown"][-1]
        assert last < 0  # must be negative percentage

    def test_early_points_are_none_before_window(self, svc):
        equity = _equity([10000 + i * 50 for i in range(20)])
        result = svc.compute(equity, rolling_window=10)
        assert result["rolling_drawdown"][0] is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_equity_raises(self, svc):
        with pytest.raises(ValueError, match="at least 2"):
            svc.compute([])

    def test_single_point_raises(self, svc):
        with pytest.raises(ValueError, match="at least 2"):
            svc.compute(_equity([10000]))

    def test_result_keys_present(self, svc):
        result = svc.compute(_equity([10000, 10500, 11000]))
        assert "cumulative_return" in result
        assert "benchmark_return" in result
        assert "alpha" in result
        assert "rolling_sharpe" in result
        assert "rolling_drawdown" in result
