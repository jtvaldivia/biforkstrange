"""La API del juego: catálogo, dudas y partida.

La partida no guarda estado: el cliente manda (perfil, semilla, duda, elecciones) y el
servidor la vuelve a jugar. Los pesos del motor se están calibrando, así que aquí no se
fija ningún número de resultado: se fija la forma, la consistencia interna y que la misma
llamada dé siempre lo mismo.
"""

import pytest

N = 20  # gemelos por opción: pocos, para que los tests sean rápidos
DUDA = "unirse_a_startup"
MAX_LLAMADAS = 80  # una partida de 10 años tiene bastante menos decisiones que esto


def _partida(client, **body):
    return client.post("/api/juego/partida", json={"gemelos": N, **body})


def _ok(client, **body) -> dict:
    r = _partida(client, **body)
    assert r.status_code == 200, r.text
    return r.json()


def _jugar_entera(client, elegir, **body) -> tuple[dict, list[dict], list[dict]]:
    """Juega como un cliente: pide la partida, elige, vuelve a pedirla con una elección más.

    Devuelve la vista final, las elecciones y todas las vistas intermedias."""
    elecciones: list[dict] = []
    vistas = []
    for _ in range(MAX_LLAMADAS):
        v = _ok(client, elecciones=elecciones, **body)
        vistas.append(v)
        if v["terminada"]:
            return v, elecciones, vistas
        pendiente = v["pendiente"]
        opcion = elegir(pendiente)
        parametros = {el["variable"]: el["alternativas"][0]["valor"] for el in opcion["elecciones_internas"]}
        elecciones = [*elecciones, {"decision": pendiente["decision"], "opcion": opcion["opcion"],
                                    "parametros": parametros}]
    raise AssertionError("la partida no terminó")


def _ultima(pendiente: dict) -> dict:
    return pendiente["opciones"][-1]


def _primera(pendiente: dict) -> dict:
    return pendiente["opciones"][0]


# ── catálogo y dudas ─────────────────────────────────────────────────────────


def test_catalogo(client):
    r = client.get("/api/juego/catalogo")
    assert r.status_code == 200
    c = r.json()
    assert set(c) >= {"rubros", "tipos_empleador", "niveles", "educacion", "ocupaciones", "carreras"}
    assert "Servicios profesionales" in c["rubros"] and "" not in c["rubros"]
    assert c["tipos_empleador"] == ["grande", "pyme", "startup", "publico", "extranjero"]
    assert [n["nivel"] for n in c["niveles"]] == [0, 1, 2, 3, 4]
    assert all(n["nombre"] for n in c["niveles"])
    assert c["educacion"] == ["media", "tecnica", "universitaria", "postgrado"]
    assert c["ocupaciones"] and all({"grupo", "nombre"} <= set(o) for o in c["ocupaciones"])
    assert c["carreras"] and all({"carrera_id", "carrera", "tipo_institucion", "area"} <= set(x) for x in c["carreras"])


def test_el_perfil_por_defecto_del_catalogo_es_jugable(client):
    """Cualquier rubro y tipo de empleador del catálogo sirve para pedir dudas."""
    c = client.get("/api/juego/catalogo").json()
    for rubro in (c["rubros"][0], c["rubros"][-1]):
        for tipo in c["tipos_empleador"]:
            r = client.post("/api/juego/dudas", json={"perfil": {"rubro": rubro, "tipo_empleador": tipo}})
            assert r.status_code == 200, (rubro, tipo, r.text)
            assert r.json()


def test_dudas(client):
    r = client.post("/api/juego/dudas", json={})
    assert r.status_code == 200
    dudas = r.json()
    ids = [d["decision"] for d in dudas]
    assert DUDA in ids and "oferta_externa" in ids
    assert len(ids) == len(set(ids))
    for d in dudas:
        assert {"decision", "nombre", "pregunta", "categoria", "calidad"} <= set(d)
        assert d["pregunta"] and d["calidad"] in ("dato", "mixto", "supuesto")
    # las decisiones que la vida fuerza no son dudas con las que se llega: está empleada, no cesante
    assert "cesantia" not in ids


