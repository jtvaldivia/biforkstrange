"""El loop anual (`motor.py`): orden de los pasos, cartas, alcance, cierre, frecuencias,
suerte compartida, detener y copiar.

Las frecuencias se revisan de dos formas: el corte exacto (con dados de laboratorio, el
evento ocurre si y solo si el dado cae bajo la probabilidad literal del paquete) y la
frecuencia con dados reales, con tolerancia de 3,5 desvíos del tamaño de muestra.
"""

import math
from collections import Counter

import pytest
from _motor_util import (CARTAS_PERFIL_BASE, DECISIONES_PERSONALES, EVENTOS_PERSONALES, NADA, DadosGuion, Guion,
                         fabrica, foto, n, pq, vida, z_binomial)

from app.sim.motor.azar import Dados
from app.sim.motor.motor import FaltaEleccion
from app.sim.motor.perfil import Perfil
from app.sim.motor.politicas import Fija, Inercia, Jugador, Poblacion

Z = 3.5
QUIETA = {"oferta_externa": "quedarse"}  # responde sin cambiar nada si llega una oferta
A_LOS_35 = Perfil(edad=35)  # empleada en pyme de Servicios profesionales, nivel 1, 2 años de antigüedad

# ------------------------------------------------------------------ cartas
def test_cartas_posibles_y_sus_pesos_son_los_del_paquete():
    v = vida(Perfil())
    assert dict(v.cartas_posibles()) == pytest.approx(CARTAS_PERFIL_BASE)
    completo = dict(vida(Perfil(), alcance="completo").cartas_posibles())
    assert completo == pytest.approx({**CARTAS_PERFIL_BASE, "buscar_pareja": 0.4})


def test_el_peso_de_renunciar_se_multiplica_por_p_renuncia_y_por_el_animo():
    assert dict(vida(Perfil(), p_renuncia=0.667).cartas_posibles())["renunciar"] == pytest.approx(0.5 * 0.0478 * 0.667)
    assert dict(vida(Perfil(), animo=40).cartas_posibles())["renunciar"] == pytest.approx(0.5 * 0.0478 * 3)
    assert "renunciar" not in dict(vida(Perfil(), p_renuncia=0).cartas_posibles())


def test_la_carta_del_anio_sale_en_proporcion_a_los_pesos():
    m = n(5000)
    salio = Counter()
    nueva = fabrica(Perfil())
    for g in range(m):
        v = nueva(Dados(11, g))
        with pytest.raises(FaltaEleccion) as falta:
            v.vivir_anio(Jugador([]))
        salio[falta.value.decision["id"]] += 1
    assert set(salio) <= set(CARTAS_PERFIL_BASE)
    total = sum(CARTAS_PERFIL_BASE.values())
    for carta, peso in CARTAS_PERFIL_BASE.items():
        assert abs(z_binomial(salio[carta], m, peso / total)) < Z, carta


def test_una_sola_carta_por_anio_y_ninguna_si_no_hay_cartas():
    for g in range(n(150)):
        v = vida(Perfil(edad=28), Dados(3, g))
        for _ in range(4):
            reg = v.vivir_anio(Poblacion())
            de_carta = [d for d in reg["decisiones"] if d["origen"] == "carta"]
            assert len(de_carta) <= 1
            assert all(d["origen"] in ("carta", "luego") for d in reg["decisiones"])
    for g in range(n(150)):
        v = vida(Perfil(edad=28), Dados(3, g))
        reg = v.vivir_anio(Inercia())  # sin cartas: solo lo que la vida obliga o encadena
        assert all(d["origen"] == "luego" for d in reg["decisiones"])


def test_las_forzadas_van_antes_que_las_cartas_y_las_reemplazan():
    """Cesante: el año parte con `cesantia` y no reparte carta, aunque quien decide reciba cartas."""
    cesante = Perfil(edad=35, estado="buscando", sueldo=1_000_000)
    for g in range(n(200)):
        v = vida(cesante, Dados(5, g), tipo_empleador="pyme", rubro="Comercio")
        assert v.cartas_posibles(), "tiene cartas disponibles, pero no le deben tocar"
        reg = v.vivir_anio(Guion({"cesantia": "nivel", **QUIETA}, con_cartas=True))
        assert reg["decisiones"][0]["decision"] == "cesantia"
        assert [d["decision"] for d in reg["decisiones"] if d["origen"] == "carta"] == ["cesantia"]


def test_varias_forzadas_en_el_mismo_anio_y_la_segunda_se_revalida():
    """A los 19, en segundo año de carrera: toca financiar y decidir si seguir. Si deja la
    carrera con la primera, la otra ya no aplica y no se pregunta."""
    estudiante = dict(estado="estudiando", edad=19, edu="media", carrera_id=11, sueldo=0, antiguedad=0)
    base = dict(semestres_restantes=8, anos_en_carrera=1, tipo_institucion="U")
    v = vida(Perfil(**estudiante), DadosGuion(), **base)
    reg = v.vivir_anio(Guion({"financiar_estudios": "familia", "seguir_o_desertar": "seguir"}))
    assert [d["decision"] for d in reg["decisiones"]] == ["financiar_estudios", "seguir_o_desertar"]
    v = vida(Perfil(**estudiante), DadosGuion(), **base, financia="familia", energia=20)
    reg = v.vivir_anio(Guion({"seguir_o_desertar": "dejar", "primera_pega": "pyme", **QUIETA}))
    # dejó la carrera, encadenó primera_pega y quedó empleada con energía 20: la licencia se pregunta el año próximo
    assert [d["decision"] for d in reg["decisiones"]] == ["seguir_o_desertar", "primera_pega"]


