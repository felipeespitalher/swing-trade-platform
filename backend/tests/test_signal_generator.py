"""
TDD stub tests for signal_generator module.
All tests are skipped until implementation is complete (Wave 3).
"""
import pytest


@pytest.mark.skip(reason="not implemented")
def test_rsi_oversold_produces_buy_signal():
    """RSI below oversold threshold (e.g., 30) produces a BUY signal."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_rsi_overbought_produces_sell_signal():
    """RSI above overbought threshold (e.g., 70) produces a SELL signal."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_rsi_neutral_zone_produces_hold_signal():
    """RSI between oversold and overbought thresholds produces a HOLD signal."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_macd_bullish_crossover_produces_buy_signal():
    """MACD line crossing above signal line (bullish crossover) produces a BUY signal."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_macd_bearish_crossover_produces_sell_signal():
    """MACD line crossing below signal line (bearish crossover) produces a SELL signal."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_macd_no_crossover_produces_hold_signal():
    """MACD with no recent crossover produces a HOLD signal."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_insufficient_data_returns_hold():
    """Fewer candles than required by the indicator period returns HOLD, not an error."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_unknown_strategy_type_raises_value_error():
    """Passing an unrecognized strategy type raises ValueError."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_signal_includes_confidence_score():
    """Generated signal includes a numeric confidence/strength score."""
    pass


@pytest.mark.skip(reason="not implemented")
def test_signal_includes_timestamp():
    """Generated signal includes the timestamp of the triggering candle."""
    pass
