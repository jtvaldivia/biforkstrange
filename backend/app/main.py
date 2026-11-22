import logging
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


log = logging.getLogger("bifurca")


class _ErrorConJson:
    """Un error no manejado sale como 500 con JSON y pasando por CORS.

    El manejador de 500 de Starlette vive en el middleware más externo, fuera de CORSMiddleware: su respuesta
    salía sin Access-Control-Allow-Origin y el navegador la mostraba como error de CORS, sin el mensaje.
    Este middleware va por dentro de CORS, así que su 500 lleva las cabeceras.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        empezo = False

        async def enviar(mensaje):
            nonlocal empezo
            if mensaje["type"] == "http.response.start":
                empezo = True
            await send(mensaje)

        try:
            await self.app(scope, receive, enviar)
        except Exception as error:  # noqa: BLE001 - es la red de seguridad de toda la API
            log.exception("error no manejado en %s %s", scope.get("method"), scope.get("path"))
            if empezo:  # la respuesta ya salió a medias: no hay cómo cambiarla
                raise
            respuesta = JSONResponse(status_code=500, content={
                "detail": f"El simulador falló: {type(error).__name__}: {error}"[:500]})
            await respuesta(scope, receive, send)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_exception_handler(RequestValidationError, _error_de_validacion)
    # el orden importa: el último agregado queda más afuera. CORS envuelve al que atrapa los errores.
    app.add_middleware(_ErrorConJson)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