def test_una_forzada_que_deja_de_aplicar_por_la_anterior_no_se_pregunta():
    """Alcance completo: con un familiar enfermo y sin energía tocan cuidar_familiar y la licencia.
    Si deja el trabajo para cuidar, la licencia (que es de empleadas) ya no se pregunta."""
    estado = dict(familiar_enfermo="madre", energia=20)
    v = vida(A_LOS_35, DadosGuion(), alcance="completo", **estado)
    assert v._forzadas() == ["cuidar_familiar", "licencia_salud_mental"]
    reg = v.vivir_anio(Guion({"cuidar_familiar": "dejar_pega"}))
    assert [d["decision"] for d in reg["decisiones"]] == ["cuidar_familiar"] and v.e["estado"] == "inactivo"
    v = vida(A_LOS_35, DadosGuion(), alcance="completo", **estado)
    reg = v.vivir_anio(Guion({"cuidar_familiar": "pagar", "licencia_salud_mental": "pedir", **QUIETA}))
    assert [d["decision"] for d in reg["decisiones"]] == ["cuidar_familiar", "licencia_salud_mental"]


def test_la_carta_se_sortea_con_su_propio_dado_en_el_orden_del_paquete():
    """Con el dado de la carta en 0 sale la primera del paquete que aplica (magíster, peso 0,4 de 8,0023);
    apenas pasado su tramo, la segunda (doctorado)."""
    total = sum(CARTAS_PERFIL_BASE.values())
    for u, esperada in ((0.0, "magister"), (0.4 / total + 1e-6, "doctorado"), (0.999999, "ahorro")):
        d = DadosGuion({"carta": u}, defecto=0.5)
        with pytest.raises(FaltaEleccion) as falta:
            vida(Perfil(), d).vivir_anio(Jugador([]))
        assert falta.value.decision["id"] == esperada and (0, "carta") in d.pedidos


def test_la_suerte_de_cada_anio_es_distinta():
    """El alza anual sale de un dado por año: una misma vida no repite el mismo salto todos los años."""
    v = vida(A_LOS_35, Dados(21, 0))
    sueldos = [v.e["sueldo"]]
    for _ in range(6):
        v.vivir_anio(Guion({"oferta_externa": "quedarse", "cesantia": "nivel"}))
        sueldos.append(v.e["sueldo"])
    alzas = {round(b / a, 6) for a, b in zip(sueldos, sueldos[1:]) if a and b}
    assert len(alzas) >= 4


def test_fija_responde_una_sola_vez_y_despues_delega():
    v = vida(A_LOS_35, DadosGuion({"evento:oferta_llega": 0.0}))
    delegado = Guion({"oferta_externa": "quedarse"})
    fija = Fija("oferta_externa", "cambiar", despues=delegado)
    r1 = v.vivir_anio(fija)
    r2 = v.vivir_anio(fija)
    assert [d["opcion"] for d in r1["decisiones"] if d["decision"] == "oferta_externa"] == ["cambiar"]
    assert [d["opcion"] for d in r2["decisiones"] if d["decision"] == "oferta_externa"] == ["quedarse"]
    assert delegado.vistas == ["oferta_externa"] and fija.con_cartas is False


def test_carta_forzada_por_la_duda_inicial_reemplaza_al_sorteo():
    v = vida(Perfil(), Dados(0, 0))
    reg = v.vivir_anio(Guion({"pedir_aumento": "esperar", **QUIETA}, con_cartas=True), carta="pedir_aumento")
    assert [d["decision"] for d in reg["decisiones"] if d["origen"] == "carta"] == ["pedir_aumento"]


# ------------------------------------------------------------------ luego
def test_luego_decision_a_decision_en_el_mismo_anio():
    v = vida(Perfil.a_los_18(), DadosGuion())
    carreras_u = [f["carrera_id"] for f in pq().filas("mifuturo_carreras") if f["tipo_institucion"] == "U"]
    reg = v.vivir_anio(Guion({"salir_del_colegio": "universidad", "elegir_carrera": carreras_u[3]}))
    assert [(d["decision"], d["origen"]) for d in reg["decisiones"]] == [
        ("salir_del_colegio", "carta"), ("elegir_carrera", "luego")]
    assert reg["edad"] == 18 and v.e["carrera_id"] == int(carreras_u[3]) and v.e["tipo_institucion"] == "U"
    fila = next(f for f in pq().filas("mifuturo_carreras") if f["carrera_id"] == carreras_u[3])
    assert v.e["area"] == fila["area"]
    # la duración real en semestres, menos los 2 del año que ya cerró
    assert v.e["semestres_restantes"] == round(float(fila["duracion_real_semestres"])) - 2


def test_elegir_carrera_ofrece_solo_las_del_tipo_de_institucion():
    v = vida(Perfil.a_los_18(), DadosGuion(), tipo_institucion="CFT")
    opciones = v.opciones("elegir_carrera")
    esperadas = {f["carrera_id"] for f in pq().filas("mifuturo_carreras") if f["tipo_institucion"] == "CFT"}
    assert {o.id for o in opciones} == esperadas and 0 < len(esperadas) < 252
    assert all(o.fila["fila_tipo_institucion"] == "CFT" for o in opciones)


def test_luego_evento_a_decision_en_el_mismo_anio():
    """`oferta_llega` encadena `oferta_externa` el mismo año, después de la carta del año."""
    d = DadosGuion({"evento:oferta_llega": 0.0})
    v = vida(A_LOS_35, d)
    guion = Guion({"pedir_aumento": "esperar", "oferta_externa": "cambiar", "tipo_de_empleador": "no se pregunta"},
                  con_cartas=True)
    reg = v.vivir_anio(guion, carta="pedir_aumento")
    assert [(x["decision"], x["origen"]) for x in reg["decisiones"]] == [
        ("pedir_aumento", "carta"), ("oferta_externa", "luego"), ("tipo_de_empleador", "luego")]
    assert "tipo_de_empleador" not in guion.vistas  # la interna no pasa por quien decide
    assert v.e["antiguedad"] == 1  # cambió de empleador este año


