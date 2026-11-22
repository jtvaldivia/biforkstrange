from app.sim.ocupacional.engine import simulate
from app.sim.ocupacional.state import Twin


def test_simulate_shapes():
    r = simulate(Twin(), ["seguir", "sabatico", "cambiar_pega"], n_runs=500, seed=1)
    assert len(r["trayectoria"]) == 3
    t = r["trayectoria"][-1]
    assert t["sueldo_p10"] <= t["sueldo_p50"] <= t["sueldo_p90"]


def test_seed_is_reproducible():
    a = simulate(Twin(), ["seguir"], n_runs=200, seed=7)
    b = simulate(Twin(), ["seguir"], n_runs=200, seed=7)
    assert a == b
