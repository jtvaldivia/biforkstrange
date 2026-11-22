from fastapi import APIRouter

from app.api.routes import decisions, health, juego, ocupaciones, simulations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(decisions.router, prefix="/api")
api_router.include_router(simulations.router, prefix="/api")
api_router.include_router(ocupaciones.router, prefix="/api")
api_router.include_router(juego.router, prefix="/api")
