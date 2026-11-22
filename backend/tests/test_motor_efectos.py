"""Semántica de los efectos y del sorteo de resultados (`Vida._aplicar`, `_sortear`, `_decidir`).

Dos laboratorios:
- efectos sintéticos aplicados a una persona inactiva (a quien el año no le mueve nada más),
  para ver cada regla aislada: valores leídos antes del resultado, `cuando`, duración, dominio;
- una decisión de laboratorio agregada a una copia del paquete, para recorrer el camino real
  (costo, dado del resultado, `luego`) con probabilidades elegidas a mano.
Y un caso literal del paquete: `separacion_empleo/cesante`.
"""

import math

import pytest
from _motor_util import NADA, DadosGuion, Guion, pq, vida

from app.sim.motor.azar import Dados
from app.sim.motor.motor import Vida
from app.sim.motor.paquete import Paquete
from app.sim.motor.perfil import Perfil, estado_inicial

INACTIVA = Perfil(estado="inactivo", edad=40, sueldo=1_000_000)


def _lab(**estado):
    """Persona inactiva con el año abierto y sin recesión: nada más toca su estado."""
    v = vida(INACTIVA, DadosGuion(), **estado)
    v.iniciar_anio(con_cartas=False)
    return v


def _cerrar(v):
    return v.avanzar(Guion()) if v.cola else v.vivir_anio(Guion())


# ------------------------------------------------------------------ valores, orden y cuando
def test_los_valores_se_leen_del_estado_de_antes_del_resultado():
    v = _lab(red=30, skill=50)
    v._aplicar([
        {"var": "sueldo_ref", "op": "fija", "valor": "red * 2"},
        {"var": "red", "op": "fija", "valor": 0},
        {"var": "skill", "op": "fija", "valor": "red"},          # red de antes (30), no 0
        {"var": "ahorro", "op": "fija", "valor": "red + skill"},  # 30 + 50 de antes
    ], "lab")
    assert (v.e["sueldo_ref"], v.e["red"], v.e["skill"], v.e["ahorro"]) == (60, 0, 30, 80)


def test_las_operaciones_se_encadenan_sobre_el_valor_que_va_quedando():
    v = _lab(red=30)
    v._aplicar([
        {"var": "red", "op": "fija", "valor": "red + 10"},   # 40
        {"var": "red", "op": "multiplica", "valor": 2},      # 80, no 60
        {"var": "red", "op": "suma", "valor": "red / 10"},   # + 3 (red de antes), 83
    ], "lab")
    assert v.e["red"] == 83


def test_cuando_de_un_efecto_se_evalua_antes_del_resultado_y_filtra_solo_ese_efecto():
    v = _lab(red=30, skill=50, animo=60)
    v._aplicar([
        {"var": "red", "op": "fija", "valor": 99},
        {"var": "skill", "op": "suma", "valor": 5, "cuando": "red < 50"},    # se cumple con la red de antes
        {"var": "animo", "op": "suma", "valor": 5, "cuando": "red > 50"},    # no se cumple
        {"var": "energia", "op": "fija", "valor": 11, "cuando": "edad == 40"},
    ], "lab")
    assert (v.e["red"], v.e["skill"], v.e["animo"], v.e["energia"]) == (99, 55, 60, 11)


def test_un_efecto_que_no_se_aplica_no_deja_nada_que_revertir():
    v = _lab(red=30)
    antes = len(v.temporales)
    v._aplicar([{"var": "red", "op": "suma", "valor": 10, "duracion": 1, "cuando": "red > 50"}], "lab")
    assert len(v.temporales) == antes
    _cerrar(v)
    assert v.e["red"] == 30


