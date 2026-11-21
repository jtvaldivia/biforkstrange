"""Gemelo contrafactual: el mismo gemelo vive cada opción con la misma suerte.
La diferencia entre dos caminos se calcula universo por universo."""

from dataclasses import dataclass, field

import numpy as np

from app.sim.context import Ctx
from app.sim.decisions import CATALOGO, disponibles
from app.sim.engine import paso
from app.sim.luck import Suerte
from app.sim.metrics import pct
from app.sim.profile import Perfil
from app.sim.state import Estado
from app.sim.tables import tablas


def p_reconvertir(origen: int, destino: int, nivel: int) -> float:
    """Probabilidad anual de lograr el cambio de ocupación."""
    from app.sim.params import P

    tb = tablas()
    p = P.RECONV_BASE + P.RECONV_AFIN * tb.afinidad[origen, destino]
    if tb.es_directivo[destino] and not tb.es_directivo[origen]:
        p *= P.RECONV_DIRECTIVO[nivel]
    return float(p)


def sugerir_destinos(ocup: int, nivel: int = 2, k: int = 3) -> list[int]:
    """Tres ocupaciones a las que mirar: la más afín, la afín menos expuesta a IA y una afín de otra familia.
    No sugiere bajar de grupo salarial, ni cargos directivos antes del nivel senior."""
    tb = tablas()
    af = tb.afinidad[ocup].copy()
    af[ocup] = 0
    af[tb.rel < 0.95 * tb.rel[ocup]] = 0
    if nivel < 2:
        af[tb.es_directivo] = 0
    cand = np.flatnonzero(af >= 0.75)
    if cand.size < k:   # pocas ocupaciones muy afines: se acepta cualquiera sobre el azar
        cand = np.flatnonzero(af > 0.5)
    if cand.size == 0:
        return []
    cand = cand[np.argsort(-af[cand])]
    familia = lambda i: tb.codigos[i][:2]  # noqa: E731
    out = [int(cand[0])]
    resto = [int(c) for c in cand if int(c) not in out]
    if resto:
        out.append(min(resto, key=lambda c: tb.ia[c]))
    otra = [c for c in resto if c not in out and familia(c) not in {familia(o) for o in out} | {familia(ocup)}]
    out += otra[:1]
    out += [c for c in resto if c not in out]
    return out[:k]


def opciones_para(yo: Estado) -> list[str]:
    out = []
    for clave in disponibles(yo):
        if clave == "reconvertir":
            out += [f"reconvertir:{tablas().codigos[d]}" for d in sugerir_destinos(int(yo.ocup[0]), int(yo.nivel[0]))]
        else:
            out.append(clave)
    return out


def proyectar(yo: Estado, perfil: Perfil, plan: list[str], n: int, seed: int, escenario: str, turno: bool = False) -> dict[str, np.ndarray]:
    """Corre un plan desde `yo` y devuelve resultados por universo. Con `turno`, el primer año es el del jugador."""
    ctx = Ctx(perfil, Suerte(seed, n), escenario)
    e = yo.replicar(n)
    ing, animo, ces, burn, deuda, emin = [], [], np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool), np.full(n, 100.0)
    primero = None
    for k, d in enumerate(plan):
        e = paso(e, d, ctx, jugador=turno and k == 0)
        primero = primero or e
        ing.append(e.ingreso)
        animo.append(e.animo)
        ces |= e.meses_ces >= 3
        burn |= e.ev["burnout"]
        deuda |= e.ahorros < 0
        emin = np.minimum(emin, e.energia)
    return {"ingreso": np.mean(ing, 0), "animo": np.mean(animo, 0), "cesantia": ces, "burnout": burn, "deuda": deuda,
            "energia_min": emin, "ahorros": e.ahorros, "final": e, "primero": primero}


