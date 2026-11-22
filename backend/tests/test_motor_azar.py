"""Los dados (`azar.py`): repetibles, uniformes, independientes entre sitios, y `elegir` respeta los pesos.

Las tolerancias salen del tamaño de muestra: 4 desvíos estándar del estimador.
"""

import math
from statistics import NormalDist, fmean, pstdev

import pytest
from _motor_util import n, z_binomial

from app.sim.motor.azar import Dados, Flujo

Z = 4.0


def _correlacion(a: list[float], b: list[float]) -> float:
    ma, mb = fmean(a), fmean(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / len(a)
    return cov / (pstdev(a) * pstdev(b))


def _chi2_uniforme(valores: list[float], cajas: int = 20) -> float:
    cuenta = [0] * cajas
    for v in valores:
        cuenta[min(cajas - 1, int(v * cajas))] += 1
    esperado = len(valores) / cajas
    return sum((c - esperado) ** 2 / esperado for c in cuenta)


CHI2_19_AL_999 = 43.82  # cuantil 0,999 de chi cuadrado con 19 grados de libertad


def test_mismo_sorteo_mismo_numero():
    a, b = Dados(7, 3), Dados(7, 3)
    for anio in range(5):
        for sitio in ("carta", "evento:recesion", "dec:renunciar:renunciar"):
            assert a.u(anio, sitio) == b.u(anio, sitio)
            assert a.u(anio, sitio) == a.u(anio, sitio)  # pedirlo dos veces no lo gasta
            assert a.elegir(anio, sitio, [1, 2, 3]) == b.elegir(anio, sitio, [1, 2, 3])
            fa, fb = a.flujo(anio, sitio), b.flujo(anio, sitio)
            assert [fa.u(), fa.normal(), fa.uniforme(2, 5), fa.entero(1, 9), fa.lognormal(1, 2, 8)] == \
                   [fb.u(), fb.normal(), fb.uniforme(2, 5), fb.entero(1, 9), fb.lognormal(1, 2, 8)]


def test_el_orden_en_que_se_piden_no_cambia_los_numeros():
    a, b = Dados(1, "tu"), Dados(1, "tu")
    sitios = [(y, s) for y in range(4) for s in ("carta", "evento:ascenso", "evento:ascenso:res", "rubro")]
    directo = {k: a.u(*k) for k in sitios}
    inverso = {k: b.u(*k) for k in reversed(sitios)}
    assert directo == inverso


def test_cada_parte_de_la_clave_cambia_el_numero():
    base = Dados(1, 2).u(3, "evento:ascenso")
    otros = [Dados(9, 2).u(3, "evento:ascenso"), Dados(1, 8).u(3, "evento:ascenso"), Dados(1, 2).u(4, "evento:ascenso"),
             Dados(1, 2).u(3, "evento:ascenso:res"), Dados(1, "2").u(3, "evento:ascens"),
             Dados(12, 3).u(3, "evento:ascenso"), Dados(1, 23).u(3, "evento:ascenso"), Dados(1, 2).u(33, "evento:ascenso"),
             Dados(1, "tu").u(3, "evento:ascenso")]
    assert len({base, *otros}) == len(otros) + 1
    # las claves no se pegan: (1, 23, 4) no es (12, 3, 4) ni (1, 2, 34)
    assert len({Dados(1, 23).u(4, "x"), Dados(12, 3).u(4, "x"), Dados(1, 2).u(34, "x"), Dados(123, 4).u(0, "x")}) == 4
    # el flujo de un sitio no es el número del sitio
    assert Dados(1, 2).flujo(3, "evento:ascenso").u() != base


def test_uniformidad_entre_gemelos_anios_y_sitios():
    m = n(20000)
    por_gemelo = [Dados(5, g).u(2, "evento:separacion_empleo") for g in range(m)]
    por_anio = [Dados(5, 0).u(a, "evento:separacion_empleo") for a in range(m)]
    por_sitio = [Dados(5, 0).u(2, f"dec:{i}:x") for i in range(m)]
    por_semilla = [Dados(s, "tu").u(0, "carta") for s in range(m)]
    for valores in (por_gemelo, por_anio, por_sitio, por_semilla):
        assert all(0.0 <= v < 1.0 for v in valores)
        assert abs(fmean(valores) - 0.5) < Z * math.sqrt(1 / 12 / m)
        assert abs(pstdev(valores) ** 2 - 1 / 12) < Z * math.sqrt(1 / 180 / m)
        assert _chi2_uniforme(valores) < CHI2_19_AL_999


PARES_DE_SITIOS = [
    ("evento:separacion_empleo", "evento:separacion_empleo:res"),  # que pase y cuál resultado
    ("evento:ascenso", "evento:separacion_empleo"),
    ("evento:recesion", "evento:separacion_empleo"),
    ("carta", "dec:renunciar:renunciar"),
    ("dec:unirse_a_startup:ir", "dec:unirse_a_startup:quedarse"),
    ("elige:cesantia", "dec:cesantia:rapido"),
    ("evento:oferta_llega", "dec:oferta_externa:cambiar"),
]


@pytest.mark.parametrize(("s1", "s2"), PARES_DE_SITIOS)
def test_independencia_entre_sitios(s1, s2):
    m = n(20000)
    a = [Dados(0, g).u(1, s1) for g in range(m)]
    b = [Dados(0, g).u(1, s2) for g in range(m)]
    assert abs(_correlacion(a, b)) < Z / math.sqrt(m)
    # y tampoco coinciden en una tabla de 4 x 4 (dependencias que la correlación lineal no ve)
    tabla = [[0] * 4 for _ in range(4)]
    for x, y in zip(a, b):
        tabla[int(x * 4)][int(y * 4)] += 1
    chi2 = sum((c - m / 16) ** 2 / (m / 16) for fila in tabla for c in fila)
    assert chi2 < 37.70  # cuantil 0,999 con 15 grados de libertad


def test_independencia_entre_anios_gemelos_y_flujo():
    m = n(20000)
    este = [Dados(0, g).u(3, "evento:ascenso") for g in range(m)]
    siguiente_anio = [Dados(0, g).u(4, "evento:ascenso") for g in range(m)]
    gemelo_vecino = [Dados(0, g + 1).u(3, "evento:ascenso") for g in range(m)]
    otra_semilla = [Dados(1, g).u(3, "evento:ascenso") for g in range(m)]
    flujo = [Dados(0, g).flujo(3, "evento:ascenso").u() for g in range(m)]
    jugador = [Dados(g, "tu").u(3, "evento:ascenso") for g in range(m)]
    for otro in (siguiente_anio, gemelo_vecino, otra_semilla, flujo, jugador):
        assert abs(_correlacion(este, otro)) < Z / math.sqrt(m)


def test_elegir_respeta_los_pesos():
    m = n(20000)
    pesos = [0.5, 0.0, 1.5, 3.0, 0.0]
    cuenta = [0] * len(pesos)
    for g in range(m):
        cuenta[Dados(2, g).elegir(0, "carta", pesos)] += 1
    assert cuenta[1] == 0 and cuenta[4] == 0  # peso cero no sale nunca
    for c, p in zip(cuenta, pesos):
        if p:
            assert abs(z_binomial(c, m, p / sum(pesos))) < Z


def test_elegir_es_el_mismo_dado_que_u():
    """`elegir` corta el intervalo [0, 1) en tramos proporcionales a los pesos, en orden."""
    for g in range(300):
        d = Dados(4, g)
        u = d.u(1, "s")
        assert d.elegir(1, "s", [0.2, 0.3, 0.5]) == (0 if u < 0.2 else 1 if u < 0.5 else 2)
        assert d.elegir(1, "s", [2, 3, 5]) == d.elegir(1, "s", [0.2, 0.3, 0.5])  # no hace falta normalizar
        assert d.elegir(1, "s", [7]) == 0


def test_elegir_sin_masa_es_un_error():
    with pytest.raises(ValueError, match="sin masa"):
        Dados(0, 0).elegir(0, "carta", [0, 0])
    with pytest.raises(ValueError, match="sin masa"):
        Dados(0, 0).elegir(0, "carta", [])


def test_flujo_reparte_como_dice_cada_funcion():
    m = n(20000)
    f = Flujo(123)
    us = [f.u() for _ in range(m)]
    assert _chi2_uniforme(us) < CHI2_19_AL_999
    unif = [f.uniforme(0.85, 1.02) for _ in range(m)]
    assert min(unif) >= 0.85 and max(unif) < 1.02
    assert abs(fmean(unif) - 0.935) < Z * 0.17 / math.sqrt(12 * m)
    normales = [f.normal() for _ in range(m)]
    assert abs(fmean(normales)) < Z / math.sqrt(m)
    assert abs(pstdev(normales) - 1) < Z / math.sqrt(2 * m)
    assert abs(z_binomial(sum(1 for x in normales if x < -1.2816), m, 0.10)) < Z
    enteros = [f.entero(1, 4) for _ in range(m)]
    assert set(enteros) == {1, 2, 3, 4}  # los dos extremos entran
    for k in (1, 2, 3, 4):
        assert abs(z_binomial(enteros.count(k), m, 0.25)) < Z
    # lognormal por percentiles: 10% bajo p10, la mitad bajo p50, 10% sobre p90
    logs = [f.lognormal(2_000_000, 10_000_000, 50_000_000) for _ in range(m)]
    assert abs(z_binomial(sum(1 for x in logs if x < 2_000_000), m, 0.10)) < Z
    assert abs(z_binomial(sum(1 for x in logs if x < 10_000_000), m, 0.50)) < Z
    assert abs(z_binomial(sum(1 for x in logs if x > 50_000_000), m, 0.10)) < Z


def test_lognormal_asimetrica_respeta_la_mediana_y_el_ancho():
    """Con p10 y p90 asimétricos (2, 10 y 60 millones) la referencia fija la mediana
    y el ancho p90/p10; los extremos no pueden calzar los dos a la vez."""
    m = n(20000)
    f = Flujo(5)
    logs = [math.log(f.lognormal(2e6, 1e7, 6e7)) for _ in range(m)]
    sigma = (math.log(6e7) - math.log(2e6)) / (2 * 1.2816)
    assert abs(fmean(logs) - math.log(1e7)) < Z * sigma / math.sqrt(m)
    assert abs(pstdev(logs) - sigma) < Z * sigma / math.sqrt(2 * m)
    assert NormalDist().inv_cdf(0.9) == pytest.approx(1.2816, abs=1e-4)
