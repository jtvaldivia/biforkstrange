"""El motor detrás de la historia.

Simula muchas vidas posibles con la misma semilla y sigue una: la tuya (la vida 0).
La historia cuenta lo que le pasó a esa vida; el resto sirve para saber qué tan
común o raro fue ("a uno de cada diez le toca quedar sin pega").
Se re-simula desde el inicio en cada capítulo: es barato y no hay que guardar estado.
"""

from dataclasses import dataclass

import numpy as np

from app.sim import carryover
from app.sim.decisions import get_decision
from app.sim.decisions.catalog import BURNOUT_LINE, ParametricDecision
from app.sim.personality import Trait, personalize
from app.sim.state import State, Twin

N_LIVES = 400
ME = 0  # la vida que se narra


@dataclass
class YearFacts:
    """Lo que pasó en tu vida ese año y qué tan común fue entre las vidas posibles."""

    decision: str
    sin_pega: bool
    sueldo_rel: float  # tu sueldo / sueldo inicial
    cambio_sueldo: float  # contra el año anterior
    desgaste: float  # 0–1
    cambio_desgaste: float
    prob_sin_pega: float  # en todas las vidas
    prob_quemado: float  # desgaste sobre la línea, en todas las vidas
    mejor_que_mitad: bool  # tu plata quedó sobre la mediana
    factores: list[dict]  # cómo te ajustaron tus rasgos (texto + efecto)
    arrastre: list[str]  # lo que trae el año anterior (estudio que rinde, volver tras quedar sin pega...)

    def as_dict(self) -> dict:
        return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


def replay(twin: Twin, decisions: list[str], seed: int, rasgos: dict[str, Trait] | None) -> list[YearFacts]:
    rng = np.random.default_rng(seed)
    state = State.from_twin(twin, N_LIVES)
    start = float(twin.sueldo)
    out: list[YearFacts] = []
    for key in decisions:
        d = get_decision(key)
        prev_s, prev_d = float(state.sueldo[ME]), float(state.desgaste[ME])
        prev_all, was_out = state.sueldo.copy(), state.desempleado.copy()
        risk_x, growth_x, arrastre = carryover.before_year(state, key, ME)
        if isinstance(d, ParametricDecision):
            params, factores = personalize(key, d.params, rasgos)
            state = d.apply_with(state, rng, params, risk_x, growth_x)
        else:
            factores = []
            state = d.apply(state, rng)
        arrastre += carryover.after_year(state, key, prev_all, was_out, ME)
        state.edad += 1
        s, w = float(state.sueldo[ME]), float(state.desgaste[ME])
        out.append(YearFacts(
            decision=key,
            sin_pega=bool(state.desempleado[ME]),
            sueldo_rel=s / start,
            cambio_sueldo=s / prev_s - 1 if prev_s else 0.0,
            desgaste=w,
            cambio_desgaste=w - prev_d,
            prob_sin_pega=float(state.desempleado.mean()),
            prob_quemado=float((state.desgaste > BURNOUT_LINE).mean()),
            mejor_que_mitad=bool(s >= float(np.median(state.sueldo))),
            factores=[{"texto": f["texto"], "param": f["param"], "delta": round(f["delta"], 4)} for f in factores],
            arrastre=arrastre,
        ))
    return out
