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
                _evaluate_strategy(db, strategy)
                evaluated += 1
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


def _evaluate_strategy(db, strategy) -> None:
    """
    Evaluate a single strategy and trigger paper trading if signal fires.

    This is a synchronous helper to keep the Celery task clean.
    Signal generator and paper trading engine will be integrated in Wave 3.
    """
    from app.services.ohlcv_service import OHLCVService

    # Get strategy config
    config = strategy.config or {}
    symbol = config.get("symbol", "BTC/USDT")
    timeframe = config.get("timeframe", "1h")

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
        return

    # Signal generator will be integrated in Wave 3a (P2-18)
    # For now, log that evaluation ran
    logger.debug(
        f"Strategy {strategy.id} evaluated: {len(closes)} closes available for {symbol} {timeframe}"
    )
