from abc import ABC, abstractmethod
from typing import ClassVar

import numpy as np

from app.sim.ocupacional.state import State

_REGISTRY: dict[str, "Decision"] = {}


class Decision(ABC):
    """Una decisión transforma el estado de un año. El motor corre antes el paso
    laboral (empleo, cesantía, cambio de ocupación), así que `apply` ya ve quién
    tiene empleo y quién lo perdió (`state.extra["perdio_empleo"]`). Para agregar una nueva,
    crea una subclase con `key` y `label` en catalog.py (o en otro módulo
    importado allí): se registra sola y aparece en la API."""

    key: ClassVar[str]
    label: ClassVar[str]
    description: ClassVar[str] = ""
    # Cómo mueve la decisión el paso laboral del año (ver sim/ocupacional/labor.py)
    riesgo_rel: ClassVar[float] = 1.0  # multiplica la prob. de caer en cesantía
    cambio_forzado: ClassVar[bool] = False  # te cambias de empleador este año

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if getattr(cls, "key", None):
            _REGISTRY[cls.key] = cls()

    @abstractmethod
    def apply(self, state: State, rng: np.random.Generator) -> State: ...


def get_decision(key: str) -> Decision:
    try:
        return _REGISTRY[key]
    except KeyError as e:
        raise ValueError(f"Decisión desconocida: {key}") from e


def all_decisions() -> list[Decision]:
    return list(_REGISTRY.values())


def decisiones_desconocidas(keys: list[str]) -> list[str]:
    """Las claves que no corresponden a ninguna decisión registrada, en el orden en que llegaron."""
    return [k for k in keys if k not in _REGISTRY]
