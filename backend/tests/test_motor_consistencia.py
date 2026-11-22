"""Consistencia del motor entre tu partida y tus copias, y dentro de un año.

- Las copias no heredan la variedad de cartas de tu partida (REPETIR_CARTA).
- Perder la pega a mitad de año (despido, cierre de la startup, reestructuración) o renunciar lleva a la misma
  cesantía, y el ingreso del año se prorratea por los meses con cada sueldo.
- El mes del despido queda fijo en la vida: las copias que se comparan desde la cesantía lo heredan.
- Un efecto `fija` con duración que sale dos años seguidos (el auge del cobre) se apaga cuando vence el último.
- El alza anual es de quien ya llevaba un año en su pega: quien entró este año gana lo que dijo su oferta.
"""

import pytest
from _motor_util import NADA, DadosGuion, Guion, pq, vida

from app.sim.motor import gemelos
from app.sim.motor.azar import Dados
from app.sim.motor.motor import FaltaEleccion
from app.sim.motor.perfil import Perfil
from app.sim.motor.politicas import Jugador

QUIETA = {"oferta_externa": "quedarse", "cesantia": "buscar", "oferta_en_cesantia": "rechazar"}
MES_7 = 0.5  # 1 + int(12 × 0,5): el séptimo mes


# ------------------------------------------------------------------ 1. la variedad es solo de tu partida
def test_las_copias_no_heredan_la_variedad_de_cartas_de_tu_partida():
    v = vida(Perfil())
    v.variedad = pq().k("REPETIR_CARTA")  # lo que hace partida.jugar con tu vida
    v.vivir_anio(Guion({"pedir_aumento": "esperar", **QUIETA}), carta="pedir_aumento")
    peso_base = dict(vida(Perfil()).cartas_posibles())["pedir_aumento"]
    assert dict(v.cartas_posibles())["pedir_aumento"] == pytest.approx(peso_base * pq().k("REPETIR_CARTA"))
    copia = v.clonar(Dados(0, 3))  # otro mundo
    assert copia.variedad == 1.0
    assert dict(copia.cartas_posibles())["pedir_aumento"] == pytest.approx(peso_base)


# ------------------------------------------------------------------ 2. perder la pega lleva a la cesantía
def test_si_la_startup_cierra_a_mitad_de_anio_cobras_hasta_ese_mes_y_buscas_desde_ahi():
    d = DadosGuion({"evento:startup_cierra": 0.0, "evento:startup_cierra:mes": MES_7})
    v = vida(Perfil(edad=30, tipo_empleador="startup", rubro="Información y comunicaciones", sueldo=1_000_000), d)
    reg = v.vivir_anio(Guion(QUIETA))
    assert [x["resultado"] for x in reg["eventos"] if x["evento"] == "startup_cierra"] == ["cierra"]
    assert [(x["decision"], x["origen"]) for x in reg["decisiones"]] == [("cesantia", "luego")]
    assert reg["meses_busqueda"] == list(range(7, 13))
    sueldo_al_cerrar = v.e["sueldo_ref"]  # el de ese momento, con el alza del año ya aplicada
    assert reg["plata"]["ganado"] == round(6 * sueldo_al_cerrar)  # enero a junio
    assert reg["plata"]["meses_sin_sueldo"] == 6 and v.meses_buscando == 6


def test_si_la_startup_cierra_al_terminar_el_anio_lo_trabajaste_entero():
    v = vida(Perfil(edad=30, tipo_empleador="startup", rubro="Información y comunicaciones", sueldo=1_000_000),
             DadosGuion(), cierra_en=1)
    reg = v.vivir_anio(Guion(QUIETA))
    assert v.e["estado"] == "buscando" and not v.cola  # la cesantía queda para el año siguiente
    assert reg["plata"]["ganado"] == round(12 * v.e["sueldo_ref"])
    assert v.vivir_anio(Guion(QUIETA))["decisiones"][0]["decision"] == "cesantia"


def test_quien_renuncia_busca_mes_a_mes_desde_enero():
    v = vida(Perfil(edad=35, sueldo=1_000_000), DadosGuion())
    reg = v.vivir_anio(Guion({"renunciar": "renunciar", **QUIETA}), carta="renunciar")
    assert [(x["decision"], x["origen"]) for x in reg["decisiones"]] == [("renunciar", "carta"), ("cesantia", "luego")]
    assert reg["meses_busqueda"] == list(range(1, 13))
    assert reg["plata"]["ganado"] == 0 and v.meses_buscando == 12


def test_despedido_en_julio_que_elige_emprender_cobra_su_sueldo_hasta_junio():
    d = DadosGuion({"evento:separacion_empleo": 0.0, "evento:separacion_empleo:mes": MES_7,
                    "dec:seguir_con_tu_empresa:seguir": 0.0})  # su empresa sigue
    v = vida(Perfil(edad=35, sueldo=1_000_000), d)
    reg = v.vivir_anio(Guion({**QUIETA, "cesantia": "emprender", "seguir_con_tu_empresa": "seguir"}))
    assert v.e["estado"] == "fundador" and v.e["sueldo"] > 0
    seis_meses = 6 * 1_000_000  # el despido va antes del alza: el sueldo de antes es el del año pasado
    assert reg["plata"]["ganado"] == round(seis_meses + 6 * v.e["sueldo"])


