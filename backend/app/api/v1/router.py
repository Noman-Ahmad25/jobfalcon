from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.profile import router as profile_router

api_v1_router = APIRouter()

# Register endpoint routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(opportunities_router)
api_v1_router.include_router(profile_router)
