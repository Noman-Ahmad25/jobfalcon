from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Literal
from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Health check response schema."""

    status: Literal["ok", "degraded", "unhealthy"] = Field(
        ..., description="Overall service operational status"
    )
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Active runtime environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check inspection",
    )
    services: Dict[str, str] = Field(
        default_factory=lambda: {"api": "ok"},
        description="Individual service dependency statuses",
    )


class ReadyStatus(BaseModel):
    """Readiness probe response schema."""

    status: Literal["ready", "not_ready"] = Field(
        ..., description="Overall readiness status"
    )
    ready: bool = Field(..., description="Boolean readiness flag")
    dependencies: Dict[str, str] = Field(
        default_factory=lambda: {"api": "ready"},
        description="Dependency readiness status map",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the readiness inspection",
    )
