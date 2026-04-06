"""
Unit tests for Celery task modules: ohlcv_tasks and paper_trading_tasks.

Tests are executed synchronously by calling task functions directly (not via .delay()).
All external dependencies (BinanceAdapter, OHLCVService, DB, asyncio.run) are mocked.
"""

import uuid
from decimal import Decimal
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

# Import task modules at module level so patch() can resolve them correctly
import app.tasks.ohlcv_tasks as ohlcv_tasks_module
import app.tasks.paper_trading_tasks as paper_trading_tasks_module
from app.tasks.ohlcv_tasks import (
    fetch_and_store_ohlcv,
    backfill_ohlcv,
    DEFAULT_SYMBOLS,
    DEFAULT_TIMEFRAMES,
)
from app.tasks.paper_trading_tasks import (
    evaluate_all_active_strategies,
    _evaluate_strategy,
)
from app.tasks.celery_app import celery_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candle(ts=1_000_000, close=50000.0):
    """Return a CCXT-format candle list."""
    return [ts, 49000.0, 51000.0, 48500.0, close, 1234.5]


def make_strategy(strategy_id=None, is_active=True, config=None):
    """Return a mock Strategy ORM object."""
    s = MagicMock()
    s.id = strategy_id or uuid.uuid4()
    s.is_active = is_active
    s.config = config or {"symbol": "BTC/USDT", "timeframe": "1h"}
    return s


# ---------------------------------------------------------------------------
# P2-13/P2-14 – fetch_and_store_ohlcv
# ---------------------------------------------------------------------------

class TestFetchAndStoreOhlcv:

    def test_fetch_and_store_ohlcv_inserts_candles(self):
        """Task returns inserted count when BinanceAdapter returns candles."""
        candles = [make_candle(i, 50000.0 + i) for i in range(5)]

        with patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch", return_value=5) as mock_upsert, \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_asyncio.run.return_value = candles
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            result = fetch_and_store_ohlcv.run("BTC/USDT", "1h")

        assert result == {"symbol": "BTC/USDT", "timeframe": "1h", "inserted": 5}
        mock_upsert.assert_called_once()
        mock_db.close.assert_called_once()

    def test_fetch_and_store_ohlcv_empty_candles(self):
        """Task returns inserted=0 when adapter returns empty list."""
        with patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch") as mock_upsert, \
             patch.object(ohlcv_tasks_module, "SessionLocal"):

            mock_asyncio.run.return_value = []

            result = fetch_and_store_ohlcv.run("ETH/USDT", "4h")

        assert result == {"symbol": "ETH/USDT", "timeframe": "4h", "inserted": 0}
        mock_upsert.assert_not_called()

    def test_fetch_and_store_ohlcv_uses_correct_exchange(self):
        """upsert_batch is always called with exchange='binance'."""
        candles = [make_candle()]

        with patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch", return_value=1) as mock_upsert, \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_asyncio.run.return_value = candles
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            fetch_and_store_ohlcv.run("BTC/USDT", "1h")

        _, kwargs = mock_upsert.call_args
        assert kwargs["exchange"] == "binance"

    def test_fetch_and_store_ohlcv_passes_symbol_and_timeframe_to_upsert(self):
        """upsert_batch receives the same symbol and timeframe passed to the task."""
        candles = [make_candle()]

        with patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch", return_value=1) as mock_upsert, \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_asyncio.run.return_value = candles
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            fetch_and_store_ohlcv.run("ETH/USDT", "4h")

        _, kwargs = mock_upsert.call_args
        assert kwargs["symbol"] == "ETH/USDT"
        assert kwargs["timeframe"] == "4h"

    def test_fetch_and_store_ohlcv_closes_db_session_on_success(self):
        """DB session is closed even when upsert succeeds."""
        candles = [make_candle()]

        with patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch", return_value=1), \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_asyncio.run.return_value = candles
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            fetch_and_store_ohlcv.run("BTC/USDT", "1d")

        mock_db.close.assert_called_once()

    def test_fetch_and_store_retries_on_exception(self):
        """Task is configured with autoretry_for=(Exception,) and max_retries=3."""
        assert Exception in fetch_and_store_ohlcv.autoretry_for
        assert fetch_and_store_ohlcv.max_retries == 3


