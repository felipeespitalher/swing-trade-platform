"""
FastAPI application entry point for Swing Trade Automation Platform.

This module initializes the FastAPI application with middleware,
exception handlers, and core route registration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, users, exchange_keys, health, audit
from app.api import strategies
from app.api.backtest import router as backtest_router
from app.api.dashboard import router as dashboard_router
from app.api.market_data import router as market_data_router
from app.api.paper_trading import router as paper_trading_router
from app.api.ws import router as ws_router
from app.core.logging import setup_logging
from app.middleware.logging import LoggingMiddleware
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.services.monitoring import MonitoringService
from app.services.ws_manager import manager as ws_manager

# Configure logging using structured logging setup
logger = setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    logger.info("Starting Swing Trade Automation Platform API")
    await ws_manager.start()
    yield
    await ws_manager.stop()
    logger.info("Shutting down Swing Trade Automation Platform API")


# Create FastAPI application
app = FastAPI(
    title="Swing Trade Automation Platform API",
    description="API for automated swing trading analysis and execution",
    version="0.1.0",
    lifespan=lifespan,
)

# Add logging middleware (should be first in chain)
app.add_middleware(LoggingMiddleware)

# Add audit middleware (after logging)
app.add_middleware(AuditMiddleware)

# Add CSRF protection middleware
app.add_middleware(CSRFMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Configure CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Request-ID"],
)




# Root endpoint
@app.get("/")
async def root() -> dict:
    """
    Root API endpoint.

    Returns:
        dict: API information
    """
    return {
        "message": "Swing Trade Automation Platform API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """
    Global exception handler.

    Args:
        request: The request object
        exc: The exception that was raised

    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include API routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(exchange_keys.router)
app.include_router(audit.router)
app.include_router(health.router)  # Health and metrics endpoints
app.include_router(strategies.router)
app.include_router(market_data_router)
app.include_router(paper_trading_router)
app.include_router(ws_router)
app.include_router(backtest_router)
app.include_router(dashboard_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
