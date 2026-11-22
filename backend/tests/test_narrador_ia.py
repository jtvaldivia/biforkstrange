"""El narrador sin red: se reemplaza `_por_api`, la función que llama a Claude."""

import threading

import anthropic
import httpx
import pytest

from app.services import narrador_ia
from app.services.narrador_ia import Item, narrar


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    """Por defecto: con credenciales, prendido y con la caché vacía."""
    monkeypatch.setattr(narrador_ia.claude_comun, "hay_credenciales", lambda: True)
    monkeypatch.delenv("NARRADOR_IA", raising=False)
    narrador_ia.limpiar_cache()
    yield
    narrador_ia.limpiar_cache()


def _oferta(i: int = 0, **contexto) -> Item:
    return Item(id=f"o{i}", tipo="oferta", plantilla=f"Plantilla de oferta {i}.",
                contexto={"empresa": "Falabella", "cargo": "analista", "rubro": "Comercio", "n": i, **contexto})


def _despido() -> Item:
    return Item(id="d", tipo="evento", plantilla="Te despiden.",
                contexto={"empresa": "Falabella", "evento": "despido", "tono": "malo"})


def _letras(id_: str) -> str:
    """El id sin dígitos, para que el texto de prueba no caiga por cifras."""
    return id_.translate(str.maketrans("0123456789", "abcdefghij"))


class _Api:
    """Reemplazo de `_por_api`: cuenta las llamadas y responde con lo que diga `textos`."""

    def __init__(self, textos=None):
        self.textos = textos or (lambda item: f"Te ofrecen ser analista en Falabella, texto {_letras(item.id)}.")
        self.llamadas: list[list[str]] = []
        self.lock = threading.Lock()

    def __call__(self, lote):
        with self.lock:
            self.llamadas.append([i.id for i in lote])
        return {i.id: t for i in lote if (t := self.textos(i)) is not None}


def test_sin_credenciales_devuelve_plantillas(monkeypatch):
    monkeypatch.setattr(narrador_ia.claude_comun, "hay_credenciales", lambda: False)
    api = _Api()
    monkeypatch.setattr(narrador_ia, "_por_api", api)
    r = narrar([_oferta()])
    assert r[0].via == "plantilla" and r[0].texto == "Plantilla de oferta 0."
    assert api.llamadas == []


def test_apagado_por_variable_devuelve_plantillas(monkeypatch):
    monkeypatch.setenv("NARRADOR_IA", "0")
    api = _Api()
    monkeypatch.setattr(narrador_ia, "_por_api", api)
    assert narrar([_oferta()])[0].via == "plantilla"
    assert api.llamadas == []


def test_texto_valido_sale_por_claude(monkeypatch):
    monkeypatch.setattr(narrador_ia, "_por_api", _Api())
    r = narrar([_oferta()])
    assert r[0].via == "claude" and r[0].texto.startswith("Te ofrecen ser analista")


@pytest.mark.parametrize("texto", [
    "Te ofrecen ser analista en Falabella por 2 años.",
    "Te ofrecen ser analista en Falabella con un sueldo de $ alto.",
    "Te ofrecen ser analista en Falabella y un bono del diez %.",
    "Te ofrecen ser analista en Falabella, pagan en USD.",
    "Te ofrecen ser analista en Falabella, ganarías varios millones.",
    "Te ofrecen ser analista en Falabella, con más pesos al mes.",
])
def test_texto_con_cifras_cae_a_plantilla(monkeypatch, texto):
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda item: texto))
    assert narrar([_oferta()])[0].via == "plantilla"


def test_evento_malo_sin_marca_de_simulacion_cae_a_plantilla(monkeypatch):
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda item: "Falabella cierra tu área y te despiden."))
    assert narrar([_despido()])[0].via == "plantilla"


def test_evento_malo_con_marca_de_simulacion_pero_con_la_empresa_cae_a_plantilla(monkeypatch):
    """La marca de simulación ya no basta: un cierre o un despido no se le atribuye a una empresa real."""
    texto = "En este mundo simulado, Falabella cierra tu área y te despiden."
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda item: texto))
    assert narrar([_despido()])[0].via == "plantilla"


