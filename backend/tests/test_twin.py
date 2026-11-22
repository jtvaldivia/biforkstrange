import math
import random

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_twin_brain, get_twin_repo
from app.core.llm import extract_json, strict_schema
from app.main import app
from app.repositories.twin_profiles import InMemoryTwinProfileRepository
from app.services.twin_brain import AdaptiveOut, OfflineBrain
from app.twin import cat
from app.twin.dims import DIM_KEYS
from app.twin.metrics import exam_metrics, next_tema
from app.twin.profile import Dim, ExamItem


class FakePriorBrain(OfflineBrain):
    """Como el stub, pero el prior 'encuentra evidencia' de asertividad."""

    def prior(self, context, keys):
        return {k: Dim(m=80, sd=10, ev="lidera reuniones") if k == "ase" else Dim(m=50, sd=28, ev="sin evidencia")
                for k in keys}


@pytest.fixture
def repo():
    return InMemoryTwinProfileRepository()


@pytest.fixture
def tc(repo):
    app.dependency_overrides[get_twin_repo] = lambda: repo
    app.dependency_overrides[get_twin_brain] = lambda: FakePriorBrain(seed=1)
    yield TestClient(app)
    app.dependency_overrides.clear()


def new_profile(tc, **basics):
    return tc.post("/api/twin/profiles", json={"basics": basics}).json()


# ---- criterios de aceptación del spec (§11) ----

def test_empty_profile_starts_at_50_30(tc):
    p = new_profile(tc)
    assert set(p["dims"]) == set(DIM_KEYS) and len(DIM_KEYS) == 26
    assert all(d["m"] == 50 and d["sd"] == 30 for d in p["dims"].values())
    # sin contexto, el prior no llama al LLM y deja todo igual
    p = tc.post(f"/api/twin/profiles/{p['id']}/prior", json={"version": p["version"]}).json()
    assert all(d["sd"] == 30 for d in p["dims"].values())
    assert p["prior_at"] is not None


def test_prior_never_overwrites_answered_dims(tc):
    p = new_profile(tc, nombre="Cris", rasgos="lidera reuniones")
    pid = p["id"]
    # responder una adaptativa primero
    r = tc.post(f"/api/twin/profiles/{pid}/adaptive/next", json={"version": p["version"]}).json()
    q, p = r["question"], r["profile"]
    p = tc.post(f"/api/twin/profiles/{pid}/adaptive/answer",
                json={"version": p["version"], "qid": q["id"], "ans": 0}).json()["profile"]
    answered = {k: d for k, d in p["dims"].items() if d["n"] > 0}
    p = tc.post(f"/api/twin/profiles/{pid}/prior", json={"version": p["version"]}).json()
    for k, d in answered.items():
        assert p["dims"][k] == d
    unanswered = [k for k in DIM_KEYS if k not in answered and k != "ase"]
    assert all(p["dims"][k]["sd"] >= 25 for k in unanswered)


def test_each_answer_lowers_sd_and_closed_dims_are_not_asked(tc):
    p = new_profile(tc)
    pid = p["id"]
    asked: list[list[str]] = []
    for _ in range(40):
        r = tc.post(f"/api/twin/profiles/{pid}/adaptive/next", json={"version": p["version"]}).json()
        q, p = r["question"], r["profile"]
        if q is None:
            break
        for k in q["dims"]:
            assert not cat.is_closed(Dim(**p["dims"][k])), "preguntó una dimensión ya cerrada"
        before = {k: p["dims"][k]["sd"] for k in q["dims"]}
        r = tc.post(f"/api/twin/profiles/{pid}/adaptive/answer",
                    json={"version": p["version"], "qid": q["id"], "ans": 1}).json()
        p = r["profile"]
        assert all(p["dims"][k]["sd"] < before[k] for k in q["dims"])
        assert {d["key"] for d in r["deltas"]} == set(q["dims"])
        asked.append(q["dims"])
    assert len(asked) >= 10


def test_none_of_these_does_not_update(tc):
    p = new_profile(tc)
    r = tc.post(f"/api/twin/profiles/{p['id']}/adaptive/next", json={"version": p["version"]}).json()
    q, p = r["question"], r["profile"]
    r = tc.post(f"/api/twin/profiles/{p['id']}/adaptive/answer",
                json={"version": p["version"], "qid": q["id"], "ans": -1, "note": "depende del equipo"}).json()
    assert r["deltas"] == []
    assert all(r["profile"]["dims"][k]["sd"] == 30 for k in q["dims"])
    assert any(n["a"] == "depende del equipo" for n in r["profile"]["notes"])


