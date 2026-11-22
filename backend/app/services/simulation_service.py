from app.repositories.simulations import SimulationRepository
from app.schemas.simulation import SimulationIn, SimulationOut
from app.sim.ocupacional.engine import simulate
from app.sim.ocupacional.state import Twin


class SimulationService:
    def __init__(self, repo: SimulationRepository, default_runs: int):
        self.repo = repo
        self.default_runs = default_runs

    def run(self, body: SimulationIn, user_id: str | None = None) -> SimulationOut:
        result = simulate(
            Twin(**body.twin.model_dump()),
            body.decisiones,
            body.n_runs or self.default_runs,
            body.seed,
        )
        sim_id = self.repo.save(body.model_dump(), result, user_id)
        return SimulationOut(id=sim_id, **result)

    def get(self, sim_id: str) -> SimulationOut | None:
        row = self.repo.get(sim_id)
        return SimulationOut(id=row["id"], **row["result"]) if row else None
