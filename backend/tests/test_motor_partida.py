"""La partida de la persona (`partida.py`) y la comparación con sus gemelos (`gemelos.py`)."""

from statistics import median

import pytest
from _motor_util import CARTAS_PERFIL_BASE, Guion, foto, n, vida, z_binomial

from app.sim.motor import gemelos, partida
from app.sim.motor.azar import Dados
from app.sim.motor.motor import FaltaEleccion
from app.sim.motor.perfil import Perfil
from app.sim.motor.politicas import Jugador

Z = 3.5
CESANTE = Perfil(edad=35, estado="buscando", sueldo=1_000_000)


def _jugar_entera(perfil=Perfil(), semilla=3, duda=None, elegir=lambda opciones: opciones[-1].id, anios=10):
    """Juega hasta el final respondiendo cada decisión pendiente. Devuelve (elecciones, partida)."""
    elecciones: list[dict] = []
    for _ in range(200):
        p = partida.jugar(perfil, semilla, elecciones, duda, anios)
        if p.terminada:
            return elecciones, p
        elecciones = [*elecciones, {"decision": p.pendiente.decision["id"], "opcion": elegir(p.pendiente.opciones)}]
    raise AssertionError("la partida no termina")


# ------------------------------------------------------------------ partida
def test_la_misma_partida_da_exactamente_lo_mismo():
    for semilla in (0, 3, 17):
        elecciones, p = _jugar_entera(semilla=semilla)
        otra = partida.jugar(Perfil(), semilla, elecciones)
        assert otra.terminada and otra.vida.historia == p.vida.historia and otra.vida.e == p.vida.e
        assert otra.vida.ingreso_total == p.vida.ingreso_total
    assert partida.jugar(Perfil(), 4, []).vida.registro != partida.jugar(Perfil(), 3, []).vida.registro or \
        partida.jugar(Perfil(), 4, []).pendiente.decision["id"] != partida.jugar(Perfil(), 3, []).pendiente.decision["id"]


def test_la_partida_dura_los_anios_pedidos_y_cierra():
    elecciones, p = _jugar_entera()
    assert p.terminada and p.pendiente is None and p.anios == 10
    assert p.vida.anio == 10 and len(p.vida.historia) == 10 and p.vida.e["edad"] == 40
    assert [r["anio"] for r in p.vida.historia] == list(range(1, 11))
    assert len(elecciones) >= 10  # una persona empleada recibe al menos una carta por año
    corta = _jugar_entera(anios=3)[1]
    assert corta.vida.anio == 3 and corta.terminada


def test_cada_eleccion_continua_la_misma_historia():
    """Volver a jugar con una elección más no cambia nada de lo ya vivido (los dados son por sitio)."""
    elecciones, completa = _jugar_entera(semilla=5)
    anios_cerrados = -1
    for k in range(len(elecciones)):
        p = partida.jugar(Perfil(), 5, elecciones[:k])
        assert not p.terminada and p.pendiente.decision["id"] == elecciones[k]["decision"]
        assert p.vida.historia == completa.vida.historia[:len(p.vida.historia)]
        assert len(p.vida.historia) >= anios_cerrados
        anios_cerrados = len(p.vida.historia)
        # lo ya decidido en el año en curso también coincide
        ya = [d["decision"] for d in p.vida.registro["decisiones"]]
        assert ya == [d["decision"] for d in completa.vida.historia[p.vida.anio]["decisiones"]][:len(ya)]


def test_elecciones_de_mas_dan_un_error_claro():
    elecciones, _ = _jugar_entera()
    with pytest.raises(ValueError, match="sobran elecciones"):
        partida.jugar(Perfil(), 3, [*elecciones, {"opcion": "no"}])


def test_eleccion_para_otra_decision_da_un_error_claro():
    pendiente = partida.jugar(Perfil(), 3, []).pendiente.decision["id"]
    otra = "renunciar" if pendiente != "renunciar" else "pedir_aumento"
    with pytest.raises(ValueError, match=f"{otra}.*{pendiente}"):
        partida.jugar(Perfil(), 3, [{"decision": otra, "opcion": "no"}])


