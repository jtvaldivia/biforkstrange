"""Paridad del compilador de expresiones (`Paquete.compilar`) con el evaluador de referencia.

El oráculo es `pq.ref.evaluar` (el evaluador que trae el paquete, que recorre el
árbol) y, para la gramática, valores calculados a mano.
"""

import math
import random

import pytest
from _motor_util import estado_al_azar, expresiones_del_paquete, n, pq

from app.sim.motor.azar import Flujo
from app.sim.motor.paquete import ErrorExpresion


class AzarEspejo:
    """Lo que el código compilado espera de `R`, sacado de un `random.Random` con las mismas
    llamadas y en el mismo orden que usa el evaluador de referencia."""

    def __init__(self, r: random.Random):
        self.r = r

    def u(self):
        return self.r.random()

    def uniforme(self, a, b):
        return self.r.uniform(a, b)

    def normal(self):
        return self.r.gauss(0, 1)

    def entero(self, a, b):
        return self.r.randint(int(a), int(b))

    def lognormal(self, p10, p50, p90):
        s = (math.log(p90) - math.log(p10)) / (2 * 1.2816)
        return math.exp(math.log(p50) + s * self.r.gauss(0, 1))


def _intento(f):
    try:
        return "ok", f()
    except Exception as x:  # noqa: BLE001 (se compara el tipo del error)
        return "error", type(x).__name__


def _iguales(a, b) -> bool:
    if a[0] != b[0]:
        return False
    if a[0] == "error":
        return a[1] == b[1]
    x, y = a[1], b[1]
    if isinstance(x, str) or isinstance(y, str):
        return type(x) is type(y) and x == y
    if isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y):
        return True
    return x == y


def _fila_al_azar(R):
    fila = R.choice(pq().ref.filas("mifuturo_carreras"))
    salida = {}
    for c, v in fila.items():
        try:
            salida[f"fila_{c}"] = float(v)
        except ValueError:
            salida[f"fila_{c}"] = v
    return salida


def test_el_catalogo_trae_todas_las_clases_de_expresion():
    """Si esto falla, la paridad de abajo estaría pasando sobre un catálogo vacío o mal leído."""
    exprs = expresiones_del_paquete()
    por_clase = {c: sum(1 for x in exprs if x[0] == c) for c in {x[0] for x in exprs}}
    assert set(por_clase) == {"cuando", "peso", "requisito", "prob", "valor", "efecto_cuando", "prob_anual", "prob_mensual",
                             "filtro"}
    assert len({x[2] for x in exprs if isinstance(x[2], str)}) >= 150
    assert por_clase["cuando"] == 40 + 14 + 2 and por_clase["peso"] == 40
    # la cesantía se vive mes a mes: dos eventos se sortean cada mes, el resto una vez al año
    assert por_clase["prob_anual"] == 14 and por_clase["prob_mensual"] == 2


def test_paridad_con_el_evaluador_de_referencia():
    """Cada expresión del paquete da lo mismo compilada que en el evaluador de referencia,
    en miles de estados al azar, incluidos los casos en que la referencia falla."""
    p = pq()
    R = random.Random(20261121)
    unicas: dict = {}
    for _, donde, expr, fila in expresiones_del_paquete():
        unicas.setdefault((expr, fila), donde)
    con_azar = {expr for (expr, _f) in unicas if isinstance(expr, str) and p.compilar(expr)[1]}
    assert len(con_azar) >= 15  # alza anual, ascensos, cesantía...
    sin_dados = random.Random(0)
    diferencias, comparadas, ambos_fallan, distintos_de_cero = [], 0, 0, 0
    for i in range(n(2000)):
        e = estado_al_azar(R)
        e_fila = {**e, **_fila_al_azar(R)}
        for (expr, fila), donde in unicas.items():
            estado = e_fila if fila else e
            if expr in con_azar:
                r_ref, r_comp = random.Random(i), random.Random(i)
                a = _intento(lambda: p.ref.evaluar(expr, estado, r_ref))
                b = _intento(lambda: p.evaluar(expr, estado, AzarEspejo(r_comp)))
                # misma cantidad de números consumidos: el siguiente también coincide
                if a[0] == "ok" and r_ref.random() != r_comp.random():
                    diferencias.append((donde, expr, "consumen distinta cantidad de azar"))
            else:
                a = _intento(lambda: p.ref.evaluar(expr, estado, sin_dados))
                b = _intento(lambda: p.evaluar(expr, estado, None))
            comparadas += 1
            ambos_fallan += a[0] == "error" and b[0] == "error"
            distintos_de_cero += a[0] == "ok" and a[1] not in (0, "")
            if not _iguales(a, b):
                diferencias.append((donde, expr, a, b))
    assert not diferencias, f"{len(diferencias)} diferencias; primeras: {diferencias[:5]}"
    assert comparadas >= n(2000) * 200
    assert ambos_fallan > 0, "ningún estado hizo fallar a la referencia: no se probó que fallen igual"
    assert distintos_de_cero > comparadas * 0.3


