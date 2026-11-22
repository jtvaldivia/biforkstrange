"""Motor Monte Carlo: aplica decisiones año a año sobre n_runs universos y anota por qué cambia cada cosa."""

import numpy as np

from app.sim.decisions import get_decision
from app.sim.decisions.catalog import BURNOUT_LINE, BURNOUT_SLOPE, ParametricDecision
from app.sim.explain import explain_step, summarize_run
from app.sim.metrics import summarize
from app.sim.personality import Trait, personalize
from app.sim.state import State, Twin


def simulate(
    twin: Twin,
    decisions: list[str],
    n_runs: int = 2000,
    seed: int | None = None,
    rasgos: dict[str, Trait] | None = None,
) -> dict:
    rng = np.random.default_rng(seed)
    state = State.from_twin(twin, n_runs)
    prev = {"sueldo_p50": float(twin.sueldo), "desgaste_p50": float(twin.desgaste), "prob_desempleo": 0.0}
    trajectory = []
    for key in decisions:
        decision = get_decision(key)
        # lo que trae el año anterior: cuántas vidas llegan quemadas y cuánto riesgo suma eso
        burnout = BURNOUT_SLOPE * np.maximum(state.desgaste - BURNOUT_LINE, 0)
        before = {"quemados": float((state.desgaste > BURNOUT_LINE).mean()), "riesgo_extra": float(burnout.mean())}

        if isinstance(decision, ParametricDecision):
            params, factores = personalize(key, decision.params, rasgos)
            state = decision.apply_with(state, rng, params)
        else:  # decisiones no paramétricas: sin desglose
            params, factores = None, []
            state = decision.apply(state, rng)

        state.edad += 1
        now = summarize(state)
        step = {"decision": key, "edad": state.edad, **now}
        step["explicacion"] = explain_step(decision, params, factores, before, prev, now)
        trajectory.append(step)
        prev = now
    return {
        "edad_final": state.edad,
        "trayectoria": trajectory,
        "resumen": summarize_run(twin, trajectory),
    }