def test_dudas_dependen_del_perfil(client):
    en_startup = client.post("/api/juego/dudas", json={"perfil": {"tipo_empleador": "startup"}}).json()
    assert DUDA not in [d["decision"] for d in en_startup]


def test_toda_duda_ofrecida_se_puede_jugar(client):
    """Lo que `/dudas` ofrece, `/partida` lo acepta como duda inicial y queda pendiente ahí."""
    for d in client.post("/api/juego/dudas", json={}).json():
        v = _ok(client, duda=d["decision"], gemelos=0)
        assert v["pendiente"]["decision"] == d["decision"], d["decision"]
        assert v["pendiente"]["pregunta"] == d["pregunta"]
        assert len(v["pendiente"]["opciones"]) >= 2


# ── partida: la decisión pendiente ───────────────────────────────────────────


def test_partida_nueva_queda_pendiente_en_la_duda(client):
    v = _ok(client, duda=DUDA, semilla=7)
    assert v["terminada"] is False and v["cierre"] is None
    assert v["anio"] == 0 and v["anios"] == 10 and v["semilla"] == 7 and v["duda"] == DUDA
    assert v["elecciones"] == [] and v["historia"] == []
    assert v["estado"]["edad"] == 30 and v["estado"]["estado"] == "empleado"
    assert v["estado"]["sueldo"] == 1_400_000 and v["estado"]["cargo"] == "Semi senior"
    assert v["anio_en_curso"]["anio"] == 1 and v["anio_en_curso"]["decisiones"] == []
    p = v["pendiente"]
    assert p["decision"] == DUDA and p["pregunta"]
    assert p["calidad"] in ("dato", "mixto", "supuesto")
    assert [o["opcion"] for o in p["opciones"]] == ["ir", "quedarse"]
    for o in p["opciones"]:
        assert {"opcion", "nombre", "detalle", "calidad", "elecciones_internas"} <= set(o)


def test_comparacion_de_la_pendiente(client):
    p = _ok(client, duda="oferta_externa", semilla=3)["pendiente"]
    comp = p["comparacion"]
    assert comp["decision"] == "oferta_externa" and comp["gemelos"] == N and comp["anios"] == 10
    assert comp["pregunta"] == p["pregunta"] and comp["creencia_vs_dato"] == p["creencia_vs_dato"]
    assert [o["opcion"] for o in comp["opciones"]] == [o["opcion"] for o in p["opciones"]]
    bases = [o for o in comp["opciones"] if o["es_base"]]
    assert len(bases) == 1 and bases[0]["opcion"] == comp["base"]
    for o in comp["opciones"]:
        s = o["sueldo"]
        assert 0 <= s["p10"] <= s["p50"] <= s["p90"] and s["p90"] > 0  # 0: terminó sin trabajo
        assert o["ingreso_total"]["p10"] <= o["ingreso_total"]["p50"] <= o["ingreso_total"]["p90"]
        for fraccion in ("paso_por_cesantia", "sin_trabajo_al_final"):
            assert 0 <= o[fraccion] <= 1
        assert o["sin_trabajo_al_final"] <= o["paso_por_cesantia"] or o["paso_por_cesantia"] < 1
        assert o["meses_sin_trabajo"] >= 0
        # los cargos reparten a todos los gemelos y el más probable es el de mayor peso
        assert sum(c["prob"] for c in o["cargos"]) == pytest.approx(1)
        assert o["cargo_mas_probable"] in [c["cargo"] for c in o["cargos"]]
        assert max(c["prob"] for c in o["cargos"]) == next(
            c["prob"] for c in o["cargos"] if c["cargo"] == o["cargo_mas_probable"])
        # el dado: los resultados reparten a todos los gemelos
        assert sum(r["gemelos"] for r in o["por_resultado"]) == N
        assert sum(r["prob"] for r in o["por_resultado"]) == pytest.approx(1)
        for r in o["por_resultado"]:
            assert r["resultado"] and r["tono"] in ("bueno", "malo", "neutro")
        # cada gemelo contra sí mismo con la opción base: gana más, igual o menos (suman 1) y por cuánto
        claves = ("gana_mas_que_base", "igual_que_base", "gana_menos_que_base")
        assert isinstance(o["parametros"], dict)
        if o["es_base"]:
            assert all(o[c] is None for c in (*claves, "diferencia_tipica"))
            assert all(r[c] is None for r in o["por_resultado"] for c in claves)
        else:
            assert all(0 <= o[c] <= 1 for c in claves)
            assert sum(o[c] for c in claves) == pytest.approx(1)
            assert isinstance(o["diferencia_tipica"], int)
            for r in o["por_resultado"]:
                assert sum(r[c] for c in claves) == pytest.approx(1)
            # las filas por resultado, pesadas por sus gemelos, dan el total de la opción
            for c in claves:
                assert sum(r[c] * r["gemelos"] for r in o["por_resultado"]) == pytest.approx(o[c] * N)
        # un punto por año, con edades seguidas desde el año siguiente
        assert len(o["trayectoria"]) == comp["anios"]
        assert [t["edad"] for t in o["trayectoria"]] == list(range(31, 41))
        for t in o["trayectoria"]:
            assert t["p10"] <= t["p50"] <= t["p90"] and 0 <= t["sin_trabajo"] <= 1
        assert "sueldos" not in o  # el detalle por gemelo no viaja al cliente


