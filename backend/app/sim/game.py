"""Partida: el jugador decide una vez al año. De los universos simulados ese año, uno
es el que 'te tocó' y la partida sigue desde ahí. En paralelo vive un gemelo sombra que
nunca cambia nada y recibe exactamente la misma suerte."""

import numpy as np

from app.sim.companies import RUBROS, nombre_empresa
from app.sim.context import Ctx
from app.sim.counterfactual import Opcion, menu
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
        "rubro": RUBROS[int(e.rubro[0])], "antiguedad": float(e.antig[0]),
        "sueldo": _sueldo(e) if sit == EMP else 0.0, "ingreso_mes": float(e.ingreso[0]), "ahorros": float(e.ahorros[0]),
        "gasto_mes": float(e.gasto[0]), "colchon_meses": float(e.ahorros[0] / max(e.gasto[0], 1)),
        "energia": float(e.energia[0]), "animo": float(e.animo[0]), "salud": float(e.salud[0]), "social": float(min(e.social[0], 100)),
        "habilidad": float(e.habilidad[0]), "reputacion": float(e.reputacion[0]), "contactos": float(e.contactos[0]),
        "pareja": bool(e.pareja[0]), "hijos": int(e.hijos[0]), "postgrado": bool(e.postgrado[0]), "estudia": int(e.estudia[0]),
        "ia": float(tb.ia[o]), "meses_sin_trabajo": float(e.meses_ces[0]),
    }


def narrar(antes: Estado, e: Estado, perfil: Perfil, decision: str = "seguir") -> list[str]:
    """Qué te pasó este año, en frases. Plantillas, sin LLM."""
    tb, ev = tablas(), e.ev
    si = lambda k: bool(ev[k][0])  # noqa: E731
    emp = lambda x: nombre_empresa(int(x.empresa[0]), perfil.empresa)  # noqa: E731
    clave = decision.split(":")[0]
    out = []
    if si("oferta_aceptada"):
        out.append(f"Te fuiste a {emp(e)}. Empiezas de cero, con mejor sueldo.")
    if si("despido"):
        meses = e.meses_ces[0]
        out.append(f"Te despidieron de {emp(antes)}. " + (
            f"{'Al mes siguiente' if meses < 1.5 else f'A los {meses:.0f} meses'} entraste a {emp(e)}, con {_M(_sueldo(e))} al mes." if si("reempleo_mismo_anio")
            else f"Terminas el año sin trabajo ({meses:.0f} meses buscando)."))
    if si("cambio"):
        out.append(f"Saliste a buscar y te resultó: te cambiaste a {emp(e)}. Cierras el año ganando {_M(_sueldo(e))} al mes.")
    elif clave == "buscar_pega" and antes.sit[0] == EMP and not si("despido"):
        out.append("Fuiste a varias entrevistas, pero nada mejoraba lo que tienes.")
    if si("postula_ok"):
        out.append(f"Postulaste y quedaste: ahora eres {NIVELES[int(e.nivel[0])]} en {emp(e)}.")
    elif si("ascenso"):
        out.append(f"Te ascendieron a {NIVELES[int(e.nivel[0])]} en {emp(e)}.")
    if si("a_jefatura"):
        out.append(f"Tu rol cambia: {tb.nombres[int(e.ocup[0])].split(' (')[0]}.")
    if si("postula_no"):
        out.append("Postulaste al ascenso y eligieron a otra persona.")
    if si("aumento"):
        out.append(f"Pediste aumento y resultó: {_M(_sueldo(e))} al mes.")
    if si("aumento_no"):
        out.append("Pediste aumento y te dijeron que este año no.")
    if si("encuentra"):
        out.append(f"Encontraste trabajo en {emp(e)} tras {e.meses_ces[0]:.0f} meses de búsqueda: {_M(_sueldo(e))} al mes.")
    if antes.sit[0] == CES and e.sit[0] == CES and not si("pausa"):
        out.append("Buscaste todo el año y no salió nada.")
    if si("cambia_ocup") and not si("reconv_ok"):
        out.append(f"El trabajo nuevo es en otra ocupación: {tb.nombres[int(e.ocup[0])].split(' (')[0]}.")
    if si("reconv_ok"):
        out.append(f"Lograste el cambio de ocupación. Ahora trabajas en {tb.nombres[int(e.ocup[0])].split(' (')[0].lower()}, en {emp(e)}, con {_M(_sueldo(e))} al mes.")
    if si("reconv_no"):
        out.append("Te formaste, pero todavía no logras el cambio de ocupación. Puedes volver a intentarlo.")
    if si("pausa"):
        out.append("Año de pausa cuidando a tu hijo." if si("sale_por_hijo") else "Te tomaste el año. Viviste de tus ahorros.")
    if si("emprende"):
        out.append(f"Partiste tu emprendimiento. Este año te dejó {_M(e.ingreso[0])} al mes.")
    elif antes.sit[0] == EMPR and e.ingreso[0] > 0:
        out.append(f"Tu emprendimiento te dejó {_M(e.ingreso[0])} al mes este año.")
    if si("cierra_emp"):
        out.append("El emprendimiento cerró. Vuelves a buscar trabajo.")
    if si("titulo"):
        out.append("Terminaste el magíster.")
    elif si("estudia"):
        out.append("Primer año de magíster, estudiando mientras trabajas.")
    if si("burnout"):
        out.append("Te agotaste: licencia médica por estrés." + (" La isapre o Fonasa la rechazó y perdiste dos meses de sueldo." if si("licencia_rechazada") else ""))
    if si("problema_salud"):
        out.append("El cuerpo pasó la cuenta: un problema de salud te tuvo un mes fuera.")
    if si("hijo"):
        out.append("Nació tu hijo." if e.hijos[0] == 1 else f"Nació tu hijo número {int(e.hijos[0])}.")
    elif clave == "tener_hijo":
        out.append("Buscaron un hijo, pero este año no llegó.")
    if si("pareja_nueva"):
        out.append("Formaste pareja.")
    if si("separacion"):
        out.append("Te separaste.")
    if e.ahorros[0] < 0 <= antes.ahorros[0]:
        out.append("Se te acabaron los ahorros: empiezas a endeudarte.")
    if not out:
        out.append({"capacitarte": "Terminaste el curso. Estás más al día en tu oficio.", "networking": "Conociste gente nueva del rubro. Tu nombre empieza a sonar.",
                    "cuidarte": "Un año cuidándote: duermes mejor y te sientes con más cuerda.", "tu_gente": "Estuviste en todas: cumpleaños, asados y domingos en familia.",
                    "pituto": "Los pitutos dejaron plata extra, a costa de tus fines de semana.", "trabajar_mas": "Un año de jornadas largas. En la oficina lo notaron.",
                    "bajar_ritmo": "Bajaste el ritmo y recuperaste energía."}.get(clave, "Año sin sobresaltos."))
    return out


