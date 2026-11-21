"""Catálogo de decisiones del jugador. Solo están las que tienen efectos medidos en datos."""

from dataclasses import dataclass, fields

import numpy as np

from app.sim.params import P
from app.sim.state import CES, EMP, EMPR, Estado
from app.sim.tables import tablas


@dataclass(frozen=True)
class Decision:
    clave: str
    nombre: str
    descripcion: str
    cuando: tuple            # situaciones en que se puede elegir
    grupo: str = "trabajo"   # base | trabajo | crecer | vida | riesgo | oportunidad


CATALOGO: dict[str, Decision] = {d.clave: d for d in [
    Decision("seguir", "Seguir igual", "Dejas que el año corra sin cambiar nada.", (EMP, CES, EMPR), "base"),
    Decision("buscar_pega", "Buscar otra pega", "Mandas currículums y vas a entrevistas. Te llegan más ofertas y aceptas mejoras más chicas.", (EMP,), "trabajo"),
    Decision("capacitarte", "Hacer un curso SENCE", "Un curso de más de 140 horas que tu empresa paga con la franquicia tributaria.", (EMP,), "crecer"),
    Decision("magister", "Hacer un magíster", "Estudias mientras trabajas y pagas el arancel. Al titularte, la prima depende de la universidad.", (EMP,), "crecer"),
    Decision("sabatico", "Año sabático", "Renuncias y paras un año. Vives de tus ahorros y vuelves a buscar con un hueco en el currículum.", (EMP,), "riesgo"),
    Decision("emprender", "Emprender", "Dejas el empleo y partes algo propio: por tu cuenta o con empleados.", (EMP, CES), "riesgo"),
    Decision("volver_empleo", "Cerrar y volver a emplearte", "Cierras el emprendimiento y sales a buscar trabajo.", (EMPR,), "trabajo"),
    Decision("aceptar_oferta", "Aceptar la oferta", "Te cambias a la empresa que te ofreció trabajo.", (EMP,), "oportunidad"),
]}

ALIAS = {"cambiar_pega": "buscar_pega", "estudiar": "magister"}
TIPOS_EMP = ["cuenta_propia", "empleador"]


def normalizar(texto: str) -> tuple[str, int]:
    """'magister:86' -> ('magister', índice de la universidad con código SIES 86). Sin código, la que más magísteres ofrece."""
    clave, _, arg = texto.strip().partition(":")
    clave = ALIAS.get(clave, clave)
    if clave not in CATALOGO:
        raise ValueError(f"Decisión desconocida: {texto}")
    if clave == "emprender":
        if arg and arg not in TIPOS_EMP:
            raise ValueError(f"Tipo de emprendimiento desconocido: {arg} (usa {' o '.join(TIPOS_EMP)})")
        return clave, TIPOS_EMP.index(arg) if arg else 0
    if clave == "magister":
        tb = tablas()
        if arg and arg not in tb.uni_idx:
            raise ValueError(f"Universidad desconocida: {arg}")
        return clave, tb.uni_idx[arg] if arg else tb.uni_defecto
    return clave, -1


@dataclass
class Intencion:
    horas: np.ndarray
    busca: np.ndarray
    magister: np.ndarray
    sabatico: np.ndarray
    emprende: np.ndarray
    volver: np.ndarray
    capacita: np.ndarray
    acepta: np.ndarray
    destino: int = -1   # universidad del magíster o tipo de emprendimiento


def intencion(e: Estado, clave: str, destino: int = -1) -> Intencion:
    """Aplica la decisión solo en los universos donde es posible; en el resto equivale a 'seguir'."""
    emp, ces, empr = e.sit == EMP, e.sit == CES, e.sit == EMPR
    i = Intencion(np.full(e.n, P.HORAS_BASE), *(np.zeros(e.n, bool) for _ in fields(Intencion)[1:-1]), destino=destino)
    campo, donde = {
        "buscar_pega": ("busca", emp), "magister": ("magister", emp & ~e.postgrado & (e.estudia == 0)), "sabatico": ("sabatico", emp),
        "emprende": ("emprende", emp | ces), "emprender": ("emprende", emp | ces), "volver_empleo": ("volver", empr),
        "capacitarte": ("capacita", emp), "aceptar_oferta": ("acepta", emp),
    }.get(clave, (None, None))
    if campo:
        setattr(i, campo, donde)
    return i


def disponibles(e: Estado) -> list[str]:
    """Decisiones con sentido para un gemelo concreto (un solo universo). La oferta depende del año (hand.py)."""
    sit = int(e.sit[0])
    out = []
    for d in CATALOGO.values():
        if sit not in d.cuando or d.grupo == "oportunidad":
            continue
        if d.clave == "magister" and (e.postgrado[0] or e.estudia[0] > 0):
            continue
        out.append(d.clave)
    return out
