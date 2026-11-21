"""La mano del año: tres cartas. Siempre está 'seguir'; si el año trae una oferta de trabajo
ocupa una carta, y el resto son decisiones posibles sorteadas con la suerte del año."""

import numpy as np

from app.sim.companies import nombre_empresa
from app.sim.context import Ctx
from app.sim.decisions import CATALOGO, disponibles
from app.sim.modules.labor import oferta_del_anio
from app.sim.profile import Perfil
from app.sim.state import CES, EMP, EMPR, Estado

MAX_CARTAS = 3   # seguir + dos jugadas
_TIPO = {"startup": "una startup", "pyme": "una pyme", "grande": "una empresa grande", "estado": "el Estado"}


def _plata(x: float) -> str:
    return f"${x / 1e6:.1f} M".replace(".", ",") if x >= 1e6 else f"${x / 1e3:.0f} mil"


def mano(yo: Estado, perfil: Perfil, ctx: Ctx) -> list[dict]:
    """Cartas del año para un gemelo: [{decision, nombre, descripcion, tipo}]."""
    from app.sim.profile import TAMANOS

    su, t, sit = ctx.suerte, yo.t, int(yo.sit[0])
    seguir = {EMP: ("Seguir igual", "Dejas que el año corra sin cambiar nada."),
              CES: ("Seguir buscando", "Sigues mandando currículums."),
              EMPR: ("Seguir con tu emprendimiento", "Otro año empujando lo tuyo.")}.get(sit, ("Seguir igual", ""))
    cartas = [{"decision": "seguir", "nombre": seguir[0], "descripcion": seguir[1], "tipo": "base"}]

    of = oferta_del_anio(yo, ctx)
    if of["existe"][0]:
        emp, tam, rel = nombre_empresa(int(of["empresa"][0])), TAMANOS[int(of["tam"][0])], float(of["rel"][0])
        sueldo = float(yo.sueldo[0] * np.exp(rel))
        cambio = f"{100 * (np.exp(rel) - 1):+.0f}%".replace("+", "+").replace("-", "−")
        cartas.append({"decision": "aceptar_oferta", "nombre": f"Irte a {emp}", "tipo": "oportunidad",
                       "descripcion": f"{emp} ({_TIPO[tam]}) te ofrece {_plata(sueldo)} al mes, {cambio} de lo que ganas. Partes de cero, sin antigüedad."})

    resto = [d for d in disponibles(yo) if d != "seguir"]
    orden = sorted(resto, key=lambda d: su.escalar(t, f"mano_{d}"))
    for d in orden[: MAX_CARTAS - len(cartas)]:
        c = CATALOGO[d]
        cartas.append({"decision": d, "nombre": c.nombre, "descripcion": c.descripcion, "tipo": c.grupo})
    return cartas
