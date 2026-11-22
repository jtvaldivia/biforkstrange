"""Lo que un año le deja al siguiente. Sin esto cada año sería independiente.

- Venir de un año sin pega: volver al mercado cuesta (más riesgo), pero al volver recuperas casi el sueldo de antes.
- Estudiar: los 3 años siguientes lo estudiado suma al crecimiento.
- Cambiarte de pega dos años seguidos: en las entrevistas preguntan por qué (más riesgo).

No consume azar: con la misma semilla, dos historias siguen compartiendo la "suerte".
"""

import numpy as np

from app.sim.state import State

RETURN_RISK = 0.12  # riesgo extra de seguir sin pega si vienes de un año sin pega
RECOVERY = 0.92  # al volver a trabajar, recuperas al menos esta fracción del sueldo de antes
STUDY_YEARS = 3
STUDY_BONUS = 0.02
JOB_HOP_RISK = 0.03


def _arr(state: State, key: str, fill: float = 0.0) -> np.ndarray:
    n = state.sueldo.shape[0]
    if key not in state.extra:
        state.extra[key] = np.full(n, fill)
    return state.extra[key]


def before_year(state: State, decision: str, me: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Riesgo y crecimiento extra por vida, más lo que le toca a `me`, en palabras."""
    was_out = state.desempleado.astype(float)
    estudio = _arr(state, "estudio")
    cambio = _arr(state, "cambio")

    risk = RETURN_RISK * was_out
    growth = STUDY_BONUS * (estudio > 0)
    if decision == "cambiar_pega":
        risk = risk + JOB_HOP_RISK * cambio

    notes = []
    if was_out[me]:
        notes.append("Vienes de un año sin pega: volver al mercado cuesta más.")
    if estudio[me] > 0:
        notes.append("Lo que estudiaste empieza a pesar en tu sueldo.")
    if decision == "cambiar_pega" and cambio[me]:
        notes.append("Es tu segundo cambio de pega seguido: en las entrevistas preguntan por qué.")
    return risk, growth, notes


def after_year(state: State, decision: str, prev_sueldo: np.ndarray, was_out: np.ndarray, me: int) -> list[str]:
    """Actualiza lo que se arrastra al año siguiente. Devuelve lo que le pasó a `me`, en palabras."""
    previo = _arr(state, "sueldo_previo")
    estudio = _arr(state, "estudio")
    now_out = state.desempleado

    notes = []
    # volver a trabajar: recuperas casi el sueldo que tenías antes de quedar sin pega
    back = was_out & ~now_out & (previo > 0)
    recovered = np.where(back, np.maximum(state.sueldo, previo * RECOVERY), state.sueldo)
    if back[me] and recovered[me] > state.sueldo[me]:
        notes.append("Al volver a trabajar recuperaste casi el sueldo de antes.")
    state.sueldo = recovered

    # recordar el sueldo de antes si recién quedaste sin pega
    state.extra["sueldo_previo"] = np.where(now_out & ~was_out, prev_sueldo, np.where(now_out, previo, 0.0))
    state.extra["estudio"] = np.full_like(estudio, STUDY_YEARS) if decision == "estudiar" else np.maximum(estudio - 1, 0)
    state.extra["cambio"] = np.full_like(estudio, 1.0 if decision == "cambiar_pega" else 0.0)
    return notes
