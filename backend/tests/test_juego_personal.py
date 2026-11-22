"""El juego a tu medida: tu relato llega al narrador como trasfondo."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services import juego_personal as jp
from app.services import narracion, narrador_ia


def test_sin_relato_no_hay_nada_que_contar():
    assert jp.desde("  ") == ""


def _capturar_narrador(monkeypatch) -> list:
    pedidos = []

    def narrar(items, relato=""):
        pedidos.append(SimpleNamespace(items=items, relato=relato))
        return [narrador_ia.Narrado(id=i.id, texto=i.plantilla, via="plantilla") for i in items]

    monkeypatch.setattr(narracion.narrador_ia, "narrar", narrar)
    return pedidos


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
