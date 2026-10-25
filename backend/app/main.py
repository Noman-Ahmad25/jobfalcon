import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown event handling."""
    # Startup actions: seed default demonstration profiles and benchmark listings
    try:
        from app.db.seed import seed_demo_data

        seed_demo_data()
    except Exception as exc:
        logger.warning("Demo data seeding failed during startup: %s", exc)
    yield
    # Shutdown actions


def create_application() -> FastAPI:
    """FastAPI application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="JobFalcon — Agentic Career Opportunity Recommendation System API",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
        docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
        redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Direct top-level healthcheck probes (standard for container runtimes)
    app.include_router(health_router)

    # API v1 Versioned Router
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Root"])
    async def root_info():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "operational",
            "docs": f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else "disabled",
        }

    return app


create_app = create_application
app = create_application()
