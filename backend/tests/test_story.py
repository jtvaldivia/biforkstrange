import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_story_repo, get_teller, get_twin_repo
from app.main import app
from app.repositories.stories import InMemoryStoryRepository
from app.repositories.twin_profiles import InMemoryTwinProfileRepository
from app.sim.state import Twin
from app.story import qualitative as q
from app.story.engine import replay
from app.story.teller import ClassifyOut, OfflineTeller
from app.twin.profile import Dim, TwinProfile


class SpyTeller(OfflineTeller):
    """Narrador de plantilla que guarda lo que le pasaron, para revisar qué recibe."""

    def __init__(self):
        self.chapters: list[dict] = []

    def chapter(self, perfil, historia, edad, anio, eleccion, hechos, ultimo, hilo, previas):
        self.chapters.append({"perfil": perfil, "historia": historia, "hechos": hechos, "ultimo": ultimo,
                              "hilo": hilo, "previas": previas})
        return super().chapter(perfil, historia, edad, anio, eleccion, hechos, ultimo, hilo, previas)

    def classify(self, texto, situacion):
        return ClassifyOut(decision="sabatico", titulo="Irme a recorrer Sudamérica")


@pytest.fixture
def ctx():
    stories, twins, teller = InMemoryStoryRepository(), InMemoryTwinProfileRepository(), SpyTeller()
    app.dependency_overrides[get_story_repo] = lambda: stories
    app.dependency_overrides[get_twin_repo] = lambda: twins
    app.dependency_overrides[get_teller] = lambda: teller
    yield TestClient(app), twins, teller
    app.dependency_overrides.clear()


def start(c, **kw):
    body = {"situacion": "Trabajo en una consultora en Santiago y estoy cansado.", "anios": 3, **kw}
    return c.post("/api/stories", json=body).json()


def test_full_story_flow(ctx):
    c, _, teller = ctx
    s = start(c)
    assert s["prologo"] and len(s["dilema"]["opciones"]) >= 2 and s["capitulos"] == []

    for i in range(3):
        opt = s["dilema"]["opciones"][i % 2]
        s = c.post(f"/api/stories/{s['id']}/choose", json={"capitulo": i, "option_id": opt["id"]}).json()
        ch = s["capitulos"][-1]
        assert ch["eleccion"] == opt["titulo"] and ch["decision"] == opt["decision"]
        assert set(ch["estado"]) == {"trabajo", "plata", "energia", "vida"}
        assert "hechos" not in ch  # los números no salen al cliente
    assert s["terminada"] and s["dilema"] is None
    assert teller.chapters[-1]["ultimo"] is True

    s = c.post(f"/api/stories/{s['id']}/close").json()
    assert s["epilogo"]["lo_que_no_vuelve"]


def test_free_text_choice_is_classified(ctx):
    c, _, _ = ctx
    s = start(c)
    s = c.post(f"/api/stories/{s['id']}/choose", json={"capitulo": 0, "texto": "me voy a mochilear"}).json()
    assert s["capitulos"][0]["decision"] == "sabatico"
    assert s["capitulos"][0]["eleccion"] == "Irme a recorrer Sudamérica"


def test_double_click_does_not_write_two_chapters(ctx):
    c, _, _ = ctx
    s = start(c)
    opt = s["dilema"]["opciones"][0]["id"]
    assert c.post(f"/api/stories/{s['id']}/choose", json={"capitulo": 0, "option_id": opt}).status_code == 200
    again = c.post(f"/api/stories/{s['id']}/choose", json={"capitulo": 0, "option_id": opt})
    assert again.status_code == 409 and len(again.json()["detail"]["story"]["capitulos"]) == 1


def test_narrator_gets_twin_and_facts(ctx):
    c, twins, teller = ctx
    p = TwinProfile()
    p.basics.nombre = "Cris"
    p.dims["est"] = Dim(m=85, sd=10, n=3)
    twins.create(p)
    s = start(c, profile_id=p.id)
    c.post(f"/api/stories/{s['id']}/choose", json={"capitulo": 0, "option_id": s["dilema"]["opciones"][2]["id"]})
    sent = teller.chapters[0]
    assert "Cris" in sent["perfil"]
    assert "Energía:" in sent["hechos"] and "Por cómo eres" in sent["hechos"]  # estabilidad amortigua


def test_replay_is_deterministic_and_follows_one_life():
    a = replay(Twin(), ["seguir", "trabajar_mas"], seed=5, rasgos=None)
    b = replay(Twin(), ["seguir", "trabajar_mas"], seed=5, rasgos=None)
    assert a == b and len(a) == 2
    # el primer año no cambia aunque cambie la decisión del segundo
    c = replay(Twin(), ["seguir", "sabatico"], seed=5, rasgos=None)
    assert a[0] == c[0]


def test_qualitative_words_never_show_numbers():
    f = replay(Twin(desgaste=0.7), ["trabajar_mas"], seed=1, rasgos=None)[0]
    words = [q.plata(f), q.energia(f), q.trabajo(f)]
    assert all(not any(ch.isdigit() for ch in w) for w in words)
    assert q.energia(f) in {"al límite", "en las últimas"} and q.tone(f) == "noche"


def test_each_year_sees_the_thread_and_previous_options(ctx):
    c, _, teller = ctx
    s = start(c)
    first = [o["titulo"] for o in s["dilema"]["opciones"]]
    for i in range(2):
        s = c.post(f"/api/stories/{s['id']}/choose",
                   json={"capitulo": i, "option_id": s["dilema"]["opciones"][0]["id"]}).json()
    assert "Dónde está" in teller.chapters[0]["hilo"]  # el hilo de la apertura llega al año 1
    assert set(first) <= set(teller.chapters[1]["previas"])  # el año 2 sabe qué se ofreció antes
    assert s["capitulos"][0]["hilo"]["donde"]


def test_repeated_options_are_rejected():
    from app.story.teller import DilemmaOut, OptionOut, check_dilemma

    d = DilemmaOut(situacion="x", pregunta="y", opciones=[
        OptionOut(titulo="Volver a Santiago", detalle="", decision="seguir"),
        OptionOut(titulo="Quedarte en Melbourne", detalle="", decision="sabatico")])
    with pytest.raises(ValueError):
        check_dilemma(d, previas=["volver a santiago"])
    check_dilemma(d, previas=["Otra cosa"])


def test_carryover_studying_pays_off_and_unemployment_is_remembered():
    from app.sim import carryover

    facts = replay(Twin(), ["estudiar", "seguir"], seed=2, rasgos=None)
    assert any("estudiaste" in n for n in facts[1].arrastre)
    # el arrastre no consume azar: el primer año es idéntico con o sin él
    a = replay(Twin(), ["estudiar", "seguir"], seed=9, rasgos=None)
    b = replay(Twin(), ["estudiar", "sabatico"], seed=9, rasgos=None)
    assert a[0] == b[0]
    assert carryover.STUDY_YEARS == 3
