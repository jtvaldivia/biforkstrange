"""Finanzas personales: gasto con hábito, ahorro o deuda y costos de las decisiones."""

import numpy as np

from app.sim.params import P


def finanzas(e, i, ctx, ev):
    tb = ctx.tb
    objetivo = np.maximum(tb.gasto_piso, (1 - tb.tasa_ahorro(e.ingreso)) * e.ingreso)
    e.gasto = P.HABITO * e.gasto + (1 - P.HABITO) * objetivo
    sin_trabajo = (e.meses_ces >= 6) | ev["pausa"]
    gasto_mes = e.gasto * np.where(sin_trabajo, P.AJUSTE_CRISIS, 1.0) + float(P.COSTO_HIJO) * e.hijos
    costos = ev["estudia"] * P.MAG_ARANCEL + (ev["reconv_ok"] | ev["reconv_no"]) * P.RECONV_COSTO + ev["emprende"] * P.EMP_CAPITAL
    interes = np.where(e.ahorros >= 0, P.INTERES_AHORRO, P.INTERES_DEUDA) * e.ahorros
    e.ahorros = e.ahorros + 12 * e.ingreso - 12 * gasto_mes - costos + interes
    ev["deuda"] = e.ahorros < 0
    ev["gasto_mes"] = gasto_mes
