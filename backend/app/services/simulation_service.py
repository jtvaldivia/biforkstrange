from app.repositories.simulations import SimulationRepository
from app.repositories.twin_profiles import TwinProfileRepository
from app.schemas.simulation import CompareIn, CompareOut, RasgoUsado, SimulationIn, SimulationOut
from app.sim.engine import simulate
from app.sim.explain import compare_runs
from app.sim.personality import Trait, weight
from app.sim.state import Twin
from app.twin.dims import DIMS


class SimulationService:
    def __init__(self, repo: SimulationRepository, default_runs: int, twins: TwinProfileRepository | None = None):
        self.repo = repo
        self.default_runs = default_runs
        self.twins = twins

    def _rasgos(self, profile_id: str | None) -> tuple[dict[str, Trait] | None, list[RasgoUsado]]:
        """Rasgos medidos del gemelo. Si no hay perfil (o no existe), la simulación es genérica."""
        if not profile_id or self.twins is None:
            return None, []
        p = self.twins.get(profile_id)
        if p is None:
            return None, []
        rasgos = {k: Trait(d.m, d.sd) for k, d in p.dims.items() if k in DIMS}
        usados = [
            RasgoUsado(key=k, nombre=DIMS[k].nombre, m=round(t.m, 1), sd=round(t.sd, 1), peso=round(weight(t.sd), 2))
            for k, t in rasgos.items()
            if weight(t.sd) > 0
        ]
        return rasgos, sorted(usados, key=lambda r: -r.peso)

    def run(self, body: SimulationIn, user_id: str | None = None) -> SimulationOut:
        rasgos, usados = self._rasgos(body.profile_id)
        result = simulate(
            Twin(**body.twin.model_dump()),
            body.decisiones,
            body.n_runs or self.default_runs,
            body.seed,
            rasgos,
        )
        sim_id = self.repo.save(body.model_dump(), result, user_id)
        return SimulationOut(id=sim_id, rasgos_usados=usados, **result)

    def compare(self, body: CompareIn) -> CompareOut:
        """A y B con la misma semilla: comparten la 'suerte' año a año, así que la diferencia es la decisión."""
        rasgos, usados = self._rasgos(body.profile_id)
        twin = Twin(**body.twin.model_dump())
        n = body.n_runs or self.default_runs
        a = simulate(twin, body.a, n, body.seed, rasgos)
        b = simulate(twin, body.b, n, body.seed, rasgos)
        return CompareOut(
            a=SimulationOut(rasgos_usados=usados, **a),
            b=SimulationOut(rasgos_usados=usados, **b),
            comparacion=compare_runs(body.a, body.b, a, b),
        )

    def get(self, sim_id: str) -> SimulationOut | None:
        row = self.repo.get(sim_id)
        return SimulationOut(id=row["id"], **row["result"]) if row else None
