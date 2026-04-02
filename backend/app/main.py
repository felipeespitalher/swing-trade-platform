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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    logger.info("Starting Swing Trade Automation Platform API")
    yield
    logger.info("Shutting down Swing Trade Automation Platform API")


# Create FastAPI application
app = FastAPI(
    title="Swing Trade Automation Platform API",
    description="API for automated swing trading analysis and execution",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        dict: Status indicator
    """
    return {"status": "ok"}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