def test_gemelos_cero_no_compara(client):
    v = _ok(client, duda=DUDA, semilla=7, gemelos=0)
    assert v["pendiente"]["decision"] == DUDA
    assert v["pendiente"]["comparacion"] is None
    assert v["pendiente"]["opciones"]
    final, _, _ = _jugar_entera(client, _ultima, duda=DUDA, semilla=7, gemelos=0)
    assert final["terminada"] and final["cierre"]["primera_decision"] is None
    assert "mejor_que_gemelos" not in final["cierre"]


def test_los_gemelos_no_cambian_lo_que_te_pasa_a_ti(client):
    """Cuántos gemelos se simulan es cosa de la comparación: tu vida es la misma."""
    con, _, _ = _jugar_entera(client, _ultima, duda=DUDA, semilla=5)
    sin, _, _ = _jugar_entera(client, _ultima, duda=DUDA, semilla=5, gemelos=0)
    assert con["historia"] == sin["historia"] and con["estado"] == sin["estado"]


def test_parametros_de_la_comparacion(client):
    """`parametros` dice qué eligen los gemelos dentro de una opción; no toca la partida."""
    base = _ok(client, duda="cambiar_de_rubro", semilla=1)
    interna = base["pendiente"]["opciones"][0]["elecciones_internas"][0]
    assert interna["variable"] == "rubro_destino"
    valores = [a["valor"] for a in interna["alternativas"]]
    assert "Servicios profesionales" not in valores  # no se ofrece el rubro en el que ya está
    otro = _ok(client, duda="cambiar_de_rubro", semilla=1, parametros={"cambiar": {"rubro_destino": valores[-1]}})
    assert otro["estado"] == base["estado"]
    assert otro["pendiente"]["comparacion"]["opciones"][1] == base["pendiente"]["comparacion"]["opciones"][1]


# ── partida: avanzar ─────────────────────────────────────────────────────────


def test_avanzar_con_una_eleccion(client):
    eleccion = {"decision": DUDA, "opcion": "ir", "parametros": {}}
    v = _ok(client, duda=DUDA, semilla=7, elecciones=[eleccion])
    assert v["elecciones"] == [eleccion]
    anio1 = v["historia"][0] if v["historia"] else v["anio_en_curso"]
    d = anio1["decisiones"][0]
    assert d["decision"] == DUDA and d["opcion"] == "ir" and d["opcion_nombre"] == "Irte"
    assert d["resultado"] in ("crece", "cierra", "sigue") and d["texto"]
    assert 0 < d["prob"] <= 1 and d["tono"] in ("bueno", "malo", "neutro")
    if v["historia"]:
        fin = anio1["fin"]
        assert fin["edad"] == 31 and fin["tipo_empleador"] == "startup"
        assert v["anio"] == 1
    assert v["terminada"] is False and v["pendiente"]["decision"]


