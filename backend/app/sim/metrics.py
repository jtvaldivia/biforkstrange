"""Resúmenes de una nube de universos."""

import numpy as np

from app.sim.state import CES, EMP, Estado


def pct(x: np.ndarray, qs=(10, 50, 90)) -> list[float]:
    return [float(v) for v in np.percentile(x, qs)]


def resumen_anual(e: Estado) -> dict:
    emp = e.sit == EMP
    sueldo = np.where(emp, e.sueldo * np.exp(-e.cicatriz), e.ingreso)
    p10, p50, p90 = pct(sueldo)
    a10, a50, a90 = pct(e.ahorros)
    return {
        "edad": e.edad,
        "sueldo_p10": p10, "sueldo_p50": p50, "sueldo_p90": p90,
        "desgaste_p50": float(1 - np.median(e.energia) / 100),
        "prob_desempleo": float((e.sit == CES).mean()),
        "ingreso_p50": float(np.median(e.ingreso)),
        "animo_p50": float(np.median(e.animo)),
        "energia_p50": float(np.median(e.energia)),
        "ahorros_p10": a10, "ahorros_p50": a50, "ahorros_p90": a90,
        "prob_deuda": float((e.ahorros < 0).mean()),
        "prob_burnout": float(e.ev["burnout"].mean()),
        "prob_pareja": float(e.pareja.mean()),
        "hijos_promedio": float(e.hijos.mean()),
        "contactos_p50": float(np.median(e.contactos)),
    }
