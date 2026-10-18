from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings
from app.schemas.health import HealthStatus

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/healthz", response_model=HealthStatus, summary="Liveness Health Check")
async def liveness_check(settings: Settings = Depends(get_settings)) -> HealthStatus:
    """Liveness probe verifying the FastAPI server process is running and responsive."""
    return HealthStatus(
        status="ok",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        services={"api": "ok"},
    )


@router.get("/readyz", response_model=HealthStatus, summary="Readiness Health Check")
async def readiness_check(settings: Settings = Depends(get_settings)) -> HealthStatus:
    """Readiness probe verifying the application is ready to accept user requests."""
    return HealthStatus(
        status="ok",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        services={"api": "ready"},
    )
