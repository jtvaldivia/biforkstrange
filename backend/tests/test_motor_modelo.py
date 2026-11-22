"""Decisiones del modelo que tomó el equipo (ver `docs/motor/TICKETS.md`).

1. El alza anual descuenta el ascenso promedio de la población, no el de la persona: ascender más paga.
2. Al fundador que ya tenía empresa se le respeta su sueldo declarado; MICRO_MEDIANA es para quien recién emprende.
3. El ingreso del independiente crece (o cae) como el de la cuenta propia de su edad en la ESI.
"""

import math
from dataclasses import replace

import pytest
from _motor_util import DadosGuion, Guion, n, pq, vida

from app.sim.motor.azar import Dados
from app.sim.motor.perfil import Perfil, estado_inicial
from app.sim.motor.politicas import Inercia

# Literales de parametros.json (no se importan del código bajo prueba)
ASCENSO_POBLACION = {"18-24": 0.056, "25-29": 0.061, "30-34": 0.061, "35-39": 0.055, "40-44": 0.05,
                     "45-49": 0.045, "50-54": 0.045}
ALZA_ASCENSO_MEDIA = (0.05 + 0.1) / 2
MICRO_MEDIANA = 400_000


# ------------------------------------------------------------------ 1. ascender más paga
def _alza(estado: dict, gemelo: int = 0) -> float:
    """El multiplicador de sueldo de alza_anual para un estado, con dados fijos."""
    expr = pq().eventos["alza_anual"]["resultados"][0]["efectos"][0]["valor"]
    return pq().evaluar(expr, estado, Dados(0, gemelo).flujo(0, "evento:alza_anual:alza"))


def test_el_alza_anual_no_depende_de_tu_propia_probabilidad_de_ascenso():
    e = vida(Perfil(edad=35)).e
    for g in range(20):
        assert _alza({**e, "prob_ascenso": 0.0}, g) == _alza({**e, "prob_ascenso": 0.4}, g)


def test_el_alza_anual_descuenta_el_ascenso_promedio_de_su_tramo_de_edad():
    """Sin ruido (todo en su valor central), el alza es el crecimiento ESI menos el ascenso promedio por su alza."""
    e = vida(Perfil(edad=35, tipo_empleador="pyme")).e
    expr = pq().eventos["alza_anual"]["resultados"][0]["efectos"][0]["valor"]
    sin_ruido = expr.replace("si(azar() < 0.9, 0.03 * azar_normal(), -0.05 + 0.08 * azar_normal())", "0")
    assert sin_ruido != expr
    for edad in (27, 35, 47):
        estado = pq().derivar({**e, "edad": edad, "recesion": 0, "anos_titulado": 10})
        # el alza tiene piso cero: en la misma pega el sueldo no baja
        esperado = 1 + max(0, estado["crecimiento_esi"] - ASCENSO_POBLACION[estado["banda7"]] * ALZA_ASCENSO_MEDIA)
        assert pq().evaluar(sin_ruido, estado) == pytest.approx(esperado)


def test_quien_asciende_mas_termina_ganando_mas():
    """Mismos dados, solo cambia el oficio (que sube la probabilidad de ascenso): antes el alza anual
    se lo quitaba entero y en promedio ganaban lo mismo."""
    diferencias, ascensos = [], [0, 0]
    for g in range(n(150)):
        finales = []
        for i, skill in enumerate((30, 80)):
            v = vida(Perfil(), Dados(0, g), skill=skill)
            v.vivir(Inercia(), 10)
            finales.append(v.sueldo_o_ultimo())
            ascensos[i] += sum(1 for a in v.historia for x in a["eventos"] if x["evento"] == "ascenso")
        if min(finales) > 0:
            diferencias.append(math.log(finales[1] / finales[0]))
    assert ascensos[1] > ascensos[0]
    assert sum(diferencias) / len(diferencias) > 0.01


# ------------------------------------------------------------------ 2. el sueldo declarado del fundador
FUNDADOR = Perfil(estado="fundador", empresa_anos=2, sueldo=1_400_000, tipo_empleador="")


def _sueldo_sobrevive() -> str:
    seguir = next(o for o in pq().decisiones["seguir_con_tu_empresa"]["opciones"] if o["id"] == "seguir")
    sobrevive = next(r for r in seguir["resultados"] if r["id"] == "sobrevive")
    return next(ef["valor"] for ef in sobrevive["efectos"] if ef["var"] == "sueldo")


