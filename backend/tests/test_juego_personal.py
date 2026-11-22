"""El juego a tu medida: tu relato y los rasgos de tu gemelo."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import get_twin_repo
from app.core.llm import ClaudeJSON
from app.main import app
from app.services import juego_personal as jp
from app.services import narracion, narrador_ia
from app.services.twin_brain import PRIOR_SD_MIN, ClaudeBrain, DimEstimate, PriorOut
from app.sim.motor import partida
from app.sim.motor.perfil import Perfil
from app.twin.profile import Dim, TwinProfile


def gemelo(**dims) -> TwinProfile:
    p = TwinProfile()
    for k, m in dims.items():
        p.dims[k] = Dim(m=m, sd=8, n=3)
    return p


def test_sin_relato_ni_gemelo_no_hay_personalizacion():
    assert jp.desde("  ", None) is None


def test_afinidad_sigue_los_rasgos_medidos_y_ignora_los_dudosos():
    arriesgado = jp.afinidad(gemelo(rcar=95, rfin=90, E=85, vind=90, pro=85))
    assert arriesgado["emprender"] > 2 and arriesgado["ahorro"] < 1
    assert "magister" not in arriesgado  # sin rasgos medidos, la carta pesa lo de siempre
    assert jp.afinidad(TwinProfile()) == {}  # gemelo recién creado: todo con duda máxima


def test_la_afinidad_cambia_las_cartas_que_salen_solo_en_tu_partida():
    p = Perfil(edad=28, sueldo=1_500_000, riesgo=5)
    afin = jp.afinidad(gemelo(rcar=98, rfin=95, E=95, vind=95, pro=95))

    def cuentan(afinidad):
        n = 0
        with partida.con_afinidad(afinidad):
            for s in range(40):
                v = partida.jugar(p, s, [])
                n += v.pendiente is not None and v.pendiente.decision["id"] in ("emprender", "independizarse", "unirse_a_startup")
        return n

    assert cuentan(afin) > cuentan({})


def _semilla_que_cambia_con(afinidad: dict, perfil: Perfil) -> int:
    """Una semilla donde la afinidad cambia la primera carta (así el test no depende de suerte)."""
    for s in range(200):
        with partida.con_afinidad(afinidad):
            con = partida.jugar(perfil, s, []).pendiente
        sin = partida.jugar(perfil, s, []).pendiente
        if con and sin and con.decision["id"] != sin.decision["id"]:
            return s
    raise AssertionError("ninguna semilla cambió de carta")


def _capturar_narrador(monkeypatch) -> list:
    pedidos = []

    def narrar(items, relato=""):
        pedidos.append(SimpleNamespace(items=items, relato=relato))
        return [narrador_ia.Narrado(id=i.id, texto=i.plantilla, via="plantilla") for i in items]

    monkeypatch.setattr(narracion.narrador_ia, "narrar", narrar)
    return pedidos


def test_narrar_rejuega_con_la_misma_afinidad_que_la_partida(monkeypatch):
    """Sin la afinidad, /narrar rejugaba otra partida y contaba otra carta que la que se ve."""
    g = get_twin_repo().create(gemelo(rcar=98, rfin=95, E=95, vind=95, pro=95, int=90, I=90))
    perfil = {"edad": 30, "sueldo": 1_400_000, "gemelo_id": g.id}
    semilla = _semilla_que_cambia_con(jp.afinidad(g), Perfil(edad=30, sueldo=1_400_000))
    pedidos = _capturar_narrador(monkeypatch)
    tc = TestClient(app)

    pend = tc.post("/api/juego/partida", json={"perfil": perfil, "semilla": semilla, "gemelos": 0}).json()["pendiente"]
    assert tc.post("/api/juego/narrar", json={"perfil": perfil, "semilla": semilla, "que": "pendiente"}).status_code == 200
    situacion = next(i for i in pedidos[0].items if i.id == "situacion")
    assert situacion.contexto["decision"] == pend["decision"]


def test_la_afinidad_congelada_manda_aunque_el_gemelo_se_pierda():
    g = get_twin_repo().create(gemelo(rcar=98, rfin=95, E=95, vind=95, pro=95))
    tc = TestClient(app)
    congelada = tc.post("/api/juego/afinidad", json={"gemelo_id": g.id}).json()["afinidad"]
    semilla = _semilla_que_cambia_con(congelada, Perfil(edad=30, sueldo=1_400_000))

    def carta(perfil):
        return tc.post("/api/juego/partida", json={"perfil": perfil, "semilla": semilla, "gemelos": 0}).json()["pendiente"]["decision"]

    viva = carta({"edad": 30, "sueldo": 1_400_000, "gemelo_id": g.id})
    perdida = {"edad": 30, "sueldo": 1_400_000, "gemelo_id": "ya-no-existe"}
    assert carta({**perdida, "afinidad": congelada}) == viva  # congelada: misma partida
    assert carta(perdida) != viva  # sin congelar, la partida cambiaba de rumbo
    assert tc.post("/api/juego/afinidad", json={"gemelo_id": "ya-no-existe"}).status_code == 404


def test_la_afinidad_del_cliente_se_acota():
    acotada = jp.acotar_afinidad({"emprender": 1e9, "ahorro": 0.0, "carta_inventada": 2.0})
    assert set(acotada) == {"emprender", "ahorro"}
    assert acotada["emprender"] <= 3.4 and acotada["ahorro"] >= 0.3


def test_el_relato_llega_al_narrador_sin_el_bloque_de_datos(monkeypatch):
    pedidos = _capturar_narrador(monkeypatch)
    relato = "```gemelo-laboral\nsueldo_liquido: 2500000\n```\n\n## Sobre mí\nSoy diseñadora y odio las reuniones largas."
    r = TestClient(app).post("/api/juego/narrar", json={"perfil": {"relato": relato}, "semilla": 1, "que": "pendiente"})
    assert r.status_code == 200
    assert "odio las reuniones" in pedidos[0].relato and "2500000" not in pedidos[0].relato


def test_el_relato_entra_al_pedido_y_a_la_llave_de_la_cache(monkeypatch):
    monkeypatch.setattr(narrador_ia.claude_comun, "hay_credenciales", lambda: True)
    monkeypatch.delenv("NARRADOR_IA", raising=False)
    narrador_ia.limpiar_cache()
    llamadas = []

    def por_api(lote, relato=""):
        llamadas.append(relato)
        return {i.id: f"Texto para {'ella' if relato else 'nadie'}." for i in lote}

    monkeypatch.setattr(narrador_ia, "_por_api", por_api)
    item = narrador_ia.Item(id="situacion", tipo="evento", plantilla="Te llega una carta.", contexto={"tono": "neutro"})
    assert narrador_ia.narrar([item], relato="Soy diseñadora.")[0].texto == "Texto para ella."
    assert narrador_ia.narrar([item])[0].texto == "Texto para nadie."  # sin relato es otra llave
    narrador_ia.narrar([item], relato="Soy diseñadora.")  # ya en caché
    assert llamadas == ["Soy diseñadora.", ""]
    narrador_ia.limpiar_cache()


def test_la_estimacion_de_claude_no_pesa_mas_que_una_respuesta():
    llm = SimpleNamespace(ask=lambda *a, **k: PriorOut(dims=[DimEstimate(key="rcar", m=85, sd=5, ev="dice que emprende")]))
    assert ClaudeBrain(llm).prior("contexto", ["rcar"])["rcar"].sd == PRIOR_SD_MIN


def test_el_reintento_le_dice_al_modelo_que_fallo():
    prompts = []

    def create(**kw):
        prompts.append(kw["messages"][0]["content"])
        texto = '{"dims": []}' if len(prompts) == 1 else '{"dims": [{"key": "rcar", "m": 60, "sd": 20, "ev": "x"}]}'
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=texto)])

    def check(o):
        if not o.dims:
            raise ValueError("faltan dimensiones")

    cliente = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    out = ClaudeJSON(cliente, "claude-sonnet-5-5").ask("estima", PriorOut, check=check)
    assert out.dims[0].key == "rcar"
    assert "faltan dimensiones" in prompts[1] and "faltan dimensiones" not in prompts[0]
