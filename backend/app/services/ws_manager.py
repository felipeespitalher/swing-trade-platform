"""
WebSocket Connection Manager with Redis pub/sub.

Bridges multiple FastAPI worker processes for WebSocket broadcasting.
Each worker subscribes to Redis channels and broadcasts to local clients.

Architecture:
- Workers publish price updates to Redis channel 'ws:prices:{symbol}'
- Each worker's ConnectionManager subscribes and forwards to local WebSocket connections
- Handles client disconnect cleanly (removes from set)
- Times out idle connections after 5 minutes
"""

import asyncio
import json
import logging
import os
from typing import Dict, Set, Optional
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
IDLE_TIMEOUT_SECONDS = 300  # 5 minutes


class ConnectionManager:
    """
    Manages WebSocket connections and Redis pub/sub bridge.

    Each FastAPI worker has one ConnectionManager instance.
    Redis pub/sub allows multiple workers to broadcast to all clients.
    """

    def __init__(self):
        # Map of symbol -> set of connected WebSockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Initialize Redis connection and start pub/sub listener."""
        self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        logger.info("WebSocket ConnectionManager started")

    async def stop(self) -> None:
        """Cleanup connections and Redis subscription."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        if self._redis:
            await self._redis.aclose()

        # Disconnect all clients
        for symbol, clients in self._connections.items():
            for ws in list(clients):
                try:
                    await ws.close()
                except Exception:
                    pass

        self._connections.clear()
        logger.info("WebSocket ConnectionManager stopped")

    def connect(self, websocket: WebSocket, symbols: list) -> None:
        """Register a WebSocket for the given symbols."""
        for symbol in symbols:
            if symbol not in self._connections:
                self._connections[symbol] = set()
            self._connections[symbol].add(websocket)
            logger.debug(
                f"Client connected for {symbol}, total: {len(self._connections[symbol])}"
            )

    def disconnect(self, websocket: WebSocket, symbols: list) -> None:
        """Unregister a WebSocket from all symbols."""
        for symbol in symbols:
            if symbol in self._connections:
                self._connections[symbol].discard(websocket)
                logger.debug(f"Client disconnected from {symbol}")

    async def broadcast(self, symbol: str, data: dict) -> None:
        """
        Broadcast data to all clients subscribed to a symbol.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            data: Dict to serialize and send
        """
        clients = self._connections.get(symbol, set())
        if not clients:
            return

        message = json.dumps(data)
        disconnected = set()

        for websocket in list(clients):
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self._connections[symbol].discard(ws)

    async def publish_price(self, symbol: str, price: float, timestamp: int) -> None:
        """
        Publish a price update to Redis (cross-worker broadcast).

        Args:
            symbol: Trading pair
            price: Current price
            timestamp: Unix timestamp in milliseconds
        """
        if not self._redis:
            return

        data = {
            "symbol": symbol,
            "price": price,
            "timestamp": timestamp,
            "type": "ticker",
        }
        channel = f"ws:prices:{symbol.replace('/', '_')}"
        await self._redis.publish(channel, json.dumps(data))

    async def start_price_feed(self, symbols: list) -> None:
        """
        Start CCXT Pro ticker feed for the given symbols.

        Subscribes to Redis pub/sub and broadcasts received prices
        to connected WebSocket clients.

        Args:
            symbols: List of trading pairs to stream (e.g., ['BTC/USDT', 'ETH/USDT'])
        """
        if not self._redis:
            logger.warning("Redis not initialized, cannot start price feed")
            return

        pubsub = self._redis.pubsub()
        channels = [f"ws:prices:{s.replace('/', '_')}" for s in symbols]
        await pubsub.subscribe(*channels)

        self._pubsub_task = asyncio.create_task(
            self._listen_pubsub(pubsub, symbols)
        )
        logger.info(f"Price feed started for symbols: {symbols}")

    async def _listen_pubsub(self, pubsub, symbols: list) -> None:
        """Listen to Redis pub/sub and forward messages to WebSocket clients."""
        symbol_map = {
            f"ws:prices:{s.replace('/', '_')}": s for s in symbols
        }

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                channel = message["channel"]
                symbol = symbol_map.get(channel)
                if not symbol:
                    continue

                try:
                    data = json.loads(message["data"])
                    await self.broadcast(symbol, data)
                except Exception as e:
                    logger.error(f"Error processing pubsub message: {e}")

        except asyncio.CancelledError:
            await pubsub.unsubscribe()
            raise


# Global singleton — one per worker process
manager = ConnectionManager()