def test_opcion_que_no_existe_o_no_esta_disponible_da_un_error_claro():
    with pytest.raises(ValueError, match="inventada"):
        partida.jugar(Perfil(), 3, [{"opcion": "inventada"}])
    # magíster vespertino pide estar empleada
    with pytest.raises(ValueError, match="vespertino"):
        partida.jugar(CESANTE, 3, [{"decision": "magister", "opcion": "vespertino"}], duda="magister")


def test_la_duda_inicial_es_la_primera_decision_y_solo_del_primer_anio():
    p = partida.jugar(Perfil(), 3, [], duda="pedir_aumento")
    assert p.pendiente.decision["id"] == "pedir_aumento" and p.vida.anio == 0
    assert [o.id for o in p.pendiente.opciones] == ["pedir", "esperar"]
    elecciones, completa = _jugar_entera(duda="pedir_aumento")
    assert elecciones[0]["decision"] == "pedir_aumento"
    de_carta = [d["decision"] for r in completa.vida.historia for d in r["decisiones"] if d["origen"] == "carta"]
    assert de_carta[0] == "pedir_aumento" and len(de_carta) <= 10
    assert "pedir_aumento" not in de_carta[1:]  # la duda es solo la carta del primer año; después se sortea
    with pytest.raises(ValueError, match="no aplica"):
        partida.jugar(Perfil(nivel=1), 3, [], duda="jefatura")  # pide nivel 2
    with pytest.raises(ValueError, match="no aplica"):
        partida.jugar(Perfil(), 3, [], duda="tipo_de_empleador")  # interna: nunca se ofrece


def test_dudas_posibles_son_las_cartas_del_perfil():
    dudas = partida.dudas_posibles(Perfil())
    assert {d["decision"] for d in dudas} == set(CARTAS_PERFIL_BASE)
    assert all(set(d) == {"decision", "nombre", "pregunta", "categoria", "calidad"} for d in dudas)
    assert "cesantia" not in {d["decision"] for d in partida.dudas_posibles(CESANTE)}  # forzada: no es una duda


def test_el_jugador_responde_en_orden_y_se_detiene_cuando_no_le_quedan_respuestas():
    v = vida(Perfil(), Dados(3, "tu"))
    jugador = Jugador([{"opcion": "no_importa"}])
    with pytest.raises(ValueError):
        v.vivir_anio(jugador)
    assert jugador.usadas == 1
    with pytest.raises(FaltaEleccion):
        vida(Perfil(), Dados(3, "tu")).vivir_anio(Jugador([]))


# ------------------------------------------------------------------ vista
CLAVES_VISTA = {"terminada", "anio", "anios", "edad_final", "semilla", "duda", "elecciones", "estado", "historia",
                "anio_en_curso", "pendiente", "cierre"}
CLAVES_ESTADO = {"edad", "estado", "sueldo", "sueldo_ref", "nivel", "cargo", "tipo_empleador", "rubro", "edu",
                 "ocupacion", "antiguedad", "ahorro", "percentil", "exposicion_ia"}
CLAVES_OPCION_COMPARADA = {"opcion", "nombre", "detalle", "calidad", "es_base", "sueldo", "ingreso_total",
                           "paso_por_cesantia", "meses_sin_trabajo", "sin_trabajo_al_final", "cargo_mas_probable", "sube_de_cargo",
                           "cargos", "gana_mas_que_base", "igual_que_base", "gana_menos_que_base",
                           "diferencia_tipica", "parametros", "por_resultado", "trayectoria"}