# ---------------------------------------------------------------------------
# P2-13/P2-14 – backfill_ohlcv
# ---------------------------------------------------------------------------

class TestBackfillOhlcv:

    def test_backfill_ohlcv_skips_if_data_exists(self):
        """Backfill skips a symbol/timeframe when count_candles returns > 0."""
        with patch.object(ohlcv_tasks_module.OHLCVService, "count_candles", return_value=100), \
             patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch") as mock_upsert, \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            result = backfill_ohlcv.run("BTC/USDT", "1h")

        mock_asyncio.run.assert_not_called()
        mock_upsert.assert_not_called()
        assert result["BTC/USDT_1h"]["skipped"] is True
        assert result["BTC/USDT_1h"]["existing"] == 100

    def test_backfill_ohlcv_fetches_if_empty(self):
        """Backfill calls fetch_ohlcv_paginated when count_candles returns 0."""
        candles = [make_candle(i) for i in range(10)]

        with patch.object(ohlcv_tasks_module.OHLCVService, "count_candles", return_value=0), \
             patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch", return_value=10), \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_asyncio.run.return_value = candles
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            result = backfill_ohlcv.run("BTC/USDT", "1h")

        mock_asyncio.run.assert_called_once()
        assert result["BTC/USDT_1h"]["inserted"] == 10
        assert result["BTC/USDT_1h"]["total_fetched"] == 10

    def test_backfill_ohlcv_single_symbol_timeframe(self):
        """When called with explicit symbol+timeframe, only that pair is processed."""
        with patch.object(ohlcv_tasks_module.OHLCVService, "count_candles", return_value=0) as mock_count, \
             patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch", return_value=1), \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_asyncio.run.return_value = [make_candle()]
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            result = backfill_ohlcv.run("ETH/USDT", "4h")

        # Only one pair queried
        mock_count.assert_called_once_with(mock_db, "ETH/USDT", "4h", "binance")
        assert list(result.keys()) == ["ETH/USDT_4h"]

    def test_backfill_ohlcv_processes_all_defaults_when_no_args(self):
        """Without args, backfill processes all DEFAULT_SYMBOLS x DEFAULT_TIMEFRAMES."""
        expected_pairs = len(DEFAULT_SYMBOLS) * len(DEFAULT_TIMEFRAMES)

        with patch.object(ohlcv_tasks_module.OHLCVService, "count_candles", return_value=0), \
             patch.object(ohlcv_tasks_module, "asyncio") as mock_asyncio, \
             patch.object(ohlcv_tasks_module.OHLCVService, "upsert_batch", return_value=1), \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_asyncio.run.return_value = [make_candle()]
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            result = backfill_ohlcv.run()

        assert len(result) == expected_pairs

    def test_backfill_ohlcv_closes_db_session_on_success(self):
        """DB session is always closed after backfill, even when all pairs skipped."""
        with patch.object(ohlcv_tasks_module.OHLCVService, "count_candles", return_value=50), \
             patch.object(ohlcv_tasks_module, "SessionLocal") as mock_session_cls:

            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            backfill_ohlcv.run("BTC/USDT", "1h")

        mock_db.close.assert_called_once()


# ---------------------------------------------------------------------------
# P2-15 – evaluate_all_active_strategies
# ---------------------------------------------------------------------------

