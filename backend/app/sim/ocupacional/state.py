"""Estado vectorizado: cada atributo es un array de n_runs (una fila por universo)."""

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Twin:
    """Punto de partida del gemelo."""

    edad: int = 25
    sueldo: float = 900_000.0  # CLP mensual
    desgaste: float = 0.2      # 0..1
    ocupacion: int = 2         # grupo ISCO a 1 dígito (0..9); 2 = profesionales
    antiguedad: float = 0.0    # años en el empleo actual


@dataclass
class State:
    edad: int
    sueldo: np.ndarray
    desgaste: np.ndarray
    desempleado: np.ndarray
    ocupacion: np.ndarray    # grupo ISCO del empleo actual (o del último, si está sin empleo)
    antiguedad: np.ndarray   # años en el empleo actual
    n_empleos: np.ndarray    # empleos nuevos desde que parte la simulación
    extra: dict[str, np.ndarray] = field(default_factory=dict)  # atributos nuevos sin tocar el core

    @classmethod
    def from_twin(cls, twin: Twin, n_runs: int) -> "State":
        return cls(
            edad=twin.edad,
            sueldo=np.full(n_runs, twin.sueldo),
            desgaste=np.full(n_runs, twin.desgaste),
            desempleado=np.zeros(n_runs, dtype=bool),
            ocupacion=np.full(n_runs, twin.ocupacion, dtype=np.int64),
            antiguedad=np.full(n_runs, twin.antiguedad),
            n_empleos=np.zeros(n_runs, dtype=np.int64),
        )