def _ks(a: list[float], b: list[float]) -> float:
    """Estadístico de Kolmogorov-Smirnov de dos muestras."""
    a, b = sorted(a), sorted(b)
    i = j = 0
    d = 0.0
    while i < len(a) and j < len(b):
        x = min(a[i], b[j])
        while i < len(a) and a[i] <= x:
            i += 1
        while j < len(b) and b[j] <= x:
            j += 1
        d = max(d, abs(i / len(a) - j / len(b)))
    return d


def test_expresiones_con_azar_tienen_la_misma_distribucion_con_los_dados_del_motor():
    """Con los dados reales (`Flujo`) cada expresión con azar reparte igual que la referencia."""
    p = pq()
    e = estado_al_azar(random.Random(3))
    e.update(estado="empleado", tipo_empleador="pyme", rubro="Comercio", sueldo=900000, sueldo_ref=900000,
             empresa_anos=2, hueco=0, sexo="m", anos_en_startup=5, edad=33)
    e = p.ref.derivar(e)
    con_azar = sorted({x for _, _, x, fila in expresiones_del_paquete()
                       if isinstance(x, str) and not fila and p.compilar(x)[1]})
    m = n(3000)
    critico = 1.95 * math.sqrt(2 / m)  # alfa = 0,001
    for expr in con_azar:
        ref_r, flujo = random.Random(11), Flujo(12)
        a = [float(p.ref.evaluar(expr, e, ref_r)) for _ in range(m)]
        b = [float(p.evaluar(expr, e, flujo)) for _ in range(m)]
        assert _ks(a, b) < critico, expr


# ------------------------------------------------------------------ gramática, con valores a mano
E0 = {"edad": 30, "sexo": "m", "edu": "universitaria", "vacio": "", "x": 2.5}
A_MANO = [
    ("2 - 3 - 4", -5), ("2 * 3 + 4 * 5", 26), ("(edad + 2) * 3", 96), ("10 / 4", 2.5), ("2 / 4 * 8", 4.0),
    ("-edad % 7", 5), ("7 % -3", -2), ("edad - -2", 32), ("+edad", 30), ("-(edad - 40)", 10), ("1 - 1 - 1", -1),
    ("pow(2, 10)", 1024), ("redondear(2.5)", 2), ("redondear(3.5)", 4), ("redondear(x)", 2), ("abs(-3.2)", 3.2),
    ("exp(0)", 1.0), ("ln(1)", 0.0), ("clamp(5, 0, 3)", 3), ("clamp(-1, 0, 3)", 0), ("clamp(2, 0, 3)", 2),
    ("min(4, 2, 9)", 2), ("max(4, 2, 9)", 9), ("min(3)", 3),
    ("1 < 2", 1), ("2 <= 2", 1), ("3 > 4", 0), ("edad >= 30", 1), ("edad == 30", 1), ("sexo != 'm'", 0),
    ("si(edad > 40, 'mayor', 'menor')", "menor"), ("si(vacio, 1, 2)", 2), ("si(sexo, 1, 2)", 1),
    ("si(0, 1 / 0, 7)", 7), ("si(1, 7, 1 / 0)", 7),
    ("y(1, 2, 3)", 1), ("y(1, 0, 1 / 0)", 0), ("y(1, vacio)", 0), ("o(0, vacio, 5)", 1), ("o(1, 1 / 0)", 1),
    ("o(0, 0)", 0), ("no(vacio)", 1), ("no(sexo)", 0), ("no(0)", 1),
    ("en(edu, 'media', 'universitaria')", 1), ("en(edu, 'media')", 0), ("en(edad, '30')", 0), ("en(edad, 30.0)", 1),
    ("falso()", 0), ("si(falso(), 1, 2)", 2),
    ("k('P_RECESION')", 0.08), ("k('P_SEPARACION', '30-44')", 0.066), ("k('ALZA_ASCENSO', 1)", 0.1),
    ("k('ASCENSO', 2)", 0.04), ("k('ASCENSO', 2.0)", 0.04), ("k('MULT_DESPIDO_RUBRO', 'Pesca submarina', 1)", 1),
    ("k('MULT_DESPIDO_RUBRO', 'Minería', 1)", 0.57),
    ("tabla('esi_perfil_edad_edu', 'p50', 'educacion', 'media', 'banda', '18-24')", 493073.0),
    ("tabla('esi_perfil_edad_edu', 'p90', 'banda', '50-54', 'educacion', edu)", 4101730.0),
    ("tabla_o(7, 'esi_perfil_edad_edu', 'p50', 'educacion', 'no hay', 'banda', '18-24')", 7),
    # celda vacía en el CSV (menos de 30 casos): tabla falla, tabla_o usa el respaldo
    ("tabla_o(0.5, 'sce_expectativas', 'p_empleado_4m', 'banda_edad', 'menor_62', 'estado', 'empleado')", 0.5),
    ("tabla_o(0.5, 'sce_expectativas', 'p_contraoferta', 'banda_edad', 'menor_62', 'estado', 'empleado')", 0.2626),
    ("q_muerte(70, 'm')", math.exp(-11.4101 + 0.10043 * 70)), ("q_muerte(200, 'h')", 0.6),
    ("luto('mama', 9)", 0),
]


