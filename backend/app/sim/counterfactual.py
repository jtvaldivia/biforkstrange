"""Gemelo contrafactual: el mismo gemelo vive cada opción con la misma suerte.
La diferencia entre dos caminos se calcula universo por universo."""

from dataclasses import dataclass, field

import numpy as np

from app.sim.choice import frecuencia, texto_frecuencia
from app.sim.context import Ctx
from app.sim.decisions import CATALOGO, disponibles
from app.sim.engine import paso
from app.sim.luck import Suerte
from app.sim.metrics import pct
from app.sim.profile import Perfil
from app.sim.state import EMP, Estado


def proyectar(yo: Estado, perfil: Perfil, plan: list[str], n: int, seed: int, turno: bool = False) -> dict:
    """Corre un plan desde `yo` y devuelve resultados por universo. Con `turno`, el primer año es el del jugador."""
    ctx = Ctx(perfil, Suerte(seed, n))
    e = yo.replicar(n)
    ing, animo = [], []
    ces, dep, deuda = np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool)
    primero = None
    for k, d in enumerate(plan):
        e = paso(e, d, ctx, jugador=turno and k == 0)
        primero = primero or e
        ing.append(e.ingreso)
        animo.append(e.animo)
        ces |= e.meses_ces >= 3
        dep |= e.depresion
        deuda |= e.ahorros < 0
    return {"ingreso": np.mean(ing, 0), "animo": np.mean(animo, 0), "cesantia": ces, "depresion": dep, "deuda": deuda,
            "ahorros": e.ahorros, "final": e, "primero": primero}


@dataclass
class Opcion:
    decision: str
    nombre: str
    ingreso: list[float]          # ingreso mensual promedio del horizonte: p10, p50, p90
    p_cesantia: float             # al menos 3 meses sin trabajo en algún año
    animo: float
    p_depresion: float            # síntomas depresivos en algún año
    ahorros: list[float]          # al final del horizonte: p10, p50, p90
    p_deuda: float
    p_mejor: float = 0.0          # futuros en que gana más que 'seguir', con la misma suerte
    p_peor: float = 0.0
    delta_ingreso: float = 0.0
    delta_ingreso_rango: list = field(default_factory=lambda: [0.0, 0.0])   # p10 y p90 de la diferencia, futuro por futuro
    delta_animo: float = 0.0
    gemelos: float | None = None  # fracción de gente de tu edad que toma esta decisión cada año (dato)
    gemelos_texto: str = ""
    descripcion: str = ""
    tipo: str = "trabajo"
    efectos: list = field(default_factory=list)   # [{texto, tono}] contra 'seguir'
    extra: dict = field(default_factory=dict)


def nombre_decision(decision: str) -> str:
    clave, _, arg = decision.partition(":")
    if clave == "magister":
        from app.sim.decisions import normalizar
        from app.sim.tables import tablas

        return f"Magíster ({tablas().universidades[normalizar(decision)[1]]['nombre']})"
    return CATALOGO[clave].nombre


def _plata(x: float) -> str:
    a = abs(x)
    return f"${a / 1e6:.1f} M".replace(".", ",") if a >= 1e6 else f"${a / 1e3:.0f} mil"


def _efectos(dec: str, r: dict, base: dict, sueldo: float, yo: Estado) -> list[dict]:
    """Chips de una carta frente a 'seguir', futuro por futuro con la misma suerte:
    1) cómo sale la apuesta, 2) el rango de plata, 3) lo que cambia en tu vida, 4) el riesgo principal."""
    out = []
    dif = r["ingreso"] - base["ingreso"]
    mejor, peor = float((dif > 0.005 * base["ingreso"]).mean()), float((dif < -0.005 * base["ingreso"]).mean())
    lo, hi = (float(x) for x in np.percentile(dif, [10, 90]))
    if (mejor >= 0.02 or peor >= 0.02) and max(abs(lo), abs(hi)) >= 0.02 * sueldo:
        if mejor >= 0.95:
            out.append({"texto": "Ganas más en casi todos tus futuros", "tono": "mas"})
        elif peor >= 0.95:
            out.append({"texto": "Ganas menos en casi todos tus futuros", "tono": "menos"})
        else:
            out.append({"texto": f"Ganas más en {100 * mejor:.0f}% · menos en {100 * peor:.0f}%", "tono": "mas" if mejor > peor else "menos"})
    signo = lambda x: ("+" if x > 0 else "−") + _plata(x)  # noqa: E731
    if max(abs(lo), abs(hi)) >= 0.02 * sueldo:
        txt = f"{signo(hi)} al mes" if abs(hi - lo) < 0.02 * sueldo else f"{signo(lo)} a {signo(hi)} al mes"
        out.append({"texto": txt, "tono": "mas" if lo + hi > 0 else "menos"})
    if dec in ("aceptar_oferta", "buscar_pega") and yo.antig[0] >= 1:
        out.append({"texto": f"Pierdes {yo.antig[0]:.0f} años de antigüedad", "tono": "menos"})
    if dec == "capacitarte":
        out.append({"texto": "+0,6% de sueldo (evaluación SENCE)", "tono": "neutro"})
    for campo, etiqueta, minimo in (("animo", "Satisfacción", 1.5), ("social", "Tiempo con tu gente", 1.5)):
        d = float(np.median(getattr(r["primero"], campo)) - np.median(getattr(base["primero"], campo)))
        if abs(d) >= minimo:
            out.append({"texto": f"{etiqueta} {'+' if d > 0 else '−'}{abs(d):.0f}", "tono": "mas" if d > 0 else "menos"})
    riesgos = [(float(r[c].mean()) - float(base[c].mean()), float(r[c].mean()), t) for c, t in
               (("deuda", "Riesgo de deuda"), ("cesantia", "Riesgo de quedar sin pega"), ("depresion", "Riesgo de depresión"))]
    sube, p, t = max(riesgos)
    if sube >= 0.03:
        out.append({"texto": f"{t} {100 * p:.0f}%", "tono": "menos"})
    return out[:4]