def test_el_fundador_parte_de_su_sueldo_declarado_y_no_de_la_mediana():
    e = estado_inicial(FUNDADOR, pq())
    assert e["base_empresa"] == pytest.approx(1_400_000 / (1 + 2 / 4))
    assert estado_inicial(Perfil(), pq())["base_empresa"] == 0  # quien no es fundador no trae empresa
    # con la misma suerte, su empresa gana lo que declaró sobre lo que gana la de un microemprendedor mediano
    for g in range(10):
        dado = lambda: Dados(0, g).flujo(0, "dec:seguir_con_tu_empresa:seguir:sobrevive")  # noqa: E731
        suyo = pq().evaluar(_sueldo_sobrevive(), e, dado())
        mediano = pq().evaluar(_sueldo_sobrevive(), {**e, "base_empresa": 0}, dado())
        assert suyo / mediano == pytest.approx(1_400_000 / (1 + 2 / 4) / MICRO_MEDIANA)


def test_el_primer_anio_el_fundador_gana_en_la_mediana_lo_que_declaro():
    """Antes, declarar 1,4 o 4 millones daba lo mismo: unos 700 mil desde el primer año."""
    for sueldo in (1_400_000, 4_000_000):
        sueldos = []
        for g in range(n(200)):
            v = vida(replace(FUNDADOR, sueldo=sueldo), Dados(0, g))
            v.vivir_anio(Guion({"seguir_con_tu_empresa": "seguir"}))
            if v.historia[0]["decisiones"][0]["resultado"] == "sobrevive":
                sueldos.append(v.e["sueldo"])
        assert sorted(sueldos)[len(sueldos) // 2] == pytest.approx(sueldo, rel=0.15)


def test_quien_recien_emprende_gana_como_un_microemprendedor_aunque_ya_haya_tenido_empresa():
    """Partir una empresa nueva vuelve base_empresa a 0: su ganancia sale de MICRO_MEDIANA, no de la anterior."""
    guion = Guion({"emprender": "emprender", "seguir_con_tu_empresa": "seguir"})
    sueldos = []
    for base in (0, 2_000_000):
        v = vida(Perfil(edad=35), DadosGuion({"dec:seguir_con_tu_empresa:seguir": 0.0}), base_empresa=base)
        v.vivir_anio(guion, carta="emprender")
        assert v.e["estado"] == "fundador" and v.e["base_empresa"] == 0
        sueldos.append(v.e["sueldo"])
    assert sueldos[0] == sueldos[1] > 0


# ------------------------------------------------------------------ 3. el ingreso del independiente
# p50 de cuenta propia en tablas/esi_ingreso_categoria_formalidad.csv
CUENTA_PROPIA_FORMAL = {"30-34": 667416, "35-39": 629303, "40-44": 798872}
CUENTA_PROPIA_INFORMAL = {"18-24": 199496, "25-29": 300127}


@pytest.mark.parametrize("edad, formal, esperado", [
    (32, 1, (CUENTA_PROPIA_FORMAL["35-39"] / CUENTA_PROPIA_FORMAL["30-34"]) ** (1 / 5) - 1),  # cae: −1,2%
    (37, 1, (CUENTA_PROPIA_FORMAL["40-44"] / CUENTA_PROPIA_FORMAL["35-39"]) ** (1 / 5) - 1),  # sube: +4,9%
    (20, 0, 0.06),  # informal de 18-24 a 25-29 sube 8,5% al año: queda en el tope
    (52, 1, 0.0),   # 50-54 es la última banda de la tabla
])
def test_el_crecimiento_por_cuenta_propia_sale_de_la_esi_por_edad(edad, formal, esperado):
    e = vida(Perfil(edad=edad, estado="independiente", sueldo=700_000, tipo_empleador=""), formal=formal).e
    assert e["crecimiento_cuenta_propia"] == pytest.approx(esperado)


def test_el_independiente_recibe_el_alza_de_su_edad_cada_anio():
    """Antes su ingreso quedaba igual diez años."""
    v = vida(Perfil(edad=37, estado="independiente", sueldo=700_000, tipo_empleador=""), DadosGuion())
    crecimiento = (CUENTA_PROPIA_FORMAL["40-44"] / CUENTA_PROPIA_FORMAL["35-39"]) ** (1 / 5) - 1
    reg = v.vivir_anio(Guion())
    assert v.e["estado"] == "independiente"
    assert "alza_independiente" in {x["evento"] for x in reg["eventos"]}
    assert v.e["sueldo"] == pytest.approx(700_000 * (1 + crecimiento))


def test_el_alza_por_cuenta_propia_no_le_llega_al_empleado():
    reg = vida(Perfil(edad=37), DadosGuion()).vivir_anio(Guion())
    assert "alza_independiente" not in {x["evento"] for x in reg["eventos"]}
