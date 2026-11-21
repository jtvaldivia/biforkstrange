"""Partida: el jugador decide una vez al año. De los universos simulados ese año, uno
es el que 'te tocó' y la partida sigue desde ahí. En paralelo vive un gemelo sombra que
nunca cambia nada y recibe exactamente la misma suerte."""

import numpy as np

from app.sim.companies import RUBROS, nombre_empresa
from app.sim.context import Ctx
from app.sim.counterfactual import Opcion, menu
from app.sim.params import P
from app.sim.decisions import normalizar
from app.sim.engine import paso
from app.sim.hand import mano
from app.sim.luck import Suerte
from app.sim.metrics import resumen_anual
from app.sim.profile import NIVELES, TAMANOS, Perfil
from app.sim.state import CES, EMP, EMPR, SITUACIONES, Estado
from app.sim.tables import tablas

_M = lambda x: f"${x / 1e6:.2f} M".replace(".", ",")  # noqa: E731


def _sueldo(e: Estado) -> float:
    return float(e.sueldo[0] * np.exp(-e.cicatriz[0]))


def ficha(e: Estado, perfil: Perfil | None = None) -> dict:
    """Estado legible de un gemelo (un solo universo)."""
    tb = tablas()
    o, sit = int(e.ocup[0]), int(e.sit[0])
    return {
        "edad": e.edad, "anio": e.anio, "situacion": SITUACIONES[sit], "ocupacion": tb.nombres[o], "isco": tb.codigos[o],
        "nivel": NIVELES[int(e.nivel[0])], "empleador": TAMANOS[int(e.tam[0])],
        "empresa": nombre_empresa(int(e.empresa[0]), perfil.empresa if perfil else "") if sit == EMP else "",
        "rubro": RUBROS[int(e.rubro[0])], "antiguedad": float(e.antig[0]), "exp_ocupacion": float(e.exp_ocup[0]),
        "sueldo": _sueldo(e) if sit == EMP else float(e.ingreso[0]) if sit == EMPR else 0.0, "ingreso_mes": float(e.ingreso[0]), "ahorros": float(e.ahorros[0]),
        "gasto_mes": float(e.gasto[0]), "colchon_meses": float(e.ahorros[0] / max(e.gasto[0], 1)),
        "animo": float(e.animo[0]), "salud": float(e.salud[0]), "social": float(min(e.social[0], 100)), "depresion": bool(e.depresion[0]),
        "horas": float(e.horas[0]), "pareja": bool(e.pareja[0]), "hijos": int(e.hijos[0]), "postgrado": bool(e.postgrado[0]),
        "estudia": int(e.estudia[0]), "ia": float(tb.ia[o]), "meses_sin_trabajo": float(e.meses_ces[0]),
    }


def narrar(antes: Estado, e: Estado, perfil: Perfil, decision: str = "seguir", nube: dict | None = None) -> list[str]:
    """Qué te pasó este año, en frases. Plantillas, sin LLM."""
    tb, ev = tablas(), e.ev
    si = lambda k: bool(ev[k][0])  # noqa: E731
    emp = lambda x: nombre_empresa(int(x.empresa[0]), perfil.empresa)  # noqa: E731
    clave = decision.split(":")[0]
    out = _negocio(antes, e, si)
    if si("oferta_aceptada"):
        out.append(f"Te fuiste a {emp(e)}. Empiezas de cero, con {_M(_sueldo(e))} al mes.")
    if si("despido"):
        meses = e.meses_ces[0]
        out.append(f"Te despidieron de {emp(antes)}. " + (
            f"{'Al mes siguiente' if meses < 1.5 else f'A los {meses:.0f} meses'} entraste a {emp(e)}, con {_M(_sueldo(e))} al mes." if si("reempleo_mismo_anio")
            else f"Terminas el año sin trabajo ({meses:.0f} meses buscando)."))
    if si("cambio"):
        out.append(f"Te llegó una oferta que mejoraba lo tuyo y te cambiaste a {emp(e)}: {_M(_sueldo(e))} al mes.")
    elif clave == "buscar_pega" and antes.sit[0] == EMP and not si("despido"):
        out.append("Fuiste a entrevistas, pero ninguna oferta superó lo que ganas.")
    if si("ascenso"):
        out.append(f"Te ascendieron a {NIVELES[int(e.nivel[0])]} en {emp(e)}.")
    if si("encuentra"):
        out.append(f"Encontraste trabajo en {emp(e)} tras {e.meses_ces[0]:.0f} meses de búsqueda: {_M(_sueldo(e))} al mes.")
    if antes.sit[0] == CES and e.sit[0] == CES and not si("pausa") and not si("emprende"):
        out.append("Buscaste todo el año y no salió nada.")
    if si("cambia_ocup"):
        out.append(f"El trabajo nuevo es en otra ocupación: {tb.nombres[int(e.ocup[0])].split(' (')[0].lower()}.")
    if si("pausa"):
        out.append("Año de pausa cuidando a tu hijo." if si("sale_por_hijo") else "Te tomaste el año. Viviste de tus ahorros.")
    if si("titulo"):
        out.append(f"Terminaste el magíster. Tu sueldo queda en {_M(_sueldo(e))}." + ("" if e.mag_sel[0] else " En una universidad no selectiva, los datos no muestran prima."))
    elif si("estudia"):
        out.append("Un año más de magíster, estudiando mientras trabajas.")
    if si("curso"):
        out.append("Terminaste el curso. En los datos de SENCE, el efecto en el sueldo es de 0,6%.")
    if e.depresion[0] and not antes.depresion[0]:
        out.append("Tuviste síntomas depresivos este año.")
    if si("hijo"):
        out.append("Nació tu hijo." if e.hijos[0] == 1 else f"Nació tu hijo número {int(e.hijos[0])}.")
    if si("pareja_nueva"):
        out.append("Formaste pareja.")
    if si("separacion"):
        out.append("Te separaste.")
    if e.ahorros[0] < 0 <= antes.ahorros[0]:
        out.append("Se te acabaron los ahorros: empiezas a endeudarte.")
    if len(out) <= 1:
        out += situaciones(antes, e, perfil, nube or {})[: 2 - len(out) + 1]
    return out or ["Año sin sobresaltos."]


