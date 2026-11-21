"""Vida familiar: pareja, separación e hijos, y su efecto sobre el trabajo y el gasto."""

import numpy as np

from app.sim.params import P
from app.sim.state import EMP, SAB
from app.sim.tables import por_tramo


def familia(e, i, ctx, ev):
    pf, u = ctx.perfil, lambda k: ctx.suerte.u(e.t, k)  # noqa: E731
    nueva = ~e.pareja & (u("union") < por_tramo(P.UNION, e.edad))
    separa = e.pareja & (u("separa") < por_tramo(P.SEPARACION, e.edad))
    e.pareja = (e.pareja & ~separa) | nueva

    edad_madre = e.edad if pf.sexo == "m" else e.edad - P.DIF_EDAD_PAREJA   # la tabla del INE es por edad de la madre
    base = ctx.tb.p_hijo(edad_madre)
    p = np.where(e.pareja, base * P.HIJO_PAREJA[0], base * P.HIJO_PAREJA[1]) * (e.hijos < 4)
    nace = u("hijo") < p
    e.edad_hijo = np.where(nace, 0.0, np.where(e.hijos > 0, e.edad_hijo + 1, 99.0))
    e.hijos = e.hijos + nace

    sale = nace & (e.sit == EMP) & (u("hijo_sale") < P.HIJO_SALE[pf.sexo])
    e.sit[sale] = SAB          # sale a cuidar; el año siguiente vuelve a buscar
    if pf.sexo == "m":
        e.penal_hijo[nace & ~sale] = P.HIJO_PENAL_MUJER
    ev.update(pareja_nueva=nueva, separacion=separa, hijo=nace, sale_por_hijo=sale)