def test_luego_no_cruza_el_alcance_laboral():
    """En alcance laboral, `enferma_familiar` (personal) no ocurre; y si algo personal quedara
    encadenado, tampoco se pregunta."""
    for alcance, esperado in (("laboral", []), ("completo", ["cuidar_familiar"])):
        d = DadosGuion({"evento:enferma_familiar": 0.0})
        v = vida(A_LOS_35, d, alcance=alcance)
        reg = v.vivir_anio(Guion({"cuidar_familiar": "pagar", **QUIETA}))
        assert [x["decision"] for x in reg["decisiones"]] == esperado


# ------------------------------------------------------------------ alcance
def test_alcance_laboral_excluye_las_6_decisiones_y_los_8_eventos_personales():
    assert len(DECISIONES_PERSONALES) == 6 and len(EVENTOS_PERSONALES) == 8
    assert DECISIONES_PERSONALES <= set(pq().decisiones) and EVENTOS_PERSONALES <= set(pq().eventos)
    # una vida con todo lo personal a punto de pasar: en pareja, con un familiar enfermo y plata para una casa
    estado = dict(pareja="convive", familiar_enfermo="madre", ahorro=40_000_000.0, animo=40)
    laboral, completo = vida(A_LOS_35, alcance="laboral", **estado), vida(A_LOS_35, alcance="completo", **estado)
    assert not {c for c, _ in laboral.cartas_posibles()} & DECISIONES_PERSONALES
    assert {c for c, _ in completo.cartas_posibles()} & DECISIONES_PERSONALES == {
        "tener_hijo", "formalizar_pareja", "separarse", "comprar_vivienda"}
    assert laboral._forzadas() == [] and completo._forzadas() == ["cuidar_familiar"]
    # con dados que hacen ocurrir todo lo que puede ocurrir
    todo_pasa = {"evento:separacion_empleo": NADA, "evento:startup_cierra": NADA}
    eventos = {}
    for alcance in ("laboral", "completo"):
        v = vida(A_LOS_35, DadosGuion(todo_pasa, defecto=0.0), alcance=alcance, **estado)
        guion = Guion({"cuidar_familiar": "pagar", "tener_hijo": "esperar", "oferta_externa": "quedarse"})
        reg = v.vivir_anio(guion)
        eventos[alcance] = {x["evento"] for x in reg["eventos"]}
        if alcance == "laboral":
            assert not set(guion.vistas) & DECISIONES_PERSONALES
    assert not eventos["laboral"] & EVENTOS_PERSONALES
    assert eventos["laboral"] == {"recesion", "alza_anual", "ascenso", "oferta_llega", "animo_vuelve"}
    assert eventos["completo"] - eventos["laboral"] == {
        "cancer", "muere_madre", "muere_padre", "termina_pareja", "herencia"}  # sin pareja ya no hay embarazo


def test_poblacion_en_alcance_laboral_nunca_toca_lo_personal():
    for g in range(n(40)):
        v = vida(Perfil(edad=24, sexo="hm"[g % 2]), Dados(8, g), pareja="convive")
        v.vivir(Poblacion(), 12)
        for reg in v.historia:
            assert not {d["decision"] for d in reg["decisiones"]} & DECISIONES_PERSONALES
            assert not {x["evento"] for x in reg["eventos"]} & EVENTOS_PERSONALES
        assert (v.e["pareja"], v.e["hijos"], v.e["salud"], v.e["madre_edad"]) == ("convive", 0, "bien", 24 + 28)


# ------------------------------------------------------------------ orden del año
def test_la_recesion_se_sortea_antes_que_todo_y_el_anio_ya_la_ve():
    """Con recesión, la separación del mismo año usa x 1,4 y el reempleo x 0,85."""
    p_normal = 0.066 * 1.12 * 1.04
    d = DadosGuion({"evento:recesion": 0.0, "evento:separacion_empleo": p_normal * 1.4 - 1e-6,
                    "evento:separacion_empleo:res": (1 - math.exp(-9 / 10.5)) * 0.85 + 1e-6})
    v = vida(A_LOS_35, d)
    reg = v.vivir_anio(Guion(QUIETA))
    assert reg["recesion"] is True
    assert [x["evento"] for x in reg["eventos"]][0] == "recesion"
    sep = [x for x in reg["eventos"] if x["evento"] == "separacion_empleo"]
    assert len(sep) == 1 and sep[0]["resultado"] == "cesante"
    assert sep[0]["prob_evento"] == pytest.approx(p_normal * 1.4)
    # prob es la de que pase el evento y además salga ese resultado (aquí, no reemplearse en recesión)
    assert sep[0]["prob"] == pytest.approx(p_normal * 1.4 * (1 - (1 - math.exp(-9 / 10.5)) * 0.85))
    assert d.pedidos[0] == (0, "evento:recesion")  # el primer dado del año es el del mundo


def test_los_eventos_van_despues_de_la_decision_y_ven_su_efecto():
    """Quien renuncia en la carta del año ya no recibe alza, ascenso, despido ni ofertas ese año."""
    v = vida(A_LOS_35, DadosGuion(defecto=0.0))
    reg = v.vivir_anio(Guion({"renunciar": "renunciar"}), carta="renunciar")
    assert {x["evento"] for x in reg["eventos"]} == {"recesion", "animo_vuelve"}
    # y los eventos van en el orden del paquete
    v = vida(A_LOS_35, DadosGuion({"evento:separacion_empleo": NADA}, defecto=0.0))
    reg = v.vivir_anio(Guion({"oferta_externa": "quedarse"}))
    assert [x["evento"] for x in reg["eventos"]] == ["recesion", "alza_anual", "ascenso", "oferta_llega", "animo_vuelve"]
    assert [x["rutina"] for x in reg["eventos"]] == [False, True, False, False, True]


