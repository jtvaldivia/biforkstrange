"""Paso laboral de un año: ¿termina tu empleo?, ¿a dónde pasas?, ¿a qué tipo de trabajo?

Para cada universo se tira un dado:

- Con empleo: sigue igual, cambia directo de empleador, cae en cesantía o sale a
  inactividad. Las probabilidades base son de la EPS por tramo de edad, ajustadas
  por cuánto dura un empleo en su grupo ocupacional (JobHop).
- Sin empleo: encuentra trabajo con 1 - P(seguir cesante a los 12 meses) de la EPS.

Quien empieza un empleo nuevo sortea su grupo ocupacional con la matriz de
transición de JobHop, condicionada al grupo de su último trabajo.

Simplificación: la inactividad se trata igual que la cesantía (`desempleado`).
"""

from dataclasses import dataclass

import numpy as np

from app.sim.ocupacional.state import State
from app.sim.ocupacional.tables import banda_idx, tablas

DESGASTE_UMBRAL = 0.6
DESGASTE_PESO = 0.3


@dataclass
class LaborYear:
    """Qué le pasó a cada universo este año (máscaras de n_runs)."""

    perdio_empleo: np.ndarray  # tenía empleo y quedó sin él
    nuevo_empleo: np.ndarray  # empezó un empleo (cambio directo o reempleo)
    cambio_grupo: np.ndarray  # el empleo nuevo es de otro grupo ocupacional
    cambio_ocupacion: np.ndarray  # el empleo nuevo es de otra ocupación específica


def _sortear_grupo(origen: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Grupo del siguiente empleo dado el del último (una fila de la matriz por universo)."""
    acumulada = np.cumsum(tablas().transicion, axis=1)[origen]
    u = rng.random(origen.shape[0])[:, None]
    return np.minimum((u > acumulada).sum(axis=1), acumulada.shape[1] - 1)


def advance(
    state: State,
    rng: np.random.Generator,
    *,
    riesgo_rel: float = 1.0,
    cambio_forzado: bool = False,
) -> LaborYear:
    """Avanza un año la situación laboral de todos los universos (modifica `state`).

    riesgo_rel multiplica la probabilidad de caer en cesantía y cambio_forzado hace
    que todo el que conserva empleo se cambie de empleador este año; los fija la
    decisión del año. Deja el resultado también en `state.extra` para las métricas.
    """
    t = tablas()
    b = banda_idx(state.edad)
    n = state.sueldo.shape[0]
    empleado = ~state.desempleado
    mult = t.mult_rotacion[state.ocupacion]

    # supuesto del equipo: el desgaste alto sube el riesgo de caída
    riesgo_desgaste = DESGASTE_PESO * np.maximum(state.desgaste - DESGASTE_UMBRAL, 0)
    p_sale = np.clip((t.p_cesantia[b] * riesgo_rel + t.p_inactividad[b]) * mult + riesgo_desgaste, 0, 1)
    p_directo = np.ones(n) if cambio_forzado else t.p_cambio_directo[b] * mult
    p_directo = np.minimum(p_directo, 1 - p_sale)

    u = rng.random(n)
    perdio = empleado & (u < p_sale)
    directo = empleado & ~perdio & (u < p_sale + p_directo)
    reempleo = state.desempleado & (rng.random(n) < 1 - t.p_sigue_cesante_12m[b])
    nuevo = directo | reempleo

    origen = state.ocupacion
    destino = np.where(nuevo, _sortear_grupo(origen, rng), origen)
    cambio_grupo = nuevo & (destino != origen)
    # Dentro del mismo grupo también se puede cambiar de ocupación específica:
    # P(cambia 4d | mismo grupo) = (p_4d - p_grupo) / (1 - p_grupo)
    p_dentro = (t.p_cambia_ocupacion - t.p_cambia_grupo) / (1 - t.p_cambia_grupo)
    cambio_ocupacion = cambio_grupo | (nuevo & (rng.random(n) < p_dentro[origen]))

    state.ocupacion = destino
    state.desempleado = (state.desempleado & ~reempleo) | perdio
    state.antiguedad = np.where(nuevo | state.desempleado, 0.0, state.antiguedad + 1)
    state.n_empleos = state.n_empleos + nuevo

    year = LaborYear(perdio, nuevo, cambio_grupo, cambio_ocupacion)
    state.extra.update(vars(year))
    return year


def perfil(grupo: int, edad: int) -> dict:
    """Lo que dicen las tablas, sin simular, para alguien de esa edad cuyo último
    trabajo es de ese grupo: qué tan probable es que termine este año, cuánto
    dura y a qué grupo pasa después."""
    t = tablas()
    b = banda_idx(edad)
    mult = float(t.mult_rotacion[grupo])
    p_directo, p_cesantia, p_inactividad = (
        float(min(p[b] * mult, 1.0)) for p in (t.p_cambio_directo, t.p_cesantia, t.p_inactividad)
    )
    return {
        "grupo": grupo,
        "nombre": t.nombres[grupo],
        "edad": edad,
        "termino_anual": {
            "total": min(p_directo + p_cesantia + p_inactividad, 1.0),
            "cambio_directo": p_directo,
            "cesantia": p_cesantia,
            "inactividad": p_inactividad,
        },
        "duracion_anios": {
            "p25": float(t.dur_p25[grupo]),
            "p50": float(t.dur_p50[grupo]),
            "p75": float(t.dur_p75[grupo]),
        },
        "p_cambia_grupo": float(t.p_cambia_grupo[grupo]),
        "p_cambia_ocupacion": float(t.p_cambia_ocupacion[grupo]),
        "siguiente": [
            {"grupo": int(d), "nombre": t.nombres[d], "prob": float(t.transicion[grupo, d])}
            for d in np.argsort(-t.transicion[grupo])
        ],
    }
