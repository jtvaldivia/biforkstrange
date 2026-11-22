"""T7: el paso laboral contra ELSOC y las metas del paquete.

Los tests fijan lo que hoy cuadra. Las brechas conocidas (`BRECHAS`) no se testean;
solo se exige que toda fila justa esté clasificada.
Detalle y números en docs/trayectoria-v1/VALIDACION.md.
"""

import numpy as np
import pytest

from app.sim import validation as v
from app.sim.tables import BANDAS, tablas

N = 20_000

# Filas de `comparar()` (promedio de grupos) donde el motor actual queda dentro de tolerancia.
CUADRA = [
    "elsoc_e_a_d_30-44",
    "elsoc_e_a_d_45-59",
    "elsoc_e_a_i_18-29",
    "esi_desocupacion_25-29",
    "esi_desocupacion_30-34",
    "esi_desocupacion_35-39",
    "esi_desocupacion_40-44",
    "esi_desocupacion_45-49",
    # no validan (la meta sale de la misma tabla EPS que el motor usa), pero fijan consistencia
    "eps_cambio_18-29",
    "eps_cambio_30-44",
    "eps_cambio_45-59",
    "eps_sigue_cesante",
]

SIN_RETORNO_EN_EL_ANIO = "quien cae en cesantía queda sin empleo todo el año; con la sobrevida de la EPS solo ~52% sigue al cierre"
INACTIVIDAD_BAJA = "la EPS da ~1% anual de salida a inactividad desde los 30; ELSOC mide ~5%"
RETORNO_RAPIDO = "1 − sigue_12m se aplica a todo el stock sin empleo, lleve lo que lleve; ELSOC mide un retorno mucho más lento"
BRECHAS = {
    "elsoc_e_a_d_18-29": SIN_RETORNO_EN_EL_ANIO,
    "elsoc_e_a_i_30-44": INACTIVIDAD_BAJA,
    "elsoc_e_a_i_45-59": INACTIVIDAD_BAJA,
    "elsoc_e_a_sin_45-59": INACTIVIDAD_BAJA,
    "elsoc_sin_a_e_18-29": RETORNO_RAPIDO,
    "elsoc_sin_a_e_30-44": RETORNO_RAPIDO,
    "elsoc_sin_a_e_45-59": RETORNO_RAPIDO,
    "elsoc_sin_empleo_18-29": RETORNO_RAPIDO,
    "elsoc_sin_empleo_30-44": INACTIVIDAD_BAJA + "; además " + RETORNO_RAPIDO,
    "elsoc_sin_empleo_45-59": INACTIVIDAD_BAJA + "; además " + RETORNO_RAPIDO,
    "esi_desocupacion_18-24": "el gemelo parte empleado a los 18; en la ESI 36% de los desocupados de 18-24 busca su primer trabajo",
}
# A menos de 0,3 puntos del límite de tolerancia: ni se fijan ni se marcan como brecha.
AL_LIMITE = {"elsoc_e_a_sin_18-29", "elsoc_e_a_sin_30-44"}


@pytest.fixture(scope="module")
def resultado() -> dict:
    return v.comparar(None, n=N, seed=0)


@pytest.fixture(scope="module")
def filas(resultado) -> dict:
    return {f["id"]: f for f in resultado["filas"]}


def test_todas_las_filas_justas_estan_clasificadas(filas):
    justas = {i for i, f in filas.items() if f["justa"]}
    assert justas <= set(CUADRA) | set(BRECHAS) | AL_LIMITE


@pytest.mark.parametrize("fila", CUADRA)
def test_cuadra(filas, fila):
    f = filas[fila]
    assert abs(f["errores"]["actual"]) <= f["tolerancia"], f


# --- el arnés mismo


def test_referencia_elsoc():
    for b, m in v.matriz_elsoc().items():
        assert np.allclose(m.sum(axis=1), 1, atol=2e-3), b
    ref = v.referencia_elsoc()
    for b in BANDAS:
        r = ref[b]
        assert r["o_a_sin"] == pytest.approx(r["o_a_d"] + r["o_a_i"])
        # el retorno de quien salió de un empleo queda entre el de inactivos y el de cesantes
        assert r["i_a_o"] < r["sin_a_o_ex_ocupado"] < r["d_a_o"]
        assert 0 < r["sin_empleo_ex_ocupado"] < 0.5