@dataclass
class Opcion:
    decision: str
    nombre: str
    ingreso: list[float]          # ingreso mensual promedio del horizonte: p10, p50, p90
    p_cesantia: float             # al menos 3 meses sin trabajo en algún año
    animo: float
    energia_min: float
    p_burnout: float
    ahorros: list[float]          # al final del horizonte: p10, p50, p90
    p_deuda: float
    p_mejor: float = 0.0          # futuros en que gana más que 'seguir', con la misma suerte
    p_peor: float = 0.0           # futuros en que gana menos
    delta_ingreso: float = 0.0    # diferencia mediana de ingreso mensual contra 'seguir'
    delta_animo: float = 0.0
    gemelos: float = 0.0          # fracción de gemelos como tú que elegiría esto
    descripcion: str = ""
    tipo: str = "trabajo"         # base | oportunidad | trabajo | crecer | vida | riesgo
    efectos: list = field(default_factory=list)   # [{texto, tono}] contra 'seguir', para mostrar en la carta
    extra: dict = field(default_factory=dict)


def nombre_decision(decision: str) -> str:
    clave, _, arg = decision.partition(":")
    if clave == "reconvertir" and arg:
        tb = tablas()
        return f"→ {tb.nombres[tb.idx[arg]].split(' (')[0]}"
    return CATALOGO[clave].nombre


_EXITO = {"pedir_aumento": "aumento", "postular_ascenso": "postula_ok", "reconvertir": "reconv_ok", "buscar_pega": "cambio", "tener_hijo": "hijo"}
_SI_RESULTA = {"pedir_aumento": "Si resulta: +6% de sueldo", "postular_ascenso": "Si resulta: subes de nivel y +8% de sueldo",
               "buscar_pega": "Si resulta: mejor sueldo, partes de cero"}
_ATRIBUTOS = [("energia", "Energía", 4), ("animo", "Ánimo", 2), ("salud", "Salud", 2), ("habilidad", "Habilidades", 2),
              ("reputacion", "Reputación", 2), ("contactos", "Contactos", 3), ("social", "Tiempo con tu gente", 4)]


def _plata(x: float) -> str:
    a = abs(x)
    return f"${a / 1e6:.1f} M".replace(".", ",") if a >= 1e6 else f"${a / 1e3:.0f} mil"


def _efectos(dec: str, r: dict, base: dict, sueldo: float) -> list[dict]:
    """Qué cambia con esta carta frente a 'seguir': plata a todo el horizonte, atributos al cierre del primer año."""
    out = []
    clave = dec.split(":")[0]
    if clave in _EXITO:
        out.append({"texto": f"Resulta en {100 * r['primero'].ev[_EXITO[clave]].mean():.0f}% de los futuros", "tono": "neutro"})
    if clave in _SI_RESULTA:
        out.append({"texto": _SI_RESULTA[clave], "tono": "mas"})
    d = float(np.median(r["ingreso"] - base["ingreso"]))
    if abs(d) >= 0.02 * sueldo:
        out.append({"texto": f"{'+' if d > 0 else '−'}{_plata(d)} al mes", "tono": "mas" if d > 0 else "menos"})
    d = float(np.median(r["ahorros"] - base["ahorros"]))
    if abs(d) >= 1.5 * sueldo:
        out.append({"texto": f"Ahorros {'+' if d > 0 else '−'}{_plata(d)}", "tono": "mas" if d > 0 else "menos"})
    attrs = []
    for campo, etiqueta, minimo in _ATRIBUTOS:
        d = float(np.median(getattr(r["primero"], campo)) - np.median(getattr(base["primero"], campo)))
        if abs(d) >= minimo:
            attrs.append((abs(d) / minimo, {"texto": f"{etiqueta} {'+' if d > 0 else '−'}{abs(d):.0f}", "tono": "mas" if d > 0 else "menos"}))
    out += [x for _, x in sorted(attrs, key=lambda t: -t[0])[:3]]
    for campo, etiqueta in (("deuda", "Riesgo de deuda"), ("cesantia", "Riesgo de quedar sin pega"), ("burnout", "Riesgo de agotamiento")):
        p, p0 = float(r[campo].mean()), float(base[campo].mean())
        if p - p0 >= 0.08:
            out.append({"texto": f"{etiqueta} {100 * p:.0f}%", "tono": "menos"})
    return out[:6]