def test_vista_con_decision_pendiente():
    v = partida.vista(Perfil(), semilla=3, duda="unirse_a_startup", n_gemelos=n(40))
    assert set(v) >= CLAVES_VISTA and set(v["estado"]) >= CLAVES_ESTADO
    assert v["edad_final"] == 40
    assert (v["terminada"], v["anio"], v["anios"], v["semilla"], v["duda"]) == (False, 0, 10, 3, "unirse_a_startup")
    assert v["cierre"] is None and v["historia"] == [] and v["elecciones"] == []
    assert set(v["anio_en_curso"]) == {"anio", "edad", "recesion", "decisiones", "eventos"}
    assert (v["anio_en_curso"]["anio"], v["anio_en_curso"]["edad"]) == (1, 30)
    assert (v["estado"]["edad"], v["estado"]["estado"], v["estado"]["sueldo"], v["estado"]["cargo"]) == (
        30, "empleado", 1_400_000, "Semi senior")
    p = v["pendiente"]
    assert set(p) == {"decision", "nombre", "pregunta", "categoria", "calidad", "creencia_vs_dato", "evidencia", "narrativa",
                      "opciones", "comparacion", "por_que", "oferta_sueldo"}
    assert p["decision"] == "unirse_a_startup" and [o["opcion"] for o in p["opciones"]] == ["ir", "quedarse"]
    assert all(set(o) == {"opcion", "nombre", "detalle", "calidad", "respaldo", "elecciones_internas", "empresa"} for o in p["opciones"])
    c = p["comparacion"]
    assert c["decision"] == "unirse_a_startup" and c["gemelos"] == n(40) and c["anios"] == 10 and c["base"] == "quedarse"
    assert [o["opcion"] for o in c["opciones"]] == ["ir", "quedarse"]
    assert all(set(o) >= CLAVES_OPCION_COMPARADA and "sueldos" not in o for o in c["opciones"])  # sin los crudos


def test_vista_sin_gemelos_y_con_demasiadas_opciones_no_compara():
    assert partida.vista(Perfil(), semilla=3, duda="unirse_a_startup", n_gemelos=0)["pendiente"]["comparacion"] is None
    v = partida.vista(Perfil.a_los_18(), semilla=3, n_gemelos=5, elecciones=[{"opcion": "universidad"}])
    assert v["pendiente"]["decision"] == "elegir_carrera" and len(v["pendiente"]["opciones"]) > 50
    assert v["pendiente"]["comparacion"] is None  # cientos de carreras: ahí no se simulan gemelos


def test_vista_muestra_lo_que_se_elige_dentro_de_una_opcion():
    v = partida.vista(Perfil(), semilla=3, duda="cambiar_de_rubro", n_gemelos=0)
    internas = {o["opcion"]: o["elecciones_internas"] for o in v["pendiente"]["opciones"]}
    assert internas["no"] == []
    (rubro,) = internas["cambiar"]
    assert rubro["variable"] == "rubro_destino"
    valores = [a["valor"] for a in rubro["alternativas"]]
    assert "Servicios profesionales" not in valores and "" not in valores and "Minería" in valores  # no el propio
    # y la elección de la persona se usa
    p = partida.jugar(Perfil(), 3, [{"opcion": "cambiar", "parametros": {"rubro_destino": "Salud"}}],
                      duda="cambiar_de_rubro")
    registro = p.vida.historia[0] if p.vida.historia else p.vida.registro
    resultado = registro["decisiones"][0]["resultado"]
    assert p.vida.e["rubro_destino"] == "Salud"
    assert (p.vida.e["rubro"] == "Salud") == (resultado == "entra")


def test_vista_al_cierre():
    elecciones, p = _jugar_entera(duda="unirse_a_startup", elegir=lambda opciones: opciones[0].id if
                                  opciones[0].id == "ir" else opciones[-1].id)
    v = partida.vista(Perfil(), semilla=3, duda="unirse_a_startup", elecciones=elecciones, n_gemelos=n(60))
    assert set(v) >= CLAVES_VISTA
    assert v["terminada"] is True and v["pendiente"] is None and v["anio"] == 10 and v["anio_en_curso"] is None
    sin_historia = [{**a, "decisiones": [{k: x for k, x in d.items() if k != "narrativa"} for d in a["decisiones"]]}
                    for a in v["historia"]]
    assert len(v["historia"]) == 10 and sin_historia == p.vida.historia and v["estado"] == p.vida.resumen()
    c = v["cierre"]
    assert set(c) == {"sueldo_final", "estado", "anios_sin_trabajo", "primera_decision", "mejor_que_gemelos"}
    assert c["estado"] == v["estado"] and c["anios_sin_trabajo"] == p.vida.anios_buscando
    assert c["sueldo_final"] == round(p.vida.e["sueldo"] or p.vida.e["sueldo_ref"])
    primera = c["primera_decision"]
    assert (primera["decision"], primera["elegida"]) == ("unirse_a_startup", "ir")
    comparacion = primera["comparacion"]
    assert comparacion["gemelos"] == n(60) and all("sueldos" not in o for o in comparacion["opciones"])
    assert 0.0 <= c["mejor_que_gemelos"] <= 1.0
    # mejor_que_gemelos: parte de los gemelos que eligieron lo mismo y terminaron con menos sueldo. Se compara lo
    # que ganas al final (0 si terminas sin trabajo), no el último sueldo que muestra el cierre
    detenida = partida.jugar(Perfil(), 3, [], duda="unirse_a_startup").vida  # el punto en que se decidió
    cruda = gemelos.comparar(detenida, "unirse_a_startup", n=n(60), semilla=3, crudo=True)
    sueldos = next(o["sueldos"] for o in cruda["opciones"] if o["opcion"] == "ir")
    assert c["mejor_que_gemelos"] == pytest.approx(sum(1 for s in sueldos if s < c["estado"]["sueldo"]) / n(60))