def test_evento_malo_con_marca_y_sin_la_empresa_pasa(monkeypatch):
    texto = "En este mundo simulado, tu empresa cierra tu área y te despiden."
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda item: texto))
    r = narrar([_despido()])
    assert r[0].via == "claude" and r[0].texto == texto


def test_marca_de_simulacion_acepta_variantes():
    assert narrador_ia.tiene_marca_simulacion("En esta SIMULACIÓN, la empresa cierra.")
    assert narrador_ia.tiene_marca_simulacion("En tu historia simulada te despiden.")
    assert not narrador_ia.tiene_marca_simulacion("La empresa cierra y te despiden.")


def test_texto_demasiado_largo_cae_a_plantilla(monkeypatch):
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda item: "Te ofrecen ser analista. " + "a" * 300))
    assert narrar([_oferta()])[0].via == "plantilla"


def test_la_cache_evita_la_segunda_llamada(monkeypatch):
    api = _Api()
    monkeypatch.setattr(narrador_ia, "_por_api", api)
    primero = narrar([_oferta()])
    segundo = narrar([_oferta()])
    assert len(api.llamadas) == 1
    assert segundo[0].via == "claude" and segundo[0].texto == primero[0].texto


def test_los_items_en_cache_no_se_reenvian(monkeypatch):
    api = _Api()
    monkeypatch.setattr(narrador_ia, "_por_api", api)
    narrar([_oferta(0)])
    narrar([_oferta(0), _oferta(1)])
    assert api.llamadas == [["o0"], ["o1"]]


def test_un_lote_de_treinta_se_parte_en_tres_llamadas(monkeypatch):
    api = _Api()
    monkeypatch.setattr(narrador_ia, "_por_api", api)
    r = narrar([_oferta(i) for i in range(30)])
    assert sorted(len(ll) for ll in api.llamadas) == [6, 12, 12]
    assert all(n.via == "claude" for n in r)


def test_id_faltante_cae_a_plantilla_solo_para_ese_item(monkeypatch):
    api = _Api(lambda item: None if item.id == "o1" else f"Te ofrecen ser analista en Falabella, {_letras(item.id)}.")
    monkeypatch.setattr(narrador_ia, "_por_api", api)
    r = narrar([_oferta(0), _oferta(1), _oferta(2)])
    assert [n.via for n in r] == ["claude", "plantilla", "claude"]
    assert r[1].texto == "Plantilla de oferta 1."


def test_conserva_orden_e_ids(monkeypatch):
    monkeypatch.setattr(narrador_ia, "_por_api", _Api())
    items = [_oferta(i) for i in (5, 2, 9, 0, 7)] + [_despido()]
    r = narrar(items)
    assert [n.id for n in r] == [i.id for i in items]
    assert r[-1].via == "plantilla"  # el despido sin marca


def test_un_error_del_sdk_no_se_propaga(monkeypatch):
    def falla(lote):
        peticion = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        raise anthropic.APIConnectionError(request=peticion)

    monkeypatch.setattr(narrador_ia, "_por_api", falla)
    r = narrar([_oferta(0), _oferta(1)])
    assert [n.via for n in r] == ["plantilla", "plantilla"]


def test_el_error_del_sdk_se_traduce_en_por_api(monkeypatch):
    """`_por_api` convierte los errores del SDK en la excepción común."""
    class Mensajes:
        def parse(self, **kwargs):
            raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))

    monkeypatch.setattr(narrador_ia.claude_comun, "cliente", lambda *a, **k: type("C", (), {"messages": Mensajes()})())
    with pytest.raises(narrador_ia.claude_comun.ClaudeNoDisponible):
        narrador_ia._por_api([_oferta()])


