"""Motor de microsimulación de paso anual. Un `paso` aplica una decisión a todos los
universos y corre los módulos en orden fijo."""

from dataclasses import replace

import numpy as np

from app.sim.context import Ctx
from app.sim.decisions import intencion, normalizar
from app.sim.luck import Suerte
from app.sim.metrics import resumen_anual
from app.sim.modules.family import familia
from app.sim.modules.finance import finanzas
from app.sim.modules.labor import trabajo
from app.sim.modules.wellbeing import bienestar
from app.sim.profile import Perfil
from app.sim.state import Estado, Eventos

MODULOS = (familia, trabajo, bienestar, finanzas)


def paso(e: Estado, decision: str, ctx: Ctx, jugador: bool = False) -> Estado:
    """Avanza un año. No modifica el estado de entrada. Con `jugador`, es el año en que decide una
    persona: no cambia de trabajo por su cuenta, solo si lo elige."""
    clave, destino = normalizar(decision)
    ctx = replace(ctx, jugador=jugador)
    e = e.copia()
    ev = Eventos(e.n)
    i = intencion(e, clave, destino)
    for modulo in MODULOS:
        modulo(e, i, ctx, ev)
    e.ev = ev
    e.t, e.edad, e.anio = e.t + 1, e.edad + 1, e.anio + 1
    return e


def simular(perfil: Perfil, plan: list[str], n: int = 2000, seed: int = 7, desde: Estado | None = None, **_) -> list[Estado]:
    """Corre un plan completo sobre n universos. Devuelve el estado al final de cada año."""
    e = (desde or Estado.desde_perfil(perfil, 1)).replicar(n)
    ctx = Ctx(perfil, Suerte(seed, n))
    out = []
    for decision in plan:
        e = paso(e, decision, ctx)
        out.append(e)
    return out


def simulate(twin, decisions: list[str], n_runs: int = 2000, seed: int | None = None, perfil: dict | None = None) -> dict:
    """Entrada de la API. `twin` es el formato simple (edad, sueldo); `perfil`, el completo."""
    base = perfil or {"edad": twin.edad, "sueldo": twin.sueldo, "ahorros": 0, "institucion": "universidad"}
    pf = Perfil.desde_dict(base)
    seed = int(seed if seed is not None else np.random.SeedSequence().entropy % 2**31)
    estados = simular(pf, decisions, n_runs, seed)
    tray = [{"decision": d, **resumen_anual(e)} for d, e in zip(decisions, estados)]
    return {"edad_final": estados[-1].edad if estados else pf.edad, "trayectoria": tray}
