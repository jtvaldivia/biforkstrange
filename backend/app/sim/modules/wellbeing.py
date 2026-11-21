"""Energía (esfuerzo y recuperación), licencias por agotamiento, ánimo y tiempo con tu gente."""

import numpy as np

from app.sim.params import P
from app.sim.state import CES, EMP


def energia(e, i, ctx, ev):
    pf, u = ctx.perfil, lambda k: ctx.suerte.u(e.t, k)  # noqa: E731
    trabaja = e.horas > 0
    demanda = (
        P.ENERGIA_HORA * np.maximum(e.horas - 44, 0)
        + 12.0 * (ev["estudia"] & trabaja)
        + 8.0 * (ev["reconv_ok"] | ev["reconv_no"])
        + 4.0 * ((e.nivel >= 3) & (e.sit == EMP))
        + P.CUIDADO[pf.sexo] * (e.edad_hijo <= 4)
    )
    recursos = 6.0 * (trabaja & (e.horas <= 40)) + 25.0 * ev["pausa"]
    sens = max(0.5, 1 + P.B_BURNOUT_N * pf.z("N"))
    delta = -demanda * sens + recursos * (1 + 0.2 * pf.z("E")) + P.ENERGIA_REVERSION * (70 - e.energia)
    e.energia = np.clip(e.energia + delta, 0, 100)

    umbral, p = P.BURNOUT
    quema = (e.energia < umbral) & trabaja & (u("burnout") < p * sens)
    rechazo = quema & (e.sit == EMP) & (u("licencia") < P.LICENCIA_RECHAZO)   # dos meses sin subsidio
    e.ingreso = np.where(rechazo, np.maximum(e.ingreso - 2 * e.sueldo / 12, 0), e.ingreso)
    e.energia = np.where(quema, 55.0, e.energia)
    e.burnout_prev = quema
    e.social = np.where(trabaja, 100 * P.SOCIAL_HORA ** np.maximum(e.horas - 45, 0), 100.0)
    ev.update(burnout=quema, licencia_rechazada=rechazo)


def animo(e, i, ctx, ev):
    o = P.ANIMO_OTROS
    evento = (
        o["aumento"] * ev["aumento"] + o["aumento_no"] * ev["aumento_no"] + o["burnout"] * ev["burnout"]
        + o["despido"] * ev["despido"] + o["sabatico"] * ev["pausa"] + o["titulo"] * ev["titulo"] + o["hijo"] * ev["hijo"]
        + o["cierre"] * ev["cierra_emp"] + P.ANIMO_REEMPLEO * (ev["encuentra"] | ev["reempleo_mismo_anio"])
        + P.ANIMO_PAREJA * ev["pareja_nueva"] + P.ANIMO_SEPARACION * ev["separacion"]
    )
    e.animo_trans = 0.5 * e.animo_trans + evento
    e.animo_pers = np.minimum(e.animo_pers + o["ascenso"] * ev["ascenso"], 9.0)
    ref = np.where(e.sit == EMP, e.sueldo, np.maximum(e.ingreso, 1.0))
    por_ingreso = np.where(e.sit == CES, 0.0, np.clip(P.ANIMO_INGRESO * np.log(ref / e.sueldo0), -8, 8))
    e.animo = np.clip(
        66 + e.animo_pers + e.animo_trans + 0.15 * (e.energia - 70) + por_ingreso
        + P.ANIMO_CESANTIA * ((e.sit == CES) & ~e.hueco_vol)
        + o["hijo_chico"] * ((e.edad_hijo >= 1) & (e.edad_hijo <= 4)) + o["deuda"] * ev["deuda"],
        0, 100,
    )