def menu(yo: Estado, perfil: Perfil, horizonte: int = 5, n: int = 1000, seed: int = 7, todas: bool = False, **_) -> list[Opcion]:
    """Las cartas del año con su proyección. Con `todas`, todas las decisiones posibles (para análisis)."""
    from app.sim.hand import mano

    if todas:
        cartas = [{"decision": d, "nombre": nombre_decision(d), "descripcion": CATALOGO[d].descripcion, "tipo": CATALOGO[d].grupo}
                  for d in disponibles(yo)]
    else:
        cartas = mano(yo, perfil, Ctx(perfil, Suerte(seed, n)))
    sueldo = float(max(yo.sueldo[0], 1))
    base = proyectar(yo, perfil, ["seguir"] * horizonte, n, seed, turno=True)
    out = []
    for c in cartas:
        dec = c["decision"]
        r = base if dec == "seguir" else proyectar(yo, perfil, [dec] + ["seguir"] * (horizonte - 1), n, seed, turno=True)
        out.append(Opcion(
            decision=dec, nombre=c["nombre"], descripcion=c["descripcion"], tipo=c["tipo"], ingreso=pct(r["ingreso"]),
            p_cesantia=float(r["cesantia"].mean()), animo=float(np.median(r["animo"])), p_depresion=float(r["depresion"].mean()),
            ahorros=pct(r["ahorros"]), p_deuda=float(r["deuda"].mean()),
            p_mejor=float((r["ingreso"] > base["ingreso"] * 1.005).mean()), p_peor=float((r["ingreso"] < base["ingreso"] * 0.995).mean()),
            delta_ingreso=float(np.median(r["ingreso"] - base["ingreso"])), delta_animo=float(np.median(r["animo"] - base["animo"])),
            delta_ingreso_rango=[float(x) for x in np.percentile(r["ingreso"] - base["ingreso"], [10, 90])],
            gemelos=frecuencia(dec, yo, perfil), gemelos_texto=texto_frecuencia(dec, frecuencia(dec, yo, perfil)), efectos=[] if dec == "seguir" else _efectos(dec, r, base, sueldo, yo),
        ))
    return out


def comparar(perfil: Perfil, planes: dict[str, list[str]], n: int = 2000, seed: int = 7, desde: Estado | None = None, **_) -> dict:
    """Varios planes completos con la misma suerte. El primero es la referencia."""
    yo = desde or Estado.desde_perfil(perfil, 1)
    res = {k: proyectar(yo, perfil, plan, n, seed) for k, plan in planes.items()}
    ref = next(iter(res.values()))
    out = {}
    for k, r in res.items():
        f = r["final"]
        out[k] = {
            "ingreso": pct(r["ingreso"]), "sueldo_final": pct(np.where(f.sit == EMP, f.sueldo * np.exp(-f.cicatriz), f.ingreso)),
            "ahorros": pct(r["ahorros"]), "animo": float(np.median(r["animo"])),
            "p_cesantia": float(r["cesantia"].mean()), "p_depresion": float(r["depresion"].mean()), "p_deuda": float(r["deuda"].mean()),
            "hijos": float(f.hijos.mean()), "p_pareja": float(f.pareja.mean()),
            "p_mas_ingreso": float((r["ingreso"] > ref["ingreso"] * 1.005).mean()), "p_menos_ingreso": float((r["ingreso"] < ref["ingreso"] * 0.995).mean()),
            "p_mas_ahorros": float((r["ahorros"] > ref["ahorros"] + 500_000).mean()), "p_mejor_animo": float((r["animo"] > ref["animo"] + 1).mean()),
            "p_peor_animo": float((r["animo"] < ref["animo"] - 1).mean()),
            "delta_ingreso": float(np.median(r["ingreso"] - ref["ingreso"])), "delta_ahorros": float(np.median(r["ahorros"] - ref["ahorros"])),
        }
    return out
