"""Partida: el jugador decide una vez al año. De los universos simulados ese año, uno
es el que 'te tocó' y la partida sigue desde ahí. En paralelo vive un gemelo sombra que
nunca cambia nada y recibe exactamente la misma suerte."""

import numpy as np

from app.sim.context import Ctx
from app.sim.counterfactual import Opcion, menu, nombre_decision
from app.sim.decisions import normalizar
from app.sim.engine import paso
from app.sim.luck import Suerte
from app.sim.metrics import resumen_anual
from app.sim.profile import NIVELES, TAMANOS, Perfil
from app.sim.state import CES, EMP, EMPR, SITUACIONES, Estado
from app.sim.tables import tablas


def ficha(e: Estado) -> dict:
    """Estado legible de un gemelo (un solo universo)."""
    tb = tablas()
    o = int(e.ocup[0])
    sit = int(e.sit[0])
    return {
        "edad": e.edad, "anio": e.anio, "situacion": SITUACIONES[sit], "ocupacion": tb.nombres[o], "isco": tb.codigos[o],
        "nivel": NIVELES[int(e.nivel[0])], "empleador": TAMANOS[int(e.tam[0])],
        "sueldo": float(e.sueldo[0] * (float(np.exp(-e.cicatriz[0])))) if sit == EMP else 0.0,
        "ingreso_mes": float(e.ingreso[0]), "ahorros": float(e.ahorros[0]), "gasto_mes": float(e.gasto[0]),
        "energia": float(e.energia[0]), "animo": float(e.animo[0]), "social": float(e.social[0]),
        "pareja": bool(e.pareja[0]), "hijos": int(e.hijos[0]), "contactos": float(e.contactos[0]),
        "postgrado": bool(e.postgrado[0]), "estudia": int(e.estudia[0]), "ia": float(tb.ia[o]),
        "meses_sin_trabajo": float(e.meses_ces[0]),
    }


def narrar(antes: Estado, e: Estado) -> list[str]:
    """Qué te pasó este año, en frases. Plantillas, sin LLM."""
    tb, ev = tablas(), e.ev
    si = lambda k: bool(ev[k][0])  # noqa: E731
    m = lambda x: f"${x / 1e6:.2f} M".replace(".", ",")  # noqa: E731
    out = []
    if si("despido"):
        meses = e.meses_ces[0]
        out.append("Te despidieron. " + (f"Encontraste otro trabajo a los {meses:.0f} meses, con sueldo de {m(e.sueldo[0] * float(np.exp(-e.cicatriz[0])))}."
                                          if si("reempleo_mismo_anio") else f"Terminas el año sin trabajo ({meses:.0f} meses buscando)."))
    if si("cambio"):
        out.append(f"Te llegó una oferta mejor y te cambiaste: de {m(antes.sueldo[0])} a {m(e.sueldo[0])}.")
    if si("ascenso"):
        out.append(f"Te ascendieron a {NIVELES[int(e.nivel[0])]}." + (f" Ahora tu rol es: {tb.nombres[int(e.ocup[0])]}." if si("a_jefatura") else ""))
    if si("aumento"):
        out.append("Pediste aumento y resultó.")
    if si("aumento_no"):
        out.append("Pediste aumento y te dijeron que no.")
    if si("encuentra"):
        out.append(f"Encontraste trabajo tras {e.meses_ces[0]:.0f} meses de búsqueda este año: {m(e.sueldo[0] * float(np.exp(-e.cicatriz[0])))} al mes.")
    if antes.sit[0] == CES and e.sit[0] == CES and not si("pausa"):
        out.append("Buscaste todo el año y no salió nada.")
    if si("cambia_ocup") and not si("reconv_ok"):
        out.append(f"Tu nuevo trabajo es en otra ocupación: {tb.nombres[int(e.ocup[0])]}.")
    if si("reconv_ok"):
        out.append(f"Lograste el cambio de ocupación. Ahora trabajas en: {tb.nombres[int(e.ocup[0])]}, con {m(e.sueldo[0])} al mes.")
    if si("reconv_no"):
        out.append("Te formaste, pero todavía no logras el cambio de ocupación. Puedes volver a intentarlo.")
    if si("pausa"):
        out.append("Año de pausa cuidando a tu hijo." if si("sale_por_hijo") else "Te tomaste el año. Viviste de tus ahorros.")
    if si("emprende"):
        out.append(f"Partiste tu emprendimiento. Este año te dejó {m(e.ingreso[0])} al mes.")
    elif antes.sit[0] == EMPR and e.ingreso[0] > 0:
        out.append(f"Tu emprendimiento te dejó {m(e.ingreso[0])} al mes este año.")
    if si("cierra_emp"):
        out.append("El emprendimiento cerró. Vuelves a buscar trabajo.")
    if si("titulo"):
        out.append("Terminaste el magíster.")
    elif si("estudia"):
        out.append("Primer año de magíster, estudiando mientras trabajas.")
    if si("burnout"):
        out.append("Te agotaste: licencia médica por estrés." + (" La isapre o Fonasa la rechazó y perdiste dos meses de sueldo." if si("licencia_rechazada") else ""))
    if si("hijo"):
        out.append("Nació tu hijo." if e.hijos[0] == 1 else f"Nació tu hijo número {int(e.hijos[0])}.")
    if si("pareja_nueva"):
        out.append("Formaste pareja.")
    if si("separacion"):
        out.append("Te separaste.")
    if e.ahorros[0] < 0 <= antes.ahorros[0]:
        out.append("Se te acabaron los ahorros: empiezas a endeudarte.")
    return out or ["Año sin sobresaltos."]


class Partida:
    def __init__(self, perfil: Perfil, seed: int = 7, n: int = 1000, escenario: str = "base", horizonte: int = 5):
        self.perfil, self.seed, self.n, self.escenario, self.horizonte = perfil, seed, n, escenario, horizonte
        self.ctx = Ctx(perfil, Suerte(seed, n), escenario)
        self.yo = Estado.desde_perfil(perfil, 1)
        self.sombra = self.yo.copia()            # el gemelo que siempre elige 'seguir'
        self.historial: list[dict] = []

    def menu(self) -> list[Opcion]:
        return menu(self.yo, self.perfil, self.horizonte, self.n, self.seed, self.escenario)

    def decidir(self, decision: str) -> dict:
        normalizar(decision)
        antes, i = self.yo, self.ctx.suerte.indice(self.yo.t)
        nube = paso(antes.replicar(self.n), decision, self.ctx)
        self.yo = nube.tomar(i)
        self.sombra = paso(self.sombra.replicar(self.n), "seguir", self.ctx).tomar(i)
        turno = {"decision": decision, "nombre": nombre_decision(decision), "eventos": narrar(antes, self.yo),
                 "yo": ficha(self.yo), "sombra": ficha(self.sombra), "nube": resumen_anual(nube),
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