def _negocio(antes: Estado, e: Estado, si) -> list[str]:
    """El emprendimiento contado con sus números y con la supervivencia real de negocios como el tuyo (EPS)."""
    from app.sim.companies import giro

    if not (si("emprende") or antes.sit[0] == EMPR):
        return []
    tipo = "empleador" if e.emp_tipo[0] == 1 else "cuenta_propia"
    g = giro(int(e.rubro[0]), float(e.emp_giro[0]))
    anio = int(e.emp_anios[0])
    rel = e.ingreso[0] / max(e.emp_ref[0], 1)
    comp = f"{100 * rel:.0f}% de lo que ganarías empleado"
    if si("cierra_voluntario"):
        return [f"Cerraste {g} después de {max(anio, 1)} {'año' if max(anio, 1) == 1 else 'años'} y saliste a buscar trabajo."]
    if si("cierra_emp"):
        return [f"{g[0].upper() + g[1:]} no aguantó: cerró en el año {max(anio, 1)}. El último año te dejó {_M(e.ingreso[0])} al mes. Vuelves a buscar trabajo."]
    sobrevive = P.EMP_SOBREVIVE[tipo][min(anio, 5)]
    if si("emprende"):
        return [f"Abriste {g}" + (" y contrataste gente" if tipo == "empleador" else "") + f". El primer año te dejó {_M(e.ingreso[0])} al mes, {comp}."]
    linea = f"Año {anio} de {g}: te dejó {_M(e.ingreso[0])} al mes, {comp}."
    if anio <= 5:
        linea += f" De cada 100 negocios como el tuyo, {100 * sobrevive:.0f} siguen abiertos a esta altura (EPS)."
    return [linea]


def situaciones(antes: Estado, e: Estado, perfil: Perfil, nube: dict) -> list[str]:
    """Lo que cambió en tu vida este año aunque no haya pasado nada grande, con los datos que lo explican."""
    tb, out = tablas(), []
    if e.sit[0] == EMP:
        a = int(e.antig[0])
        if a in (1, 3, 5, 10, 15, 20):
            extra = " Con 5 años o más, el riesgo de despido baja a un tercio (EPS)." if a == 5 else ""
            out.append(f"Cumpliste {a} {'año' if a == 1 else 'años'} en {nombre_empresa(int(e.empresa[0]), perfil.empresa)}.{extra}")
        d = nube.get("despido", 0)
        if d >= 0.05 and not e.ev["despido"][0]:
            out.append(f"Este año despidieron al {100 * d:.0f}% de la gente con tu perfil. A ti no.")
        if antes.sit[0] == EMP and abs(e.sueldo[0] / max(antes.sueldo[0], 1) - 1) >= 0.03:
            out.append(f"Tu sueldo pasó de {_M(_sueldo(antes))} a {_M(_sueldo(e))} con la edad y el reajuste de la economía (ESI e INE).")
        if e.edad <= P.IA_EDAD_MAX and tb.ia[int(e.ocup[0])] >= P.IA_QUINTIL:
            out.append("Tu ocupación está entre las más expuestas a la IA: a tu edad llegan 19% menos ofertas (Brynjolfsson et al.).")
        m = e.mult_rubro[0]
        if m >= 1.3 and e.anio % 4 == 0:
            out.append(f"En {RUBROS[int(e.rubro[0])].lower()} se despide {m:.1f} veces más que el promedio (INE).".replace(".", ",", 1))
    meses0, meses1 = antes.ahorros[0] / max(antes.gasto[0], 1), e.ahorros[0] / max(e.gasto[0], 1)
    for hito in (6, 12, 24):
        if meses0 < hito <= meses1:
            out.append(f"Tus ahorros ya cubren {hito} meses de gastos.")
            break
    if e.hijos[0] and e.edad_hijo[0] in (1, 6, 14):
        out.append(f"Tu hijo menor cumple {int(e.edad_hijo[0])}. Cada hijo cuesta cerca de $383 mil al mes en bienes y servicios (UNICEF 2025).")
    return out


