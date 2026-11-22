from fastapi import APIRouter

from app.api.routes import decisions, health, simulations, stories, twin

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(decisions.router, prefix="/api")
api_router.include_router(simulations.router, prefix="/api")
api_router.include_router(twin.router, prefix="/api")
api_router.include_router(stories.router, prefix="/api")
