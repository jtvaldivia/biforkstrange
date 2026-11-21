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
    if cand.size < k:
        cand = np.argsort(-af)[: max(k, 5)]
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


def proyectar(yo: Estado, perfil: Perfil, plan: list[str], n: int, seed: int, escenario: str) -> dict[str, np.ndarray]:
    """Corre un plan desde `yo` y devuelve resultados por universo."""
    ctx = Ctx(perfil, Suerte(seed, n), escenario)
    e = yo.replicar(n)
    ing, animo, ces, burn, deuda, emin = [], [], np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool), np.full(n, 100.0)
    for d in plan:
        e = paso(e, d, ctx)
        ing.append(e.ingreso)
        animo.append(e.animo)
        ces |= e.meses_ces >= 3
        burn |= e.ev["burnout"]
        deuda |= e.ahorros < 0
        emin = np.minimum(emin, e.energia)
    return {"ingreso": np.mean(ing, 0), "animo": np.mean(animo, 0), "cesantia": ces, "burnout": burn, "deuda": deuda,
            "energia_min": emin, "ahorros": e.ahorros, "final": e}


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
    extra: dict = field(default_factory=dict)


def nombre_decision(decision: str) -> str:
    clave, _, arg = decision.partition(":")
    if clave == "reconvertir" and arg:
        tb = tablas()
        return f"→ {tb.nombres[tb.idx[arg]].split(' (')[0]}"
    return CATALOGO[clave].nombre


def menu(yo: Estado, perfil: Perfil, horizonte: int = 5, n: int = 1000, seed: int = 7, escenario: str = "base") -> list[Opcion]:
    from app.sim.choice import repartir_gemelos

    tb = tablas()
    base = proyectar(yo, perfil, ["seguir"] * horizonte, n, seed, escenario)
    out = []
    for dec in opciones_para(yo):
        r = base if dec == "seguir" else proyectar(yo, perfil, [dec] + ["seguir"] * (horizonte - 1), n, seed, escenario)
        op = Opcion(
            decision=dec, nombre=nombre_decision(dec), ingreso=pct(r["ingreso"]), p_cesantia=float(r["cesantia"].mean()),
            animo=float(np.median(r["animo"])), energia_min=float(np.median(r["energia_min"])), p_burnout=float(r["burnout"].mean()),
            ahorros=pct(r["ahorros"]), p_deuda=float(r["deuda"].mean()),
            p_mejor=float((r["ingreso"] > base["ingreso"] * 1.005).mean()), p_peor=float((r["ingreso"] < base["ingreso"] * 0.995).mean()),
            delta_ingreso=float(np.median(r["ingreso"] - base["ingreso"])), delta_animo=float(np.median(r["animo"] - base["animo"])),
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
