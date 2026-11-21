import json
from pathlib import Path

PERFIL = json.loads((Path(__file__).parent.parent / "perfiles" / "ejemplo.json").read_text())


def test_list_decisions(client):
    keys = {d["key"] for d in client.get("/api/decisions").json()}
    assert {"seguir", "sabatico", "emprender", "magister"} <= keys


def test_run_and_fetch(client):
    res = client.post("/api/simulations", json={"decisiones": ["seguir", "capacitarte"], "seed": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["edad_final"] == 27 and "ahorros_p50" in body["trayectoria"][0]
    assert client.get(f"/api/simulations/{body['id']}").status_code == 200


def test_simulacion_con_perfil(client):
    res = client.post("/api/simulations", json={"perfil": PERFIL, "decisiones": ["magister", "seguir"], "seed": 1, "n_runs": 300})
    assert res.status_code == 200 and res.json()["edad_final"] == PERFIL["edad"] + 2


def test_unknown_decision(client):
    assert client.post("/api/simulations", json={"decisiones": ["volar"]}).status_code == 422


def test_turno_de_juego(client):
    res = client.post("/api/juego/turno", json={"perfil": PERFIL, "decisiones": ["buscar_pega"], "n_runs": 300})
    assert res.status_code == 200
    body = res.json()
    assert body["yo"]["edad"] == PERFIL["edad"] + 1 and len(body["historial"]) == 1
    assert body["menu"][0]["decision"] == "seguir"
    assert client.post("/api/juego/turno", json={"perfil": PERFIL, "decisiones": ["volar"]}).status_code == 422