def test_vista_al_cierre_sin_elecciones_no_inventa_comparacion():
    inactiva = Perfil(estado="inactivo", edad=40)
    v = partida.vista(inactiva, semilla=1, elecciones=[], n_gemelos=5, anios=1)
    if v["terminada"]:
        assert v["cierre"]["primera_decision"] is None and "mejor_que_gemelos" not in v["cierre"]


# ------------------------------------------------------------------ gemelos
def _al_inicio(perfil=Perfil(edad=35), **estado):
    return vida(perfil, Dados(0, "tu"), **estado)


def _detenida(decision="unirse_a_startup"):
    p = partida.jugar(Perfil(edad=35), 0, [], duda=decision)
    assert p.vida.cola and p.pendiente.decision["id"] == decision
    return p.vida


@pytest.mark.parametrize("fabricar", [_al_inicio, _detenida], ids=["inicio de año", "detenida a mitad de año"])
def test_comparar_no_modifica_la_vida_que_recibe(fabricar):
    v = fabricar()
    antes = foto(v)
    gemelos.comparar(v, "unirse_a_startup", n=n(25), anios=3, semilla=1)
    assert foto(v) == antes


def test_comparar_misma_semilla_mismo_resultado():
    v = _al_inicio()
    a = gemelos.comparar(v, "unirse_a_startup", n=n(40), anios=4, semilla=7, crudo=True)
    b = gemelos.comparar(v, "unirse_a_startup", n=n(40), anios=4, semilla=7, crudo=True)
    c = gemelos.comparar(v, "unirse_a_startup", n=n(40), anios=4, semilla=8, crudo=True)
    assert a == b
    assert a["opciones"][0]["sueldos"] != c["opciones"][0]["sueldos"]
    # los dados de los gemelos no son los de la vida que se compara
    otra = vida(Perfil(edad=35), Dados(99, "otra persona"))
    assert gemelos.comparar(otra, "unirse_a_startup", n=n(40), anios=4, semilla=7, crudo=True) == a


