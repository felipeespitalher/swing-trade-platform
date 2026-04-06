"""
WebSocket price feed endpoint.

Endpoint:
- WS /api/ws/prices?symbols=BTC/USDT,ETH/USDT&token=<jwt>

Authentication:
- JWT extracted from ?token= query parameter
- Unauthenticated connections rejected with code 4001

Usage:
- Client connects with: ws://localhost:8000/api/ws/prices?symbols=BTC/USDT&token=<jwt>
- Server streams: {"symbol": "BTC/USDT", "price": 42300.0, "timestamp": 1704067200000, "type": "ticker"}
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from app.core.security import verify_token
from app.services.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

SUPPORTED_SYMBOLS = {"BTC/USDT", "ETH/USDT"}


def _validate_jwt_token(token: str) -> bool:
    """
    Validate a JWT access token for WebSocket authentication.

    Uses the project's existing verify_token() from app.core.security,
    which validates signature, expiry, and token type.

    Args:
        token: JWT token string from query param

    Returns:
        True if valid access token, False otherwise
    """
    if not token:
        return False
    payload = verify_token(token, token_type="access")
    return payload is not None


@router.websocket("/api/ws/prices")
async def websocket_price_feed(
    websocket: WebSocket,
    symbols: str = Query("BTC/USDT", description="Comma-separated symbols"),
    token: str = Query("", description="JWT access token"),
):
    """
    WebSocket endpoint for real-time price streaming.

    Authenticates via ?token= query parameter.
    Streams ticker data for requested symbols.
    """
    # Authenticate before accepting connection
    if not _validate_jwt_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Parse and validate symbols
    requested_symbols = [s.strip().upper() for s in symbols.split(",")]
    valid_symbols = [s for s in requested_symbols if s in SUPPORTED_SYMBOLS]

    if not valid_symbols:
        await websocket.close(code=4002, reason="No valid symbols requested")
        return

    # Accept the WebSocket connection
    await websocket.accept()
    manager.connect(websocket, valid_symbols)

    logger.info(f"WebSocket client connected for symbols: {valid_symbols}")

    try:
        # Keep connection alive — client sends pings
        while True:
            try:
                # Wait for client message (ping/pong or close)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,  # 30s timeout per receive
                )
                # Echo pings
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from {valid_symbols}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, valid_symbols)
