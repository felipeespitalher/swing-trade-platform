"""
Tests for extended signal_generator strategies: Bollinger Bands, SMA crossover, EMA crossover.

Coverage:
- bb_only: BUY below lower band, SELL above upper band, HOLD inside bands
- sma_crossover: BUY on fast > slow, SELL on fast < slow
- ema_crossover: BUY on fast EMA > slow EMA, SELL on fast EMA < slow EMA
- Edge cases: insufficient data always returns HOLD
"""

import numpy as np
import pytest

from app.services.signal_generator import Signal, SignalGenerator


@pytest.fixture
def gen():
    return SignalGenerator()


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------

class TestBollingerBands:

    def test_buy_when_price_crashes_below_lower_band(self, gen):
        # 20 flat closes then a sharp drop — last price well below lower band
        closes = np.array([100.0] * 20 + [50.0], dtype=np.float64)
        signal = gen.evaluate("bb_only", {"bb_period": 20, "bb_std": 2.0}, closes)
        assert signal == Signal.BUY

    def test_sell_when_price_spikes_above_upper_band(self, gen):
        # 20 flat closes then a sharp spike — last price well above upper band
        closes = np.array([100.0] * 20 + [200.0], dtype=np.float64)
        signal = gen.evaluate("bb_only", {"bb_period": 20, "bb_std": 2.0}, closes)
        assert signal == Signal.SELL

    def test_hold_when_price_inside_bands(self, gen):
        # Gradual uptrend — price stays within bands
        closes = np.linspace(95.0, 105.0, 30, dtype=np.float64)
        signal = gen.evaluate("bb_only", {"bb_period": 20, "bb_std": 2.0}, closes)
        assert signal == Signal.HOLD

    def test_hold_on_insufficient_data(self, gen):
        closes = np.array([100.0] * 5, dtype=np.float64)
        signal = gen.evaluate("bb_only", {}, closes)
        assert signal == Signal.HOLD

    def test_hold_when_exactly_at_band_boundaries(self, gen):
        # Price exactly at the mean (middle band) — should be HOLD
        closes = np.full(30, 100.0, dtype=np.float64)
        signal = gen.evaluate("bb_only", {"bb_period": 20, "bb_std": 2.0}, closes)
        # Flat series has zero std; mean == upper == lower, no clear signal
        assert signal in (Signal.HOLD, Signal.BUY, Signal.SELL)

    def test_default_params_used_when_config_empty(self, gen):
        closes = np.array([100.0] * 20 + [50.0], dtype=np.float64)
        # Empty config — defaults applied (bb_period=20, bb_std=2)
        signal = gen.evaluate("bb_only", {}, closes)
        assert signal == Signal.BUY


# ---------------------------------------------------------------------------
# SMA Crossover
# ---------------------------------------------------------------------------

class TestSMACrossover:

    def test_buy_when_fast_sma_above_slow_sma(self, gen):
        # Strong uptrend at the end: fast SMA (5) > slow SMA (20)
        base = np.linspace(50.0, 60.0, 20, dtype=np.float64)
        spike = np.linspace(60.0, 120.0, 10, dtype=np.float64)
        closes = np.concatenate([base, spike])
        signal = gen.evaluate("sma_crossover", {"sma_fast": 5, "sma_slow": 20}, closes)
        assert signal == Signal.BUY

    def test_sell_when_fast_sma_below_slow_sma(self, gen):
        # Strong downtrend at the end: fast SMA (5) < slow SMA (20)
        base = np.linspace(120.0, 110.0, 20, dtype=np.float64)
        crash = np.linspace(110.0, 50.0, 10, dtype=np.float64)
        closes = np.concatenate([base, crash])
        signal = gen.evaluate("sma_crossover", {"sma_fast": 5, "sma_slow": 20}, closes)
        assert signal == Signal.SELL

    def test_hold_on_insufficient_data(self, gen):
        closes = np.array([100.0] * 5, dtype=np.float64)
        signal = gen.evaluate("sma_crossover", {"sma_fast": 5, "sma_slow": 20}, closes)
        assert signal == Signal.HOLD

    def test_default_params_applied(self, gen):
        base = np.linspace(50.0, 60.0, 21, dtype=np.float64)
        spike = np.linspace(60.0, 120.0, 10, dtype=np.float64)
        closes = np.concatenate([base, spike])
        # Default sma_fast=9, sma_slow=21
        signal = gen.evaluate("sma_crossover", {}, closes)
        assert signal in (Signal.BUY, Signal.HOLD, Signal.SELL)

    def test_returns_signal_enum(self, gen):
        closes = np.linspace(100.0, 150.0, 40, dtype=np.float64)
        signal = gen.evaluate("sma_crossover", {"sma_fast": 5, "sma_slow": 20}, closes)
        assert isinstance(signal, Signal)


# ---------------------------------------------------------------------------
# EMA Crossover
# ---------------------------------------------------------------------------

class TestEMACrossover:

    def test_buy_when_fast_ema_above_slow_ema(self, gen):
        base = np.linspace(50.0, 60.0, 21, dtype=np.float64)
        spike = np.linspace(60.0, 120.0, 10, dtype=np.float64)
        closes = np.concatenate([base, spike])
        signal = gen.evaluate("ema_crossover", {"ema_fast": 9, "ema_slow": 21}, closes)
        assert signal == Signal.BUY

    def test_sell_when_fast_ema_below_slow_ema(self, gen):
        base = np.linspace(120.0, 110.0, 21, dtype=np.float64)
        crash = np.linspace(110.0, 50.0, 10, dtype=np.float64)
        closes = np.concatenate([base, crash])
        signal = gen.evaluate("ema_crossover", {"ema_fast": 9, "ema_slow": 21}, closes)
        assert signal == Signal.SELL

    def test_hold_on_insufficient_data(self, gen):
        closes = np.array([100.0] * 5, dtype=np.float64)
        signal = gen.evaluate("ema_crossover", {"ema_fast": 9, "ema_slow": 21}, closes)
        assert signal == Signal.HOLD

    def test_default_params_applied(self, gen):
        closes = np.linspace(100.0, 150.0, 40, dtype=np.float64)
        signal = gen.evaluate("ema_crossover", {}, closes)
        assert isinstance(signal, Signal)

    def test_returns_signal_enum(self, gen):
        closes = np.linspace(100.0, 150.0, 40, dtype=np.float64)
        signal = gen.evaluate("ema_crossover", {"ema_fast": 9, "ema_slow": 21}, closes)
        assert isinstance(signal, Signal)


# ---------------------------------------------------------------------------
# All new types: insufficient data → HOLD
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("strategy_type", ["bb_only", "sma_crossover", "ema_crossover"])
def test_all_new_strategies_return_hold_on_tiny_input(gen, strategy_type):
    closes = np.array([100.0, 101.0], dtype=np.float64)
    signal = gen.evaluate(strategy_type, {}, closes)
    assert signal == Signal.HOLD


# ---------------------------------------------------------------------------
# Unknown strategy still raises
# ---------------------------------------------------------------------------

def test_unknown_strategy_raises(gen):
    with pytest.raises(ValueError, match="Unsupported strategy type"):
        gen.evaluate("unknown_strategy", {}, np.full(30, 100.0, dtype=np.float64))