# (nombre, condición sobre el estado antes y después del año)
LOGROS = [
    ("Primer ascenso", lambda a, e: e.ev["ascenso"][0]),
    ("Jefatura", lambda a, e: e.nivel[0] >= 3 and e.sit[0] == EMP),
    ("Un año de colchón", lambda a, e: e.ahorros[0] >= 12 * e.gasto[0]),
    ("Los primeros $100 millones", lambda a, e: e.ahorros[0] >= 100e6),
    ("Sueldo duplicado", lambda a, e: e.sit[0] == EMP and e.sueldo[0] >= 2 * e.sueldo0),
    ("De pie otra vez", lambda a, e: e.ev["encuentra"][0] or e.ev["reempleo_mismo_anio"][0]),
    ("Magíster", lambda a, e: e.ev["titulo"][0]),
    ("Nueva ocupación", lambda a, e: e.ev["reconv_ok"][0]),
    ("Emprendimiento rentable", lambda a, e: a.sit[0] == EMPR and e.ingreso[0] > e.sueldo[0]),
    ("Familia", lambda a, e: e.ev["hijo"][0] and e.hijos[0] == 1),
    ("Red de 100 contactos", lambda a, e: e.contactos[0] >= 100),
    ("Al día en tu oficio", lambda a, e: e.habilidad[0] >= 80),
    ("En plena forma", lambda a, e: e.energia[0] >= 75 and e.salud[0] >= 85),
]


class Partida:
    def __init__(self, perfil: Perfil, seed: int = 7, n: int = 1000, escenario: str = "base", horizonte: int = 5):
        self.perfil, self.seed, self.n, self.escenario, self.horizonte = perfil, seed, n, escenario, horizonte
        self.ctx = Ctx(perfil, Suerte(seed, n), escenario)
        self.yo = Estado.desde_perfil(perfil, 1)
        self.sombra = self.yo.copia()            # el gemelo que siempre elige 'seguir'
        self.historial: list[dict] = []
        self.logros: list[str] = []

    def menu(self, todas: bool = False) -> list[Opcion]:
        return menu(self.yo, self.perfil, self.horizonte, self.n, self.seed, self.escenario, todas=todas)

    def decidir(self, decision: str) -> dict:
        normalizar(decision)
        antes, i = self.yo, self.ctx.suerte.indice(self.yo.t)
        carta = next((c for c in mano(antes, self.perfil, self.ctx) if c["decision"] == decision), None)
        nube = paso(antes.replicar(self.n), decision, self.ctx, jugador=True)
        self.yo = nube.tomar(i)
        self.sombra = paso(self.sombra.replicar(self.n), "seguir", self.ctx, jugador=True).tomar(i)
        nuevos = [nombre for nombre, cond in LOGROS if nombre not in self.logros and cond(antes, self.yo)]
        self.logros += nuevos
        from app.sim.counterfactual import nombre_decision

        turno = {"decision": decision, "nombre": carta["nombre"] if carta else nombre_decision(decision),
                 "eventos": narrar(antes, self.yo, self.perfil, decision), "logros": nuevos,
                 "yo": ficha(self.yo, self.perfil), "sombra": ficha(self.sombra, self.perfil), "nube": resumen_anual(nube),
                 "nube_eventos": {k: float(nube.ev[k].mean()) for k in ("despido", "cambio", "ascenso", "aumento", "burnout", "encuentra", "reconv_ok", "cierra_emp", "hijo")}}
        self.historial.append(turno)
        return turno

    @classmethod
    def reproducir(cls, perfil: Perfil, decisiones: list[str], **kw) -> "Partida":
        """Reconstruye una partida a partir de sus decisiones (la suerte es determinista)."""
        p = cls(perfil, **kw)
        for d in decisiones:
            p.decidir(d)
        return p
