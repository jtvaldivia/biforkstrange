"""Un cálculo pesado a la vez.

En Render gratis el servidor tiene 0,1 CPU. Con cuatro partidas simuladas en paralelo, los hilos se
reparten la CPU, cada una tarda cuatro veces más y /health deja de contestar a tiempo; Render da el
servicio por muerto y lo reinicia (502 para todos). Haciendo fila, cada partida sale en su tiempo
normal, una tras otra, y /health sigue respondiendo.

`CALCULOS_A_LA_VEZ` cambia cuántos corren juntos (sube con más CPU). Quien espera más de
`ESPERA_MAXIMA` segundos recibe un 503 con Retry-After en vez de colgarse.
"""

import functools
import os
import threading

from fastapi import HTTPException

CALCULOS_A_LA_VEZ = max(1, int(os.environ.get("CALCULOS_A_LA_VEZ", "1")))
ESPERA_MAXIMA = float(os.environ.get("ESPERA_MAXIMA", "90"))

_fila = threading.BoundedSemaphore(CALCULOS_A_LA_VEZ)


def en_fila(funcion):
    """Para endpoints síncronos que simulan gemelos: esperan su turno antes de calcular."""

    @functools.wraps(funcion)
    def con_turno(*args, **kwargs):
        if not _fila.acquire(timeout=ESPERA_MAXIMA):
            raise HTTPException(503, "Hay muchas simulaciones en curso. Prueba de nuevo en unos segundos.",
                                headers={"Retry-After": "10"})
        try:
            return funcion(*args, **kwargs)
        finally:
            _fila.release()

    return con_turno