def test_la_decision_de_la_eleccion_es_opcional(client):
    """`decision` solo sirve para detectar un cliente desincronizado; sin ella vale igual."""
    con = _ok(client, duda=DUDA, semilla=7, elecciones=[{"decision": DUDA, "opcion": "quedarse"}])
    sin = _ok(client, duda=DUDA, semilla=7, elecciones=[{"opcion": "quedarse"}])
    assert con["historia"] == sin["historia"] and con["pendiente"] == sin["pendiente"]


def test_eleccion_interna_cambia_el_destino(client):
    """Elegir "a qué rubro" dentro de la opción lleva a ese rubro cuando el dado dice que entras."""
    for semilla in range(40):
        v = _ok(client, duda="cambiar_de_rubro", semilla=semilla, gemelos=0,
                elecciones=[{"opcion": "cambiar", "parametros": {"rubro_destino": "Salud"}}])
        anio1 = v["historia"][0] if v["historia"] else v["anio_en_curso"]
        if anio1["decisiones"][0]["resultado"] == "entra" and len(anio1["decisiones"]) == 1 and v["historia"]:
            assert anio1["fin"]["rubro"] == "Salud"
            return
    raise AssertionError("en 40 semillas nunca entró al rubro nuevo")


def test_partida_completa_como_la_juega_un_cliente(client):
    final, elecciones, vistas = _jugar_entera(client, _ultima, duda=DUDA, semilla=7)
    assert final["terminada"] is True and final["pendiente"] is None and final["anio_en_curso"] is None
    assert final["anio"] == 10 and len(final["historia"]) == 10
    assert len(vistas) == len(elecciones) + 1
    assert final["elecciones"] == elecciones

    # la historia: un registro por año, edades que avanzan, y cada elección quedó en su año
    edades = [r["fin"]["edad"] for r in final["historia"]]
    assert edades == sorted(edades) and len(set(edades)) == 10 and edades[0] > 30
    assert [r["anio"] for r in final["historia"]] == list(range(1, 11))
    jugadas = [(d["decision"], d["opcion"]) for r in final["historia"] for d in r["decisiones"] if d["origen"] != "luego"
               or d["decision"] in {e["decision"] for e in elecciones}]
    assert [(e["decision"], e["opcion"]) for e in elecciones] == [j for j in jugadas if j[0] != "tipo_de_empleador"]
    for r in final["historia"]:
        assert isinstance(r["recesion"], bool)
        for d in r["decisiones"]:
            assert 0 <= d["prob"] <= 1
        for ev in r["eventos"]:
            assert ev["nombre"] and 0 < ev["prob"] <= 1 and isinstance(ev["rutina"], bool)
        fin = r["fin"]
        assert fin["estado"] in ("estudiando", "buscando", "empleado", "independiente", "fundador", "inactivo")
        assert fin["sueldo"] >= 0 and fin["cargo"]
    assert final["estado"] == final["historia"][-1]["fin"]

    # el cierre: tu vida frente a los gemelos de la primera decisión
    cierre = final["cierre"]
    assert cierre["estado"] == final["estado"]
    assert cierre["sueldo_final"] == final["estado"]["sueldo"]
    assert cierre["ultimo_sueldo"] == (None if final["estado"]["sueldo"] > 0 else final["estado"]["sueldo_ref"])
    assert cierre["anios_sin_trabajo"] == sum(1 for r in final["historia"] if r["fin"]["estado"] == "buscando")
    assert 0 <= cierre["mejor_que_gemelos"] <= 1
    primera = cierre["primera_decision"]
    assert primera["decision"] == DUDA and primera["elegida"] == elecciones[0]["opcion"]
    # la comparación del cierre es la misma que se mostró antes de elegir
    assert primera["comparacion"] == vistas[0]["pendiente"]["comparacion"]