# ------------------------------------------------------------------ dominio
@pytest.mark.parametrize(("var", "op", "valor", "esperado"), [
    ("red", "suma", 500, 100), ("red", "suma", -500, 0), ("nivel", "fija", 9, 4), ("nivel", "suma", -3, 0),
    ("sueldo_ref", "suma", -5_000_000_000, 0), ("sueldo_ref", "fija", 99_000_000, 30_000_000),
    ("ahorro", "suma", -900_000_000, -100_000_000), ("tasa_ahorro", "fija", 0.9, 0.5),
    ("p_encontrar", "multiplica", 50, 2), ("edad", "suma", 40, 60), ("hijos", "suma", 10, 6),
    ("marcado", "fija", 7, 1), ("alza_extra_anual", "suma", 0.2, 0.05),
])
def test_los_efectos_se_acotan_al_dominio_de_la_variable(var, op, valor, esperado):
    v = _lab()
    v._aplicar([{"var": var, "op": op, "valor": valor}], "lab")
    assert v.e[var] == esperado


def test_enteros_quedan_enteros_y_categorias_no_se_tocan():
    v = _lab(semestres_restantes=4, hijos=1)
    v._aplicar([
        {"var": "semestres_restantes", "op": "suma", "valor": 1.4},
        {"var": "hijos", "op": "multiplica", "valor": 2.6},
        {"var": "pais", "op": "fija", "valor": "'afuera'"},
        {"var": "rubro_destino", "op": "fija", "valor": "'Minería'"},
        {"var": "animo", "op": "suma", "valor": 0.25},
    ], "lab")
    assert v.e["semestres_restantes"] == 5 and type(v.e["semestres_restantes"]) is int
    assert v.e["hijos"] == 3 and type(v.e["hijos"]) is int
    assert v.e["pais"] == "afuera" and v.e["rubro_destino"] == "Minería"
    assert v.e["animo"] == pytest.approx(64.25)  # los números no se redondean


# ------------------------------------------------------------------ derivadas
def test_las_variables_derivadas_no_se_pisan_y_se_recalculan():
    v = vida(Perfil(edad=29, nivel=1), DadosGuion())
    v.iniciar_anio(con_cartas=False)
    antes = {k: v.e[k] for k in ("prob_ascenso", "percentil", "banda3", "banda7", "quintil", "seniority")}
    temporales = len(v.temporales)
    v._aplicar([
        {"var": "prob_ascenso", "op": "multiplica", "valor": 0.5},
        {"var": "prob_ascenso", "op": "fija", "valor": 0.4, "duracion": 2},
        {"var": "percentil", "op": "fija", "valor": 1},
        {"var": "banda3", "op": "fija", "valor": "'45-59'"},
        {"var": "seniority", "op": "fija", "valor": "'Expert'"},
    ], "lab")
    assert {k: v.e[k] for k in antes} == antes
    assert len(v.temporales) == temporales  # una derivada con duración no deja nada que revertir
    # y si cambia de qué dependen, cambian en el momento (no al año siguiente)
    v._aplicar([{"var": "edad", "op": "suma", "valor": 1}, {"var": "nivel", "op": "fija", "valor": 4},
                {"var": "sueldo", "op": "multiplica", "valor": 3}], "lab")
    assert v.e["banda3"] == "30-44" and v.e["banda7"] == "30-34" and v.e["seniority"] == "Expert"
    assert v.e["prob_ascenso"] == 0.0  # el ascenso pide nivel < 4
    assert v.e["percentil"] > antes["percentil"]


def test_prob_ascenso_derivada_es_la_del_evento_ascenso():
    """Literal del paquete: ASCENSO[1] = 0,08 con oficio 50; +0,0006 por punto de oficio;
    0 si el evento no aplica (sin antigüedad, o sin empleo)."""
    assert vida(Perfil(nivel=1)).e["prob_ascenso"] == pytest.approx(0.08)
    assert vida(Perfil(nivel=0), skill=60).e["prob_ascenso"] == pytest.approx(0.10 + 10 * 0.0006)
    # oficio 50 explícito: sin dato, quien terminó la media a los 18 tiene a los 30 el oficio de 12 años de experiencia
    assert vida(Perfil(nivel=1, edu="media", skill=50)).e["prob_ascenso"] == pytest.approx(0.04)
    assert vida(Perfil(nivel=1, tipo_empleador="startup")).e["prob_ascenso"] == pytest.approx(0.13)
    assert vida(Perfil(nivel=1, tipo_empleador="publico")).e["prob_ascenso"] == pytest.approx(0.04)
    assert vida(Perfil(nivel=1), parcial=1).e["prob_ascenso"] == pytest.approx(0.04)
    # prob_ascenso_extra se suma tal cual (por ejemplo ASCENSO_HORAS, que escribe trabajar_mas_horas)
    assert vida(Perfil(nivel=1), prob_ascenso_extra=0.0064).e["prob_ascenso"] == pytest.approx(0.08 + 0.0064)
    assert vida(Perfil(nivel=3), marcado=1).e["prob_ascenso"] == pytest.approx(0.01)  # piso del clamp
    assert vida(Perfil(nivel=1, antiguedad=0)).e["prob_ascenso"] == 0.0
    assert vida(Perfil(nivel=4)).e["prob_ascenso"] == 0.0
    assert vida(Perfil(nivel=1, estado="buscando")).e["prob_ascenso"] == 0.0