def test_el_registro_del_anio_trae_edad_de_inicio_y_resumen_de_cierre():
    v = vida(A_LOS_35, DadosGuion())
    r1 = v.vivir_anio(Guion(QUIETA))
    r2 = v.vivir_anio(Guion(QUIETA))
    assert (r1["anio"], r1["edad"], r1["fin"]["edad"]) == (1, 35, 36)
    assert (r2["anio"], r2["edad"], r2["fin"]["edad"]) == (2, 36, 37)
    assert v.historia == [r1, r2] and v.anio == 2 and v.registro is None and v.cola == []
    fin = r2["fin"]
    assert fin == v.resumen()
    assert (fin["estado"], fin["sueldo"], fin["nivel"], fin["cargo"], fin["tipo_empleador"], fin["rubro"]) == (
        "empleado", round(v.e["sueldo"]), 1, "Semi senior", "pyme", "Servicios profesionales")
    assert (fin["antiguedad"], fin["edu"], fin["ahorro"]) == (4, "universitaria", round(v.e["ahorro"]))


def test_no_se_puede_iniciar_un_anio_con_otro_abierto():
    v = vida(A_LOS_35, Dados(0, 0))
    with pytest.raises(FaltaEleccion):
        v.vivir_anio(Jugador([]))
    with pytest.raises(RuntimeError):
        v.iniciar_anio(con_cartas=True)


def test_vivir_se_detiene_a_los_60():
    v = vida(Perfil(edad=57), DadosGuion())
    v.vivir(Guion(QUIETA), 10)
    assert v.e["edad"] == 60 and v.anio == 3 and v.terminada()


# ------------------------------------------------------------------ cierre
def _independiente(**estado):
    """Trabaja por cuenta propia: ningún evento le mueve el sueldo, así el cierre se ve limpio."""
    base = dict(tasa_ahorro=0.08, ahorro=1_000_000.0, skill=50)
    return vida(Perfil(edad=35, estado="independiente", sueldo=1_000_000), DadosGuion(), **{**base, **estado})


def test_cierre_edad_ahorro_y_oficio():
    v = _independiente()
    v.vivir_anio(Guion())
    assert v.e["edad"] == 36 and v.anio == 1
    # ahorro: lo que había + 8% de 12 sueldos, y sobre eso el retorno real de 3%
    assert v.e["ahorro"] == pytest.approx((1_000_000 + 12 * 1_000_000 * 0.08) * 1.03)
    assert v.e["skill"] == pytest.approx(51.5)       # +1,5 de oficio por año trabajado
    assert v.ingreso_total == pytest.approx(12_000_000)
    assert v.e["antiguedad"] == 0                     # la antigüedad es del empleo dependiente
    assert v.e["anos_titulado"] == 12                 # 35 - 24, más el año
    v.vivir_anio(Guion())
    assert v.e["ahorro"] == pytest.approx(((1_000_000 + 960_000) * 1.03 + 960_000) * 1.03)
    assert v.ingreso_total == pytest.approx(24_000_000) and v.e["skill"] == pytest.approx(53)


def test_cierre_el_oficio_crece_segun_aprendizaje_y_solo_si_trabaja():
    v = _independiente(aprendizaje=0.78)
    v.vivir_anio(Guion())
    assert v.e["skill"] == pytest.approx(50 + 1.5 * 0.78)
    v = vida(Perfil(estado="inactivo", edad=40), DadosGuion(), skill=50)
    v.vivir_anio(Guion())
    assert v.e["skill"] == 50 and v.ingreso_total == 0


def test_cierre_ahorro_negativo_no_rinde_y_sin_sueldo_no_se_ahorra():
    v = _independiente(ahorro=-20_000_000.0, tasa_ahorro=0.0)
    v.vivir_anio(Guion())
    assert v.e["ahorro"] == -20_000_000
    v = vida(Perfil(estado="inactivo", edad=40), DadosGuion(), ahorro=5_000_000.0, tasa_ahorro=0.2)
    v.vivir_anio(Guion())
    assert v.e["ahorro"] == pytest.approx(5_000_000 * 1.03)


@pytest.mark.parametrize(("deuda", "pago"), [(5_000_000, 1_200_000), (700_000, 700_000)])
def test_cierre_el_credito_se_paga_con_el_10_por_ciento_del_sueldo(deuda, pago):
    v = _independiente(deuda_estudios=float(deuda), tasa_ahorro=0.0, ahorro=3_000_000.0)
    v.vivir_anio(Guion())
    assert v.e["deuda_estudios"] == pytest.approx(deuda - pago)
    assert v.e["ahorro"] == pytest.approx((3_000_000 - pago) * 1.03)


def test_cierre_el_credito_no_se_paga_estudiando_ni_sin_sueldo():
    estudiante = Perfil(estado="estudiando", edad=20, edu="media", carrera_id=11, sueldo=0)
    v = vida(estudiante, DadosGuion(), deuda_estudios=5_000_000.0, semestres_restantes=6, anos_en_carrera=2,
             financia="cae", tipo_institucion="U")
    v.vivir_anio(Guion())
    assert v.e["deuda_estudios"] == 5_000_000
    v = vida(Perfil(estado="inactivo", edad=40), DadosGuion(), deuda_estudios=5_000_000.0)
    v.vivir_anio(Guion())
    assert v.e["deuda_estudios"] == 5_000_000


def test_cierre_antiguedad_sube_empleada_y_vuelve_a_cero_sin_empleo():
    v = vida(Perfil(edad=35, antiguedad=7), DadosGuion())
    v.vivir_anio(Guion(QUIETA))
    assert v.e["antiguedad"] == 8 and v.e["sueldo_ref"] == v.e["sueldo"]
    v = vida(Perfil(edad=35, antiguedad=7), DadosGuion())
    v.vivir_anio(Guion({"renunciar": "renunciar"}), carta="renunciar")
    assert v.e["antiguedad"] == 0 and v.anios_buscando == 1
    v = vida(Perfil(edad=35, antiguedad=40), DadosGuion())
    v.vivir_anio(Guion(QUIETA))
    assert v.e["antiguedad"] == 40  # tope del dominio


