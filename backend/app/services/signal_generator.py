"""
Signal generator for trading strategy evaluation.

Evaluates strategy configurations against OHLCV close prices and
returns BUY, SELL, or HOLD signals.

Supported strategy types:
- rsi_only: RSI-based signals (oversold=BUY, overbought=SELL)
- macd_only: MACD crossover signals
- rsi_macd: Combined RSI + MACD confirmation
- bb_only: Bollinger Bands (price < lower band=BUY, price > upper band=SELL)
- sma_crossover: Simple Moving Average crossover (fast > slow=BUY, fast < slow=SELL)
- ema_crossover: Exponential Moving Average crossover (fast > slow=BUY, fast < slow=SELL)

TA-Lib is the primary indicator library. pandas-ta is used as fallback
if TA-Lib C library is not available.
"""

import logging
from enum import Enum
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Try to import TA-Lib (requires libta-lib-dev system package)
try:
    import talib
    TALIB_AVAILABLE = True
    logger.debug("TA-Lib loaded successfully")
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib not available, falling back to pandas-ta")


class Signal(str, Enum):
    """Trading signal output."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# Minimum candles needed for each strategy
MIN_CANDLES = {
    "rsi_only": 14,          # RSI period
    "macd_only": 26,         # MACD slow period
    "rsi_macd": 26,          # Max of RSI + MACD requirements
    "bb_only": 20,           # Bollinger Bands default period
    "sma_crossover": 21,     # Slow SMA default period
    "ema_crossover": 21,     # Slow EMA default period
}

DEFAULT_RSI_PERIOD = 14
DEFAULT_RSI_OVERSOLD = 30.0
DEFAULT_RSI_OVERBOUGHT = 70.0
DEFAULT_MACD_FAST = 12
DEFAULT_MACD_SLOW = 26
DEFAULT_MACD_SIGNAL = 9
DEFAULT_BB_PERIOD = 20
DEFAULT_BB_STD = 2.0
DEFAULT_SMA_FAST = 9
DEFAULT_SMA_SLOW = 21
DEFAULT_EMA_FAST = 9
DEFAULT_EMA_SLOW = 21


def _compute_rsi_numpy(closes: np.ndarray, period: int) -> Optional[float]:
    """
    Pure numpy RSI implementation (Wilder's Smoothed Moving Average method).
    Returns the most recent RSI value, or None on failure.
    """
    if len(closes) < period + 1:
        return None
    try:
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        # Initial average gain/loss over first period
        avg_gain = float(np.mean(gains[:period]))
        avg_loss = float(np.mean(losses[:period]))

        # Wilder smoothing for remaining values
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_gain == 0.0 and avg_loss == 0.0:
            # No price movement at all — RSI is undefined/neutral
            return None
        if avg_loss == 0.0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))
    except Exception as e:
        logger.error(f"Numpy RSI computation failed: {e}")
        return None


def _compute_macd_numpy(
    closes: np.ndarray,
    fast: int,
    slow: int,
    signal: int,
) -> tuple:
    """
    Pure numpy MACD implementation using exponential moving averages.
    Returns (macd_line, signal_line, histogram) last values, or (None, None, None).
    """
    if len(closes) < slow + signal:
        return None, None, None
    try:
        def ema(data: np.ndarray, span: int) -> np.ndarray:
            k = 2.0 / (span + 1)
            result = np.empty(len(data))
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = data[i] * k + result[i - 1] * (1.0 - k)
            return result

        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = ema(macd_line, signal)
        histogram = macd_line - signal_line
        return float(macd_line[-1]), float(signal_line[-1]), float(histogram[-1])
    except Exception as e:
        logger.error(f"Numpy MACD computation failed: {e}")
        return None, None, None


def _compute_rsi(closes: np.ndarray, period: int = DEFAULT_RSI_PERIOD) -> Optional[float]:
    """
    Compute RSI and return the most recent value.
    Returns None if insufficient data or computation fails.
    """
    if len(closes) < period + 1:
        return None

    if TALIB_AVAILABLE:
        try:
            rsi = talib.RSI(closes, timeperiod=period)
            # Last non-NaN value
            valid = rsi[~np.isnan(rsi)]
            return float(valid[-1]) if len(valid) > 0 else None
        except Exception as e:
            logger.warning(f"TA-Lib RSI failed: {e}, trying pandas-ta")

    # pandas-ta fallback
    try:
        import pandas as pd
        import pandas_ta as pta
        series = pd.Series(closes)
        rsi_series = pta.rsi(series, length=period)
        if rsi_series is None or rsi_series.empty:
            return None
        valid = rsi_series.dropna()
        return float(valid.iloc[-1]) if not valid.empty else None
    except Exception as e:
        logger.warning(f"pandas-ta RSI also failed: {e}, falling back to numpy")

    # Pure numpy fallback (always available)
    return _compute_rsi_numpy(closes, period)


def _compute_macd(
    closes: np.ndarray,
    fast: int = DEFAULT_MACD_FAST,
    slow: int = DEFAULT_MACD_SLOW,
    signal: int = DEFAULT_MACD_SIGNAL,
) -> tuple:
    """
    Compute MACD and return (macd_line, signal_line, histogram) last values.
    Returns (None, None, None) if insufficient data or computation fails.
    """
    if len(closes) < slow + signal:
        return None, None, None

    if TALIB_AVAILABLE:
        try:
            macd, signal_line, histogram = talib.MACD(
                closes, fastperiod=fast, slowperiod=slow, signalperiod=signal
            )
            # Get last non-NaN values
            valid_idx = ~(np.isnan(macd) | np.isnan(signal_line) | np.isnan(histogram))
            if not np.any(valid_idx):
                return None, None, None
            last_idx = np.where(valid_idx)[0][-1]
            return (
                float(macd[last_idx]),
                float(signal_line[last_idx]),
                float(histogram[last_idx]),
            )
        except Exception as e:
            logger.warning(f"TA-Lib MACD failed: {e}, trying pandas-ta")

    # pandas-ta fallback
    try:
        import pandas as pd
        import pandas_ta as pta
        series = pd.Series(closes)
        result = pta.macd(series, fast=fast, slow=slow, signal=signal)
        if result is None or result.empty:
            return None, None, None
        # pandas-ta MACD columns: MACD_{fast}_{slow}_{signal}, MACDh_{...}, MACDs_{...}
        col_macd = [c for c in result.columns if c.startswith("MACD_")][0]
        col_signal = [c for c in result.columns if c.startswith("MACDs_")][0]
        col_hist = [c for c in result.columns if c.startswith("MACDh_")][0]
        row = result.dropna().iloc[-1]
        return float(row[col_macd]), float(row[col_signal]), float(row[col_hist])
    except Exception as e:
        logger.warning(f"pandas-ta MACD also failed: {e}, falling back to numpy")

    # Pure numpy fallback (always available)
    return _compute_macd_numpy(closes, fast, slow, signal)


def _compute_sma(closes: np.ndarray, period: int) -> Optional[float]:
    """Return the most recent SMA value, or None if insufficient data."""
    if len(closes) < period:
        return None
    return float(np.mean(closes[-period:]))


def _compute_ema(closes: np.ndarray, period: int) -> Optional[float]:
    """
    Return the most recent EMA value using exponential smoothing.
    Returns None if insufficient data.
    """
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    ema = float(closes[0])
    for price in closes[1:]:
        ema = float(price) * k + ema * (1.0 - k)
    return ema


def _compute_bollinger_bands(
    closes: np.ndarray,
    period: int,
    num_std: float,
) -> tuple:
    """
    Compute Bollinger Bands upper and lower values.
    Returns (upper, lower) or (None, None) if insufficient data.
    """
    if len(closes) < period:
        return None, None
    window = closes[-period:]
    sma = float(np.mean(window))
    std = float(np.std(window, ddof=0))
    upper = sma + num_std * std
    lower = sma - num_std * std
    return upper, lower


class SignalGenerator:
    """
    Evaluates strategy configurations against OHLCV close prices.

    Usage:
        gen = SignalGenerator()
        signal = gen.evaluate('rsi_only', {'rsi_period': 14, 'rsi_oversold': 30}, closes)
    """

    def evaluate(
        self,
        strategy_type: str,
        config: dict,
        closes: np.ndarray,
    ) -> Signal:
        """
        Evaluate a strategy configuration against close prices.

        Args:
            strategy_type: One of 'rsi_only', 'macd_only', 'rsi_macd',
                           'bb_only', 'sma_crossover', 'ema_crossover'
            config: Strategy parameters dict
            closes: numpy array of close prices (float64), oldest first

        Returns:
            Signal.BUY, Signal.SELL, or Signal.HOLD

        Raises:
            ValueError: If strategy_type is not supported
        """
        supported = {"rsi_only", "macd_only", "rsi_macd", "bb_only", "sma_crossover", "ema_crossover"}
        if strategy_type not in supported:
            raise ValueError(
                f"Unsupported strategy type: {strategy_type!r}. "
                f"Supported: {sorted(supported)}"
            )

        min_candles = MIN_CANDLES.get(strategy_type, 26)
        if len(closes) < min_candles:
            logger.debug(
                f"Insufficient data for {strategy_type}: "
                f"{len(closes)} closes (need {min_candles}+), returning HOLD"
            )
            return Signal.HOLD

        if strategy_type == "rsi_only":
            return self._evaluate_rsi(config, closes)
        elif strategy_type == "macd_only":
            return self._evaluate_macd(config, closes)
        elif strategy_type == "rsi_macd":
            return self._evaluate_rsi_macd(config, closes)
        elif strategy_type == "bb_only":
            return self._evaluate_bb(config, closes)
        elif strategy_type == "sma_crossover":
            return self._evaluate_sma_crossover(config, closes)
        elif strategy_type == "ema_crossover":
            return self._evaluate_ema_crossover(config, closes)

        return Signal.HOLD

    def _evaluate_rsi(self, config: dict, closes: np.ndarray) -> Signal:
        """RSI-based signal: oversold -> BUY, overbought -> SELL."""
        period = int(config.get("rsi_period", DEFAULT_RSI_PERIOD))
        oversold = float(config.get("rsi_oversold", DEFAULT_RSI_OVERSOLD))
        overbought = float(config.get("rsi_overbought", DEFAULT_RSI_OVERBOUGHT))

        rsi = _compute_rsi(closes, period)
        if rsi is None:
            return Signal.HOLD

        logger.debug(f"RSI={rsi:.2f} (oversold={oversold}, overbought={overbought})")

        if rsi <= oversold:
            return Signal.BUY
        elif rsi >= overbought:
            return Signal.SELL
        return Signal.HOLD

    def _evaluate_macd(self, config: dict, closes: np.ndarray) -> Signal:
        """MACD crossover signal: macd > signal -> BUY, macd < signal -> SELL."""
        fast = int(config.get("macd_fast", DEFAULT_MACD_FAST))
        slow = int(config.get("macd_slow", DEFAULT_MACD_SLOW))
        signal_period = int(config.get("macd_signal", DEFAULT_MACD_SIGNAL))

        macd_val, signal_val, histogram = _compute_macd(closes, fast, slow, signal_period)
        if macd_val is None or signal_val is None:
            return Signal.HOLD

        logger.debug(f"MACD={macd_val:.4f} signal={signal_val:.4f} hist={histogram:.4f}")

        if macd_val > signal_val:
            return Signal.BUY
        elif macd_val < signal_val:
            return Signal.SELL
        return Signal.HOLD

    def _evaluate_rsi_macd(self, config: dict, closes: np.ndarray) -> Signal:
        """Combined RSI + MACD: both must agree for a signal."""
        rsi_signal = self._evaluate_rsi(config, closes)
        macd_signal = self._evaluate_macd(config, closes)

        # Both must agree for a trade signal
        if rsi_signal == Signal.BUY and macd_signal == Signal.BUY:
            return Signal.BUY
        elif rsi_signal == Signal.SELL and macd_signal == Signal.SELL:
            return Signal.SELL
        return Signal.HOLD

    def _evaluate_bb(self, config: dict, closes: np.ndarray) -> Signal:
        """Bollinger Bands signal: price < lower band → BUY, price > upper band → SELL."""
        period = int(config.get("bb_period", DEFAULT_BB_PERIOD))
        num_std = float(config.get("bb_std", DEFAULT_BB_STD))

        upper, lower = _compute_bollinger_bands(closes, period, num_std)
        if upper is None or lower is None:
            return Signal.HOLD

        current_price = float(closes[-1])
        logger.debug(f"BB price={current_price:.4f} upper={upper:.4f} lower={lower:.4f}")

        if current_price < lower:
            return Signal.BUY
        elif current_price > upper:
            return Signal.SELL
        return Signal.HOLD

    def _evaluate_sma_crossover(self, config: dict, closes: np.ndarray) -> Signal:
        """SMA crossover: fast SMA > slow SMA → BUY, fast SMA < slow SMA → SELL."""
        fast_period = int(config.get("sma_fast", DEFAULT_SMA_FAST))
        slow_period = int(config.get("sma_slow", DEFAULT_SMA_SLOW))

        fast_sma = _compute_sma(closes, fast_period)
        slow_sma = _compute_sma(closes, slow_period)

        if fast_sma is None or slow_sma is None:
            return Signal.HOLD

        logger.debug(f"SMA fast={fast_sma:.4f} slow={slow_sma:.4f}")

        if fast_sma > slow_sma:
            return Signal.BUY
        elif fast_sma < slow_sma:
            return Signal.SELL
        return Signal.HOLD

    def _evaluate_ema_crossover(self, config: dict, closes: np.ndarray) -> Signal:
        """EMA crossover: fast EMA > slow EMA → BUY, fast EMA < slow EMA → SELL."""
        fast_period = int(config.get("ema_fast", DEFAULT_EMA_FAST))
        slow_period = int(config.get("ema_slow", DEFAULT_EMA_SLOW))

        fast_ema = _compute_ema(closes, fast_period)
        slow_ema = _compute_ema(closes, slow_period)

        if fast_ema is None or slow_ema is None:
            return Signal.HOLD

        logger.debug(f"EMA fast={fast_ema:.4f} slow={slow_ema:.4f}")

        if fast_ema > slow_ema:
            return Signal.BUY
        elif fast_ema < slow_ema:
            return Signal.SELL
        return Signal.HOLD