def test_quedarse_hasta_tarde_suma_el_ascenso_por_horas_una_sola_vez():
    """trabajar_mas_horas fija 55 horas y suma ASCENSO_HORAS (0,0064, panel ESI) a prob_ascenso_extra; el
    ascenso lee prob_ascenso_extra, así que sube 0,0064 una vez, como cuando leía horas >= 55, y vuelve al año siguiente."""
    v = vida(Perfil(nivel=1), DadosGuion())
    v.iniciar_anio(con_cartas=False)
    si = next(o for o in pq().decisiones["trabajar_mas_horas"]["opciones"] if o["id"] == "si")
    v._aplicar(si["resultados"][0]["efectos"], "lab")
    assert v.e["horas"] == 55 and v.e["prob_ascenso"] == pytest.approx(0.08 + 0.0064)
    _cerrar(v)
    assert v.e["horas"] == 44 and v.e["prob_ascenso_extra"] == pytest.approx(0)


# ------------------------------------------------------------------ duración
EFECTOS_CON_DURACION = [
    {"var": "red", "op": "suma", "valor": 10, "duracion": 2},
    {"var": "p_renuncia", "op": "multiplica", "valor": 0.5, "duracion": 2},
    {"var": "horas", "op": "fija", "valor": 55, "duracion": 2},
    {"var": "pais", "op": "fija", "valor": "'afuera'", "duracion": 2},
    {"var": "skill", "op": "suma", "valor": 7},                       # sin duración: permanente
    {"var": "energia", "op": "suma", "valor": -15, "duracion": 1},
    {"var": "animo", "op": "fija", "valor": 10, "duracion": 3},
]


def _estado_lab(v):
    return {k: v.e[k] for k in ("red", "p_renuncia", "horas", "pais", "skill", "energia")}


def test_duracion_revierte_al_vencer_suma_multiplica_y_fija():
    v = _lab(red=30, skill=50, energia=70)
    v._aplicar(EFECTOS_CON_DURACION, "lab")
    aplicado = {"red": 40, "p_renuncia": 0.5, "horas": 55, "pais": "afuera", "skill": 57, "energia": 55}
    assert _estado_lab(v) == aplicado
    _cerrar(v)  # cierre 1: vence lo de 1 año
    assert _estado_lab(v) == {**aplicado, "energia": 70}
    _cerrar(v)  # cierre 2: vence lo de 2 años
    original = {"red": 30, "p_renuncia": 1, "horas": 44, "pais": "chile", "skill": 57, "energia": 70}
    assert _estado_lab(v) == original
    assert len(v.temporales) == 1  # queda el de 3 años
    _cerrar(v)
    assert v.temporales == []
    for _ in range(3):  # no se revierte dos veces
        _cerrar(v)
    assert _estado_lab(v) == original


def test_la_reversion_deshace_el_efecto_no_los_cambios_posteriores():
    """Suma y multiplica se deshacen sobre el valor que haya; fija vuelve al valor anterior."""
    v = _lab(red=30)
    v._aplicar([{"var": "red", "op": "suma", "valor": 10, "duracion": 2},
                {"var": "tiempo_con_tu_gente", "op": "multiplica", "valor": 0.5, "duracion": 2}], "lab")
    _cerrar(v)
    v.iniciar_anio(con_cartas=False)
    v._aplicar([{"var": "red", "op": "suma", "valor": 5},
                {"var": "tiempo_con_tu_gente", "op": "multiplica", "valor": 1.5}], "lab")
    _cerrar(v)
    assert v.e["red"] == 35
    assert v.e["tiempo_con_tu_gente"] == pytest.approx(1.5)


