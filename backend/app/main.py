import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings


def _finito(valor):
    """Infinity y NaN como texto: el JSON de la respuesta no los acepta."""
    if isinstance(valor, float) and not math.isfinite(valor):
        return str(valor)
    if isinstance(valor, dict):
        return {k: _finito(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_finito(v) for v in valor]
    return valor


async def _error_de_validacion(_: Request, error: RequestValidationError) -> JSONResponse:
    """El 422 de FastAPI, pero sin romperse (500) cuando lo que llegó trae Infinity o NaN."""
    return JSONResponse(status_code=422, content={"detail": _finito(jsonable_encoder(error.errors()))})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_exception_handler(RequestValidationError, _error_de_validacion)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
