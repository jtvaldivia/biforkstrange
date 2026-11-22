"""Del perfil al estado inicial (`perfil.py`): lo declarado y los supuestos escritos en TICKETS.md."""

import pytest
from _motor_util import pq

from app.sim.motor.azar import Dados
from app.sim.motor.motor import Vida
from app.sim.motor.perfil import Perfil, estado_inicial
from app.sim.motor.politicas import Inercia


def _e(**perfil):
    return estado_inicial(Perfil(**perfil), pq())


def test_lo_declarado_pasa_tal_cual():
    e = _e(edad=41, sexo="h", edu="tecnica", rubro="Salud", tipo_empleador="grande", nivel=2, sueldo=1_234_567,
           riesgo=7, antiguedad=6, region="otra")
    assert (e["edad"], e["sexo"], e["edu"], e["rubro"], e["tipo_empleador"], e["nivel"]) == (
        41, "h", "tecnica", "Salud", "grande", 2)
    assert (e["sueldo"], e["sueldo_ref"], e["antiguedad"], e["region"], e["estado"]) == (
        1_234_567, 1_234_567, 6, "otra", "empleado")
    assert e["riesgo"] == 70  # de 0-10 a la escala 0-100 del paquete
    assert e["primer_empleo"] == 0 and e["anos_titulado"] == 41 - 21


def test_supuestos_de_lo_que_la_persona_no_declara():
    """TICKETS.md: contactos 30, oficio 50, ahorro de dos sueldos, sin pareja ni hijos."""
    e = _e(sueldo=1_400_000)
    assert (e["red"], e["skill"], e["pareja"], e["hijos"], e["edad_hijo_menor"]) == (30, 50, "no", 0, -1)
    assert e["ahorro"] == 2 * 1_400_000
    assert _e(ahorro=123.0)["ahorro"] == 123.0
    assert (e["animo"], e["energia"], e["horas"], e["formal"], e["pais"], e["salud"]) == (64, 70, 44, 1, "chile", "bien")
    assert (e["p_encontrar"], e["p_renuncia"], e["aprendizaje"], e["deja_de_trabajar"], e["recesion"]) == (1, 1, 1, 0, 0)
    assert e["madre_edad"] in (30 + 28, 30 + 29) and e["padre_edad"] > e["madre_edad"]
    assert set(pq().variables) - set(e) == {v for v, d in pq().variables.items() if d["inicio"] == "deriva"}


@pytest.mark.parametrize(("sueldo", "tasa"), [(400_000, 0.03), (1_400_000, 0.08), (9_000_000, 0.195)])
def test_la_tasa_de_ahorro_inicial_sale_del_percentil(sueldo, tasa):
    """TASA_AHORRO literal: 3% bajo la mediana, 8% entre p50 y p79, 19,5% desde p80."""
    assert _e(sueldo=sueldo)["tasa_ahorro"] == tasa


def test_quien_no_trabaja_parte_sin_sueldo_pero_recuerda_el_ultimo():
    e = _e(estado="buscando", sueldo=1_000_000)
    assert (e["sueldo"], e["sueldo_ref"], e["primer_empleo"], e["tipo_empleador"], e["antiguedad"]) == (
        0, 1_000_000, 0, "", 0)
    assert _e(estado="buscando", sueldo=0)["primer_empleo"] == 1
    joven = estado_inicial(Perfil.a_los_18(), pq())
    assert (joven["edad"], joven["estado"], joven["edu"], joven["carrera_id"], joven["sueldo"]) == (
        18, "estudiando", "media", -1, 0)
    assert joven["anos_titulado"] == 0 and joven["primer_empleo"] == 1


def test_la_carrera_trae_su_area_y_tipo_de_institucion():
    fila = pq().filas("mifuturo_carreras")[57]
    e = _e(carrera_id=int(fila["carrera_id"]))
    assert (e["area"], e["tipo_institucion"]) == (fila["area"], fila["tipo_institucion"])
    assert (_e()["area"], _e()["tipo_institucion"]) == ("", "")


# ------------------------------------------------------------------ quien estudia
ICI = 166  # Ingeniería Civil Industrial: dura 14 semestres en la práctica (mifuturo_carreras)


def _estudiante(**extra):
    return dict(edad=20, estado="estudiando", edu="media", carrera_id=ICI, sueldo=0, rubro="", tipo_empleador="",
                nivel=0, antiguedad=0) | extra


def test_sin_estudiar_una_carrera_no_cambia_nada():
    """Regla dura: quien no estudia una carrera del catálogo parte como siempre, con 0 semestres."""
    for e in (_e(), _e(carrera_id=ICI), estado_inicial(Perfil.a_los_18(), pq()),
              _e(semestres_restantes=4, anos_en_carrera=2)):  # el dato solo cuenta si estudia
        assert (e["semestres_restantes"], e["anos_en_carrera"]) == (0, 0)


def test_quien_estudia_parte_con_lo_que_le_falta():
    assert pq().tabla("mifuturo_carreras", "duracion_real_semestres", "carrera_id", ICI) == 14
    e = _e(**_estudiante())  # supuesto: entró a los 18 y va al día
    assert (e["semestres_restantes"], e["anos_en_carrera"]) == (14 - 4, 2)
    e = _e(**_estudiante(semestres_restantes=4))  # "egreso esperado" en dos años: el CV manda
    assert (e["semestres_restantes"], e["anos_en_carrera"]) == (4, 5)
    e = _e(**_estudiante(anos_en_carrera=0))  # "cursando 1er año"
    assert (e["semestres_restantes"], e["anos_en_carrera"]) == (14, 0)
    e = _e(**_estudiante(edad=35))  # mayor que la carrera: igual le queda un año
    assert (e["semestres_restantes"], e["anos_en_carrera"]) == (2, 6)


def test_quien_estudia_ya_no_se_titula_al_primer_anio():
    """Antes todos partían en 0 semestres: el cierre del año 1 los titulaba."""
    v = Vida(_e(**_estudiante(semestres_restantes=4)), Dados(0, "t"), pq())
    v.vivir_anio(Inercia())
    assert v.e["estado"] == "estudiando" and v.e["semestres_restantes"] == 2
    v.vivir_anio(Inercia())
    assert v.e["estado"] != "estudiando" and v.e["edu"] == "universitaria"
