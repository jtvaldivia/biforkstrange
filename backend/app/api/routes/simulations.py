from fastapi import APIRouter, HTTPException

from app.api.deps import SimulationServiceDep
from app.schemas.simulation import CompareIn, CompareOut, SimulationIn, SimulationOut
from app.sim.decisions.base import _REGISTRY

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationOut)
def run_simulation(body: SimulationIn, service: SimulationServiceDep):
    unknown = [d for d in body.decisiones if d not in _REGISTRY]
    if unknown:
        raise HTTPException(422, f"Decisiones desconocidas: {unknown}")
    return service.run(body)


@router.post("/compare", response_model=CompareOut)
def compare(body: CompareIn, service: SimulationServiceDep):
    unknown = [d for d in body.a + body.b if d not in _REGISTRY]
    if unknown:
        raise HTTPException(422, f"Decisiones desconocidas: {unknown}")
    return service.compare(body)


@router.get("/{sim_id}", response_model=SimulationOut)
def get_simulation(sim_id: str, service: SimulationServiceDep):
    sim = service.get(sim_id)
    if sim is None:
        raise HTTPException(404, "Simulación no encontrada")
    return sim
