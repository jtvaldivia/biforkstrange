"""Traducción de errores del dominio a respuestas HTTP, en un solo lugar."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, status


@contextmanager
def partida_invalida() -> Iterator[None]:
    """El motor valida la partida (duda, elecciones, mundo) con ValueError o KeyError: eso es un 422."""
    try:
        yield
    except (ValueError, KeyError) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
