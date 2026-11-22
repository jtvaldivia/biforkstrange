from fastapi.testclient import TestClient

from app.api.deps import get_simulation_repo, get_twin_repo
from app.main import app
from app.repositories.simulations import InMemorySimulationRepository
from app.repositories.twin_profiles import InMemoryTwinProfileRepository
from app.sim.decisions import get_decision
from app.sim.engine import simulate
from app.sim.personality import Trait, personalize, weight
from app.sim.state import Twin
from app.twin.profile import Dim, TwinProfile


def test_every_year_explains_itself():
    r = simulate(Twin(), ["seguir", "cambiar_pega", "sabatico"], n_runs=500, seed=1)
    for s in r["trayectoria"]:
        e = s["explicacion"]
        assert e["titular"]
        assert e["factores"][0]["fuente"] == "decision"
    assert r["resumen"]["titular"].startswith("En 3 años")


def test_sabbatical_headline_says_why_salary_drops():
    r = simulate(Twin(), ["sabatico"], n_runs=2000, seed=1)
    tit = r["trayectoria"][0]["explicacion"]["titular"]
    assert "baja" in tit and "cuesta plata" in tit


def test_burnout_is_explained_when_it_drives_risk():
    r = simulate(Twin(desgaste=0.5), ["trabajar_mas"] * 4, n_runs=2000, seed=1)
    textos = [f["texto"] for s in r["trayectoria"][1:] for f in s["explicacion"]["factores"]]
    assert any("desgaste alto" in t for t in textos)


def test_unmeasured_traits_do_not_move_anything():
    base = get_decision("cambiar_pega").params
    params, factores = personalize("cambiar_pega", base, {"rcar": Trait(95, 30)})
    assert params == base and factores == []
    assert weight(30) == 0 and weight(12) == 1


def test_measured_traits_adjust_the_decision_with_a_reason():
    base = get_decision("cambiar_pega").params
    params, factores = personalize("cambiar_pega", base, {"rcar": Trait(90, 10), "ase": Trait(20, 10)})
    assert params.growth != base.growth and params.risk < base.risk
    assert any("Riesgo de carrera 90" in f["texto"] for f in factores)
    assert any("Negociar" in f["texto"] for f in factores)  # asertividad baja


def test_same_seed_means_only_the_decision_differs():
    a = simulate(Twin(), ["seguir", "seguir"], n_runs=500, seed=3)
    b = simulate(Twin(), ["seguir", "sabatico"], n_runs=500, seed=3)
    assert a["trayectoria"][0]["sueldo_p50"] == b["trayectoria"][0]["sueldo_p50"]  # año 1 idéntico
    assert a["trayectoria"][1]["sueldo_p50"] != b["trayectoria"][1]["sueldo_p50"]


def test_api_uses_twin_profile_and_compares():
    sims, twins = InMemorySimulationRepository(), InMemoryTwinProfileRepository()
    p = TwinProfile()
    p.dims["rcar"] = Dim(m=85, sd=10, n=3)
    twins.create(p)
    app.dependency_overrides[get_simulation_repo] = lambda: sims
    app.dependency_overrides[get_twin_repo] = lambda: twins
    try:
        c = TestClient(app)
        r = c.post("/api/simulations", json={"decisiones": ["cambiar_pega"], "seed": 1, "profile_id": p.id}).json()
        assert [x["key"] for x in r["rasgos_usados"]] == ["rcar"]
        assert any(f["fuente"] == "rasgo" for f in r["trayectoria"][0]["explicacion"]["factores"])
        assert "_rasgos" not in r["trayectoria"][0]["explicacion"]

        cmp = c.post("/api/simulations/compare",
                     json={"a": ["seguir", "seguir"], "b": ["seguir", "cambiar_pega"], "profile_id": p.id}).json()
        assert cmp["comparacion"]["titular"].startswith("B termina")
        assert any("A los" in x for x in cmp["comparacion"]["puntos"])

        d = {x["key"]: x for x in c.get("/api/decisions").json()}
        assert d["sabatico"]["growth"] < 0 and d["sabatico"]["why"]
    finally:
        app.dependency_overrides.clear()