def test_dos_efectos_con_duracion_sobre_la_misma_variable():
    v = _lab(red=30)
    v._aplicar([{"var": "red", "op": "suma", "valor": 10, "duracion": 1},
                {"var": "red", "op": "suma", "valor": 20, "duracion": 2}], "lab")
    assert v.e["red"] == 60
    _cerrar(v)
    assert v.e["red"] == 50
    _cerrar(v)
    assert v.e["red"] == 30


def test_la_recesion_dura_exactamente_el_anio():
    """Literal: `recesion` fija 1 con duración 1. Empieza al inicio del año y se va en el cierre."""
    d = DadosGuion({(0, "evento:recesion"): 0.0})
    v = vida(INACTIVA, d)
    v.iniciar_anio(con_cartas=False)
    assert v.e["recesion"] == 1 and v.registro["recesion"] is True
    cerrado = v.avanzar(Guion())
    assert cerrado["recesion"] is True and v.e["recesion"] == 0
    cerrado = v.vivir_anio(Guion())
    assert cerrado["recesion"] is False and v.e["recesion"] == 0


# ------------------------------------------------------------------ azar dentro de los efectos
def test_el_azar_de_un_efecto_depende_solo_de_gemelo_anio_y_sitio():
    def aplicar(dados, sitio="lab"):
        v = vida(INACTIVA, dados)
        v.iniciar_anio(con_cartas=False)
        v._aplicar([{"var": "red", "op": "fija", "valor": "100 * azar()"},
                    {"var": "skill", "op": "fija", "valor": "100 * azar()"},
                    {"var": "ahorro", "op": "fija", "valor": "azar_uniforme(1000, 2000)"}], sitio)
        return v.e["red"], v.e["skill"], v.e["ahorro"]

    a = aplicar(Dados(1, 5))
    assert a == aplicar(Dados(1, 5))
    assert a != aplicar(Dados(1, 6)) and a != aplicar(Dados(2, 5)) and a != aplicar(Dados(1, 5), "otro")
    assert a[0] != a[1]  # dentro de un resultado cada azar() es un número nuevo
    assert 1000 <= a[2] < 2000


# ------------------------------------------------------------------ caso literal del paquete
def _despedida(antiguedad: int, cesante: bool):
    guion = {"evento:separacion_empleo": 0.0} if cesante else {}
    v = vida(Perfil(edad=35, sueldo=1_000_000, antiguedad=antiguedad), DadosGuion(guion), ahorro=0.0)
    registro = v.vivir_anio(Guion({"oferta_externa": "quedarse"}))
    return v, registro


@pytest.mark.parametrize(("antiguedad", "sueldos_de_finiquito"), [(5, 5), (15, 11), (0, 0)])
def test_separacion_cesante_lee_sueldo_y_antiguedad_de_antes(antiguedad, sueldos_de_finiquito):
    """`separacion_empleo/cesante`: el sueldo queda en 0, pero el finiquito es sueldo x min(antigüedad, 11)
    y `sueldo_ref` queda en sueldo x (1 - CAIDA_REEMPLEO) = sueldo x 0,85. Todo con el sueldo de antes."""
    gemela, _ = _despedida(antiguedad, cesante=False)   # misma suerte, sin despido: su sueldo es el de antes
    sueldo_antes = gemela.e["sueldo"]
    assert 800_000 <= sueldo_antes <= 1_250_000 and sueldo_antes != 1_000_000  # ya pasó el alza del año
    v, registro = _despedida(antiguedad, cesante=True)
    assert [x["resultado"] for x in registro["eventos"] if x["evento"] == "separacion_empleo"] == ["cesante"]
    assert v.e["estado"] == "buscando" and v.e["sueldo"] == 0
    assert v.e["sueldo_ref"] == pytest.approx(sueldo_antes * 0.85, rel=1e-12)
    # cierre: sin sueldo no hay ahorro del año; el finiquito rinde el retorno real (3%)
    assert v.e["ahorro"] == pytest.approx(sueldo_antes * sueldos_de_finiquito * 1.03, rel=1e-12)
    assert v.e["animo"] < gemela.e["animo"]


