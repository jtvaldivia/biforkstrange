from fastapi import APIRouter, HTTPException, status

from app.api.deps import SimulationServiceDep
from app.schemas.simulation import SimulationIn, SimulationOut
from app.sim.ocupacional.decisions import decisiones_desconocidas

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationOut)
def run_simulation(body: SimulationIn, service: SimulationServiceDep):
    desconocidas = decisiones_desconocidas(body.decisiones)
    if desconocidas:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Decisiones desconocidas: {desconocidas}")
    return service.run(body)


@router.get("/{sim_id}", response_model=SimulationOut)
def get_simulation(sim_id: str, service: SimulationServiceDep):
    sim = service.get(sim_id)
    if sim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Simulación no encontrada")
    return sim
