"""Catálogo de decisiones. growth, riesgo_rel y wear son de relleno: calibrar con datos reales."""

import numpy as np

from app.sim.decisions.base import Decision
from app.sim.state import State


CAIDA_SUELDO_AL_PERDER_EMPLEO = 0.6  # relleno


class ParametricDecision(Decision):
    """Decisión definida por (crecimiento, riesgo relativo de cesantía, desgaste).

    El riesgo base de perder el empleo sale de la EPS según la edad; `riesgo_rel`
    lo multiplica (1.0 = igual que el promedio de tu edad).
    """

    growth: float = 0.0
    wear: float = 0.0

    def apply(self, state: State, rng: np.random.Generator) -> State:
        n = state.sueldo.shape[0]
        shock = rng.normal(self.growth, 0.06, n)
        perdio = state.extra["perdio_empleo"]
        # quien pierde el empleo baja su sueldo de referencia una vez; sin empleo no se mueve
        factor = np.where(perdio, CAIDA_SUELDO_AL_PERDER_EMPLEO, np.where(state.desempleado, 1.0, 1 + shock))
        state.sueldo = state.sueldo * factor
        state.desgaste = np.clip(state.desgaste + self.wear + rng.normal(0, 0.03, n), 0, 1)
        return state


class Seguir(ParametricDecision):
    key, label = "seguir", "Seguir igual"
    growth, riesgo_rel, wear = 0.03, 1.0, 0.02


class Sabatico(ParametricDecision):
    key, label = "sabatico", "Año sabático"
    growth, riesgo_rel, wear = -0.10, 2.0, -0.15


class CambiarPega(ParametricDecision):
    key, label = "cambiar_pega", "Cambiar de trabajo"
    growth, riesgo_rel, wear = 0.08, 1.6, 0.05
    cambio_forzado = True


class TrabajarMas(ParametricDecision):
    key, label = "trabajar_mas", "Trabajar más horas"
    growth, riesgo_rel, wear = 0.05, 0.8, 0.12


class Estudiar(ParametricDecision):
    key, label = "estudiar", "Estudiar"
    growth, riesgo_rel, wear = -0.05, 0.6, 0.04