class TestEvaluateAllActiveStrategies:

    def test_evaluate_all_active_strategies_no_active(self):
        """Returns evaluated=0, signals=0 when no active strategies exist."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        with patch.object(paper_trading_tasks_module, "SessionLocal", return_value=mock_db):
            result = evaluate_all_active_strategies.run()

        assert result == {"evaluated": 0, "signals": 0}
        mock_db.close.assert_called_once()

    def test_evaluate_all_active_strategies_calls_evaluate(self):
        """With 2 active strategies, evaluated=2 is returned."""
        strategies = [make_strategy(is_active=True), make_strategy(is_active=True)]
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = strategies

        with patch.object(paper_trading_tasks_module, "SessionLocal", return_value=mock_db), \
             patch.object(paper_trading_tasks_module, "_evaluate_strategy") as mock_eval:

            result = evaluate_all_active_strategies.run()

        assert result["evaluated"] == 2
        assert mock_eval.call_count == 2
        mock_db.close.assert_called_once()

    def test_evaluate_all_active_strategies_continues_on_single_error(self):
        """Evaluation continues for remaining strategies if one raises an exception."""
        strategies = [make_strategy(), make_strategy(), make_strategy()]
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = strategies

        call_count = 0

        def side_effect(db, strategy):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("simulated error")

        with patch.object(paper_trading_tasks_module, "SessionLocal", return_value=mock_db), \
             patch.object(paper_trading_tasks_module, "_evaluate_strategy", side_effect=side_effect):

            result = evaluate_all_active_strategies.run()

        # 2 of 3 succeed (one errored)
        assert result["evaluated"] == 2

    def test_evaluate_all_active_strategies_closes_db_on_success(self):
        """DB session is closed after evaluation regardless of outcome."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        with patch.object(paper_trading_tasks_module, "SessionLocal", return_value=mock_db):
            evaluate_all_active_strategies.run()

        mock_db.close.assert_called_once()


# ---------------------------------------------------------------------------
# P2-15 – _evaluate_strategy helper
# ---------------------------------------------------------------------------

class TestEvaluateStrategy:

    def test_evaluate_strategy_skips_insufficient_data(self):
        """_evaluate_strategy returns without error when closes array has < 26 elements."""
        strategy = make_strategy(config={"symbol": "BTC/USDT", "timeframe": "1h"})
        mock_db = MagicMock()

        short_closes = np.array([50000.0] * 10, dtype=np.float64)

        # OHLCVService is imported locally inside _evaluate_strategy, patch at source
        with patch("app.services.ohlcv_service.OHLCVService.get_closes_array",
                   return_value=short_closes):
            # Should not raise
            _evaluate_strategy(mock_db, strategy)

    def test_evaluate_strategy_uses_config_symbol_and_timeframe(self):
        """_evaluate_strategy reads symbol and timeframe from strategy.config."""
        strategy = make_strategy(config={"symbol": "ETH/USDT", "timeframe": "4h"})
        mock_db = MagicMock()

        sufficient_closes = np.array([3000.0] * 30, dtype=np.float64)

        with patch("app.services.ohlcv_service.OHLCVService.get_closes_array",
                   return_value=sufficient_closes) as mock_get:

            _evaluate_strategy(mock_db, strategy)

        mock_get.assert_called_once_with(
            db=mock_db,
            symbol="ETH/USDT",
            timeframe="4h",
            limit=200,
        )

    def test_evaluate_strategy_defaults_to_btc_usdt_1h_when_config_empty(self):
        """When strategy.config is empty, defaults to BTC/USDT 1h."""
        strategy = make_strategy(config={})
        mock_db = MagicMock()

        with patch("app.services.ohlcv_service.OHLCVService.get_closes_array",
                   return_value=np.array([], dtype=np.float64)) as mock_get:

            _evaluate_strategy(mock_db, strategy)

        mock_get.assert_called_once_with(
            db=mock_db,
            symbol="BTC/USDT",
            timeframe="1h",
            limit=200,
        )

    def test_evaluate_strategy_buy_signal_creates_trade(self):
        """BUY signal from SignalGenerator → simulate_entry → TradeService.create_paper_trade called."""
        from app.services.signal_generator import Signal
        from app.services.paper_trading_engine import PaperPortfolio

        strategy_id = uuid.uuid4()
        strategy = make_strategy(
            strategy_id=strategy_id,
            config={"symbol": "BTC/USDT", "timeframe": "1h", "type": "rsi_only"},
        )
        # Ensure strategy.type returns a clean string so SignalGenerator accepts it
        strategy.type = "rsi_only"

        mock_db = MagicMock()
        sufficient_closes = np.array([50000.0] * 50, dtype=np.float64)
        # Candle list: [timestamp_ms, open, high, low, close, volume]
        mock_candles = [[1_000_000, 49000.0, 51000.0, 48500.0, 50100.0, 1234.5]]

        # Build a real PaperPortfolio with no open positions
        portfolio = PaperPortfolio(strategy_id=strategy_id, initial_balance=Decimal("10000"))

        mock_position = MagicMock()
        mock_position.entry_price = Decimal("50200.0")
        mock_position.quantity = Decimal("0.01")

        with patch("app.services.ohlcv_service.OHLCVService.get_closes_array",
                   return_value=sufficient_closes), \
             patch("app.services.ohlcv_service.OHLCVService.get_candles",
                   return_value=mock_candles), \
             patch("app.services.signal_generator.SignalGenerator.evaluate",
                   return_value=Signal.BUY), \
             patch("app.services.paper_trading_session.PaperTradingSessionManager.get_session",
                   return_value=portfolio), \
             patch("app.services.paper_trading_session.PaperTradingSessionManager.save_session"), \
             patch("app.services.paper_trading_engine.PaperTradingEngine.simulate_entry",
                   return_value=mock_position) as mock_entry, \
             patch("app.services.trade_service.TradeService.create_paper_trade") as mock_create:

            result = _evaluate_strategy(mock_db, strategy)

        assert result == "BUY"
        mock_entry.assert_called_once()
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs["strategy_id"] == str(strategy_id)
        assert call_kwargs.kwargs["trade_dict"]["symbol"] == "BTC/USDT"

    def test_evaluate_strategy_hold_signal_no_trade(self):
        """HOLD signal from SignalGenerator → TradeService.create_paper_trade NOT called."""
        from app.services.signal_generator import Signal

        strategy_id = uuid.uuid4()
        strategy = make_strategy(
            strategy_id=strategy_id,
            config={"symbol": "BTC/USDT", "timeframe": "1h", "type": "rsi_only"},
        )
        strategy.type = "rsi_only"

        mock_db = MagicMock()
        sufficient_closes = np.array([50000.0] * 50, dtype=np.float64)

        with patch("app.services.ohlcv_service.OHLCVService.get_closes_array",
                   return_value=sufficient_closes), \
             patch("app.services.signal_generator.SignalGenerator.evaluate",
                   return_value=Signal.HOLD), \
             patch("app.services.trade_service.TradeService.create_paper_trade") as mock_create:

            result = _evaluate_strategy(mock_db, strategy)

        assert result == "HOLD"
        mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# Task configuration assertions