def test_renunciar_guarda_el_ultimo_sueldo_como_referencia():
    v = vida(Perfil(edad=35, sueldo=1_000_000), DadosGuion())
    v.vivir_anio(Guion({"renunciar": "renunciar"}), carta="renunciar")
    assert v.e["estado"] == "buscando" and v.e["sueldo"] == 0 and v.e["sueldo_ref"] == 1_000_000


# ------------------------------------------------------------------ decisión de laboratorio
def _resultado(id_, prob, efectos=(), luego=None):
    r = {"id": id_, "prob": prob, "texto": f"sale {id_}", "tono": "neutro", "efectos": list(efectos)}
    if luego:
        r["luego"] = luego
    return r


@pytest.fixture(scope="module")
def paquete_lab():
    """Una copia del paquete con decisiones de laboratorio (el paquete compartido no se toca)."""
    p = Paquete()
    marca = lambda v: [{"var": "red", "op": "fija", "valor": v}]  # noqa: E731

    def decision(id_, opciones, tipo="carta"):
        p.decisiones[id_] = {"id": id_, "nombre": id_, "pregunta": "¿?", "categoria": "lab", "cuando": "1",
                             "aparicion": {"tipo": tipo, "peso": 1}, "opciones": opciones, "evidencia": [],
                             "calidad": "supuesto"}

    decision("lab", [
        {"id": "sin_resto", "nombre": "", "resultados": [_resultado("a", 0.3, marca(1)), _resultado("b", 0.2, marca(2))],
         "costo": [{"var": "ahorro", "op": "suma", "valor": -1000}]},
        {"id": "con_resto", "nombre": "", "resultados": [_resultado("a", 0.3, marca(1)), _resultado("r", "resto", marca(9)),
                                                         _resultado("b", 0.2, marca(2))]},
        {"id": "pasada", "nombre": "", "resultados": [_resultado("a", 0.7, marca(1)), _resultado("b", 0.6, marca(2)),
                                                      _resultado("r", "resto", marca(9))]},
        {"id": "fuera_de_rango", "nombre": "", "resultados": [_resultado("neg", "0 - 0.5", marca(1)),
                                                              _resultado("mas", "1.7", marca(2))]},
        {"id": "expresion", "nombre": "", "resultados": [_resultado("a", "red / 100", marca(1)),
                                                         _resultado("r", "resto", marca(9))]},
        {"id": "encadena", "nombre": "", "resultados": [_resultado("a", 1, marca(1), luego="lab2")]},
        {"id": "a_evento", "nombre": "", "resultados": [_resultado("a", 1, marca(1), luego="herencia")]},
        {"id": "con_requisito", "nombre": "", "requisito": "red > 90", "resultados": [_resultado("a", 1)]},
    ])
    decision("lab2", [{"id": "x", "nombre": "", "resultados": [
        _resultado("visto", 1, [{"var": "skill", "op": "fija", "valor": "red"}], luego="lab3")]}])
    decision("lab3", [{"id": "auto", "nombre": "", "resultados": [_resultado("fin", 1, [
        {"var": "animo", "op": "fija", "valor": 1}])]},
        {"id": "otra", "nombre": "", "resultados": [_resultado("no", 1)]}], tipo="interna")
    return p


def _jugar_lab(p, opcion, u, alcance="laboral", **estado):
    e = estado_inicial(INACTIVA, p)
    e.update(estado)
    d = DadosGuion({f"dec:lab:{opcion}": u})
    v = Vida(e, d, p, alcance)
    registro = v.vivir_anio(Guion({"lab": opcion, "lab2": "x"}), carta="lab")
    return v, registro, d


