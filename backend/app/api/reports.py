"""
Performance reports API endpoints.

Endpoints:
- POST /api/reports/performance  - Compute performance metrics for an equity curve
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from uuid import UUID

from app.api.dependencies import get_current_user
from app.services.performance_report_service import PerformanceReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

_report_service = PerformanceReportService()


class EquityPoint(BaseModel):
    date: str
    value: float


class BenchmarkPoint(BaseModel):
    date: str
    close: float


class PerformanceReportRequest(BaseModel):
    equity_curve: List[EquityPoint]
    benchmark_prices: Optional[List[BenchmarkPoint]] = None
    rolling_window: int = 30

    @field_validator("equity_curve")
    @classmethod
    def validate_equity_curve(cls, v):
        if len(v) < 2:
            raise ValueError("equity_curve must have at least 2 points")
        return v

    @field_validator("rolling_window")
    @classmethod
    def validate_rolling_window(cls, v):
        if v < 2:
            raise ValueError("rolling_window must be at least 2")
        return v


class PerformanceReportResponse(BaseModel):
    cumulative_return: float
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    rolling_sharpe: List[Optional[float]]
    rolling_drawdown: List[Optional[float]]


@router.post("/performance", response_model=PerformanceReportResponse)
def compute_performance_report(
    data: PerformanceReportRequest,
    user_id: UUID = Depends(get_current_user),
):
    """
    Compute performance metrics for a given equity curve.

    Accepts the equity curve and an optional benchmark price series.
    Returns cumulative return, alpha, rolling Sharpe, and rolling drawdown.
    """
    equity = [{"date": pt.date, "value": pt.value} for pt in data.equity_curve]
    benchmark = (
        [{"date": pt.date, "close": pt.close} for pt in data.benchmark_prices]
        if data.benchmark_prices
        else None
    )

    try:
        result = _report_service.compute(
            equity_curve=equity,
            benchmark_prices=benchmark,
            rolling_window=data.rolling_window,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return PerformanceReportResponse(**result)