def test_cada_llamada_repite_lo_ya_jugado(client):
    """Jugar de nuevo con más elecciones no cambia el pasado: la historia solo crece."""
    final, elecciones, vistas = _jugar_entera(client, _primera, duda="pedir_aumento", semilla=11, gemelos=0)
    assert final["terminada"]
    for antes, despues in zip(vistas, vistas[1:]):
        assert despues["historia"][: len(antes["historia"])] == antes["historia"]
        assert len(despues["elecciones"]) == len(antes["elecciones"]) + 1
    # y cualquier corte de las elecciones lleva al mismo punto intermedio
    medio = len(elecciones) // 2
    assert _ok(client, duda="pedir_aumento", semilla=11, gemelos=0, elecciones=elecciones[:medio]) == vistas[medio]


def test_determinismo(client):
    body = {"duda": DUDA, "semilla": 21, "elecciones": [{"opcion": "ir"}]}
    assert _ok(client, **body) == _ok(client, **body)
    final, elecciones, _ = _jugar_entera(client, _ultima, duda=DUDA, semilla=21)
    assert _ok(client, duda=DUDA, semilla=21, elecciones=elecciones) == final
    # otra semilla es otra suerte: en alguna de estas cambia el primer año
    primeros = {str(_ok(client, duda=DUDA, semilla=s, gemelos=0, elecciones=[{"opcion": "ir"}])["historia"][:1])
                for s in range(8)}
    assert len(primeros) > 1


def test_la_semilla_no_cambia_la_pregunta_solo_la_suerte(client):
    a = _ok(client, duda=DUDA, semilla=1, gemelos=0)["pendiente"]
    b = _ok(client, duda=DUDA, semilla=2, gemelos=0)["pendiente"]
    # la historia de la carta (qué empresa, quién escribe) y la empresa de cada opción
    # sí cambian con la semilla; la decisión no
    a.pop("narrativa"), b.pop("narrativa")
    for o in a["opciones"] + b["opciones"]:
        o.pop("empresa")
    assert a == b


def test_partida_sin_duda_reparte_una_carta(client):
    """Sin duda inicial el mundo reparte la primera carta."""
    v = _ok(client, semilla=4, gemelos=0)
    assert v["duda"] is None and v["terminada"] is False
    ofrecidas = [d["decision"] for d in client.post("/api/juego/dudas", json={}).json()]
    assert v["pendiente"]["decision"] in ofrecidas


@pytest.mark.parametrize(
    "perfil, duda",
    [
        ({"edad": 22, "edu": "media", "rubro": "Comercio", "nivel": 0, "sueldo": 550000}, "renunciar"),
        ({"edad": 45, "sexo": "h", "edu": "postgrado", "rubro": "Finanzas y seguros", "tipo_empleador": "grande",
          "nivel": 3, "sueldo": 4500000}, "emprender"),
        ({"edad": 50, "tipo_empleador": "publico", "rubro": "Administración pública", "nivel": 4, "sueldo": 8000000},
         "sabatico"),
    ],
)
@pytest.mark.parametrize("elegir", [_primera, _ultima], ids=["primera", "ultima"])
def test_otros_perfiles_llegan_al_cierre(client, perfil, duda, elegir):
    final, elecciones, _ = _jugar_entera(client, elegir, perfil=perfil, duda=duda, semilla=3)
    assert final["terminada"] and final["cierre"]["primera_decision"]["decision"] == duda
    assert final["cierre"]["primera_decision"]["elegida"] == elecciones[0]["opcion"]
    # sin trabajo al final el sueldo final es $0, pero siempre hay un sueldo que mostrar: el de hoy o el último
    assert final["cierre"]["sueldo_final"] > 0 or final["cierre"]["ultimo_sueldo"] > 0
    assert final["estado"]["edad"] <= 60


