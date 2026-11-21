"""Catálogo de decisiones del jugador y su traducción a intenciones para los módulos."""

from dataclasses import dataclass

import numpy as np

from app.sim.state import CES, EMP, EMPR, Estado
from app.sim.tables import tablas


@dataclass(frozen=True)
class Decision:
    clave: str
    nombre: str
    descripcion: str
    cuando: tuple   # situaciones en que se puede elegir


CATALOGO: dict[str, Decision] = {d.clave: d for d in [
    Decision("seguir", "Seguir igual", "Mantienes el rumbo. Si estás sin trabajo, sigues buscando; si emprendes, continúas.", (EMP, CES, EMPR)),
    Decision("buscar_pega", "Buscar otra pega", "Buscas activamente en tu misma ocupación: llegan más ofertas y aceptas mejoras más chicas.", (EMP,)),
    Decision("pedir_aumento", "Pedir aumento", "Negocias tu sueldo. Puede resultar o no.", (EMP,)),
    Decision("trabajar_mas", "Trabajar más horas", "Un año a 55 horas semanales: más opción de ascenso, menos energía y menos tiempo con tu gente.", (EMP,)),
    Decision("bajar_ritmo", "Bajar el ritmo", "Un año a 38 horas: recuperas energía, sin apurar ascensos.", (EMP,)),
    Decision("magister", "Hacer un magíster", "Dos años estudiando mientras trabajas. Pagas arancel y te cansas; al titularte sube tu sueldo y tu opción de ascenso.", (EMP,)),
    Decision("reconvertir", "Cambiar de ocupación", "Un año formándote para pasar a otra ocupación. Mientras más afín a la tuya, más probable y menos castigo.", (EMP, CES)),
    Decision("sabatico", "Año sabático", "Renuncias y paras un año. Vives de tus ahorros y vuelves a buscar con un hueco en el CV.", (EMP,)),
    Decision("emprender", "Emprender", "Dejas el empleo y partes algo propio. La mayoría gana menos que empleada; pocos ganan mucho.", (EMP, CES)),
    Decision("volver_empleo", "Cerrar y volver a emplearte", "Cierras el emprendimiento y buscas trabajo.", (EMPR,)),
    Decision("bajar_pretensiones", "Bajar pretensiones", "Aceptas la primera oferta razonable: encuentras antes, con menos sueldo.", (CES,)),
    Decision("tener_hijo", "Tener un hijo", "Buscan un hijo este año (requiere pareja).", (EMP, CES, EMPR)),
]}

ALIAS = {"cambiar_pega": "buscar_pega", "estudiar": "magister"}


def normalizar(texto: str) -> tuple[str, int]:
    """'reconvertir:133' -> ('reconvertir', índice de la ocupación). Lanza ValueError si no existe."""
    clave, _, arg = texto.strip().partition(":")
    clave = ALIAS.get(clave, clave)
    if clave not in CATALOGO:
        raise ValueError(f"Decisión desconocida: {texto}")
    destino = -1
    if clave == "reconvertir":
        if arg not in tablas().idx:
            raise ValueError("reconvertir necesita una ocupación ISCO-3, por ejemplo reconvertir:133")
        destino = tablas().idx[arg]
    return clave, destino


@dataclass
class Intencion:
    busca: np.ndarray
    pide: np.ndarray
    horas: np.ndarray
    magister: np.ndarray
    reconv: np.ndarray     # índice de ocupación destino o -1
    sabatico: np.ndarray
    emprende: np.ndarray
    volver: np.ndarray
    baja: np.ndarray
    hijo: np.ndarray


def intencion(e: Estado, clave: str, destino: int = -1) -> Intencion:
    """Aplica la decisión solo en los universos donde es posible; en el resto equivale a 'seguir'."""
    no = np.zeros(e.n, bool)
    emp, ces, empr = e.sit == EMP, e.sit == CES, e.sit == EMPR
    i = Intencion(no.copy(), no.copy(), np.full(e.n, 44.0), no.copy(), np.full(e.n, -1), no.copy(), no.copy(), no.copy(), no.copy(), no.copy())
    if clave == "buscar_pega":
        i.busca = emp
    elif clave == "pedir_aumento":
        i.pide = emp
    elif clave == "trabajar_mas":
        i.horas[emp] = 55.0
    elif clave == "bajar_ritmo":
        i.horas[emp] = 38.0
    elif clave == "magister":
        i.magister = emp
    elif clave == "reconvertir":
        i.reconv[emp | ces] = destino
    elif clave == "sabatico":
        i.sabatico = emp
    elif clave == "emprender":
        i.emprende = emp | ces
    elif clave == "volver_empleo":
        i.volver = empr
    elif clave == "bajar_pretensiones":
        i.baja = ces
    elif clave == "tener_hijo":
        i.hijo = e.pareja & (e.hijos < 4)
    return i


def disponibles(e: Estado) -> list[str]:
    """Decisiones que tienen sentido para un gemelo concreto (estado de un solo universo)."""
    sit = int(e.sit[0])
    out = []
    for d in CATALOGO.values():
        if sit not in d.cuando:
            continue
        if d.clave == "magister" and (e.postgrado[0] or e.estudia[0] > 0):
            continue
        if d.clave == "tener_hijo" and not (e.pareja[0] and e.hijos[0] < 4 and e.edad <= 45):
            continue
        out.append(d.clave)
    return out
