from fastapi import APIRouter
from app.api.v1.discovery import router as discovery_router
from app.api.v1.health import router as health_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.orchestration import router as orchestration_router
from app.api.v1.profile import router as profile_router
from app.api.v1.ranking import router as ranking_router
from app.api.v1.explanation import router as explanation_router
from app.api.v1.career_path import router as career_path_router

api_v1_router = APIRouter()

# Register endpoint routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(opportunities_router)
api_v1_router.include_router(profile_router)
api_v1_router.include_router(discovery_router)
api_v1_router.include_router(orchestration_router)
api_v1_router.include_router(ranking_router)
api_v1_router.include_router(explanation_router)
api_v1_router.include_router(career_path_router)