# ── errores ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "body",
    [
        {"duda": "no_existe"},
        {"duda": "cesantia"},                                              # está empleada: no aplica
        {"duda": DUDA, "perfil": {"tipo_empleador": "startup"}},           # ya está en una startup
        {"duda": DUDA, "elecciones": [{"opcion": "no_existe"}]},
        {"duda": DUDA, "elecciones": [{"decision": "renunciar", "opcion": "ir"}]},  # cliente desincronizado
        {"duda": DUDA, "elecciones": [{"opcion": "ir", "parametros": {"sueldo": 99000000}}]},
        {"duda": DUDA, "elecciones": [{"decision": DUDA}]},                # falta la opción
        {"duda": DUDA, "gemelos": 5000},
        {"duda": DUDA, "gemelos": -1},
        {"duda": DUDA, "perfil": {"edad": 10}},
        {"duda": DUDA, "perfil": {"sueldo": 0}},
        {"duda": DUDA, "perfil": {"tipo_empleador": "ong"}},
        {"duda": DUDA, "semilla": "siete"},
    ],
)
def test_partida_invalida_da_422(client, body):
    r = _partida(client, **body)
    assert r.status_code == 422, r.text
    assert r.json()["detail"]


def test_sobran_elecciones_da_422(client):
    _, elecciones, _ = _jugar_entera(client, _ultima, duda=DUDA, semilla=7, gemelos=0)
    r = _partida(client, duda=DUDA, semilla=7, gemelos=0, elecciones=[*elecciones, {"opcion": "quedarse"}])
    assert r.status_code == 422
    assert "sobran" in r.json()["detail"]


def test_dudas_con_perfil_invalido_da_422(client):
    assert client.post("/api/juego/dudas", json={"perfil": {"edad": 99}}).status_code == 422


# ------------------------------------------------------------------ mundos explorables
def _mundo(client, mundo: int, **body):
    return client.post("/api/juego/mundo", json={"gemelos": N, "mundo": mundo, **body})


def test_ganador_por_mundo(client):
    """Un ganador por mundo, que es una de las opciones o un empate (None)."""
    comp = _ok(client, duda="oferta_externa")["pendiente"]["comparacion"]
    ganadores = comp["ganador_por_mundo"]
    assert len(ganadores) == N
    opciones = {o["opcion"] for o in comp["opciones"]}
    assert all(g is None or g in opciones for g in ganadores)


def test_un_mundo_coincide_con_la_comparacion(client):
    """Abrir un mundo vuelve a vivirlo con los mismos dados: el ganador y los sueldos calzan con la nube."""
    comp = _ok(client, duda="oferta_externa", semilla=7)["pendiente"]["comparacion"]
    for numero in (0, 3, N - 1):
        r = _mundo(client, numero, duda="oferta_externa", semilla=7)
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["mundo"] == numero and m["ganador"] == comp["ganador_por_mundo"][numero]
        assert {o["opcion"] for o in m["opciones"]} == {o["opcion"] for o in comp["opciones"]}
        for o in m["opciones"]:
            assert 1 <= len(o["anios"]) <= 10 and o["anios"][0]["anio"] == 1
            assert all({"tipo", "nombre", "texto", "tono"} <= s.keys() for a in o["anios"] for s in a["sucesos"])
        # lo que le pasa al mundo (la recesión) es igual con todas las opciones
        largo = min(len(o["anios"]) for o in m["opciones"])
        assert len({tuple(a["recesion"] for a in o["anios"][:largo]) for o in m["opciones"]}) == 1


def test_la_primera_decision_del_mundo_es_la_opcion(client):
    m = _mundo(client, 0, duda="oferta_externa").json()
    for o in m["opciones"]:
        primera = o["anios"][0]["sucesos"][0]
        assert primera["tipo"] == "decision" and primera["opcion"] == o["nombre"]


def test_mundo_sin_decision_pendiente_da_422(client):
    final, elecciones, _ = _jugar_entera(client, lambda p: p["opciones"][0], duda="oferta_externa")
    assert final["terminada"]
    assert _mundo(client, 0, duda="oferta_externa", elecciones=elecciones).status_code == 422


