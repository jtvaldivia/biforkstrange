"""Lo que vale cada línea del CV (la duda con cada dato y sin él, con los mismos dados)
y la duda que el CV esconde (de las sugeridas, la que tiene más en juego).

Como en test_api_juego, no se fijan números del motor (se está calibrando): se fija la forma,
que "con el dato" sea la misma comparación que muestra la carta, y que sea determinista.
"""

N = 40  # gemelos por opción: pocos, para que el test sea rápido
CV = {"ingles": 1, "skill": 75, "red": 60, "usa_ia": 1, "nivel": 2, "edu": "postgrado", "anos_por_empleo": 2.5}


def _peso(client, **body) -> dict:
    r = client.post("/api/juego/peso-cv", json={"gemelos": N, "semilla": 7, **body})
    assert r.status_code == 200, r.text
    return r.json()


def test_forma_y_orden(client):
    p = _peso(client, perfil=CV, duda="emigrar")
    assert p["decision"] == "emigrar" and p["gemelos"] == N and p["pregunta"]
    assert 0 < len(p["datos"]) <= 4
    cambios = [d["cambio"] for d in p["datos"]]
    assert cambios == sorted(cambios, reverse=True)
    campos = [d["campo"] for d in p["datos"]] + p["sin_efecto"] + p["otros"]
    assert len(campos) == len(set(campos)) and set(campos) <= set(CV)
    for d in p["datos"]:
        assert d["tuyo"] == CV[d["campo"]] and d["tuyo"] != d["neutro"]
        assert d["mueve"] in ("gana", "sueldo")
        assert d["opcion"] in [o["opcion"] for o in d["opciones"]]
        for o in d["opciones"]:
            assert 0 <= o["gana_con"] <= 1 and 0 <= o["gana_sin"] <= 1
            assert o["sueldo_con"] > 0 and o["sueldo_sin"] > 0


def test_el_ingles_pesa_al_emigrar(client):
    p = _peso(client, perfil=CV, duda="emigrar")
    assert "ingles" in [d["campo"] for d in p["datos"]]


def test_con_el_dato_es_la_carta_de_la_duda(client):
    """Mismo perfil, semilla y gemelos: "con" son los mismos mundos que ve la persona en su carta."""
    p = _peso(client, perfil=CV, duda="emigrar")
    r = client.post("/api/juego/partida", json={"perfil": CV, "duda": "emigrar", "semilla": 7, "gemelos": N})
    comp = r.json()["pendiente"]["comparacion"]
    ganadores = comp["ganador_por_mundo"]
    tipicos = {o["opcion"]: o["sueldo"]["p50"] for o in comp["opciones"]}
    for d in p["datos"]:
        for o in d["opciones"]:
            assert o["gana_con"] == ganadores.count(o["opcion"]) / len(ganadores)
            assert o["sueldo_con"] == tipicos[o["opcion"]]


def test_sin_datos_del_cv_no_hay_nada_que_pesar(client):
    """Un perfil que ya está en los valores neutros no tiene líneas que quitar."""
    p = _peso(client, perfil={"edu": "media"}, duda="oferta_externa")
    assert p["datos"] == [] and p["sin_efecto"] == [] and p["otros"] == []


def test_es_determinista(client):
    a = _peso(client, perfil=CV, duda="oferta_externa")
    b = _peso(client, perfil=CV, duda="oferta_externa")
    assert a == b


def test_duda_que_no_aplica(client):
    r = client.post("/api/juego/peso-cv", json={"perfil": {"tipo_empleador": "startup"}, "duda": "unirse_a_startup"})
    assert r.status_code == 422


# ── la duda que tu CV esconde ────────────────────────────────────────────────

SUGERIDAS = ["emigrar", "unirse_a_startup", "oferta_externa"]


def _en_juego(client, **body) -> dict:
    r = client.post("/api/juego/dudas-en-juego", json={"gemelos": N, **body})
    assert r.status_code == 200, r.text
    return r.json()


def test_marca_la_duda_con_mas_en_juego(client):
    j = _en_juego(client, perfil=CV, dudas=SUGERIDAS)
    assert [d["decision"] for d in j["dudas"]] == SUGERIDAS
    for d in j["dudas"]:
        assert d["nombre"] and d["pregunta"]
        assert 0 < d["mala"] <= d["tipico"] <= d["buena"]
        assert d["dispersion"] >= 0 and d["entre_opciones"] >= 0
    assert j["mas_en_juego"] == max(j["dudas"], key=lambda d: d["dispersion"])["decision"]


def test_el_rango_es_el_de_la_carta(client):
    """`mala` y `buena` son el peor p10 y el mejor p90 de las opciones que muestra la carta de esa duda."""
    j = _en_juego(client, perfil=CV, dudas=["oferta_externa"], semilla=3)
    r = client.post("/api/juego/partida", json={"perfil": CV, "duda": "oferta_externa", "semilla": 3, "gemelos": N})
    opciones = r.json()["pendiente"]["comparacion"]["opciones"]
    (d,) = j["dudas"]
    assert d["mala"] == min(o["sueldo"]["p10"] for o in opciones)
    assert d["buena"] == max(o["sueldo"]["p90"] for o in opciones)


def test_con_una_sola_duda_no_hay_cual_marcar(client):
    j = _en_juego(client, perfil=CV, dudas=["emigrar"])
    assert len(j["dudas"]) == 1 and j["mas_en_juego"] is None


def test_salta_las_dudas_que_no_aplican(client):
    j = _en_juego(client, perfil={"tipo_empleador": "startup"}, dudas=["unirse_a_startup", "oferta_externa", "emigrar"])
    assert [d["decision"] for d in j["dudas"]] == ["oferta_externa", "emigrar"]


def test_duda_que_no_existe(client):
    r = client.post("/api/juego/dudas-en-juego", json={"dudas": ["no_existe"]})
    assert r.status_code == 422
