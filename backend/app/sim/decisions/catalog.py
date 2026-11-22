"""Catálogo de decisiones. Valores de relleno: calibrar con datos reales."""

import numpy as np

from app.sim.decisions.base import Decision
from app.sim.personality import Params
from app.sim.state import State

BURNOUT_LINE = 0.6  # sobre este desgaste sube el riesgo de quedar sin pega
BURNOUT_SLOPE = 0.3  # cada punto de desgaste sobre la línea suma 0,3 puntos de riesgo
UNEMPLOYED_CUT = 0.6  # quien queda sin pega ese año cobra el 60%
SHOCK_SD = 0.06  # dispersión del crecimiento entre vidas
WEAR_SD = 0.03


class ParametricDecision(Decision):
    """Decisión definida por (crecimiento, riesgo de desempleo, desgaste)."""

    growth: float = 0.0
    unemployment_risk: float = 0.05
    wear: float = 0.0
    why: str = ""  # por qué la decisión tiene esas palancas, en una frase

    @property
    def params(self) -> Params:
        return Params(self.growth, self.unemployment_risk, self.wear)

    def apply(self, state: State, rng: np.random.Generator) -> State:
        return self.apply_with(state, rng, self.params)

    def apply_with(
        self, state: State, rng: np.random.Generator, p: Params,
        risk_extra: np.ndarray | float = 0.0, growth_extra: np.ndarray | float = 0.0,
    ) -> State:
        """Aplica un año con parámetros dados (ya personalizados). Siempre consume el mismo azar,
        así dos escenarios con la misma semilla comparten la 'suerte' y solo difieren por las decisiones.
        `risk_extra` y `growth_extra` (por vida) traen lo que arrastras del año anterior (sim/carryover.py)."""
        n = state.sueldo.shape[0]
        burnout = BURNOUT_SLOPE * np.maximum(state.desgaste - BURNOUT_LINE, 0)
        prob = np.clip(p.risk + burnout + risk_extra, 0, 1)
        state.desempleado = rng.random(n) < prob
        shock = rng.normal(p.growth, SHOCK_SD, n) + growth_extra
        state.sueldo = np.where(state.desempleado, state.sueldo * UNEMPLOYED_CUT, state.sueldo * (1 + shock))
        state.desgaste = np.clip(state.desgaste + p.wear + rng.normal(0, WEAR_SD, n), 0, 1)
        return state


class Seguir(ParametricDecision):
    key, label = "seguir", "Seguir igual"
    growth, unemployment_risk, wear = 0.03, 0.05, 0.02
    why = "Lo conocido: reajuste moderado, riesgo bajo y un desgaste que se acumula de a poco."


class Sabatico(ParametricDecision):
    key, label = "sabatico", "Año sabático"
    growth, unemployment_risk, wear = -0.10, 0.10, -0.15
    why = "Recargas energía, pero dejas de ganar y volver al mercado tiene su riesgo."


class CambiarPega(ParametricDecision):
    key, label = "cambiar_pega", "Cambiar de pega"
    growth, unemployment_risk, wear = 0.08, 0.08, 0.05
    why = "Cambiarse es la forma más rápida de subir sueldo, pero el período de prueba y la adaptación pesan."


class TrabajarMas(ParametricDecision):
    key, label = "trabajar_mas", "Trabajar más horas"
    growth, unemployment_risk, wear = 0.05, 0.04, 0.12
    why = "Más horas se notan en el sueldo y te hacen menos prescindible, pero el desgaste sube fuerte."


class TrabajarMenos(ParametricDecision):
    key, label = "trabajar_menos", "Trabajar menos horas"
    growth, unemployment_risk, wear = -0.02, 0.06, -0.07
    why = "Menos horas o una jornada más corta: ganas algo menos y pierdes vitrina, pero recuperas tiempo y energía."


class Estudiar(ParametricDecision):
    key, label = "estudiar", "Estudiar"
    growth, unemployment_risk, wear = -0.05, 0.03, 0.04
    why = "Inviertes en ti: ganas menos este año, pero quedas más protegido ante despidos."