def test_sobrevida_cesantia():
    sv = v.sobrevida_cesantia()
    # 18-29: S3 0.565, S6 0.467, S12 0.298, S24 0.183
    assert sv["m1"][0] == pytest.approx((1 + 2 * 0.565 + 3 * 0.467 + 2 * 0.298) / 8)
    assert sv["f1"][0] == pytest.approx(1 - ((0.298 + 0.183) / 2) / sv["m1"][0])
    assert sv["f2"][0] == pytest.approx(1 - 0.183 / 0.298)
    # la salida se frena con el tiempo, y siempre es más lenta que la que usa el motor
    assert (sv["f2"] < sv["f1"]).all()
    assert (sv["f1"] < 1 - tablas().p_sigue_cesante_12m).all()


def test_la_hipotesis_del_paso_anual_explica_la_cesantia():
    """Tasa EPS de caer en cesantía × m1 queda a ~1 punto de ELSOC O→D, sin simular nada."""
    t, sv, ref = tablas(), v.sobrevida_cesantia(), v.referencia_elsoc()
    for i, b in enumerate(BANDAS):
        assert t.p_cesantia[i] * sv["m1"][i] == pytest.approx(ref[b]["o_a_d"], abs=0.012)


@pytest.mark.parametrize("edad", [24, 37, 52])
def test_el_paso_del_arnes_reproduce_al_motor(edad):
    """Las variantes parten de una copia del paso; con los interruptores apagados mide lo mismo."""
    motor = v.medir_regimen(v.paso_actual, edad, None, n=N, quema=15, anios=10, seed=1)
    copia = v.medir_regimen(v.paso_equivalente, edad, None, n=N, quema=15, anios=10, seed=2)
    for k in ("e_a_sin", "e_a_d", "e_a_i", "sin_empleo", "cambio_directo", "nuevos_empleos"):
        assert copia[k] == pytest.approx(motor[k], abs=0.006), k
    assert copia["sin_a_e"] == pytest.approx(motor["sin_a_e"], abs=0.02)


def test_regimen_del_motor_es_el_de_las_tablas():
    t, b, g = tablas(), 1, 2
    m = v.medir_regimen(v.paso_actual, 37, g, n=N, seed=3)
    sale = (t.p_cesantia[b] + t.p_inactividad[b]) * t.mult_rotacion[g]
    vuelve = 1 - t.p_sigue_cesante_12m[b]
    assert m["e_a_sin"] == pytest.approx(sale, abs=0.004)
    assert m["sin_a_e"] == pytest.approx(vuelve, abs=0.02)
    assert m["sin_empleo"] == pytest.approx(sale / (sale + vuelve), abs=0.005)


def test_variantes(resultado, filas):
    """Lo que sostiene la recomendación del informe."""
    todas, elsoc, esi = (v.error_medio(resultado, p) for p in ("", "elsoc", "esi"))
    # B baja el error contra ELSOC a menos de la mitad; A sola no mejora y empeora la ESI
    assert elsoc["B"] < 0.5 * elsoc["actual"]
    assert todas["A"] > todas["actual"]
    assert esi["A"] > esi["actual"] + 0.02
    # B deja el retorno al empleo dentro de tolerancia en los tres tramos
    assert all(filas[f"elsoc_sin_a_e_{b}"]["dentro"]["B"] for b in BANDAS)
    # y no arregla la salida a inactividad desde los 30: eso no depende del paso
    assert not filas["elsoc_e_a_i_30-44"]["dentro"]["B"]
    assert not filas["elsoc_e_a_i_45-59"]["dentro"]["B"]
    reg = resultado["regimen"]["B"]
    assert all(reg[b]["sin_a_e_mas_de_un_anio"] < reg[b]["sin_a_e_primer_anio"] for b in BANDAS)
