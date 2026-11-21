"""Qué harían 'gemelos como tú': elección con utilidad aleatoria (logit).
La constante de cada opción es la frecuencia con que la gente la toma; la personalidad y
los resultados esperados de la opción (del contrafactual) la mueven desde ahí."""

import numpy as np

from app.sim.params import P
from app.sim.profile import Perfil
from app.sim.state import Estado
from app.sim.tables import tablas, tramo3


def _base(clave: str, n_reconv: int, yo: Estado, perfil: Perfil) -> float:
    if clave == "tener_hijo":
        edad = yo.edad if perfil.sexo == "m" else yo.edad - 2
        return max(tablas().p_hijo(edad) * P.HIJO_PAREJA[0], 0.002)
    b = P.GEMELOS_BASE.get(clave, 0.05)
    if isinstance(b, dict):
        b = b[tramo3(yo.edad)]
    return b / n_reconv if clave == "reconvertir" else b


def repartir_gemelos(opciones: list, yo: Estado, perfil: Perfil) -> None:
    """Llena `gemelos` en cada opción del menú."""
    beta, rasgos = P.GEMELOS_BETA, P.GEMELOS_RASGOS
    z = {"riesgo": perfil.riesgo, "ambicion": perfil.ambicion, "O": perfil.z("O"), "E": perfil.z("E")}
    ref = next(o for o in opciones if o.decision == "seguir")
    n_reconv = max(1, sum(o.decision.startswith("reconvertir") for o in opciones))
    claves = [o.decision.split(":")[0] for o in opciones]
    bases = [0.0 if c == "seguir" else _base(c, n_reconv, yo, perfil) for c in claves]
    u = []
    for o, c, b in zip(opciones, claves, bases):
        const = np.log(max(1 - sum(bases), 0.05)) if c == "seguir" else np.log(b)
        rasgo = sum(z[r] * pesos.get(c, 0.0) for r, pesos in rasgos.items())
        d_ing = np.log(max(o.ingreso[1], 1) / max(ref.ingreso[1], 1))
        d_malo = (o.p_cesantia + o.p_deuda) - (ref.p_cesantia + ref.p_deuda)
        u.append(const + rasgo + beta["ingreso"] * (1 + 0.3 * perfil.ambicion) * d_ing
                 - beta["riesgo"] * (1 - 0.4 * perfil.riesgo) * d_malo + beta["animo"] * (o.animo - ref.animo))
    p = np.exp(np.array(u) - max(u))
    p /= p.sum()
    for o, v in zip(opciones, p):
        o.gemelos = float(v)
