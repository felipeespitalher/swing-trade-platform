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
from app.api import strategies, portfolios
from app.api.backtest import router as backtest_router
from app.api.dashboard import router as dashboard_router
from app.api.market_data import router as market_data_router
from app.api.paper_trading import router as paper_trading_router
from app.api.ws import router as ws_router
from app.core.config import settings
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


def _run_migrations():
    """Run SQL migrations on startup, skipping unsupported statements gracefully."""
    import os, re, psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    # Extensions that may not be available on managed PostgreSQL
    OPTIONAL_EXTENSIONS = {"timescaledb"}
    # Statements that depend on TimescaleDB
    SKIP_PATTERNS = [
        "create_hypertable",
        "timescaledb_information",
        "timescaledb.compress",
        "add_compression_policy",
        "add_retention_policy",
    ]

    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")
    if not os.path.isdir(migrations_dir):
        logger.warning(f"Migrations dir not found: {migrations_dir}")
        return

    try:
        conn = psycopg2.connect(settings.database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in cur.fetchall()}

        def version_of(f):
            m = re.match(r"V(\d+)__", f)
            return int(m.group(1)) if m else -1

        files = sorted(
            [f for f in os.listdir(migrations_dir) if f.endswith(".sql") and version_of(f) > 0],
            key=version_of,
        )

        for filename in files:
            v = version_of(filename)
            if v in applied:
                continue

            sql = open(os.path.join(migrations_dir, filename), encoding="utf-8").read()
            # Split into individual statements
            statements = [s.strip() for s in sql.split(";") if s.strip()]
            skipped = 0
            for stmt in statements:
                stmt_lower = stmt.lower()
                # Skip optional extension installs
                if "create extension" in stmt_lower:
                    ext = re.search(r'create extension.*?"?(\w+)"?', stmt_lower)
                    if ext and ext.group(1) in OPTIONAL_EXTENSIONS:
                        continue
                # Skip TimescaleDB-specific statements
                if any(p in stmt_lower for p in SKIP_PATTERNS):
                    skipped += 1
                    continue
                try:
                    cur.execute(stmt)
                except Exception as e:
                    logger.warning(f"  stmt skipped in {filename}: {e}")

            cur.execute(
                "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                (v, filename),
            )
            logger.info(f"Migration applied: {filename} (skipped {skipped} TimescaleDB stmts)")

        cur.close()
        conn.close()
        logger.info("Migrations complete")
    except Exception as e:
        logger.error(f"Migration startup error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    logger.info("Starting Swing Trade Automation Platform API")
    _run_migrations()
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
_cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://frontend-red-one-62.vercel.app",
]
if settings.frontend_url and settings.frontend_url not in _cors_origins:
    _cors_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
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
app.include_router(portfolios.router)
app.include_router(market_data_router)
app.include_router(paper_trading_router)
app.include_router(ws_router)
app.include_router(backtest_router)
app.include_router(dashboard_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
