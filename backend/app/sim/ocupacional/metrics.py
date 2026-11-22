"""Resúmenes del estado por año. Agregar métricas aquí sin tocar el motor."""

import numpy as np

from app.sim.ocupacional.state import State
from app.sim.ocupacional.tables import N_GRUPOS, tablas


def summarize(state: State) -> dict:
    p10, p50, p90 = np.percentile(state.sueldo, [10, 50, 90])
    n = state.sueldo.shape[0]
    cero = np.zeros(n, dtype=bool)
    reparto = np.bincount(state.ocupacion, minlength=N_GRUPOS) / n
    nombres = tablas().nombres
    return {
        "sueldo_p10": float(p10),
        "sueldo_p50": float(p50),
        "sueldo_p90": float(p90),
        "desgaste_p50": float(np.median(state.desgaste)),
        "prob_desempleo": float(state.desempleado.mean()),
        # este año
        "prob_nuevo_empleo": float(state.extra.get("nuevo_empleo", cero).mean()),
        "prob_cambio_grupo": float(state.extra.get("cambio_grupo", cero).mean()),
        "prob_cambio_ocupacion": float(state.extra.get("cambio_ocupacion", cero).mean()),
        # acumulado
        "antiguedad_p50": float(np.median(state.antiguedad)),
        "empleos_p50": float(np.median(state.n_empleos)),
        # en qué grupo ocupacional están los universos (el último, si están sin empleo)
        "ocupaciones": [
            {"grupo": int(g), "nombre": nombres[g], "prob": float(reparto[g])}
            for g in np.argsort(-reparto)
            if reparto[g] > 0
        ],
    }
