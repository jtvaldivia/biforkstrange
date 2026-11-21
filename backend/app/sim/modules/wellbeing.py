"""Bienestar medido: satisfacción con la vida, salud subjetiva, síntomas depresivos y tiempo con tu gente."""

import numpy as np

from app.sim.params import P
from app.sim.state import CES, EMP, EMPR
from app.sim.tables import por_tramo


def bienestar(e, i, ctx, ev):
    u = lambda k: ctx.suerte.u(e.t, k)  # noqa: E731
    trabaja = e.horas > 0
    # tiempo con tu gente (ENUT)
    e.social = np.where(trabaja, 100 * P.SOCIAL_HORA ** np.maximum(e.horas - 45, 0), 100.0)
    # síntomas depresivos del año según horas (ELSOC); la cesantía los sube
    p = np.where(trabaja, _por_horas(e.horas), P.DEPRESION_OCUPADOS) + P.DEPRESION_CESANTE * (e.sit == CES)
    e.depresion = u("depresion") < p
    # salud subjetiva por edad (ELSOC)
    e.salud = np.full(e.n, por_tramo(P.SALUD_BASE, e.edad + 1))
    # satisfacción con la vida: base por edad + ingreso + cesantía + lo que pasó este año (ELSOC)
    # el efecto del ingreso se estimó entre ocupados (ELSOC): solo se aplica a quien trabaja o emprende
    con_ingreso = (e.sit == EMP) | (e.sit == EMPR)
    ref = np.where(e.sit == EMP, e.sueldo * np.exp(-e.cicatriz), np.where(con_ingreso, np.maximum(e.ingreso, 1.0), e.sueldo0))
    e.animo = np.clip(
        por_tramo(P.ANIMO_BASE, e.edad + 1) + P.ANIMO_INGRESO * np.log(np.maximum(ref, 1.0) / e.sueldo0)
        + P.ANIMO_CESANTIA * (e.sit == CES) + P.ANIMO_HORAS_55 * (e.horas >= P.HORAS_LARGAS)
        + P.ANIMO_REEMPLEO * (ev["encuentra"] | ev["reempleo_mismo_anio"])
        + P.ANIMO_PAREJA * ev["pareja_nueva"] + P.ANIMO_SEPARACION * ev["separacion"],
        0, 100,
    )


def _por_horas(h: np.ndarray) -> np.ndarray:
    t = P.DEPRESION
    return np.select([h < 30, h < 40, h <= 45, h < 55], [t["<30"], t["30-39"], t["40-45"], t["46-54"]], t["55+"])
