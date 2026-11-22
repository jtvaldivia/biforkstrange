"""Persistencia detrás de una interfaz: hoy en memoria, por proceso."""

import uuid
from typing import Protocol


class SimulationRepository(Protocol):
    def save(self, input: dict, result: dict, user_id: str | None = None) -> str: ...
    def get(self, sim_id: str) -> dict | None: ...


class InMemorySimulationRepository:
    """Las corridas viven en la memoria del proceso: se pierden al reiniciar."""

    def __init__(self):
        self._rows: dict[str, dict] = {}

    def save(self, input: dict, result: dict, user_id: str | None = None) -> str:
        sim_id = str(uuid.uuid4())
        self._rows[sim_id] = {"id": sim_id, "input": input, "result": result, "user_id": user_id}
        return sim_id

    def get(self, sim_id: str) -> dict | None:
        return self._rows.get(sim_id)
