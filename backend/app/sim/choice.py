"""Qué hace la gente como tú: la frecuencia anual con que se toma cada decisión, según los datos.
No es un modelo de elección: es el dato observado para tu edad, para comparar."""

from app.sim.params import P
from app.sim.profile import Perfil
from app.sim.state import Estado
from app.sim.tables import tramo3


_TEXTO = {
    "aceptar_oferta": "Se acepta el {p} de las ofertas (EE.UU.)",
    "buscar_pega": "Busca otra pega el {p} de los asalariados (EE.UU.)",
}


def texto_frecuencia(decision: str, f: float | None) -> str:
    if f is None:
        return ""
    p = f"{100 * f:.1f}%".replace(".0%", "%").replace(".", ",") if f < 0.1 else f"{100 * f:.0f}%"
    return _TEXTO.get(decision.split(":")[0], "Lo hace el {p} de la gente de tu edad cada año").format(p=p)


def frecuencia(decision: str, yo: Estado, perfil: Perfil) -> float | None:
    clave, _, arg = decision.partition(":")
    if clave == "emprender":
        f = P.EMP_ENTRADA[arg or "cuenta_propia"][tramo3(yo.edad)]
        f *= (1 + P.B_EMP_ENTRADA["O"]) ** perfil.z("O") * (1 + P.B_EMP_ENTRADA["E"]) ** perfil.z("E")   # Caliendo et al. 2014
        return float(f)
    if clave == "volver_empleo":
        return None   # la carta ya dice cuánto cierra
    f = P.FRECUENCIA.get(clave)
    if f is None:
        return None
    f = f[tramo3(yo.edad)] if isinstance(f, dict) else f
    return float(f)
