def test_list_decisions(client):
    keys = {d["key"] for d in client.get("/api/decisions").json()}
    assert {"seguir", "sabatico"} <= keys


def test_run_and_fetch(client):
    res = client.post("/api/simulations", json={"decisiones": ["seguir", "trabajar_mas"], "seed": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["edad_final"] == 27
    assert client.get(f"/api/simulations/{body['id']}").status_code == 200


def test_unknown_decision(client):
    assert client.post("/api/simulations", json={"decisiones": ["volar"]}).status_code == 422


def test_ocupaciones(client):
    grupos = client.get("/api/ocupaciones").json()
    assert len(grupos) == 10
    perfil = client.get("/api/ocupaciones/2", params={"edad": 30}).json()
    assert perfil["siguiente"][0]["prob"] > 0
    assert client.get("/api/ocupaciones/12").status_code == 404


def test_run_con_ocupacion(client):
    body = {"twin": {"ocupacion": 5}, "decisiones": ["cambiar_pega"], "seed": 1}
    step = client.post("/api/simulations", json=body).json()["trayectoria"][0]
    assert step["prob_nuevo_empleo"] > 0.75
    assert step["ocupaciones"][0]["nombre"]
    assert (
        client.post("/api/simulations", json={"twin": {"ocupacion": 10}, "decisiones": ["seguir"]}).status_code == 422
    )