def menu(yo: Estado, perfil: Perfil, horizonte: int = 5, n: int = 1000, seed: int = 7, escenario: str = "base",
         todas: bool = False) -> list[Opcion]:
    """Las cartas del año con su proyección. Con `todas`, la lista completa de decisiones (para análisis)."""
    from app.sim.choice import repartir_gemelos
    from app.sim.hand import mano

    tb = tablas()
    if todas:
        cartas = [{"decision": d, "nombre": nombre_decision(d), "descripcion": CATALOGO[d.split(":")[0]].descripcion,
                   "tipo": CATALOGO[d.split(":")[0]].grupo} for d in opciones_para(yo)]
    else:
        cartas = mano(yo, perfil, Ctx(perfil, Suerte(seed, n), escenario))
    sueldo = float(max(yo.sueldo[0], 1))
    base = proyectar(yo, perfil, ["seguir"] * horizonte, n, seed, escenario, turno=True)
    out = []
    for c in cartas:
        dec = c["decision"]
        r = base if dec == "seguir" else proyectar(yo, perfil, [dec] + ["seguir"] * (horizonte - 1), n, seed, escenario, turno=True)
        op = Opcion(
            decision=dec, nombre=c["nombre"], descripcion=c["descripcion"], tipo=c["tipo"], ingreso=pct(r["ingreso"]),
            p_cesantia=float(r["cesantia"].mean()), animo=float(np.median(r["animo"])), energia_min=float(np.median(r["energia_min"])),
            p_burnout=float(r["burnout"].mean()), ahorros=pct(r["ahorros"]), p_deuda=float(r["deuda"].mean()),
            p_mejor=float((r["ingreso"] > base["ingreso"] * 1.005).mean()), p_peor=float((r["ingreso"] < base["ingreso"] * 0.995).mean()),
            delta_ingreso=float(np.median(r["ingreso"] - base["ingreso"])), delta_animo=float(np.median(r["animo"] - base["animo"])),
            efectos=[] if dec == "seguir" else _efectos(dec, r, base, sueldo),
        )
        if dec.startswith("reconvertir:"):
            d = tb.idx[dec.split(":")[1]]
            a = int(yo.ocup[0])
            op.extra = {"afinidad": float(tb.afinidad[a, d]), "ia_destino": float(tb.ia[d]), "ia_origen": float(tb.ia[a]),
                        "logra": p_reconvertir(a, d, int(yo.nivel[0])), "sueldo_rel": float(tb.rel[d] / tb.rel[a])}
        out.append(op)
    repartir_gemelos(out, yo, perfil)
    return out


def comparar(perfil: Perfil, planes: dict[str, list[str]], n: int = 2000, seed: int = 7, escenario: str = "base",
             desde: Estado | None = None) -> dict:
    """Varios planes completos con la misma suerte. El primero es la referencia."""
    yo = desde or Estado.desde_perfil(perfil, 1)
    res = {k: proyectar(yo, perfil, plan, n, seed, escenario) for k, plan in planes.items()}
    ref = next(iter(res.values()))
    out = {}
    for k, r in res.items():
        f = r["final"]
        out[k] = {
            "ingreso": pct(r["ingreso"]), "sueldo_final": pct(np.where(f.sit == 0, f.sueldo * np.exp(-f.cicatriz), f.ingreso)),
            "ahorros": pct(r["ahorros"]), "animo": float(np.median(r["animo"])), "energia_min": float(np.median(r["energia_min"])),
            "p_cesantia": float(r["cesantia"].mean()), "p_burnout": float(r["burnout"].mean()), "p_deuda": float(r["deuda"].mean()),
            "hijos": float(f.hijos.mean()), "p_pareja": float(f.pareja.mean()),
            "p_mas_ingreso": float((r["ingreso"] > ref["ingreso"] * 1.005).mean()), "p_menos_ingreso": float((r["ingreso"] < ref["ingreso"] * 0.995).mean()),
            "p_mas_ahorros": float((r["ahorros"] > ref["ahorros"] + 500_000).mean()), "p_mejor_animo": float((r["animo"] > ref["animo"] + 1).mean()),
            "p_peor_animo": float((r["animo"] < ref["animo"] - 1).mean()),
            "delta_ingreso": float(np.median(r["ingreso"] - ref["ingreso"])), "delta_ahorros": float(np.median(r["ahorros"] - ref["ahorros"])),
        }
    return out
