"""
Celery tasks for paper trading signal evaluation.
"""

import logging
from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.paper_trading_tasks.evaluate_all_active_strategies",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
    queue="paper_trading",
)
def evaluate_all_active_strategies(self) -> dict:
    """
    Evaluate signals for all active paper trading strategies.

    Runs every 5 minutes (scheduled in celery_app beat_schedule).
    For each active strategy:
    1. Fetch OHLCV closes from DB
    2. Run signal generator
    3. If BUY/SELL signal, trigger paper trading engine

    Returns:
        Dict with count of strategies evaluated and signals emitted
    """
    from app.models.strategy import Strategy

    db = SessionLocal()
    try:
        # Load all active strategies (is_active=True matches the Strategy model field)
        active_strategies = (
            db.query(Strategy)
            .filter(Strategy.is_active == True)  # noqa: E712
            .all()
        )

        if not active_strategies:
            logger.debug("No active strategies to evaluate")
            return {"evaluated": 0, "signals": 0}

        evaluated = 0
        signals_emitted = 0

        for strategy in active_strategies:
            try:
                signal = _evaluate_strategy(db, strategy)
                evaluated += 1
                if signal in ("BUY", "SELL"):
                    signals_emitted += 1
            except Exception as e:
                logger.error(
                    f"Error evaluating strategy {strategy.id}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"Evaluated {evaluated}/{len(active_strategies)} active strategies, "
            f"{signals_emitted} signals emitted"
        )
        return {"evaluated": evaluated, "signals": signals_emitted}

    finally:
        db.close()


def _evaluate_strategy(db, strategy) -> str:
    """
    Evaluate a single strategy: fetch closes → signal → trade if BUY/SELL.

    Returns the signal string ('BUY', 'SELL', 'HOLD').
    """
    from app.services.ohlcv_service import OHLCVService
    from app.services.signal_generator import SignalGenerator, Signal
    from app.services.paper_trading_engine import PaperTradingEngine
    from app.services.paper_trading_session import PaperTradingSessionManager
    from app.services.trade_service import TradeService
    from decimal import Decimal

    # Get strategy config — symbol, timeframe and type live inside the config JSON.
    # strategy.type is the top-level ORM column; it takes precedence for strategy_type.
    config = strategy.config or {}
    symbol = config.get("symbol", "BTC/USDT")
    timeframe = config.get("timeframe", "1h")
    # strategy.type is a real model column; fall back to config key for flexibility
    strategy_type = getattr(strategy, "type", None) or config.get("type", "rsi_only")

    # Fetch closes for signal evaluation
    closes = OHLCVService.get_closes_array(
        db=db,
        symbol=symbol,
        timeframe=timeframe,
        limit=200,
    )

    if len(closes) < 26:
        logger.debug(
            f"Insufficient data for strategy {strategy.id}: "
            f"{len(closes)} candles (need 26+)"
        )
        return Signal.HOLD.value

    # Evaluate signal using the strategy type and config parameters
    gen = SignalGenerator()
    try:
        signal = gen.evaluate(strategy_type, config, closes)
    except ValueError as e:
        logger.warning(f"Strategy {strategy.id}: signal evaluation error: {e}")
        return Signal.HOLD.value

    logger.debug(f"Strategy {strategy.id} ({symbol} {timeframe}): signal={signal}")

    if signal == Signal.HOLD:
        return signal.value

    # Retrieve active paper trading session from Redis
    session_mgr = PaperTradingSessionManager()
    portfolio = session_mgr.get_session(str(strategy.id))

    if portfolio is None:
        # No active session — skip trade execution until session is started via API
        logger.debug(
            f"No active session for strategy {strategy.id}, skipping {signal} signal"
        )
        return signal.value

    engine = PaperTradingEngine(portfolio)

    # Fetch the most recent candle to use its close as fill price.
    # Simulates candle N+1 open without lookahead bias risk at this resolution.
    candles = OHLCVService.get_candles(db=db, symbol=symbol, timeframe=timeframe, limit=2)
    if not candles:
        return signal.value

    # CCXT candle format: [timestamp_ms, open, high, low, close, volume] — index 4 = close
    fill_price = Decimal(str(candles[-1][4]))

    trade_created = False

    if signal == Signal.BUY and symbol not in portfolio.open_positions:
        position = engine.simulate_entry(symbol, fill_price)
        if position:
            try:
                trade_dict = {
                    "symbol": symbol,
                    "entry_price": float(position.entry_price),
                    "quantity": float(position.quantity),
                }
                TradeService.create_paper_trade(
                    db=db,
                    strategy_id=str(strategy.id),
                    trade_dict=trade_dict,
                )
                trade_created = True
                logger.info(
                    f"Strategy {strategy.id}: opened position {symbol} @ {position.entry_price}"
                )
            except Exception as e:
                logger.error(f"Strategy {strategy.id}: failed to persist entry: {e}")

    elif signal == Signal.SELL and symbol in portfolio.open_positions:
        trade_result = engine.simulate_exit(symbol, fill_price, reason="signal")
        if trade_result:
            try:
                open_trades = TradeService.get_open_trades(
                    db=db,
                    strategy_id=str(strategy.id),
                )
                if open_trades:
                    TradeService.close_paper_trade(
                        db=db,
                        trade_id=str(open_trades[0].id),
                        exit_price=Decimal(str(trade_result["exit_price"])),
                        pnl=Decimal(str(trade_result["pnl"])),
                        pnl_pct=Decimal(str(trade_result["pnl_pct"])),
                        reason="signal",
                    )
                    trade_created = True
                    logger.info(
                        f"Strategy {strategy.id}: closed position {symbol} @ "
                        f"{trade_result['exit_price']}, pnl={trade_result['pnl']:.4f}"
                    )
            except Exception as e:
                logger.error(f"Strategy {strategy.id}: failed to persist exit: {e}")

    # Persist updated portfolio state to Redis after any trade activity
    if trade_created or signal != Signal.HOLD:
        try:
            session_mgr.save_session(portfolio)
        except Exception as e:
            logger.warning(f"Strategy {strategy.id}: failed to save session: {e}")

    return signal.value