# (nombre, condición sobre el estado antes y después del año). Son marcas del juego, no parámetros del modelo.
LOGROS = [
    ("Primer ascenso", lambda a, e: e.ev["ascenso"][0]),
    ("Jefatura", lambda a, e: e.nivel[0] >= 3 and e.sit[0] == EMP),
    ("Un año de colchón", lambda a, e: e.ahorros[0] >= 12 * e.gasto[0]),
    ("Los primeros $100 millones", lambda a, e: e.ahorros[0] >= 100e6),
    ("Sueldo duplicado", lambda a, e: e.sit[0] == EMP and e.sueldo[0] >= 2 * e.sueldo0),
    ("De pie otra vez", lambda a, e: e.ev["encuentra"][0] or e.ev["reempleo_mismo_anio"][0]),
    ("Magíster", lambda a, e: e.ev["titulo"][0]),
    ("Nueva ocupación", lambda a, e: e.ev["cambia_ocup"][0]),
    ("Emprendimiento rentable", lambda a, e: a.sit[0] == EMPR and e.ingreso[0] > e.sueldo[0]),
    ("Familia", lambda a, e: e.ev["hijo"][0] and e.hijos[0] == 1),
    ("Cinco años en lo tuyo", lambda a, e: e.exp_ocup[0] >= 5),
]


class Partida:
    def __init__(self, perfil: Perfil, seed: int = 7, n: int = 1000, horizonte: int = 5, **_):
        self.perfil, self.seed, self.n, self.horizonte = perfil, seed, n, horizonte
        self.ctx = Ctx(perfil, Suerte(seed, n))
        self.yo = Estado.desde_perfil(perfil, 1)
        self.sombra = self.yo.copia()            # el gemelo que siempre elige 'seguir'
        self.historial: list[dict] = []
        self.logros: list[str] = []

    def menu(self, todas: bool = False) -> list[Opcion]:
        return menu(self.yo, self.perfil, self.horizonte, self.n, self.seed, todas=todas)

    def decidir(self, decision: str) -> dict:
        normalizar(decision)
        antes, i = self.yo, self.ctx.suerte.indice(self.yo.t)
        carta = next((c for c in mano(antes, self.perfil, self.ctx) if c["decision"] == decision), None)
        nube = paso(antes.replicar(self.n), decision, self.ctx, jugador=True)
        nube_emp = np.full(self.n, antes.sit[0] == EMP)
        self.yo = nube.tomar(i)
        self.sombra = paso(self.sombra.replicar(self.n), "seguir", self.ctx, jugador=True).tomar(i)
        nuevos = [nombre for nombre, cond in LOGROS if nombre not in self.logros and cond(antes, self.yo)]
        self.logros += nuevos
        from app.sim.counterfactual import nombre_decision

        turno = {"decision": decision, "nombre": carta["nombre"] if carta else nombre_decision(decision),
                 "eventos": narrar(antes, self.yo, self.perfil, decision, {"despido": float(nube.ev["despido"][nube_emp].mean()) if nube_emp.any() else 0.0}), "logros": nuevos,
                 "yo": ficha(self.yo, self.perfil), "sombra": ficha(self.sombra, self.perfil), "nube": resumen_anual(nube),
                 "nube_eventos": {k: float(nube.ev[k].mean()) for k in ("despido", "cambio", "ascenso", "encuentra", "cierra_emp", "hijo")}
                 | {"depresion": float(nube.depresion.mean())}}
        self.historial.append(turno)
        return turno

    @classmethod
    def reproducir(cls, perfil: Perfil, decisiones: list[str], **kw) -> "Partida":
        """Reconstruye una partida a partir de sus decisiones (la suerte es determinista)."""
        p = cls(perfil, **kw)
        for d in decisiones:
            p.decidir(d)
        return p