def test_comparar_forma_y_coherencia_interna():
    m, anios = n(60), 5
    c = gemelos.comparar(_al_inicio(), "unirse_a_startup", n=m, anios=anios, semilla=2, crudo=True)
    assert (c["decision"], c["gemelos"], c["anios"], c["base"]) == ("unirse_a_startup", m, anios, "quedarse")
    assert [o["es_base"] for o in c["opciones"]] == [False, True]
    for o in c["opciones"]:
        assert set(o) >= CLAVES_OPCION_COMPARADA | {"sueldos"}
        assert len(o["sueldos"]) == m and o["sueldos"] == sorted(o["sueldos"])
        assert o["sueldo"]["p10"] <= o["sueldo"]["p50"] <= o["sueldo"]["p90"]
        assert o["sueldo"]["p50"] == pytest.approx(median(o["sueldos"]), abs=1)
        for clave, q in (("p10", 0.1), ("p90", 0.9)):  # percentil por interpolación lineal, a mano
            pos = (m - 1) * q
            abajo = o["sueldos"][int(pos)]
            arriba = o["sueldos"][min(m - 1, int(pos) + 1)]
            assert o["sueldo"][clave] == pytest.approx(abajo + (arriba - abajo) * (pos - int(pos)), abs=2)
        assert sum(r["gemelos"] for r in o["por_resultado"]) == m
        assert sum(r["prob"] for r in o["por_resultado"]) == pytest.approx(1)
        assert sum(x["prob"] for x in o["cargos"]) == pytest.approx(1)
        assert o["cargo_mas_probable"] == max(o["cargos"], key=lambda x: x["prob"])["cargo"]
        assert 0 <= o["sube_de_cargo"] <= 1
        assert len(o["trayectoria"]) == anios
        assert [t["edad"] for t in o["trayectoria"]] == [36 + i for i in range(anios)]
        assert all(set(t) == {"edad", "p10", "p50", "p90", "sin_trabajo"} for t in o["trayectoria"])
        assert 0 <= o["sin_trabajo_al_final"] <= o["paso_por_cesantia"] <= 1
        assert o["meses_sin_trabajo"] >= 12 * o["paso_por_cesantia"] - 1e-9
        assert o["trayectoria"][-1]["sin_trabajo"] == pytest.approx(o["sin_trabajo_al_final"])
        assert o["trayectoria"][-1]["p50"] == o["sueldo"]["p50"]
        assert o["ingreso_total"]["p50"] > 0
    ir, quedarse = c["opciones"]
    assert quedarse["gana_mas_que_base"] is None and 0 <= ir["gana_mas_que_base"] <= 1
    assert {r["resultado"] for r in ir["por_resultado"]} <= {"crece", "cierra", "sigue"}
    assert [r["resultado"] for r in quedarse["por_resultado"]] == ["queda"]
    assert all(r["gana_mas_que_base"] is None for r in quedarse["por_resultado"])
    assert ir["gana_mas_que_base"] + ir["igual_que_base"] + ir["gana_menos_que_base"] == pytest.approx(1)
    # los que ganan en cada resultado, ponderados por cuántos son, dan el total de la opción
    assert sum(r["gana_mas_que_base"] * r["gemelos"] for r in ir["por_resultado"]) == pytest.approx(
        ir["gana_mas_que_base"] * m)


def test_comparar_reparte_los_resultados_segun_las_probabilidades_del_paquete():
    """unirse_a_startup/ir: 0,242 adquirida, 0,299 cierra, el resto sigue (literal del paquete)."""
    m = n(1500)
    c = gemelos.comparar(_al_inicio(), "unirse_a_startup", n=m, anios=1, semilla=5)
    por = {r["resultado"]: r for r in c["opciones"][0]["por_resultado"]}
    for resultado, p in (("crece", 0.242), ("cierra", 0.299), ("sigue", 1 - 0.242 - 0.299)):
        assert abs(z_binomial(por[resultado]["gemelos"], m, p)) < Z, resultado
        assert por[resultado]["prob"] == por[resultado]["gemelos"] / m
        assert por[resultado]["texto"] and por[resultado]["tono"] in ("bueno", "malo", "neutro")


def test_gana_mas_que_base_sigue_al_resultado_de_cada_gemelo():
    """Pedir aumento: a quien le dicen que no, termina igual que su versión que no pidió; a quien
    le dicen que sí, casi siempre termina arriba (mismos dados después, sueldo 4% a 10% mayor).
    Que los del no queden todos iguales prueba que la comparación es gemelo a gemelo: contra otro
    gemelo, o contra la lista ordenada, cerca de la mitad ganaría."""
    m = n(200)
    c = gemelos.comparar(_al_inicio(Perfil(edad=35, sexo="m")), "pedir_aumento", n=m, anios=5, semilla=4)
    pedir, esperar = c["opciones"]
    assert c["base"] == "esperar" and esperar["gana_mas_que_base"] is None
    por = {r["resultado"]: r for r in pedir["por_resultado"]}
    assert (por["no"]["gana_mas_que_base"], por["no"]["igual_que_base"]) == (0.0, 1.0)
    assert por["si"]["gana_mas_que_base"] >= 0.9 and por["si"]["diferencia_tipica"] > 0
    assert pedir["gana_mas_que_base"] == pytest.approx(por["si"]["gana_mas_que_base"] * por["si"]["gemelos"] / m)
    assert abs(z_binomial(por["si"]["gemelos"], m, 0.20)) < Z  # P_AUMENTO_PEDIDO de una mujer


