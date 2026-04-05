"""
Celery application configuration with Redis broker and celery-redbeat scheduler.

Configuration:
- Broker: Redis DB 0 (task queue)
- Result backend: Redis DB 1 (task results)
- Beat scheduler: RedBeatScheduler (Redis DB 2, survives restarts)
- Timezone: UTC (all timestamps in UTC)
"""

import os
import logging
from celery import Celery
from kombu import Queue

logger = logging.getLogger(__name__)

# Redis connection URLs from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDBEAT_REDIS_URL = os.getenv("REDBEAT_REDIS_URL", "redis://localhost:6379/2")

# Create Celery application
celery_app = Celery(
    "swing_trade",
    broker=REDIS_URL,
    backend=REDIS_URL.replace("/0", "/1"),
    include=[
        "app.tasks.ohlcv_tasks",
        "app.tasks.paper_trading_tasks",
    ],
)

# Configuration
celery_app.conf.update(
    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Task routing
    task_queues=(
        Queue("default"),
        Queue("ohlcv"),
        Queue("paper_trading"),
    ),
    task_default_queue="default",

    # Beat scheduler: use redbeat for Redis-backed schedule
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=REDBEAT_REDIS_URL,
    redbeat_key_prefix="redbeat:",

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    # Beat schedule: OHLCV fetch for BTC/USDT and ETH/USDT
    beat_schedule={
        "fetch-btc-usdt-1h": {
            "task": "app.tasks.ohlcv_tasks.fetch_and_store_ohlcv",
            "schedule": 3600.0,  # Every hour
            "args": ("BTC/USDT", "1h"),
            "options": {"queue": "ohlcv"},
        },
        "fetch-btc-usdt-4h": {
            "task": "app.tasks.ohlcv_tasks.fetch_and_store_ohlcv",
            "schedule": 14400.0,  # Every 4 hours
            "args": ("BTC/USDT", "4h"),
            "options": {"queue": "ohlcv"},
        },
        "fetch-btc-usdt-1d": {
            "task": "app.tasks.ohlcv_tasks.fetch_and_store_ohlcv",
            "schedule": 86400.0,  # Every day
            "args": ("BTC/USDT", "1d"),
            "options": {"queue": "ohlcv"},
        },
        "fetch-eth-usdt-1h": {
            "task": "app.tasks.ohlcv_tasks.fetch_and_store_ohlcv",
            "schedule": 3600.0,
            "args": ("ETH/USDT", "1h"),
            "options": {"queue": "ohlcv"},
        },
        "fetch-eth-usdt-4h": {
            "task": "app.tasks.ohlcv_tasks.fetch_and_store_ohlcv",
            "schedule": 14400.0,
            "args": ("ETH/USDT", "4h"),
            "options": {"queue": "ohlcv"},
        },
        "fetch-eth-usdt-1d": {
            "task": "app.tasks.ohlcv_tasks.fetch_and_store_ohlcv",
            "schedule": 86400.0,
            "args": ("ETH/USDT", "1d"),
            "options": {"queue": "ohlcv"},
        },
        "evaluate-all-active-strategies": {
            "task": "app.tasks.paper_trading_tasks.evaluate_all_active_strategies",
            "schedule": 300.0,  # Every 5 minutes
            "options": {"queue": "paper_trading"},
        },
    },
)

logger.info("Celery application configured with RedBeat scheduler")
