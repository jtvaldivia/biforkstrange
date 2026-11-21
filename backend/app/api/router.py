from fastapi import APIRouter

from app.api.routes import decisions, game, health, simulations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(decisions.router, prefix="/api")
api_router.include_router(simulations.router, prefix="/api")
api_router.include_router(game.router, prefix="/api")