def test_comparar_mide_desde_el_punto_de_partida_de_la_vida():
    """Los años sin trabajo y el ingreso que la vida ya traía no cuentan para los gemelos."""
    limpia = _al_inicio()
    con_pasado = _al_inicio()
    con_pasado.anios_buscando = 4
    con_pasado.ingreso_total = 500_000_000.0
    a = gemelos.comparar(limpia, "renunciar", n=n(60), anios=3, semilla=6)
    b = gemelos.comparar(con_pasado, "renunciar", n=n(60), anios=3, semilla=6)
    assert a == b
    renunciar, aguantar = a["opciones"]
    assert renunciar["paso_por_cesantia"] == 1.0 and renunciar["meses_sin_trabajo"] >= 12
    assert aguantar["paso_por_cesantia"] < 0.5
    assert renunciar["ingreso_total"]["p50"] < aguantar["ingreso_total"]["p50"]
    assert renunciar["trayectoria"][0]["sin_trabajo"] == 1.0


def test_comparar_desde_una_vida_detenida_usa_el_anio_en_curso():
    """Detenida a mitad de año: los gemelos terminan ese año (no empiezan otro) y viven `anios` en total."""
    v = _detenida("renunciar")
    c = gemelos.comparar(v, "renunciar", n=n(40), anios=3, semilla=6)
    renunciar = c["opciones"][0]
    assert len(renunciar["trayectoria"]) == 3 and renunciar["trayectoria"][0]["edad"] == 36
    assert renunciar["trayectoria"][0]["sin_trabajo"] == 1.0
    assert [r["resultado"] for r in renunciar["por_resultado"]] == ["renuncia"]


def test_comparar_desde_una_vida_con_historia_mira_el_anio_de_la_decision():
    v = _al_inicio()
    for _ in range(2):
        v.vivir_anio(Guion({"oferta_externa": "quedarse", "cesantia": "nivel"}))
    assert v.e["estado"] == "empleado" and len(v.historia) == 2
    c = gemelos.comparar(v, "pedir_aumento", n=n(60), anios=2, semilla=1)
    pedir = c["opciones"][0]
    assert {r["resultado"] for r in pedir["por_resultado"]} == {"si", "no"}
    assert [t["edad"] for t in pedir["trayectoria"]] == [38, 39]


def test_los_dados_de_la_persona_no_son_los_de_ningun_gemelo():
    p = partida.jugar(Perfil(), 3, [])
    assert p.vida.dados.semilla == 3 and not isinstance(p.vida.dados.gemelo, int)
    assert Dados(3, p.vida.dados.gemelo).u(0, "carta") not in {Dados(3, g).u(0, "carta") for g in range(2000)}


def test_el_cierre_compara_con_los_gemelos_del_momento_de_la_primera_decision():
    for semilla in range(6):
        primera = partida.jugar(Perfil(), semilla, [], duda="pedir_aumento")
        elecciones, _ = _jugar_entera(semilla=semilla, duda="pedir_aumento")
        cierre = partida.vista(Perfil(), semilla=semilla, duda="pedir_aumento", elecciones=elecciones,
                               n_gemelos=n(12))["cierre"]
        esperada = gemelos.comparar(primera.vida, "pedir_aumento", n=n(12), semilla=semilla)
        assert cierre["primera_decision"]["comparacion"] == esperada


def test_comparar_usa_los_parametros_de_cada_opcion():
    """Cambiarse a Minería paga más que cambiarse a Hoteles y restaurantes (ESI, mediana por rubro)."""
    def mediana(rubro):
        c = gemelos.comparar(_al_inicio(), "cambiar_de_rubro", n=n(80), anios=1, semilla=2,
                             parametros={"cambiar": {"rubro_destino": rubro}})
        cambiar = c["opciones"][0]
        assert cambiar["opcion"] == "cambiar" and {r["resultado"] for r in cambiar["por_resultado"]} == {"entra", "nada"}
        return cambiar["sueldo"]["p90"]
    assert mediana("Minería") > mediana("Hoteles y restaurantes")