# ---------------------------------------------------------------------------

class TestTaskConfiguration:

    def test_fetch_and_store_ohlcv_task_name(self):
        """Task has canonical name used in beat_schedule."""
        assert fetch_and_store_ohlcv.name == "app.tasks.ohlcv_tasks.fetch_and_store_ohlcv"

    def test_backfill_ohlcv_task_name(self):
        """Task has canonical name."""
        assert backfill_ohlcv.name == "app.tasks.ohlcv_tasks.backfill_ohlcv"

    def test_evaluate_all_active_strategies_task_name(self):
        """Task has canonical name used in beat_schedule."""
        assert evaluate_all_active_strategies.name == (
            "app.tasks.paper_trading_tasks.evaluate_all_active_strategies"
        )

    def test_celery_app_beat_schedule_contains_btc_1h(self):
        """Beat schedule includes BTC/USDT 1h periodic fetch."""
        schedule = celery_app.conf.beat_schedule
        assert "fetch-btc-usdt-1h" in schedule
        assert schedule["fetch-btc-usdt-1h"]["args"] == ("BTC/USDT", "1h")
        assert schedule["fetch-btc-usdt-1h"]["schedule"] == 3600.0

    def test_celery_app_beat_schedule_contains_strategy_evaluation(self):
        """Beat schedule includes strategy evaluation every 5 minutes."""
        schedule = celery_app.conf.beat_schedule
        assert "evaluate-all-active-strategies" in schedule
        assert schedule["evaluate-all-active-strategies"]["schedule"] == 300.0

    def test_celery_app_uses_utc_timezone(self):
        """Celery is configured to use UTC timezone."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_app_uses_redbeat_scheduler(self):
        """Celery beat scheduler is configured to use RedBeatScheduler."""
        assert celery_app.conf.beat_scheduler == "redbeat.RedBeatScheduler"

    def test_backfill_ohlcv_has_retry_config(self):
        """backfill_ohlcv is configured with autoretry and retry_kwargs max_retries=2."""
        assert Exception in backfill_ohlcv.autoretry_for
        # retry_kwargs stores the max_retries value passed to autoretry
        assert backfill_ohlcv.retry_kwargs.get("max_retries") == 2