@pytest.mark.parametrize(("u", "resultado", "prob", "red"), [
    (0.0, "a", 0.3, 1), (0.2999, "a", 0.3, 1), (0.3001, "b", 0.2, 2), (0.4999, "b", 0.2, 2),
    (0.5001, None, 0.5, 30), (0.99, None, 0.5, 30),
])
def test_sorteo_sin_resto_puede_no_dar_ningun_resultado(paquete_lab, u, resultado, prob, red):
    v, registro, _ = _jugar_lab(paquete_lab, "sin_resto", u, red=30, ahorro=5000.0)
    d = registro["decisiones"][0]
    assert (d["decision"], d["opcion"], d["resultado"]) == ("lab", "sin_resto", resultado)
    assert d["prob"] == pytest.approx(prob)
    assert v.e["red"] == red
    assert v.e["ahorro"] == pytest.approx(4000 * 1.03)  # el costo de la opción se paga salga lo que salga


@pytest.mark.parametrize(("u", "resultado", "prob"), [
    (0.2999, "a", 0.3), (0.3001, "r", 0.5), (0.7999, "r", 0.5), (0.8001, "b", 0.2), (0.9999, "b", 0.2),
])
def test_resto_es_uno_menos_los_demas_y_va_en_su_lugar_de_la_lista(paquete_lab, u, resultado, prob):
    _, registro, _ = _jugar_lab(paquete_lab, "con_resto", u)
    d = registro["decisiones"][0]
    assert d["resultado"] == resultado and d["prob"] == pytest.approx(prob)


@pytest.mark.parametrize(("u", "resultado"), [(0.6999, "a"), (0.7001, "b"), (0.9999, "b")])
def test_probabilidades_que_suman_mas_de_uno_dejan_el_resto_en_cero(paquete_lab, u, resultado):
    _, registro, _ = _jugar_lab(paquete_lab, "pasada", u)
    assert registro["decisiones"][0]["resultado"] == resultado


@pytest.mark.parametrize("u", [0.0, 0.5, 0.9999])
def test_probabilidades_fuera_de_rango_se_recortan_a_0_y_1(paquete_lab, u):
    _, registro, _ = _jugar_lab(paquete_lab, "fuera_de_rango", u)
    d = registro["decisiones"][0]
    assert d["resultado"] == "mas" and d["prob"] == 1.0


def test_la_probabilidad_puede_ser_una_expresion_del_estado(paquete_lab):
    assert _jugar_lab(paquete_lab, "expresion", 0.39, red=40)[1]["decisiones"][0]["resultado"] == "a"
    assert _jugar_lab(paquete_lab, "expresion", 0.41, red=40)[1]["decisiones"][0]["resultado"] == "r"


def test_luego_encadena_en_el_mismo_anio_y_la_interna_no_pregunta(paquete_lab):
    v, registro, _ = _jugar_lab(paquete_lab, "encadena", 0.5, red=30, skill=50)
    assert [(d["decision"], d["opcion"], d["resultado"], d["origen"]) for d in registro["decisiones"]] == [
        ("lab", "encadena", "a", "carta"), ("lab2", "x", "visto", "luego"), ("lab3", "auto", "fin", "luego")]
    assert v.e["skill"] == 1  # lab2 ya vio el efecto de lab (red = 1): se aplicó antes de encadenar
    assert v.anio == 1 and len(v.historia) == 1


def test_luego_a_un_evento_lo_hace_ocurrir_sin_sortear_su_probabilidad(paquete_lab):
    """`herencia` tiene 1% anual y es un evento personal: por `luego` ocurre seguro en alcance
    completo y no ocurre en alcance laboral."""
    v, registro, d = _jugar_lab(paquete_lab, "a_evento", 0.5, alcance="completo", ahorro=0.0)
    assert [x["evento"] for x in registro["eventos"]].count("herencia") == 1
    assert v.e["ahorro"] > 0
    v, registro, d = _jugar_lab(paquete_lab, "a_evento", 0.5, alcance="laboral", ahorro=0.0)
    assert "herencia" not in [x["evento"] for x in registro["eventos"]]
    assert v.e["ahorro"] == 0