@pytest.mark.parametrize(("tipo_institucion", "edu"), [("U", "universitaria"), ("IP", "tecnica"), ("CFT", "tecnica")])
def test_cierre_titulacion_al_terminar_los_semestres(tipo_institucion, edu):
    carrera = next(int(f["carrera_id"]) for f in pq().filas("mifuturo_carreras")
                   if f["tipo_institucion"] == tipo_institucion)
    estudiante = Perfil(estado="estudiando", edad=21, edu="media", carrera_id=carrera, sueldo=0)
    v = vida(estudiante, DadosGuion(), semestres_restantes=4, anos_en_carrera=3, financia="familia")
    assert v.e["tipo_institucion"] == tipo_institucion
    v.vivir_anio(Guion())
    assert (v.e["estado"], v.e["edu"], v.e["semestres_restantes"], v.e["anos_en_carrera"]) == (
        "estudiando", "media", 2, 4)
    assert v.e["anos_titulado"] == 3  # no corre mientras estudia (21 - 18 al partir)
    v.vivir_anio(Guion())
    assert (v.e["estado"], v.e["edu"], v.e["primer_empleo"], v.e["anos_titulado"]) == ("buscando", edu, 1, 0)
    assert (v.e["semestres_restantes"], v.e["anos_en_carrera"], v.e["carrera_id"]) == (0, 0, carrera)
    assert v.anios_buscando == 1
    # el año siguiente la vida le pone delante su primera pega
    with pytest.raises(FaltaEleccion) as falta:
        v.vivir_anio(Jugador([]))
    assert falta.value.decision["id"] == "primera_pega"


def test_cierre_el_hueco_de_una_pausa_pesa_dos_anios():
    v = vida(Perfil(estado="inactivo", edad=40), DadosGuion(), hueco=1)
    v.vivir_anio(Guion())
    assert v.e["hueco"] == 1
    v.vivir_anio(Guion())
    assert v.e["hueco"] == 0
    v.vivir_anio(Guion())
    assert v.e["hueco"] == 0


def test_cierre_la_startup_con_cierre_sorteado_cierra_cuando_se_cumple_el_plazo():
    en_startup = Perfil(edad=35, tipo_empleador="startup", sueldo=1_000_000)
    v = vida(en_startup, DadosGuion(), cierra_en=2)
    r1 = v.vivir_anio(Guion(QUIETA))
    assert (v.e["cierra_en"], v.e["estado"], v.e["anos_en_startup"]) == (1, "empleado", 1)
    assert "startup_cierra" not in [x["evento"] for x in r1["eventos"]]
    sueldo_antes = v.e["sueldo"]
    gemela = v.clonar()
    gemela.e["cierra_en"] = 0  # misma suerte, sin cierre: su sueldo de fin de año es el de antes del cierre
    gemela.vivir_anio(Guion(QUIETA))
    r2 = v.vivir_anio(Guion(QUIETA))
    assert [x["evento"] for x in r2["eventos"]][-1] == "startup_cierra"
    assert (v.e["cierra_en"], v.e["estado"], v.e["sueldo"]) == (0, "buscando", 0)
    assert v.e["sueldo_ref"] == pytest.approx(gemela.e["sueldo"]) and gemela.e["sueldo"] != sueldo_antes
    assert r2["fin"]["estado"] == "buscando" and v.anios_buscando == 1
    # si ya no está en una startup, el plazo corre pero no la saca de su trabajo
    v = vida(Perfil(edad=35, tipo_empleador="pyme"), DadosGuion(), cierra_en=1)
    v.vivir_anio(Guion(QUIETA))
    assert (v.e["cierra_en"], v.e["estado"]) == (0, "empleado")


def test_cierre_deja_de_trabajar_pasa_a_inactiva_y_guarda_el_ultimo_sueldo():
    v = vida(A_LOS_35, DadosGuion(), deja_de_trabajar=1)
    gemela = vida(A_LOS_35, DadosGuion())
    gemela.vivir_anio(Guion(QUIETA))
    v.vivir_anio(Guion(QUIETA))
    assert (v.e["estado"], v.e["sueldo"], v.e["deja_de_trabajar"]) == ("inactivo", 0, 0)
    assert v.e["sueldo_ref"] == pytest.approx(gemela.e["sueldo"])
    assert v.ingreso_total == pytest.approx(gemela.ingreso_total)  # el año se trabajó


def test_cierre_alza_extra_anual_se_suma_al_alza_de_la_empleada():
    """Titularse en recesión: -9% al partir y +0,9% extra por año durante 10 años (literal)."""
    con, sin = vida(A_LOS_35, DadosGuion(), alza_extra_anual=0.009), vida(A_LOS_35, DadosGuion())
    for _ in range(3):
        con.vivir_anio(Guion(QUIETA))
        sin.vivir_anio(Guion(QUIETA))
    assert con.e["sueldo"] / sin.e["sueldo"] == pytest.approx(1.009 ** 3)
    # el evento: solo en recesión y recién titulada; dura 10 cierres
    recien = Perfil(edad=24, sueldo=1_000_000, antiguedad=0)
    assert vida(recien).e["anos_titulado"] == 0
    v = vida(recien, DadosGuion({(0, "evento:recesion"): 0.0}))
    gemela = vida(recien, DadosGuion())
    reg = v.vivir_anio(Guion(QUIETA))
    gemela.vivir_anio(Guion(QUIETA))
    assert "titularse_en_recesion" in [x["evento"] for x in reg["eventos"]]
    assert v.e["alza_extra_anual"] == pytest.approx(0.009)
    # mismo dado del alza anual; en recesión el alza del año baja 1,5 puntos; después -9% y +0,9%
    alza_gemela = gemela.e["sueldo"] / 1_000_000
    assert v.e["sueldo"] == pytest.approx(1_000_000 * (alza_gemela - 0.015) * 0.91 * 1.009)
    for _ in range(9):
        v.vivir_anio(Guion(QUIETA))
    assert v.e["alza_extra_anual"] == pytest.approx(0.0, abs=1e-12)
    assert "titularse_en_recesion" not in [x["evento"] for x in gemela.historia[0]["eventos"]]