def test_exam_prediction_is_persisted_before_user_sees_options(tc, repo):
    p = new_profile(tc)
    r = tc.post(f"/api/twin/profiles/{p['id']}/exam/next", json={"version": p["version"], "tema": "plata"}).json()
    q = r["question"]
    assert "probs" not in q
    # el cliente no ve la predicción, pero ya está guardada
    assert r["profile"]["exam"][0]["probs"] == []
    stored = repo.get(p["id"]).exam[0]
    assert stored.id == q["id"] and math.isclose(sum(stored.probs), 100, abs_tol=0.5)

    reveal = tc.post(f"/api/twin/profiles/{p['id']}/exam/answer",
                     json={"version": r["profile"]["version"], "eid": q["id"], "ans": 2, "why": "me gusta viajar"}).json()
    e = reveal["reveal"]
    assert e["probs"] == stored.probs and e["hit"] == (e["top"] == 2)
    assert e["p_ans"] == stored.probs[2]
    assert reveal["profile"]["corrections"][-1]["fix"].endswith("me gusta viajar")


def test_exam_other_answer_scores_zero(tc):
    p = new_profile(tc)
    r = tc.post(f"/api/twin/profiles/{p['id']}/exam/next", json={"version": p["version"]}).json()
    e = tc.post(f"/api/twin/profiles/{p['id']}/exam/answer",
                json={"version": r["profile"]["version"], "eid": r["question"]["id"], "ans": -1,
                      "ans_text": "ninguna, haría otra cosa"}).json()["reveal"]
    assert e["hit"] is False and e["p_ans"] == 0


def test_summary_panel(tc):
    p = new_profile(tc)
    for _ in range(3):
        r = tc.post(f"/api/twin/profiles/{p['id']}/exam/next", json={"version": p["version"]}).json()
        p = tc.post(f"/api/twin/profiles/{p['id']}/exam/answer",
                    json={"version": r["profile"]["version"], "eid": r["question"]["id"], "ans": 0}).json()["profile"]
    s = tc.get(f"/api/twin/profiles/{p['id']}/summary").json()
    ex = s["examen"]
    assert ex["n"] == 3 and ex["azar"] == 25.0
    assert {"acierto", "p_media", "log_score", "brier", "calibracion", "por_tema", "tendencia"} <= set(ex)
    assert s["claridad"]["total"] == 26 and len(s["ajuste"]) == 7


def test_recalibration_replaces_previous_calibration_notes(tc):
    p = new_profile(tc)
    pid = p["id"]
    assert tc.post(f"/api/twin/profiles/{pid}/calibration/propose").status_code == 422  # < 4 respuestas
    for _ in range(4):
        r = tc.post(f"/api/twin/profiles/{pid}/exam/next", json={"version": p["version"]}).json()
        p = tc.post(f"/api/twin/profiles/{pid}/exam/answer",
                    json={"version": r["profile"]["version"], "eid": r["question"]["id"], "ans": 3}).json()["profile"]
    assert tc.post(f"/api/twin/profiles/{pid}/calibration/propose").status_code == 200

    p = tc.post(f"/api/twin/profiles/{pid}/notes", json={"version": p["version"], "q": "Familia", "a": "dos hermanos"}).json()
    first = [{"tema": "Plata", "patron": "Invierto en vez de ahorrar", "evidencia": "bono"},
             {"tema": "Gustos", "patron": "Me gustan los museos", "evidencia": "sábado"}]
    p = tc.put(f"/api/twin/profiles/{pid}/calibration", json={"version": p["version"], "patrones": first}).json()
    second = [{"tema": "sesgo del gemelo", "patron": "Me pinta más cauteloso", "evidencia": "4 fallos"}]
    p = tc.put(f"/api/twin/profiles/{pid}/calibration", json={"version": p["version"], "patrones": second}).json()
    calib = [n for n in p["notes"] if n["q"].startswith("Calibración:")]
    assert len(calib) == 1 and "cauteloso" in calib[0]["a"]
    assert any(n["q"] == "Familia" for n in p["notes"])  # las otras notas no se tocan


