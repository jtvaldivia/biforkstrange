from dataclasses import dataclass

import numpy as np

from app.sim.luck import Suerte
from app.sim.params import P
from app.sim.profile import Perfil
from app.sim.state import ANIO_INICIAL
from app.sim.tables import Tablas, tablas


@dataclass
class Ctx:
    perfil: Perfil
    suerte: Suerte
    escenario_ia: str = "base"
    jugador: bool = False   # True en el año que decide el jugador: solo cambia de trabajo si lo elige

    @property
    def tb(self) -> Tablas:
        return tablas()

    def ia_g(self, anio: int) -> float:
        """Cuántas veces la brecha de empleo por IA de hoy (19%) se aplica en `anio`."""
        t0, techo = P.IA_ESCENARIOS[self.escenario_ia]
        a = lambda x: 1 / (1 + np.exp(-0.35 * (x - t0)))  # noqa: E731
        return float(1 + (techo - 1) * max(a(anio) - a(ANIO_INICIAL), 0) / (1 - a(ANIO_INICIAL)))