def test_cierre_cuenta_los_anios_buscando():
    v = vida(Perfil(edad=35, estado="buscando", sueldo=1_000_000), DadosGuion(), tipo_empleador="pyme", rubro="Comercio")
    for esperado in (1, 2, 3):
        v.vivir_anio(Guion({"cesantia": "nivel"}))  # con este dado no encuentra
        assert v.anios_buscando == esperado and v.e["meses_cesante"] == 12 * esperado
    v.dados = DadosGuion({"dec:cesantia:nivel": 0.0, "dec:tipo_de_empleador:sorteo": 0.5})
    v.vivir_anio(Guion({"cesantia": "nivel", **QUIETA}))
    assert v.anios_buscando == 3 and v.e["estado"] == "empleado" and v.e["meses_cesante"] == 0
    assert 0.93 * 1_000_000 * 0.8 <= v.e["sueldo"] <= 1.06 * 1_000_000 * 1.25  # sueldo_ref x U(0,93; 1,06) y el alza


# ------------------------------------------------------------------ frecuencias: corte exacto
def _ocurre(evento: str, u: float, perfil: Perfil, guion: dict | None = None, **estado):
    d = DadosGuion({f"evento:{evento}": u, **(guion or {})})
    v = vida(perfil, d, **estado)
    reg = v.vivir_anio(Guion(QUIETA))
    assert (0, f"evento:{evento}") in d.pedidos or not any(x["evento"] == evento for x in reg["eventos"])
    return [x["prob_evento"] for x in reg["eventos"] if x["evento"] == evento]


RECESION = {"evento:recesion": 0.0}
SEPARACION = [
    # (perfil, dados extra, probabilidad literal del paquete)
    (dict(edad=35), {}, 0.066 * 1.12 * 1.04),                     # 30-44, pyme, Servicios profesionales
    (dict(edad=35), RECESION, 0.066 * 1.12 * 1.04 * 1.4),         # lo mismo en recesión
    (dict(edad=44), {}, 0.066 * 1.12 * 1.04),
    (dict(edad=45), {}, 0.05 * 1.12 * 1.04),                      # cambia de tramo a los 45
    (dict(edad=29), {}, 0.143 * 1.12 * 1.04),
    (dict(edad=30), {}, 0.066 * 1.12 * 1.04),
    (dict(edad=25, tipo_empleador="grande", rubro="Minería"), {}, 0.143 * 0.89 * 0.57),
    (dict(edad=35, tipo_empleador="startup", rubro="Construcción"), {}, 0.066 * 1.5 * 1.67),
    (dict(edad=35, rubro="Otros servicios"), {}, 0.066 * 1.12),   # rubro sin multiplicador: 1
    (dict(edad=50, tipo_empleador="publico", rubro="Administración pública"), {}, 0.05 * 0.5),
    (dict(edad=50, tipo_empleador="publico", rubro="Construcción"), RECESION, 0.05 * 0.5 * 1.4),  # Estado: sin rubro
]


@pytest.mark.parametrize(("perfil", "extra", "p"), SEPARACION)
def test_separacion_ocurre_exactamente_bajo_la_probabilidad_del_paquete(perfil, extra, p):
    assert _ocurre("separacion_empleo", p - 1e-7, Perfil(**perfil), extra) == [pytest.approx(p)]
    assert _ocurre("separacion_empleo", p + 1e-7, Perfil(**perfil), extra) == []


def test_separacion_no_aplica_al_empleo_extranjero_ni_a_quien_no_es_empleada():
    assert _ocurre("separacion_empleo", 0.0, Perfil(tipo_empleador="extranjero")) == []
    assert _ocurre("separacion_empleo", 0.0, Perfil(estado="independiente")) == []
    assert _ocurre("separacion_empleo", 0.0, Perfil(estado="inactivo")) == []


@pytest.mark.parametrize(("evento", "perfil", "estado", "extra", "p"), [
    ("ascenso", dict(nivel=1), {}, {}, 0.08),
    ("ascenso", dict(nivel=0), {}, {}, 0.10),
    ("ascenso", dict(nivel=2), dict(skill=80), {}, 0.05 + 30 * 0.0006),
    ("ascenso", dict(nivel=1), dict(prob_ascenso_extra=0.0064), {}, 0.08 + 0.0064),  # ASCENSO_HORAS: panel ESI
    ("oferta_llega", dict(edad=35), {}, {}, 0.1377 * 1.5 * 1.3),
    ("oferta_llega", dict(edad=25), dict(red=80), {}, 0.2178 * 1.5 * 1.8),
    ("startup_cierra", dict(tipo_empleador="startup"), {}, {}, 1 - (1 - 0.299) ** (1 / 8)),
    ("titularse_en_recesion", dict(edad=24, antiguedad=0), {}, RECESION, 1.0),
])
def test_eventos_laborales_ocurren_bajo_su_probabilidad_literal(evento, perfil, estado, extra, p):
    guion = {"evento:separacion_empleo": NADA, **extra}
    if p < 1:
        assert _ocurre(evento, p + 1e-7, Perfil(**perfil), guion, **estado) == []
    assert _ocurre(evento, p - 1e-7, Perfil(**perfil), guion, **estado) == [pytest.approx(p)]


def test_la_recesion_ocurre_bajo_0_12_y_el_reempleo_bajo_su_corte():
    for u, hay in ((0.12 - 1e-7, True), (0.12 + 1e-7, False)):
        v = vida(A_LOS_35, DadosGuion({"evento:recesion": u}))
        assert v.vivir_anio(Guion(QUIETA))["recesion"] is hay
    corte = 1 - math.exp(-9 / 10.5)  # MESES_CESANTIA 30-44 = 10,5
    for u, resultado in ((corte - 1e-7, "reemplea"), (corte + 1e-7, "cesante")):
        d = DadosGuion({"evento:separacion_empleo": 0.0, "evento:separacion_empleo:res": u,
                        "dec:tipo_de_empleador:sorteo": 0.5})
        reg = vida(A_LOS_35, d).vivir_anio(Guion(QUIETA))
        assert [x["resultado"] for x in reg["eventos"] if x["evento"] == "separacion_empleo"] == [resultado]