@pytest.mark.parametrize(("expr", "esperado"), A_MANO)
def test_gramatica_con_valores_calculados_a_mano(expr, esperado):
    p = pq()
    compilado, referencia = p.evaluar(expr, E0), p.ref.evaluar(expr, E0)
    assert compilado == pytest.approx(esperado, rel=1e-12) if not isinstance(esperado, str) else compilado == esperado
    assert type(compilado) is type(referencia) and compilado == referencia


FALLAN = [
    ("1 / 0", ZeroDivisionError), ("edad % 0", ZeroDivisionError), ("ln(0)", ValueError),
    ("k('NO_EXISTE')", ErrorExpresion), ("k('P_SEPARACION', '99-100')", ErrorExpresion),
    ("k('MULT_DESPIDO_TIPO', vacio)", ErrorExpresion),
    ("tabla('esi_perfil_edad_edu', 'p50', 'educacion', 'no hay', 'banda', '18-24')", ErrorExpresion),
    ("tabla('sce_expectativas', 'p_empleado_4m', 'banda_edad', 'menor_62', 'estado', 'empleado')", ErrorExpresion),
    ("tabla_o(1, 'tabla_que_no_existe', 'p50')", KeyError),  # tabla_o solo perdona fila o celda faltante
    ("edad < sexo", TypeError), ("-sexo", TypeError), ("y(1, 1 / 0)", ZeroDivisionError),
    ("tabla_o(1 / 0, 'esi_perfil_edad_edu', 'p50', 'educacion', 'media', 'banda', '18-24')", ZeroDivisionError),
]


@pytest.mark.parametrize(("expr", "error"), FALLAN)
def test_ambos_fallan_en_los_mismos_casos(expr, error):
    p = pq()
    with pytest.raises(error):
        p.ref.evaluar(expr, E0)
    with pytest.raises(error):
        p.evaluar(expr, E0)


def test_variable_sin_valor_falla_en_los_dos():
    """La referencia avisa con ErrorExpresion; el compilado con KeyError. Ninguno inventa un valor."""
    p = pq()
    with pytest.raises(ErrorExpresion):
        p.ref.evaluar("no_declarada + 1", E0)
    with pytest.raises((ErrorExpresion, KeyError)):
        p.evaluar("no_declarada + 1", E0)


@pytest.mark.parametrize("expr", [
    "__import__('os')", "edad if 1 else 2", "1 < 2 < 3", 'k("P_RECESION")', "[1, 2]", "lambda: 1", "edad.real",
    "k(nombre='P_RECESION')", "(1).__class__", "edad and 1", "not edad", "print(1)", "R.u()", "_k('P_RECESION')",
    "edad ** 2", "edad // 2",
])
def test_lo_que_esta_fuera_de_la_gramatica_no_compila(expr):
    with pytest.raises((ErrorExpresion, SyntaxError)):
        pq().compilar(expr)


def test_los_numeros_literales_se_evaluan_tal_cual():
    p = pq()
    assert p.evaluar(1, {}) == 1 and p.evaluar(0.35, {}) == 0.35 and p.evaluar(0, {}) == 0
    assert p.compilar(0.35)[1] is False and p.compilar("azar() < 0.2")[1] is True
    assert p.compilar("k('P_RECESION')")[1] is False


def test_ninguna_condicion_ni_probabilidad_usa_azar():
    """El motor evalúa cuando, peso, requisito, prob y prob_anual sin dados: si el paquete
    pusiera azar ahí, reventaría. El azar solo puede estar en los efectos."""
    p = pq()
    for clase, donde, expr, _ in expresiones_del_paquete():
        if clase in ("cuando", "peso", "requisito", "prob", "prob_anual", "filtro") and isinstance(expr, str):
            assert not p.compilar(expr)[1], f"{clase} de {donde} usa azar"