def test_requisito_filtra_opciones_y_una_opcion_no_disponible_es_error(paquete_lab):
    e = estado_inicial(INACTIVA, paquete_lab)
    v = Vida({**e, "red": 30}, DadosGuion(), paquete_lab)
    assert "con_requisito" not in [o.id for o in v.opciones("lab")]
    assert "con_requisito" in [o.id for o in Vida({**e, "red": 95}, DadosGuion(), paquete_lab).opciones("lab")]
    with pytest.raises(ValueError, match="con_requisito"):
        v.vivir_anio(Guion({"lab": "con_requisito"}), carta="lab")


def test_solo_las_variables_de_eleccion_se_pueden_pasar_como_parametros(paquete_lab):
    e = estado_inicial(INACTIVA, paquete_lab)
    v = Vida(e, DadosGuion(), paquete_lab)
    with pytest.raises(ValueError, match="sueldo"):
        v.vivir_anio(Guion({"lab": "con_resto"}, parametros={"lab": {"sueldo": 9_000_000}}), carta="lab")
    v = Vida(e, DadosGuion(), paquete_lab)
    v.vivir_anio(Guion({"lab": "con_resto"}, parametros={"lab": {"rubro_destino": "Minería"}}), carta="lab")
    assert v.e["rubro_destino"] == "Minería"


def test_sortear_los_literales_del_paquete():
    """Cortes literales: unirse_a_startup/ir = 0,242 | 0,299 | resto; tipo_de_empleador =
    0,12 | 0,88 x 0,40 | 0,88 x 0,59 | resto; pedir_aumento (mujer) = 0,20 | resto."""
    def resultado(decision, opcion, u, **perfil):
        v = vida(Perfil(edad=35, **perfil), DadosGuion({f"dec:{decision}:{opcion}": u}))
        reg = v.vivir_anio(Guion({"oferta_externa": "quedarse", decision: opcion}), carta=decision)
        return reg["decisiones"][0]["resultado"], reg["decisiones"][0]["prob"]

    eps = 1e-6
    assert resultado("unirse_a_startup", "ir", 0.242 - eps) == ("crece", pytest.approx(0.242))
    assert resultado("unirse_a_startup", "ir", 0.242 + eps) == ("cierra", pytest.approx(0.299))
    assert resultado("unirse_a_startup", "ir", 0.541 - eps)[0] == "cierra"
    assert resultado("unirse_a_startup", "ir", 0.541 + eps) == ("sigue", pytest.approx(0.459))
    assert resultado("pedir_aumento", "pedir", 0.20 - eps, sexo="m")[0] == "si"
    assert resultado("pedir_aumento", "pedir", 0.20 + eps, sexo="m") == ("no", pytest.approx(0.80))
    assert resultado("pedir_aumento", "pedir", 0.27 - eps, sexo="h")[0] == "si"
    assert resultado("pedir_aumento", "pedir", 0.27 + eps, sexo="h")[0] == "no"
    # contraoferta: 0,2626 (SCE) | 0,5 | resto
    assert resultado("oferta_externa", "contraoferta", 0.2626 - eps)[0] == "igualan"
    assert resultado("oferta_externa", "contraoferta", 0.7626 - eps)[0] == "no_igualan"
    assert resultado("oferta_externa", "contraoferta", 0.7626 + eps) == ("te_vas", pytest.approx(0.2374))


@pytest.mark.parametrize(("u", "tipo", "rubro"), [
    (0.12 - 1e-6, "publico", "Administración pública"), (0.12 + 1e-6, "grande", "Comercio"),
    (0.472 - 1e-6, "grande", "Comercio"), (0.472 + 1e-6, "pyme", "Comercio"), (0.9912 - 1e-6, "pyme", "Comercio"),
    (0.9912 + 1e-6, "startup", "Comercio"),
])
def test_tipo_de_empleador_al_reemplearse(u, tipo, rubro):
    """Despido con reempleo el mismo año: encadena la decisión interna `tipo_de_empleador`."""
    d = DadosGuion({"evento:separacion_empleo": 0.0, "evento:separacion_empleo:res": 0.0,
                    "dec:tipo_de_empleador:sorteo": u})
    v = vida(Perfil(edad=35, rubro="Comercio", tipo_empleador="pyme", antiguedad=6), d)
    registro = v.vivir_anio(Guion({"oferta_externa": "quedarse"}))
    assert [x["resultado"] for x in registro["eventos"] if x["evento"] == "separacion_empleo"] == ["reemplea"]
    interna = [x for x in registro["decisiones"] if x["decision"] == "tipo_de_empleador"]
    assert len(interna) == 1 and interna[0]["origen"] == "luego" and interna[0]["resultado"] == tipo
    assert v.e["estado"] == "empleado" and v.e["tipo_empleador"] == tipo and v.e["rubro"] == rubro
    assert v.e["antiguedad"] == 1  # volvió a 0 con el reempleo y sumó el año al cierre
    assert math.isfinite(v.e["sueldo"]) and v.e["sueldo"] > 0