def test_el_ascenso_sube_un_nivel_y_entre_5_y_10_por_ciento():
    gemela = vida(A_LOS_35, DadosGuion())
    gemela.vivir_anio(Guion(QUIETA))
    v = vida(A_LOS_35, DadosGuion({"evento:ascenso": 0.0}))
    v.vivir_anio(Guion(QUIETA))
    assert v.e["nivel"] == 2 and gemela.e["nivel"] == 1
    assert 1.05 <= v.e["sueldo"] / gemela.e["sueldo"] <= 1.10


# ------------------------------------------------------------------ frecuencias: dados reales
def _frecuencia_separacion(m: int, **estado) -> tuple[int, int]:
    despidos = recesiones = 0
    nueva = fabrica(A_LOS_35, **estado)
    for g in range(m):
        v = nueva(Dados(2026, g))
        reg = v.vivir_anio(Guion(QUIETA))
        despidos += any(x["evento"] == "separacion_empleo" for x in reg["eventos"])
        recesiones += reg["recesion"]
    return despidos, recesiones


def test_frecuencia_de_separacion_y_de_recesion_con_dados_reales():
    m = n(8000)
    p = 0.066 * 1.12 * 1.04
    despidos, recesiones = _frecuencia_separacion(m)
    assert abs(z_binomial(recesiones, m, 0.12)) < Z
    # 12% de los años son de recesión, donde la separación sube 40%
    assert abs(z_binomial(despidos, m, p * (0.88 + 0.12 * 1.4))) < Z
    despidos_recesion, _ = _frecuencia_separacion(m, recesion=1)
    assert abs(z_binomial(despidos_recesion, m, p * 1.4)) < Z
    assert z_binomial(despidos_recesion, m, p) > Z  # y se distingue de la tasa sin recesión


def test_frecuencia_de_resultados_de_una_decision_con_dados_reales():
    """unirse_a_startup/ir: 24,2% adquirida, 29,9% cierra, resto sigue (YC, literal del paquete)."""
    m = n(5000)
    salio = Counter()
    nueva = fabrica(A_LOS_35)
    for g in range(m):
        v = nueva(Dados(77, g))
        reg = v.vivir_anio(Guion({"unirse_a_startup": "ir", **QUIETA}), carta="unirse_a_startup")
        salio[reg["decisiones"][0]["resultado"]] += 1
    for resultado, p in (("crece", 0.242), ("cierra", 0.299), ("sigue", 1 - 0.242 - 0.299)):
        assert abs(z_binomial(salio[resultado], m, p)) < Z, resultado


# ------------------------------------------------------------------ suerte compartida
def _vidas_del_mismo_gemelo(g, opcion_a, opcion_b, decision, alcance="laboral", anios=10, perfil=A_LOS_35):
    vidas = []
    for opcion in (opcion_a, opcion_b):
        v = vida(perfil, Dados(4, g), alcance=alcance)
        decisor = Fija(decision, opcion)
        v.vivir_anio(decisor, carta=decision)
        v.vivir(decisor, anios - 1)
        vidas.append(v)
    return vidas


def test_suerte_compartida_una_decision_que_no_toca_el_trabajo_deja_la_carrera_identica():
    """Ahorrar mucho o gastar todo no cambia nada del trabajo: las dos vidas del mismo gemelo
    tienen que tener exactamente la misma recesión, los mismos eventos y el mismo sueldo."""
    distintos = set()
    for g in range(n(120)):
        a, b = _vidas_del_mismo_gemelo(g, "mucho", "gastar", "ahorro")
        assert a.historia[0]["decisiones"][0]["opcion"] == "mucho" and b.historia[0]["decisiones"][0]["opcion"] == "gastar"
        for ra, rb in zip(a.historia, b.historia, strict=True):
            assert ra["recesion"] == rb["recesion"]
            assert [(x["evento"], x["resultado"], x["prob"]) for x in ra["eventos"]] == \
                   [(x["evento"], x["resultado"], x["prob"]) for x in rb["eventos"]]
            assert [(d["decision"], d["opcion"], d["resultado"]) for d in ra["decisiones"][1:]] == \
                   [(d["decision"], d["opcion"], d["resultado"]) for d in rb["decisiones"][1:]]
            for k in ("estado", "sueldo", "sueldo_ref", "nivel", "tipo_empleador", "rubro", "antiguedad"):
                assert ra["fin"][k] == rb["fin"][k]
        assert a.e["ahorro"] > b.e["ahorro"] or a.e["sueldo"] == 0
        distintos.add(tuple(r["fin"]["sueldo"] for r in a.historia))
    assert len(distintos) > n(120) * 0.9  # y cada gemelo tiene su propia suerte


def test_suerte_compartida_lo_que_no_depende_de_la_decision_es_igual_en_las_dos_vidas():
    """Irse a una startup cambia la carrera, pero no la recesión ni la vida personal:
    la herencia, el cáncer, la muerte de los padres y la pareja caen igual en las dos vidas."""
    ajenos = EVENTOS_PERSONALES | {"recesion"}
    vistos = Counter()
    difieren_en_el_trabajo = 0
    for g in range(n(150)):
        a, b = _vidas_del_mismo_gemelo(g, "ir", "quedarse", "unirse_a_startup", alcance="completo",
                                       perfil=Perfil(edad=38))
        for ra, rb in zip(a.historia, b.historia, strict=True):
            ea = [(x["evento"], x["resultado"]) for x in ra["eventos"] if x["evento"] in ajenos]
            eb = [(x["evento"], x["resultado"]) for x in rb["eventos"] if x["evento"] in ajenos]
            assert ea == eb
            assert ra["recesion"] == rb["recesion"]
            vistos.update(e for e, _ in ea)
        assert (a.e["pareja"], a.e["hijos"], a.e["madre_edad"], a.e["padre_edad"], a.e["salud"]) == \
               (b.e["pareja"], b.e["hijos"], b.e["madre_edad"], b.e["padre_edad"], b.e["salud"])
        difieren_en_el_trabajo += a.e["tipo_empleador"] != b.e["tipo_empleador"] or a.e["sueldo"] != b.e["sueldo"]
    assert vistos["recesion"] > 0 and vistos["forma_pareja"] > 0 and vistos["herencia"] + vistos["muere_padre"] > 0
    assert difieren_en_el_trabajo > n(150) * 0.9


