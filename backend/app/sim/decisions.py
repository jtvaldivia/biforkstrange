"""Catálogo de decisiones del jugador y su traducción a intenciones para los módulos."""

from dataclasses import dataclass, fields

import numpy as np

from app.sim.state import CES, EMP, EMPR, Estado
from app.sim.tables import tablas


@dataclass(frozen=True)
class Decision:
    clave: str
    nombre: str
    descripcion: str
    cuando: tuple            # situaciones en que se puede elegir
    grupo: str = "trabajo"   # trabajo | crecer | vida | riesgo | oportunidad | base


CATALOGO: dict[str, Decision] = {d.clave: d for d in [
    Decision("seguir", "Seguir igual", "Dejas que el año corra sin cambiar nada.", (EMP, CES, EMPR), "base"),
    Decision("buscar_pega", "Buscar otra pega", "Mandas currículums y vas a entrevistas. Si aparece algo mejor, te cambias.", (EMP,), "trabajo"),
    Decision("pedir_aumento", "Pedir aumento", "Te sientas con tu jefe a negociar el sueldo. Puede salir bien o no.", (EMP,), "trabajo"),
    Decision("trabajar_mas", "Ponerte la camiseta", "Un año a 55 horas semanales: te haces notar, pero te cansas y ves menos a tu gente.", (EMP,), "trabajo"),
    Decision("pituto", "Agarrar un pituto", "Trabajos extra los fines de semana: entra más plata, se va el descanso.", (EMP, CES), "trabajo"),
    Decision("capacitarte", "Hacer un curso", "Una certificación o un curso corto para ponerte al día en tu oficio.", (EMP, CES, EMPR), "crecer"),
    Decision("networking", "Mover tus contactos", "Charlas, cafés y eventos del rubro. Más gente sabe quién eres.", (EMP, CES, EMPR), "crecer"),
    Decision("magister", "Hacer un magíster", "Dos años estudiando mientras trabajas. Caro y cansador; al titularte suben sueldo y ascensos.", (EMP,), "crecer"),
    Decision("reconvertir", "Cambiar de ocupación", "Un año formándote para pasar a otra ocupación. Mientras más afín a la tuya, más probable.", (EMP, CES), "crecer"),
    Decision("cuidarte", "Cuidarte", "Deporte, sueño y chequeos. Este año tu salud va primero.", (EMP, CES, EMPR), "vida"),
    Decision("tu_gente", "Priorizar a tu gente", "Sales a la hora y no faltas a nada. Ganas vida; quizás pierdes un ascenso.", (EMP, EMPR), "vida"),
    Decision("bajar_ritmo", "Bajar el ritmo", "Un año a 38 horas para recuperar energía.", (EMP,), "vida"),
    Decision("tener_hijo", "Tener un hijo", "Buscan un hijo este año.", (EMP, CES, EMPR), "vida"),
    Decision("sabatico", "Año sabático", "Renuncias y paras un año. Vives de tus ahorros y vuelves con un hueco en el currículum.", (EMP,), "riesgo"),
    Decision("emprender", "Emprender", "Dejas el empleo y partes algo propio. La mayoría gana menos que empleada; pocos ganan mucho.", (EMP, CES), "riesgo"),
    Decision("volver_empleo", "Cerrar y volver a emplearte", "Cierras el emprendimiento y sales a buscar trabajo.", (EMPR,), "trabajo"),
    Decision("bajar_pretensiones", "Bajar pretensiones", "Aceptas la primera oferta razonable: encuentras antes, con menos sueldo.", (CES,), "trabajo"),
    Decision("aceptar_oferta", "Aceptar la oferta", "Te cambias a la empresa que te vino a buscar.", (EMP,), "oportunidad"),
    Decision("postular_ascenso", "Postular al ascenso", "Se abrió un cupo arriba tuyo y te la juegas por él.", (EMP,), "oportunidad"),
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
    horas: np.ndarray
    reconv: np.ndarray     # índice de ocupación destino o -1
    busca: np.ndarray
    pide: np.ndarray
    magister: np.ndarray
    sabatico: np.ndarray
    emprende: np.ndarray
    volver: np.ndarray
    baja: np.ndarray
    hijo: np.ndarray
    capacita: np.ndarray
    networking: np.ndarray
    cuida: np.ndarray
    tu_gente: np.ndarray
    pituto: np.ndarray
    acepta: np.ndarray
    postula: np.ndarray


def intencion(e: Estado, clave: str, destino: int = -1) -> Intencion:
    """Aplica la decisión solo en los universos donde es posible; en el resto equivale a 'seguir'."""
    emp, ces, empr = e.sit == EMP, e.sit == CES, e.sit == EMPR
    todos = emp | ces | empr
    i = Intencion(np.full(e.n, 44.0), np.full(e.n, -1), *(np.zeros(e.n, bool) for _ in fields(Intencion)[2:]))
    if clave == "trabajar_mas":
        i.horas[emp] = 55.0
    elif clave == "bajar_ritmo":
        i.horas[emp] = 38.0
    elif clave == "reconvertir":
        i.reconv[emp | ces] = destino
    elif clave == "tener_hijo":
        i.hijo = e.pareja & (e.hijos < 4)
    else:
        campo, donde = {
            "buscar_pega": ("busca", emp), "pedir_aumento": ("pide", emp), "magister": ("magister", emp), "sabatico": ("sabatico", emp),
            "emprender": ("emprende", emp | ces), "volver_empleo": ("volver", empr), "bajar_pretensiones": ("baja", ces),
            "capacitarte": ("capacita", todos), "networking": ("networking", todos), "cuidarte": ("cuida", todos),
            "tu_gente": ("tu_gente", emp | empr), "pituto": ("pituto", emp | ces), "aceptar_oferta": ("acepta", emp),
            "postular_ascenso": ("postula", emp),
        }.get(clave, (None, None))
        if campo:
            setattr(i, campo, donde)
    return i


def disponibles(e: Estado) -> list[str]:
    """Decisiones que tienen sentido para un gemelo concreto (estado de un solo universo).
    Las de oportunidad no entran aquí: dependen de lo que el año te ofrezca (ver opportunities.py)."""
    sit = int(e.sit[0])
    out = []
    for d in CATALOGO.values():
        if sit not in d.cuando or d.grupo == "oportunidad":
            continue
        if d.clave == "magister" and (e.postgrado[0] or e.estudia[0] > 0):
            continue
        if d.clave == "tener_hijo" and not (e.pareja[0] and e.hijos[0] < 4 and e.edad <= 45):
            continue
        out.append(d.clave)
    return out
