"""Tablas del paquete de datos (`datos_laborales/simulador/tablas`) que usa el motor.

Se leen una vez y quedan como arrays indexables por tramo de edad y por grupo
ocupacional (ISCO a 1 dígito, 0..9).

| Tabla                  | Fuente                    | Qué aporta                                   |
|------------------------|---------------------------|----------------------------------------------|
| eps_terminos_empleo    | EPS 2024, Chile           | Prob. anual de que el empleo termine, y a dónde pasas |
| eps_cesantia_duracion  | EPS 2024, Chile           | Prob. de seguir cesante a los 12 meses       |
| jobhop_transiciones    | CVs de VDAB, Flandes      | A qué grupo ocupacional pasas según el último |
| jobhop_cambio_grupo    | CVs de VDAB, Flandes      | Prob. de cambiar de ocupación específica     |
| jobhop_duracion        | CVs de VDAB, Flandes      | Cuánto dura un empleo según el grupo         |

Las de JobHop son de Flandes, no de Chile: calidad "mixto" en el paquete.
"""

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[1] / "data"  # app/sim/data, compartido con el motor

BANDAS = ("18-29", "30-44", "45-59")
PERIODO_EPS = "2016_2024"  # el mismo que usa P_SEPARACION en el paquete
N_GRUPOS = 10


def _rows(nombre: str) -> list[dict[str, str]]:
    with open(DATA_DIR / f"{nombre}.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def banda_idx(edad: int) -> int:
    """Tramo de edad de las tablas EPS. Fuera de 18-59 se usa el tramo más cercano."""
    if edad < 30:
        return 0
    return 1 if edad < 45 else 2


@dataclass(frozen=True)
class Tablas:
    # EPS, por banda (3,)
    p_cambio_directo: np.ndarray
    p_cesantia: np.ndarray
    p_inactividad: np.ndarray
    p_sigue_cesante_12m: np.ndarray
    # JobHop, por grupo ISCO (10,) o (10, 10)
    nombres: tuple[str, ...]
    transicion: np.ndarray  # [origen, destino], filas suman 1
    p_cambia_grupo: np.ndarray
    p_cambia_ocupacion: np.ndarray  # ocupación a 4 dígitos
    dur_p25: np.ndarray
    dur_p50: np.ndarray
    dur_p75: np.ndarray
    dur_media: np.ndarray
    mult_rotacion: np.ndarray  # duración media total / duración media del grupo


@lru_cache(maxsize=1)
def tablas() -> Tablas:
    eps = {r["banda"]: r for r in _rows("eps_terminos_empleo") if r["periodo"] == PERIODO_EPS}
    ces = {r["banda"]: r for r in _rows("eps_cesantia_duracion")}

    def por_banda(fuente: dict, col: str) -> np.ndarray:
        return np.array([float(fuente[b][col]) for b in BANDAS])

    transicion = np.zeros((N_GRUPOS, N_GRUPOS))
    nombres = [""] * N_GRUPOS
    for r in _rows("jobhop_transiciones"):
        o, d = int(r["origen"]), int(r["destino"])
        transicion[o, d] = float(r["prob"])
        nombres[o] = r["origen_nombre"]
    transicion /= transicion.sum(axis=1, keepdims=True)  # el CSV viene redondeado a 4 decimales

    def por_grupo(tabla: str, col: str) -> tuple[np.ndarray, float]:
        filas = _rows(tabla)
        grupos = {int(r["valor"]): float(r[col]) for r in filas if r["dimension"] == "grupo_isco_1d"}
        total = next(float(r[col]) for r in filas if r["dimension"] == "total")
        return np.array([grupos[g] for g in range(N_GRUPOS)]), total

    dur_media, dur_media_total = por_grupo("jobhop_duracion", "dur_media_anios")

    return Tablas(
        p_cambio_directo=por_banda(eps, "cambio_empleador_directo"),
        p_cesantia=por_banda(eps, "pasa_a_cesantia"),
        p_inactividad=por_banda(eps, "pasa_a_inactividad"),
        p_sigue_cesante_12m=por_banda(ces, "sigue_12m"),
        nombres=tuple(nombres),
        transicion=transicion,
        p_cambia_grupo=por_grupo("jobhop_cambio_grupo", "p_cambia_grupo_1d")[0],
        p_cambia_ocupacion=por_grupo("jobhop_cambio_grupo", "p_cambia_ocupacion_4d")[0],
        dur_p25=por_grupo("jobhop_duracion", "dur_p25_anios")[0],
        dur_p50=por_grupo("jobhop_duracion", "dur_p50_anios")[0],
        dur_p75=por_grupo("jobhop_duracion", "dur_p75_anios")[0],
        dur_media=dur_media,
        # Un empleo que dura menos termina más seguido. Se usa solo la diferencia
        # relativa entre grupos (Flandes) sobre la tasa base chilena (EPS).
        mult_rotacion=dur_media_total / dur_media,
    )