def test_suerte_compartida_la_misma_vida_dos_veces_es_identica_y_otra_semilla_no():
    def una(semilla, g):
        v = vida(Perfil(edad=26), Dados(semilla, g))
        v.vivir(Poblacion(), 8)
        return v
    a, b = una(1, 7), una(1, 7)
    assert a.historia == b.historia and a.e == b.e and a.ingreso_total == b.ingreso_total
    assert una(2, 7).historia != a.historia and una(1, 8).historia != a.historia


# ------------------------------------------------------------------ detener y copiar
def _detenida_en_recesion():
    """Una vida detenida a mitad de año esperando la carta, con un efecto temporal vivo (la recesión)."""
    for g in range(200):
        v = vida(Perfil(), Dados(9, g))
        with pytest.raises(FaltaEleccion) as falta:
            v.vivir_anio(Jugador([]))
        if v.e["recesion"]:
            assert v.temporales and v.registro is not None and v.cola
            return v, falta.value
    raise AssertionError("ninguna semilla dio recesión en el primer año")


def test_una_vida_detenida_por_falta_de_eleccion_queda_intacta():
    v, falta = _detenida_en_recesion()
    assert [o.id for o in falta.opciones] == [o.id for o in v.opciones(falta.decision["id"])]
    assert v.cola[0][:2] == ("decision", falta.decision["id"]) and v.anio == 0 and v.historia == []
    antes = foto(v)
    for _ in range(3):  # volver a intentar sin respuesta no avanza ni gasta nada
        with pytest.raises(FaltaEleccion) as otra:
            v.avanzar(Jugador([]))
        assert otra.value.decision["id"] == falta.decision["id"]
        assert foto(v) == antes
    with pytest.raises(FaltaEleccion):
        v.vivir_anio(Jugador([]))  # tampoco vuelve a sortear el mundo
    assert foto(v) == antes


def test_detener_y_seguir_da_lo_mismo_que_no_haberse_detenido():
    for g in range(n(40)):
        de_corrido = vida(Perfil(), Dados(13, g))
        ultima = Guion({}, con_cartas=True)
        ultima.elegir = lambda vida_, decision, opciones: (opciones[-1].id, {})  # siempre la última opción
        for _ in range(3):
            de_corrido.vivir_anio(ultima)
        a_saltos = vida(Perfil(), Dados(13, g))
        paradas, respuesta = 0, []
        while a_saltos.anio < 3:
            try:
                if respuesta:
                    pendiente, respuesta = respuesta, []
                    a_saltos.avanzar(Jugador(pendiente))
                else:
                    a_saltos.vivir_anio(Jugador([]))
            except FaltaEleccion as falta:
                paradas += 1
                respuesta = [{"decision": falta.decision["id"], "opcion": falta.opciones[-1].id}]
        assert paradas >= 3
        assert a_saltos.historia == de_corrido.historia and a_saltos.e == de_corrido.e


def test_clonar_es_independiente_del_original():
    v, falta = _detenida_en_recesion()
    antes = foto(v)
    copia = v.clonar()
    assert foto(copia) == antes
    assert copia.temporales is not v.temporales and copia.temporales[0] is not v.temporales[0]
    assert copia.registro is not v.registro and copia.registro["eventos"] is not v.registro["eventos"]
    assert copia.e is not v.e and copia.cola is not v.cola and copia.historia is not v.historia

    # la copia vive 3 años: el original no se entera
    siempre_ultima = Guion({}, con_cartas=True)
    siempre_ultima.elegir = lambda vida_, decision, opciones: (opciones[-1].id, {})
    copia.avanzar(siempre_ultima)
    copia.vivir(siempre_ultima, 2)
    assert copia.anio == 3 and len(copia.historia) == 3
    assert foto(v) == antes

    # y al revés: se ensucia el original a mano y la copia no cambia
    copia2 = v.clonar()
    foto2 = foto(copia2)
    v.e["sueldo"] = 1.0
    v.temporales[0]["quedan"] = 99
    v.temporales.append({"quedan": 1, "var": "red", "op": "suma", "valor": 1, "previo": 0})
    v.registro["eventos"].append({"evento": "inventado"})
    v.registro["recesion"] = "sucio"
    v.cola.pop()
    v.historia.append({"anio": 99})
    v.anios_buscando += 5
    assert foto(copia2) == foto2


def test_clonar_con_los_mismos_dados_repite_la_vida_y_con_otros_no():
    v, falta = _detenida_en_recesion()

    def seguir(copia):
        decisor = Fija(falta.decision["id"], falta.opciones[-1].id)
        copia.avanzar(decisor)
        copia.vivir(decisor, 6)
        return copia

    a, b = seguir(v.clonar()), seguir(v.clonar())
    assert a.historia == b.historia and a.e == b.e
    otras = [seguir(v.clonar(Dados(9, f"otro{i}"))) for i in range(6)]
    assert any(o.historia != a.historia for o in otras)
    # el año en curso ya tenía su recesión: los clones con otros dados la conservan
    assert all(o.historia[0]["recesion"] is True for o in otras)
    assert v.dados.gemelo != otras[0].dados.gemelo and otras[0].dados.semilla == 9