def test_stale_tab_cannot_overwrite_newer_data(tc):
    p = new_profile(tc)
    pid, v0 = p["id"], p["version"]
    ok = tc.put(f"/api/twin/profiles/{pid}/basics", json={"version": v0, "basics": {"nombre": "Pestaña nueva"}})
    assert ok.status_code == 200
    stale = tc.put(f"/api/twin/profiles/{pid}/basics", json={"version": v0, "basics": {"nombre": "Pestaña vieja"}})
    assert stale.status_code == 409
    assert stale.json()["detail"]["profile"]["basics"]["nombre"] == "Pestaña nueva"
    assert tc.get(f"/api/twin/profiles/{pid}").json()["basics"]["nombre"] == "Pestaña nueva"


def test_unknown_profile_404(tc):
    assert tc.get("/api/twin/profiles/nope").status_code == 404


# ---- dominio ----

def test_bayesian_update_matches_spec():
    d = cat.update(Dim(m=50, sd=30), obs=80, at=0)
    p0, p1 = 1 / 30**2, 1 / 18**2
    assert math.isclose(d.m, (50 * p0 + 80 * p1) / (p0 + p1))
    assert math.isclose(d.sd, math.sqrt(1 / (p0 + p1)))
    assert d.n == 1
    tight = cat.update(Dim(m=50, sd=6.1), obs=50, at=0)
    assert tight.sd == 6.0  # piso


def test_profile_clear_when_all_closed():
    dims = {k: Dim(m=50, sd=10, n=2) for k in DIM_KEYS}
    assert cat.select_targets(dims, random.Random(0)) is None
    dims["ord"] = Dim(m=50, sd=10, n=1)  # sd bajo pero menos de 2 respuestas: sigue abierta
    assert cat.select_targets(dims, random.Random(0)) == ["ord"]


def test_interest_questions_contrast_three_dims():
    dims = {k: Dim(m=50, sd=8, n=3) for k in DIM_KEYS}
    for k in ("I", "A", "S"):
        dims[k] = Dim(m=50, sd=30)
    assert set(cat.select_targets(dims, random.Random(0))) == {"I", "A", "S"}


def test_drift_raises_sd_per_month():
    dims = {"ase": Dim(m=60, sd=10, n=3, updated_at=0)}
    assert cat.apply_drift(dims, at=3 * cat.SECONDS_PER_MONTH + 5)
    assert dims["ase"].sd == 13
    assert not cat.apply_drift(dims, at=3 * cat.SECONDS_PER_MONTH + 10)  # no se acumula dos veces


def test_job_fit_neutral_profile():
    fit = cat.job_fit({k: Dim() for k in DIM_KEYS})
    assert all(f["score"] == 50 for f in fit)
    assert all(0 < f["margen"] <= 40 for f in fit)


def test_exam_metrics_and_auto_tema():
    items = [ExamItem(q="a", opts=["x", "y"], tema="plata", probs=[80, 20], top=0, pq="", ans=0, hit=True, p_ans=80),
             ExamItem(q="b", opts=["x", "y"], tema="plata", probs=[60, 40], top=0, pq="", ans=1, hit=False, p_ans=40)]
    m = exam_metrics(items)
    assert m["acierto"] == 50 and m["azar"] == 50 and m["p_media"] == 60
    assert m["calibracion"][0]["rango"] == "60–80%"
    assert next_tema(items) != "plata"  # primero los temas con menos de 2 preguntas


def test_strict_schema_and_json_extraction():
    s = strict_schema(AdaptiveOut)
    nested = s["$defs"]["OpcionAdaptativa"]
    assert s["additionalProperties"] is False and nested["additionalProperties"] is False
    assert nested["required"] == ["texto", "niveles"]
    assert extract_json('ok {"a": {"b": 1}} fin') == '{"a": {"b": 1}}'


def test_import_llm_context_feeds_prior_and_context(tc, repo):
    p = new_profile(tc)
    texto = "- Trabajo: ingeniero de datos en una fintech, 3 años.\n- Decido: prefiero estabilidad."
    p = tc.put(f"/api/twin/profiles/{p['id']}/contexto", json={"version": p["version"], "texto": texto}).json()
    assert p["contexto_llm"] == texto and p["contexto_llm_at"] is not None
    assert p["prior_at"] is not None  # importar estima los rasgos de una
    assert any(d["sd"] < 30 for d in p["dims"].values())
    from app.twin.context import build_context
    assert "fintech" in build_context(repo.get(p["id"]))
    # sin estimar: solo guarda
    p2 = new_profile(tc)
    p2 = tc.put(f"/api/twin/profiles/{p2['id']}/contexto",
                json={"version": p2["version"], "texto": "hola", "estimar": False}).json()
    assert p2["contexto_llm"] == "hola" and p2["prior_at"] is None
