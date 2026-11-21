from fastapi import APIRouter, HTTPException

from app.api.deps import SimulationServiceDep
from app.schemas.simulation import SimulationIn, SimulationOut
from app.sim.decisions import normalizar

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationOut)
def run_simulation(body: SimulationIn, service: SimulationServiceDep):
    try:
        for d in body.decisiones:
            normalizar(d)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
    return service.run(body)


@router.get("/{sim_id}", response_model=SimulationOut)
def get_simulation(sim_id: str, service: SimulationServiceDep):
    sim = service.get(sim_id)
    if sim is None:
        raise HTTPException(404, "Simulación no encontrada")
    return sim
