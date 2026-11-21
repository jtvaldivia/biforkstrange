"""Finanzas personales: gasto según la tasa de ahorro de tu tramo de ingreso (EPF), hijos y arancel."""

import numpy as np

from app.sim.params import P


def finanzas(e, i, ctx, ev):
    tb = ctx.tb
    e.gasto = np.maximum(tb.gasto_piso, (1 - tb.tasa_ahorro(e.ingreso)) * e.ingreso) + float(P.HIJO_COSTO) * e.hijos
    arancel = ev["estudia"] * P.MAG_ARANCEL
    e.ahorros = e.ahorros + 12 * (e.ingreso - e.gasto) - arancel
    ev["deuda"] = e.ahorros < 0
