import logging
"""Lo que comparten los servicios que llaman a Claude: credenciales, cliente y errores.

Lo usan `perfil_ia` (leer el CV), `narrador_ia` (narrar ofertas, eventos y mundos) y el gemelo
(`app.core.llm`).
"""

import os
from pathlib import Path

import anthropic

# Los errores del SDK que significan "Claude no respondió": llave inválida, límite de uso,
# error del servidor, sin conexión o tiempo agotado (APITimeoutError es un APIConnectionError).
ERRORES_API = (anthropic.APIStatusError, anthropic.APIConnectionError)


class ClaudeNoDisponible(RuntimeError):
    """No se pudo llamar a Claude o no devolvió una respuesta usable."""


def _llave() -> str | None:
    """La llave de `backend/.env`: la config la lee aunque no esté exportada en el entorno."""
    from app.core.config import get_settings

    return get_settings().anthropic_api_key or None


def hay_credenciales() -> bool:
    """`backend/.env` más las fuentes que resuelve el SDK: variables de entorno o un perfil de `ant auth login`."""
    return bool(_llave() or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or (Path.home() / ".config" / "anthropic").is_dir())


def cliente(timeout: float, max_retries: int) -> anthropic.Anthropic:
    """Un cliente con la llave de `.env` o, si no hay, las credenciales del entorno. `timeout` es por intento, en segundos."""
    return anthropic.Anthropic(api_key=_llave(), timeout=timeout, max_retries=max_retries)


def traducir_error(error: Exception, clase: type[ClaudeNoDisponible] = ClaudeNoDisponible) -> ClaudeNoDisponible:
    """Un error del SDK como excepción propia, con un mensaje que se le puede mostrar a la persona."""
    if isinstance(error, anthropic.AuthenticationError):
        return clase("La llave de la API de Claude no es válida.")
    if isinstance(error, anthropic.RateLimitError):
        return clase("La API de Claude está con límite de uso; prueba en un minuto.")
    if isinstance(error, anthropic.APIStatusError):
        # el detalle va al log del servidor (sin datos de la persona), para diagnosticar en producción
        logging.getLogger(__name__).warning("La API de Claude respondió %s: %s", error.status_code, error.message)
        return clase(f"La API de Claude respondió con un error ({error.status_code}).")
    if isinstance(error, anthropic.APIConnectionError):
        return clase("No se pudo conectar con la API de Claude.")
    return clase(f"Falló la llamada a Claude ({type(error).__name__}).")
