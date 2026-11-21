from dataclasses import dataclass

from app.sim.luck import Suerte
from app.sim.profile import Perfil
from app.sim.tables import Tablas, tablas


@dataclass
class Ctx:
    perfil: Perfil
    suerte: Suerte
    jugador: bool = False   # True en el año que decide el jugador: solo cambia de trabajo si lo elige

    @property
    def tb(self) -> Tablas:
        return tablas()
