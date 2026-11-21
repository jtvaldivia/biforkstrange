"""Vida familiar: pareja, separación e hijos, y su efecto sobre el trabajo."""

import numpy as np

from app.sim.params import P
from app.sim.state import EMP, SAB


def familia(e, i, ctx, ev):
    pf, u = ctx.perfil, lambda k: ctx.suerte.u(e.t, k)  # noqa: E731
    p_union = P.UNION[0] if 20 <= e.edad <= 35 else P.UNION[1]
    nueva = ~e.pareja & (u("union") < p_union)
    separa = e.pareja & (u("separa") < P.SEPARACION)
    e.pareja = (e.pareja & ~separa) | nueva

    edad_fertil = e.edad if pf.sexo == "m" else e.edad - 2   # la tabla del INE es por edad de la madre
    base = ctx.tb.p_hijo(edad_fertil)
    p = np.where(e.pareja, base * P.HIJO_PAREJA[0], base * P.HIJO_PAREJA[1])
    buscado = P.HIJO_BUSCADO[0] if edad_fertil <= 37 else P.HIJO_BUSCADO[1]
    p = np.where(i.hijo & e.pareja, buscado, p) * (e.hijos < 4)
    nace = u("hijo") < p
    e.edad_hijo = np.where(nace, 0.0, np.where(e.hijos > 0, e.edad_hijo + 1, 99.0))
    e.hijos = e.hijos + nace

    # efecto laboral del nacimiento
    sale = nace & (e.sit == EMP) & (u("hijo_sale") < P.HIJO_SALE[pf.sexo])
    e.sit[sale] = SAB          # sale a cuidar; el año siguiente vuelve a buscar
    if pf.sexo == "m":
        e.penal_hijo[nace & ~sale] = P.HIJO_PENAL_MUJER
    ev.update(pareja_nueva=nueva, separacion=separa, hijo=nace, sale_por_hijo=sale)
