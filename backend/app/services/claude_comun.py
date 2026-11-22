import logging
"""Lo que comparten los servicios que llaman a Claude: credenciales, cliente y errores.

Lo usan `perfil_ia` (leer el CV) y `narrador_ia` (narrar ofertas, eventos y mundos).
"""

import os
from pathlib import Path

import anthropic

# Los errores del SDK que significan "Claude no respondió": llave inválida, límite de uso,
# error del servidor, sin conexión o tiempo agotado (APITimeoutError es un APIConnectionError).
ERRORES_API = (anthropic.APIStatusError, anthropic.APIConnectionError)


class ClaudeNoDisponible(RuntimeError):
    """No se pudo llamar a Claude o no devolvió una respuesta usable."""


def hay_credenciales() -> bool:
    """Las mismas fuentes que resuelve el SDK: variables de entorno o un perfil de `ant auth login`."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or (Path.home() / ".config" / "anthropic").is_dir())


def cliente(timeout: float, max_retries: int) -> anthropic.Anthropic:
    """Un cliente con las credenciales del entorno. `timeout` es por intento, en segundos."""
    return anthropic.Anthropic(timeout=timeout, max_retries=max_retries)


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