def test_p_encontrar_multiplica_la_probabilidad_de_encontrar_trabajo():
    """Literal: cesantía a los 30-44 con red 30, sin hueco ni recesión:
    rápido = (1 - exp(-12 / 10,5)) x 1,15 = 0,7833; a tu nivel = x 0,8 = 0,5449.
    Con p_encontrar = 0,81 (ignorar la IA siendo joven en un área expuesta), se multiplican."""
    base = 1 - math.exp(-12 / 10.5)
    for opcion, p in (("rapido", base * 1.15), ("nivel", base * 0.8)):
        for p_encontrar in (1.0, 0.81):
            corte = p * p_encontrar
            for u, esperado in ((corte - 1e-6, "encuentra"), (corte + 1e-6, "nada")):
                d = DadosGuion({f"dec:cesantia:{opcion}": u})
                v = vida(Perfil(edad=35, estado="buscando", sueldo=1_000_000), d, p_encontrar=p_encontrar,
                         tipo_empleador="pyme", rubro="Comercio")
                reg = v.vivir_anio(Guion({"cesantia": opcion, "oferta_externa": "quedarse"}))
                assert reg["decisiones"][0]["resultado"] == esperado, (opcion, p_encontrar, u)
    assert NADA < 1


def test_el_azar_de_un_efecto_cambia_de_un_anio_a_otro():
    v = vida(INACTIVA, Dados(1, 5))
    valores = []
    for _ in range(4):
        v.iniciar_anio(con_cartas=False)
        v._aplicar([{"var": "red", "op": "fija", "valor": "100 * azar()"}], "lab")
        valores.append(v.e["red"])
        v.avanzar(Guion())
    assert len(set(valores)) == 4


def test_quedar_sin_trabajo_con_sueldo_lo_pasa_a_sueldo_de_referencia():
    """Reglas del paquete como bootcamp/sin_pega dejan 'buscando' sin tocar el sueldo: el motor lo
    lleva a 0 y guarda ese último sueldo (no uno más viejo) como referencia para la vuelta."""
    v = vida(Perfil(edad=35, sueldo=1_000_000), DadosGuion({"dec:bootcamp:hacer": 0.99}), sueldo_ref=500_000.0)
    reg = v.vivir_anio(Guion({"bootcamp": "hacer"}), carta="bootcamp")
    assert reg["decisiones"][0]["resultado"] == "sin_pega"
    assert (v.e["estado"], v.e["sueldo"], v.e["sueldo_ref"]) == ("buscando", 0, 1_000_000)


def test_la_decision_encadenada_corre_antes_que_los_eventos_que_siguen():
    """Despido con reempleo en una startup: `tipo_de_empleador` se resuelve en el acto, así que el
    evento `startup_cierra`, que viene después en el año, ya la encuentra en una startup."""
    d = DadosGuion({"evento:separacion_empleo": 0.0, "evento:separacion_empleo:res": 0.0,
                    "dec:tipo_de_empleador:sorteo": 0.995, "evento:startup_cierra": 0.0})
    v = vida(Perfil(edad=35, rubro="Comercio"), d)
    reg = v.vivir_anio(Guion({"oferta_externa": "quedarse"}))
    assert [x["evento"] for x in reg["eventos"] if x["evento"] in ("separacion_empleo", "startup_cierra")] == [
        "separacion_empleo", "startup_cierra"]
    assert v.e["tipo_empleador"] == "startup" and v.e["estado"] == "buscando"
