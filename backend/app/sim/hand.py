"""La mano del año: en vez de mostrar todas las decisiones posibles, el juego reparte tres
cartas. Siempre está 'seguir'; si el año trae una oportunidad (una oferta con nombre, un cupo
de ascenso) ocupa una carta, y el resto son acciones elegidas según cómo está el gemelo,
cada una de un grupo distinto."""

import numpy as np

from app.sim.companies import nombre_empresa
from app.sim.context import Ctx
from app.sim.decisions import CATALOGO, disponibles
from app.sim.modules.labor import cupo_del_anio, oferta_del_anio
from app.sim.params import P
from app.sim.profile import NIVELES, TAMANOS, Perfil
from app.sim.state import CES, EMP, EMPR, Estado
from app.sim.tables import tablas

MAX_CARTAS = 3   # seguir + dos jugadas, como un dilema de cartas
_TIPO = {"startup": "una startup", "pyme": "una pyme", "grande": "una empresa grande", "estado": "el Estado"}


def _plata(x: float) -> str:
    return f"${x / 1e6:.1f} M".replace(".", ",") if x >= 1e6 else f"${x / 1e3:.0f} mil"


def _destino(yo: Estado) -> int | None:
    """Ocupación a la que conviene mirar: la afín menos expuesta a IA si la tuya está muy expuesta; si no, la más afín."""
    from app.sim.counterfactual import sugerir_destinos

    ds = sugerir_destinos(int(yo.ocup[0]), int(yo.nivel[0]))
    if not ds:
        return None
    return ds[1] if len(ds) > 1 and tablas().ia[int(yo.ocup[0])] >= 0.65 else ds[0]


def _pesos(yo: Estado, perfil: Perfil) -> list[dict[str, float]]:
    """Grupos de acciones candidatas con su peso; de cada grupo sale una carta."""
    tb = tablas()
    energia, salud, social = float(yo.energia[0]), float(yo.salud[0]), float(yo.social[0])
    colchon = float(yo.ahorros[0] / max(yo.gasto[0], 1))          # meses de gasto cubiertos
    ia, contactos, antig = float(tb.ia[int(yo.ocup[0])]), float(yo.contactos[0]), float(yo.antig[0])
    sit, ok = int(yo.sit[0]), set(disponibles(yo))
    reconv = _destino(yo)
    clave_reconv = f"reconvertir:{tb.codigos[reconv]}" if reconv is not None else None
    if sit == EMP:
        grupos = [
            {"buscar_pega": 1.0 * (2 if ia >= 0.65 or yo.animo[0] < 60 else 1), "pedir_aumento": 1.0 * (1.6 if antig >= 2 else 0.6),
             "trabajar_mas": 0.8 * (0.3 if energia < 50 else 1), "pituto": 0.7 * (2.5 if colchon < 3 else 1) * (0.3 if energia < 50 else 1)},
            {"capacitarte": 1.0 * (2 if ia >= 0.65 else 1), "networking": 1.0 * (1.6 if contactos < 40 else 1),
             "magister": 0.7 * (1 if yo.ahorros[0] > P.MAG_ARANCEL else 0.2), clave_reconv: 0.5 * (2.5 if ia >= 0.85 else 1)},
            {"cuidarte": 1.0 * (3 if energia < 50 or salud < 65 else 1), "bajar_ritmo": 0.5 * (4 if energia < 45 else 1),
             "tu_gente": 1.0 * (1.8 if social < 95 or yo.pareja[0] else 1), "tener_hijo": 0.5 * (2 if 30 <= yo.edad <= 38 else 1),
             "sabatico": 0.25 * (3 if colchon >= 12 else 1), "emprender": 0.3 * (3 if colchon >= 8 else 1) * (1.5 if perfil.riesgo > 0 else 1)},
        ]
    elif sit == CES:
        grupos = [{"bajar_pretensiones": 1.0}, {"capacitarte": 1.0, "networking": 1.2, "pituto": 1.0 * (2 if colchon < 3 else 1)},
                  {clave_reconv: 1.0, "emprender": 0.6, "cuidarte": 0.6}]
    elif sit == EMPR:
        grupos = [{"volver_empleo": 1.0}, {"networking": 1.0, "capacitarte": 0.8}, {"cuidarte": 1.0, "tu_gente": 1.0, "tener_hijo": 0.6}]
    else:
        grupos = []
    return [{k: w for k, w in g.items() if k and w > 0 and k.split(":")[0] in ok} for g in grupos]


def mano(yo: Estado, perfil: Perfil, ctx: Ctx) -> list[dict]:
    """Cartas del año para un gemelo: [{decision, nombre, descripcion, tipo}]."""
    tb, su, t = tablas(), ctx.suerte, yo.t
    sit = int(yo.sit[0])
    seguir = {EMP: ("Seguir igual", "Dejas que el año corra sin cambiar nada."), CES: ("Seguir buscando", "Sigues mandando currículums con tus pretensiones de siempre."),
              EMPR: ("Seguir con tu emprendimiento", "Otro año empujando lo tuyo.")}.get(sit, ("Seguir igual", ""))
    cartas = [{"decision": "seguir", "nombre": seguir[0], "descripcion": seguir[1], "tipo": "base"}]

    of = oferta_del_anio(yo, ctx)
    if of["existe"][0]:
        emp, tam = nombre_empresa(int(of["empresa"][0])), TAMANOS[int(of["tam"][0])]
        sueldo = float(yo.sueldo[0] * (1 + of["alza"][0]))
        cartas.append({"decision": "aceptar_oferta", "nombre": f"Irte a {emp}", "tipo": "oportunidad",
                       "descripcion": f"Te vinieron a buscar de {emp} ({_TIPO[tam]}): {_plata(sueldo)} al mes, {100 * of['alza'][0]:.0f}% más. Partes de cero, sin antigüedad."})
    if cupo_del_anio(yo, ctx)[0]:
        sube = NIVELES[min(int(yo.nivel[0]) + 1, 4)]
        cartas.append({"decision": "postular_ascenso", "nombre": f"Postular a {sube}", "tipo": "oportunidad",
                       "descripcion": f"Se abrió un cupo de {sube} en {nombre_empresa(int(yo.empresa[0]), perfil.empresa)}. Si no quedas, te quedas donde estás."})

    cartas = cartas[:MAX_CARTAS]
    grupos = _pesos(yo, perfil)
    orden = sorted(range(len(grupos)), key=lambda k: su.escalar(t, f"orden_{k}"))   # qué grupos salen este año varía
    for k in orden:
        grupo = grupos[k]
        if len(cartas) >= MAX_CARTAS or not grupo:
            continue
        claves, pesos = list(grupo), np.array(list(grupo.values()))
        dec = claves[int(np.searchsorted(np.cumsum(pesos / pesos.sum()), su.escalar(t, f"mano_{k}")).clip(max=len(claves) - 1))]
        clave, _, arg = dec.partition(":")
        d = CATALOGO[clave]
        nombre, desc = d.nombre, d.descripcion
        if clave == "reconvertir":
            o, a = tb.idx[arg], int(yo.ocup[0])
            nombre = f"Pasarte a {tb.nombres[o].split(' (')[0].lower()}"
            desc = f"Un año formándote para cambiar de ocupación. Afinidad con la tuya: {100 * tb.afinidad[a, o]:.0f}%."
        cartas.append({"decision": dec, "nombre": nombre, "descripcion": desc, "tipo": d.grupo})
    return cartas