# ------------------------------------------------------------------ por qué te tocó la carta
def test_la_duda_elegida_se_dice_elegida(client):
    assert _ok(client, duda="oferta_externa")["pendiente"]["por_que"] == {"tipo": "elegida"}


def test_sin_duda_la_primera_carta_es_un_sorteo_con_su_probabilidad(client):
    for semilla in range(5):
        por_que = _ok(client, semilla=semilla)["pendiente"]["por_que"]
        if "prob" in por_que:  # una oferta que llegó por su evento, con su probabilidad
            assert por_que["tipo"] == "llega" and 0 < por_que["prob"] <= 1 and por_que["posibles"] >= 1
        else:
            assert por_que["tipo"] in {"obligada", "consecuencia", "llega", "buscada", "tranquilo"}


def test_cada_carta_dice_por_que_te_toco(client):
    _, _, vistas = _jugar_entera(client, lambda p: p["opciones"][-1], duda=DUDA)
    tipos = {v["pendiente"]["por_que"]["tipo"] for v in vistas if v["pendiente"]}
    assert tipos <= {"elegida", "llega", "buscada", "tranquilo", "obligada", "consecuencia"} and "elegida" in tipos


# ── lo que llega mal se rechaza con un 422 que dice qué (antes: 500 o 200 en silencio) ──────


def _detalle(r) -> str:
    assert r.status_code == 422, r.text
    return str(r.json()["detail"])


@pytest.mark.parametrize("numero", ["Infinity", "-Infinity", "NaN", "1e300"])
def test_ahorro_infinito_o_absurdo_da_422(client, numero):
    r = client.post("/api/juego/partida", content=f'{{"perfil": {{"ahorro": {numero}}}, "gemelos": 0}}',
                    headers={"content-type": "application/json"})
    assert "ahorro" in _detalle(r)
    assert _partida(client, perfil={"ahorro": -2_000_000}, duda=DUDA).status_code == 200  # una deuda sí


def test_rubros_fuera_del_paquete_dan_422(client):
    assert "Criptomonedas" in _detalle(_partida(client, perfil={"rubro": "Criptomonedas"}, duda=DUDA))
    assert "Criptomonedas" in _detalle(_partida(client, perfil={"rubro_sonado": "Criptomonedas"}, duda=DUDA))
    assert _partida(client, perfil={"rubro_sonado": "Salud"}, duda=DUDA).status_code == 200
    assert _partida(client, perfil={"rubro_sonado": None}, duda=DUDA).status_code == 200


def test_parametros_fuera_del_dominio_dan_422(client):
    duda = "cambiar_de_rubro"
    # la opción no existe, la variable no se elige, o el valor no es una alternativa
    assert "'zzz' no es una opción" in _detalle(_partida(client, duda=duda, parametros={"zzz": {}}))
    assert "'nope'" in _detalle(_partida(client, duda=duda, parametros={"cambiar": {"nope": "x"}}))
    assert "no es una alternativa de rubro_destino" in _detalle(
        _partida(client, duda=duda, parametros={"cambiar": {"rubro_destino": "Criptomonedas"}}))
    eleccion = {"decision": duda, "opcion": "cambiar", "parametros": {"rubro_destino": "Criptomonedas"}}
    assert "rubro_destino" in _detalle(_partida(client, duda=duda, elecciones=[eleccion]))
    # una alternativa que ofrece la carta sí sirve
    pendiente = _ok(client, duda=duda)["pendiente"]
    cambiar = next(o for o in pendiente["opciones"] if o["opcion"] == "cambiar")
    valor = cambiar["elecciones_internas"][0]["alternativas"][-1]["valor"]
    assert _partida(client, duda=duda, parametros={"cambiar": {"rubro_destino": valor}}).status_code == 200


def test_un_mundo_mas_alla_de_los_gemelos_da_422(client):
    r = client.post("/api/juego/mundo", json={"duda": DUDA, "gemelos": N, "mundo": N})
    assert f"del 0 al {N - 1}" in _detalle(r)
    assert client.post("/api/juego/mundo", json={"duda": DUDA, "gemelos": N, "mundo": N - 1}).status_code == 200