def test_la_base_de_comparacion():
    assert gemelos.comparar(_al_inicio(), "oferta_externa", n=3, anios=1)["base"] == "quedarse"
    assert gemelos.comparar(_al_inicio(), "magister", n=3, anios=1)["base"] == "no"
    assert gemelos.comparar(_al_inicio(), "pedir_aumento", n=3, anios=1)["base"] == "esperar"
    cesante = gemelos.comparar(vida(CESANTE, Dados(0, "tu"), tipo_empleador="pyme"), "cesantia", n=3, anios=1)
    assert [o["es_base"] for o in cesante["opciones"]].count(True) == 1
    assert cesante["base"] != "emprender"  # en una forzada la base no es la última opción de la lista


def test_comparar_pendiente_solo_compara_cuando_tiene_sentido():
    en_curso = partida.jugar(Perfil(), 3, [], duda="unirse_a_startup")
    assert partida.comparar_pendiente(en_curso, 3, n=0) is None
    assert partida.comparar_pendiente(en_curso, 3, n=4)["gemelos"] == 4
    carrera = partida.jugar(Perfil.a_los_18(), 3, [{"opcion": "universidad"}])
    assert carrera.pendiente.decision["id"] == "elegir_carrera"
    assert partida.comparar_pendiente(carrera, 3, n=4) is None  # demasiadas opciones
    terminada = _jugar_entera(anios=1)[1]
    assert partida.comparar_pendiente(terminada, 3, n=4) is None


# ── historia de las cartas ────────────────────────────────────────────────────

def test_cada_carta_trae_su_historia_y_tu_empresa_no_cambia():
    from app.sim.motor.partida import vista
    from app.sim.motor.perfil import Perfil

    perfil = Perfil(edad=33, rubro="Finanzas y seguros", tipo_empleador="startup", nivel=2, sueldo=2_624_000)
    elecciones, propias = [], set()
    v = vista(perfil, 4, "oferta_externa", elecciones, n_gemelos=0)
    primera = v["pendiente"]["narrativa"]["situacion"]
    oferta = next(o["empresa"] for o in v["pendiente"]["opciones"] if o["empresa"])
    # la historia nombra la misma empresa del catálogo que muestra la carta
    assert oferta["nombre"] in primera and "$" not in primera and "%" not in primera
    while not v["terminada"]:
        pendiente = v["pendiente"]
        texto = (pendiente["narrativa"] or {}).get("situacion", "")
        for nombre in ("Kuota", "Cuentaclara"):
            if f"En {nombre} " in texto or f"desempeño en {nombre}" in texto:
                propias.add(nombre)
        elecciones.append({"opcion": pendiente["opciones"][-1]["opcion"]})
        v = vista(perfil, 4, "oferta_externa", elecciones, n_gemelos=0)
    assert len(propias) <= 1, f"tu empresa cambió de nombre sin cambiarte de trabajo: {propias}"
    # la historia queda también en lo ya vivido, igual a la que se mostró
    assert v["historia"][0]["decisiones"][0]["narrativa"]["situacion"] == primera


def test_la_historia_no_mueve_los_numeros():
    from app.sim.motor.partida import vista
    from app.sim.motor.perfil import Perfil

    con = vista(Perfil(), 3, "oferta_externa", [{"opcion": "cambiar"}], n_gemelos=0)
    for a in con["historia"]:
        for d in a["decisiones"]:
            d.pop("narrativa", None)
    import app.sim.motor.partida as partida
    original = partida.narrar
    partida.narrar = lambda *a, **k: None
    try:
        sin = vista(Perfil(), 3, "oferta_externa", [{"opcion": "cambiar"}], n_gemelos=0)
    finally:
        partida.narrar = original
    for a in sin["historia"]:
        for d in a["decisiones"]:
            d.pop("narrativa", None)
    assert [a["fin"] for a in con["historia"]] == [a["fin"] for a in sin["historia"]]


def test_terminar_sin_trabajo_cuenta_cero_en_la_comparacion():
    """Antes, una copia que terminaba cesante contaba con su último sueldo y empataba con una que seguía
    empleada. Ahora cuenta lo que gana al final: 0."""
    c = gemelos.comparar(_al_inicio(), "unirse_a_startup", n=n(60), anios=5, semilla=2, crudo=True)
    for o in c["opciones"]:
        sin_trabajo = round(o["sin_trabajo_al_final"] * len(o["sueldos"]))
        assert sum(1 for s in o["sueldos"] if s == 0) >= sin_trabajo
