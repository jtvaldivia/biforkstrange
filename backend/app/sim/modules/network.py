"""Red de contactos: crece con el trabajo y los cambios, se enfría con el tiempo sin trabajar."""

import numpy as np

from app.sim.params import P
from app.sim.state import CES, EMP, EMPR


def factor_red(contactos: np.ndarray) -> np.ndarray:
    """Multiplicador de ofertas y de búsqueda de empleo según contactos."""
    return np.clip(1 + P.RED_ELAST * np.log(np.maximum(contactos, 1.0) / P.RED_REF), 0.6, 1.6)


def red(e, i, ctx, ev):
    g = P.RED_GANA
    e.contactos = e.contactos + g["anual"] * (e.sit == EMP) + g["emprende"] * (e.sit == EMPR) + g["titulo"] * ev["titulo"]
    e.contactos = e.contactos + P.ACCIONES["red_contactos"] * i.networking + P.ACCIONES["pituto_contactos"] * i.pituto
    e.contactos = np.where((e.sit == CES) & (e.anios_ces >= 1), e.contactos * (1 - P.RED_PIERDE), e.contactos)