def test_por_api_arma_la_llamada_sin_datos_privados(monkeypatch):
    vistos = {}

    class Mensajes:
        def parse(self, **kwargs):
            vistos.update(kwargs)
            salida = narrador_ia._Lote(items=[narrador_ia._Texto(id="o0", texto=" Hola. ")])
            return type("R", (), {"stop_reason": "end_turn", "parsed_output": salida})()

    monkeypatch.setattr(narrador_ia.claude_comun, "cliente", lambda *a, **k: type("C", (), {"messages": Mensajes()})())
    assert narrador_ia._por_api([_oferta(sueldo=1_500_000)]) == {"o0": "Hola."}
    assert vistos["model"] == narrador_ia.MODELO
    assert vistos["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "sueldo" not in vistos["messages"][0]["content"]


def test_con_haiku_el_pedido_va_sin_razonar(monkeypatch):
    """Haiku es el modelo por defecto: el pedido apaga el razonamiento (permitido con esfuerzo bajo)."""
    from types import SimpleNamespace

    pedidos = []

    def parse(**kw):
        pedidos.append(kw)
        return SimpleNamespace(stop_reason="end_turn",
                               parsed_output=narrador_ia._Lote(items=[narrador_ia._Texto(id="o0", texto="Hola.")]))

    cliente = SimpleNamespace(messages=SimpleNamespace(parse=parse))
    monkeypatch.setattr(narrador_ia.claude_comun, "cliente", lambda *a, **k: cliente)
    monkeypatch.setattr(narrador_ia, "MODELO", "claude-haiku-5-5")
    monkeypatch.setattr(narrador_ia, "SIN_RAZONAR", True)
    narrador_ia._por_api([_oferta()])
    assert pedidos[0]["model"] == "claude-haiku-5-5" and pedidos[0]["thinking"] == {"type": "disabled"}
    assert pedidos[0]["output_config"] == {"effort": "low"}


def _cierre_sin_empresa() -> Item:
    """Como lo arma narracion.items_historia: el contexto va sin la empresa y su nombre queda en sin_nombrar."""
    return Item(id="c", tipo="evento", plantilla="La startup donde trabajas cierra.",
                contexto={"evento": "cierre", "tono": "malo"}, sin_nombrar=["Jumpseller"])


def test_evento_malo_que_nombra_la_empresa_cae_a_plantilla(monkeypatch):
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda item: "En este mundo simulado, Jumpseller cierra."))
    assert narrar([_cierre_sin_empresa()])[0].via == "plantilla"


def test_evento_malo_sin_nombre_pasa(monkeypatch):
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda item: "La startup donde trabajas cierra sus puertas."))
    assert narrar([_cierre_sin_empresa()])[0].via == "claude"


def test_sin_nombrar_no_se_le_manda_al_modelo():
    assert "sin_nombrar" not in _cierre_sin_empresa().model_dump()


def test_la_historia_no_le_pasa_la_empresa_a_un_evento_malo():
    from app.services.narracion import items_historia

    fin = {"empresa": "Jumpseller", "rol": "Analista", "rubro": "Información y comunicaciones", "tipo_empleador": "startup"}
    vista = {"historia": [{"anio": 1, "edad": 30, "fin": fin, "decisiones": [], "eventos": [
        {"nombre": "Cierre de la startup", "texto": "La startup donde trabajas cierra.", "tono": "malo"},
        {"nombre": "Ascenso", "texto": "Te ascienden.", "tono": "bueno"}]}]}
    malo, bueno = items_historia(vista)
    assert "empresa" not in malo.contexto and malo.sin_nombrar == ["Jumpseller"]
    assert bueno.contexto["empresa"] == "Jumpseller" and bueno.sin_nombrar == []


def test_una_empresa_real_no_va_en_la_misma_frase_que_un_cierre(monkeypatch):
    item = Item(id="m", tipo="mundo", plantilla="Te cambias y terminas en Jumpseller.",
                contexto={"empresa": "Jumpseller", "tono": "neutro"})
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda i: "Entras a Jumpseller, pero Jumpseller cierra al tercer año."))
    assert narrar([item])[0].via == "plantilla"
    narrador_ia.limpiar_cache()
    monkeypatch.setattr(narrador_ia, "_por_api", _Api(lambda i: "Entras a Jumpseller. Años después, la startup cierra."))
    assert narrar([item])[0].via == "claude"