@pytest.mark.ia
def test_la_reestructuracion_por_ia_lleva_a_la_misma_cesantia_sin_descontar_el_sueldo_de_referencia():
    ev = pq().eventos["ia_reestructura"]
    cesante = next(r for r in ev["resultados"] if r["id"] == "cesante")
    despido = pq().eventos["separacion_empleo"]["resultados"][0]
    assert cesante["luego"] == despido["luego"] == "cesantia"
    assert [(x["var"], x["op"]) for x in cesante["efectos"]] == [(x["var"], x["op"]) for x in despido["efectos"]]


# ------------------------------------------------------------------ 6. el mes del despido es de la vida
def test_las_copias_que_se_comparan_desde_la_cesantia_heredan_el_mes_del_despido():
    d = DadosGuion({"evento:separacion_empleo": 0.0, "evento:separacion_empleo:mes": MES_7})
    v = vida(Perfil(edad=35, sueldo=1_000_000), d)
    v.iniciar_anio(con_cartas=False)
    with pytest.raises(FaltaEleccion):
        v.avanzar(Jugador([]))
    assert v.cola[0][:2] == ("decision", "cesantia") and v.mes_perdida == 7
    for g in range(8):  # cada copia tiene otros dados: antes, cada una sorteaba su propio mes
        copia = gemelos._vivir(v.clonar(Dados(5, g)), "cesantia", "buscar", {}, 1)
        anio = copia.historia[-1]
        assert anio["meses_busqueda"][0] == 7
        assert anio["plata"]["ganado"] >= round(6 * 1_000_000)  # enero a junio, con el sueldo de antes


# ------------------------------------------------------------------ 7. el auge del cobre se apaga
def test_un_fija_con_duracion_que_se_repite_vuelve_al_valor_de_antes_al_vencer_el_ultimo():
    auge = {"var": "auge_cobre", "op": "fija", "valor": 1, "duracion": 2}
    v = vida(Perfil(), DadosGuion())
    prendido = []
    for anio in range(4):
        v.iniciar_anio(con_cartas=False)
        if anio < 2:
            v._aplicar([auge], f"auge:{anio}")  # sale dos años seguidos
        v.avanzar(Guion(QUIETA))
        prendido.append(v.e["auge_cobre"])
    # el segundo auge dura hasta el cierre del tercer año; antes quedaba prendido para siempre
    assert prendido == [1, 1, 0, 0]


@pytest.mark.ia
def test_el_auge_del_cobre_dos_anios_seguidos_dura_tres_y_se_apaga():
    d = DadosGuion({(0, "evento:auge_cobre"): 0.0, (1, "evento:auge_cobre"): 0.0})
    v = vida(Perfil(), d)
    prendido = []
    for _ in range(5):
        reg = v.vivir_anio(Guion(QUIETA))
        prendido.append(reg["ia"]["auge_cobre"])
    assert prendido == [True, True, True, False, False]


# ------------------------------------------------------------------ 8. sin alza en la pega nueva
def test_si_te_despiden_y_te_recontratan_el_mismo_anio_no_hay_alza_anual_sobre_la_oferta():
    d = DadosGuion({"evento:separacion_empleo": 0.0, "evento:separacion_empleo:mes": 0.0,
                    "evento:oferta_cesante:mes2": 0.0})
    v = vida(Perfil(edad=35, sueldo=1_000_000), d)
    reg = v.vivir_anio(Guion({**QUIETA, "oferta_en_cesantia": "aceptar"}))
    assert v.e["estado"] == "empleado"
    assert "alza_anual" not in [x["evento"] for x in reg["eventos"]]
    oferta = next(x for x in reg["decisiones"] if x["decision"] == "oferta_en_cesantia")
    assert oferta["opcion"] == "aceptar"
    # la misma persona sin despido sí tiene su alza
    sigue = vida(Perfil(edad=35, sueldo=1_000_000), DadosGuion({"evento:separacion_empleo": NADA}))
    assert "alza_anual" in [x["evento"] for x in sigue.vivir_anio(Guion(QUIETA))["eventos"]]


def test_quien_se_cambia_por_una_oferta_gana_lo_que_dice_la_oferta_ese_anio():
    v = vida(Perfil(edad=35, sueldo=1_000_000), DadosGuion({"dec:oferta_externa:cambiar": 0.0}))
    reg = v.vivir_anio(Guion({"oferta_externa": "cambiar", **{k: x for k, x in QUIETA.items() if k != "oferta_externa"}}),
                       carta="oferta_externa")
    assert v.e["antiguedad"] == 1  # entró este año y cerró su primer año en la pega
    assert "alza_anual" not in [x["evento"] for x in reg["eventos"]]
