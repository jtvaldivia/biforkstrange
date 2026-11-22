"""Validación del paso laboral contra datos chilenos que el motor no usó (T7).

Qué hay aquí:

- Referencias: la matriz anual ELSOC (ocupado / desocupado / inactivo) y las metas
  del paquete (`data/validacion_referencias.json`). El motor no lee ninguna.
- Pasos: `paso_actual` envuelve `labor.advance` tal cual; `paso_variante_a` y
  `paso_variante_b` son alternativas que solo viven en este módulo.
- Medidas: `medir_regimen` (edad fija, grupo fijo), `medir_cohorte` (18 a 49) y
  `medir_cohorte_motor` (el motor completo con la decisión "seguir").
- `comparar()` arma la tabla; `python -m app.sim.ocupacional.validation` la imprime.

Definiciones que importan al comparar:

- El motor tiene un solo flag `desempleado` que junta cesantía e inactividad.
  ELSOC los separa (D, I) y la desocupación de la ESI es D / (O + D), sin inactivos.
- Para separar D de I en el motor, el arnés etiqueta a cada persona que pierde el
  empleo como inactiva con probabilidad p_inactividad / (p_cesantia + p_inactividad)
  de su tramo. Es exacto en esperanza porque el motor trata igual a ambas.
- ELSOC incluye gente que nunca ha trabajado (estudiantes, labores de casa); el
  gemelo siempre parte con empleo. Por eso el stock ELSOC de "sin empleo" no es
  comparable directo: se usa el que implica la matriz para quien sale de un empleo
  (`referencia_elsoc`).
"""

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from app.sim.ocupacional import labor
from app.sim.ocupacional.engine import simulate
from app.sim.ocupacional.state import State, Twin
from app.sim.ocupacional.tables import BANDAS, DATA_DIR, N_GRUPOS, banda_idx, tablas

EDAD_REGIMEN = {"18-29": 24, "30-44": 37, "45-59": 52}  # punto medio de cada tramo EPS
BANDAS_ESI = ("18-24", "25-29", "30-34", "35-39", "40-44", "45-49")
VARIANTES = ("actual", "A", "B")

# Tolerancias. 0.03 es la del paquete para todas sus metas de tasas; se usa la misma
# para las filas ELSOC con origen O (n de 900 a 2.300 pares, error estándar ~0.01).
# El retorno al empleo se apoya en las filas D e I (n de 135 a 800, y el índice del
# paquete advierte "muestras chicas en la fila D"): 0.08, unos dos errores estándar.
TOL = 0.03
TOL_RETORNO = 0.08


# --------------------------------------------------------------------------- referencias


@lru_cache(maxsize=1)
def referencias() -> dict:
    with open(DATA_DIR / "validacion_referencias.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def matriz_elsoc() -> dict[str, np.ndarray]:
    """Matriz anual ELSOC por tramo: [origen, destino] con orden O, D, I."""
    orden = {"O": 0, "D": 1, "I": 2}
    m = {b: np.zeros((3, 3)) for b in BANDAS}
    with open(DATA_DIR / "elsoc_transiciones_actividad.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            m[r["banda"]][orden[r["origen"]], orden[r["destino"]]] = float(r["prob"])
    return m


def referencia_elsoc() -> dict[str, dict[str, float]]:
    """Lo que dice ELSOC, en las unidades del motor, para alguien que tenía empleo.

    `sin_a_o_ex_ocupado` y `sin_empleo_ex_ocupado` no están en la tabla: se derivan
    suponiendo que la matriz es de Markov. Quien sale de O entra a D o I en la
    proporción de la fila O y se mueve entre D e I hasta volver a O. T es el número
    esperado de años fuera; la tasa anual de retorno del stock es 1/T y la proporción
    sin empleo en régimen es s·T / (1 + s·T), con s = P(O → D o I).
    """
    out = {}
    for b, m in matriz_elsoc().items():
        s = m[0, 1] + m[0, 2]
        entrada = m[0, 1:] / s
        anios_fuera = entrada @ np.linalg.inv(np.eye(2) - m[1:, 1:]) @ np.ones(2)
        out[b] = {
            "o_a_sin": float(s),
            "o_a_d": float(m[0, 1]),
            "o_a_i": float(m[0, 2]),
            "d_a_o": float(m[1, 0]),
            "i_a_o": float(m[2, 0]),
            "d_a_d": float(m[1, 1]),
            "sin_a_o_ex_ocupado": float(1 / anios_fuera),
            "sin_empleo_ex_ocupado": float(s * anios_fuera / (1 + s * anios_fuera)),
        }
    return out


@lru_cache(maxsize=1)
def sobrevida_cesantia() -> dict[str, np.ndarray]:
    """Columnas de `eps_cesantia_duracion` y lo que las variantes derivan de ellas.

    S(m) = proporción que sigue cesante a los m meses, lineal entre los puntos de
    la tabla (0, 3, 6, 12, 24).

    - m1: promedio de S entre 0 y 12 meses = (1 + 2·S3 + 3·S6 + 2·S12) / 8.
      Es P(seguir cesante al cierre del año) para quien cae en un mes al azar.
    - m2: promedio de S entre 12 y 24 meses = (S12 + S24) / 2.
    - f1 = 1 − m2/m1: P(volver durante el año) para quien empezó el año sin empleo
      habiendo caído el año anterior (lleva entre 0 y 12 meses).
    - f2 = 1 − S24/S12: lo mismo para quien lleva más de un año (el riesgo de salida
      de los meses 12 a 24, supuesto constante de ahí en adelante).
    """
    with open(DATA_DIR / "eps_cesantia_duracion.csv", encoding="utf-8", newline="") as f:
        filas = {r["banda"]: r for r in csv.DictReader(f)}
    s3, s6, s12, s24 = (
        np.array([float(filas[b][c]) for b in BANDAS]) for c in ("sigue_3m", "sigue_6m", "sigue_12m", "sigue_24m")
    )
    m1 = (1 + 2 * s3 + 3 * s6 + 2 * s12) / 8
    m2 = (s12 + s24) / 2
    return {"s12": s12, "s24": s24, "m1": m1, "m2": m2, "f1": 1 - m2 / m1, "f2": 1 - s24 / s12}


def pesos_grupo() -> np.ndarray:
    """Reparto de los ocupados chilenos por grupo ocupacional (ESI 2025, 18-54)."""
    p = referencias()["esi_peso_grupo_ocupacional"]
    w = np.array([p[str(g)] for g in range(N_GRUPOS)])
    return w / w.sum()


# --------------------------------------------------------------------------- pasos


@dataclass
class Anio:
    """Qué pasó en el año, con el detalle que el arnés necesita (máscaras de n)."""

    cayo_cesantia: np.ndarray  # tenía empleo y cayó en cesantía (aunque vuelva en el año)
    cayo_inactividad: np.ndarray  # tenía empleo y salió a inactividad
    retorno: np.ndarray  # cayó en cesantía y encontró empleo antes del cierre
    directo: np.ndarray  # cambió de empleador sin cesantía entremedio
    reempleo: np.ndarray  # empezó el año sin empleo y lo terminó con empleo


Paso = Callable[[State, np.random.Generator], Anio]


def paso_actual(state: State, rng: np.random.Generator) -> Anio:
    """`labor.advance` sin tocar. Solo agrega la etiqueta cesante / inactivo."""
    t = tablas()
    b = banda_idx(state.edad)
    antes = state.desempleado.copy()
    year = labor.advance(state, rng)
    share_inactivo = t.p_inactividad[b] / (t.p_cesantia[b] + t.p_inactividad[b])
    a_inactividad = year.perdio_empleo & (rng.random(antes.shape[0]) < share_inactivo)
    return Anio(
        cayo_cesantia=year.perdio_empleo & ~a_inactividad,
        cayo_inactividad=a_inactividad,
        retorno=np.zeros_like(antes),
        directo=year.nuevo_empleo & ~antes,
        reempleo=year.nuevo_empleo & antes,
    )


def _paso_alternativo(
    state: State, rng: np.random.Generator, *, retorno_en_anio: bool, reempleo_por_duracion: bool
) -> Anio:
    """Mismo paso que `labor.advance` (sin desgaste ni decisiones) con dos interruptores.

    Con ambos apagados reproduce al motor; `test_validation` lo verifica.
    Lee `state.extra["anios_sin_empleo"]` (cierres de año seguidos sin empleo).
    """
    t, sv = tablas(), sobrevida_cesantia()
    b = banda_idx(state.edad)
    n = state.sueldo.shape[0]
    empleado = ~state.desempleado
    mult = t.mult_rotacion[state.ocupacion]

    p_ces = t.p_cesantia[b] * mult
    p_sale = np.clip(p_ces + t.p_inactividad[b] * mult, 0, 1)
    p_directo = np.minimum(t.p_cambio_directo[b] * mult, 1 - p_sale)
    u = rng.random(n)
    cayo_cesantia = empleado & (u < p_ces)
    cayo_inactividad = empleado & (u >= p_ces) & (u < p_sale)
    directo = empleado & (u >= p_sale) & (u < p_sale + p_directo)

    retorno = np.zeros(n, dtype=bool)
    if retorno_en_anio:
        retorno = cayo_cesantia & (rng.random(n) < 1 - sv["m1"][b])

    if reempleo_por_duracion:
        p_reempleo = np.where(state.extra["anios_sin_empleo"] <= 1, sv["f1"][b], sv["f2"][b])
    else:
        p_reempleo = 1 - t.p_sigue_cesante_12m[b]
    reempleo = state.desempleado & (rng.random(n) < p_reempleo)

    nuevo = directo | reempleo | retorno
    state.ocupacion = np.where(nuevo, labor._sortear_grupo(state.ocupacion, rng), state.ocupacion)
    state.desempleado = (state.desempleado & ~reempleo) | (cayo_cesantia & ~retorno) | cayo_inactividad
    state.antiguedad = np.where(nuevo | state.desempleado, 0.0, state.antiguedad + 1)
    state.n_empleos = state.n_empleos + nuevo
    return Anio(cayo_cesantia, cayo_inactividad, retorno, directo, reempleo)


def paso_equivalente(state: State, rng: np.random.Generator) -> Anio:
    """Control del arnés: debe medir lo mismo que `paso_actual`."""
    return _paso_alternativo(state, rng, retorno_en_anio=False, reempleo_por_duracion=False)


def paso_variante_a(state: State, rng: np.random.Generator) -> Anio:
    """A: quien cae en cesantía durante el año solo queda sin empleo al cierre con
    probabilidad m1; el resto volvió a trabajar dentro del año. La salida de quien
    ya partió el año sin empleo no cambia (1 − sigue_12m)."""
    return _paso_alternativo(state, rng, retorno_en_anio=True, reempleo_por_duracion=False)


def paso_variante_b(state: State, rng: np.random.Generator) -> Anio:
    """B: A, y además quien partió el año sin empleo vuelve con f1 si cayó el año
    anterior y con f2 si lleva más de un año."""
    return _paso_alternativo(state, rng, retorno_en_anio=True, reempleo_por_duracion=True)


PASOS: dict[str, Paso] = {"actual": paso_actual, "A": paso_variante_a, "B": paso_variante_b}


# --------------------------------------------------------------------------- arnés


def _estado(edad: int, grupo: int | None, n: int, rng: np.random.Generator) -> State:
    state = State.from_twin(Twin(edad=edad), n)
    if grupo is None:
        state.ocupacion = rng.choice(N_GRUPOS, size=n, p=pesos_grupo())
    else:
        state.ocupacion = np.full(n, grupo, dtype=np.int64)
    state.extra["inactivo"] = np.zeros(n, dtype=bool)
    state.extra["anios_sin_empleo"] = np.zeros(n, dtype=np.int64)
    return state


def _avanzar(paso: Paso, state: State, rng: np.random.Generator) -> Anio:
    anio = paso(state, rng)
    state.extra["inactivo"] = (state.extra["inactivo"] & state.desempleado & ~anio.reempleo) | anio.cayo_inactividad
    state.extra["anios_sin_empleo"] = np.where(state.desempleado, state.extra["anios_sin_empleo"] + 1, 0)
    return anio


def _div(a: float, b: float) -> float:
    return float(a / b) if b else float("nan")


def medir_regimen(
    paso: Paso,
    edad: int,
    grupo: int | None = 2,
    *,
    n: int = 40_000,
    quema: int = 40,
    anios: int = 10,
    seed: int = 0,
) -> dict[str, float]:
    """Matriz anual y stock en régimen, con la edad fija y el grupo ocupacional fijo.

    Parte con todos empleados, descarta `quema` años y junta los `anios` siguientes.
    `grupo=None` reparte los gemelos según el peso de cada grupo en la ESI. El grupo
    se repone después de cada año (si no, tras la quema todos los puntos de partida
    terminan en la misma mezcla de JobHop) y el desgaste queda en 0,2, bajo el umbral.
    Todas las transiciones son de punta a punta: estado al inicio vs al cierre.
    """
    rng = np.random.default_rng(seed)
    state = _estado(edad, grupo, n, rng)
    grupos = state.ocupacion.copy()
    c: dict[str, float] = dict.fromkeys(
        (
            "emp0",
            "sin0",
            "e_sin",
            "e_d",
            "e_i",
            "sin_e",
            "sin0_1",
            "sin_e_1",
            "sin0_2",
            "sin_e_2",
            "directo",
            "nuevos",
            "ev_ces",
            "sigue2",
            "personas",
            "sin",
            "d",
        ),
        0.0,
    )
    ces_anterior = np.zeros(n, dtype=bool)
    for k in range(quema + anios):
        antes = state.desempleado.copy()
        dur0 = state.extra["anios_sin_empleo"].copy()
        anio = _avanzar(paso, state, rng)
        state.ocupacion = grupos.copy()
        ahora, inactivo = state.desempleado, state.extra["inactivo"]
        if k >= quema:
            c["emp0"] += (~antes).sum()
            c["sin0"] += antes.sum()
            c["e_sin"] += (~antes & ahora).sum()
            c["e_d"] += (~antes & ahora & ~inactivo).sum()
            c["e_i"] += (~antes & ahora & inactivo).sum()
            c["sin_e"] += (antes & ~ahora).sum()
            c["sin0_1"] += (antes & (dur0 == 1)).sum()
            c["sin_e_1"] += (antes & (dur0 == 1) & ~ahora).sum()
            c["sin0_2"] += (antes & (dur0 >= 2)).sum()
            c["sin_e_2"] += (antes & (dur0 >= 2) & ~ahora).sum()
            c["directo"] += anio.directo.sum()
            c["nuevos"] += (anio.directo | anio.reempleo | anio.retorno).sum()
            c["ev_ces"] += ces_anterior.sum()
            c["sigue2"] += (ces_anterior & ahora & (state.extra["anios_sin_empleo"] == 2)).sum()
            c["personas"] += n
            c["sin"] += ahora.sum()
            c["d"] += (ahora & ~inactivo).sum()
        ces_anterior = anio.cayo_cesantia
    ocupados = c["personas"] - c["sin"]
    return {
        "e_a_sin": _div(c["e_sin"], c["emp0"]),
        "e_a_d": _div(c["e_d"], c["emp0"]),
        "e_a_i": _div(c["e_i"], c["emp0"]),
        "sin_a_e": _div(c["sin_e"], c["sin0"]),
        "sin_a_e_primer_anio": _div(c["sin_e_1"], c["sin0_1"]),
        "sin_a_e_mas_de_un_anio": _div(c["sin_e_2"], c["sin0_2"]),
        "sin_empleo": _div(c["sin"], c["personas"]),
        "desocupacion": _div(c["d"], ocupados + c["d"]),
        "cambio_directo": _div(c["directo"], c["emp0"]),
        "nuevos_empleos": _div(c["nuevos"], c["personas"]),
        # de los que cayeron en cesantía un año, cuántos siguen al cierre del año siguiente
        "cesante_al_cierre_siguiente": _div(c["sigue2"], c["ev_ces"]),
    }


def medir_cohorte(
    paso: Paso,
    grupo: int | None = 2,
    *,
    edad_inicial: int = 18,
    edad_final: int = 49,
    n: int = 40_000,
    seed: int = 0,
) -> dict[str, dict[str, float]]:
    """Una cohorte que parte empleada a los 18 y llega a `edad_final`, como pide el
    campo `medir` de las metas. El grupo ocupacional evoluciona libre.

    Devuelve, por tramo ESI, `desocupacion` (cesantes / (ocupados + cesantes), con la
    etiqueta del arnés) y `flag` (proporción con `desempleado`); por tramo EPS,
    `cambio_directo` por año empleado; y `sigue_cesante` sobre todos los episodios.
    """
    rng = np.random.default_rng(seed)
    state = _estado(edad_inicial, grupo, n, rng)
    esi = {b: dict.fromkeys(("n", "sin", "d"), 0.0) for b in BANDAS_ESI}
    eps = {b: dict.fromkeys(("emp0", "directo"), 0.0) for b in BANDAS}
    episodios = siguen = 0.0
    ces_anterior = np.zeros(n, dtype=bool)
    for edad in range(edad_inicial, edad_final + 1):
        state.edad = edad
        antes = state.desempleado.copy()
        anio = _avanzar(paso, state, rng)
        ahora, inactivo = state.desempleado, state.extra["inactivo"]
        tramo = next((b for b in BANDAS_ESI if int(b[:2]) <= edad <= int(b[3:])), None)
        if tramo:
            esi[tramo]["n"] += n
            esi[tramo]["sin"] += ahora.sum()
            esi[tramo]["d"] += (ahora & ~inactivo).sum()
        e = eps[BANDAS[banda_idx(edad)]]
        e["emp0"] += (~antes).sum()
        e["directo"] += anio.directo.sum()
        episodios += ces_anterior.sum()
        siguen += (ces_anterior & ahora & (state.extra["anios_sin_empleo"] == 2)).sum()
        ces_anterior = anio.cayo_cesantia
    return {
        "desocupacion": {b: _div(v["d"], v["n"] - v["sin"] + v["d"]) for b, v in esi.items()},
        "flag": {b: _div(v["sin"], v["n"]) for b, v in esi.items()},
        "cambio_directo": {b: _div(v["directo"], v["emp0"]) for b, v in eps.items()},
        "sigue_cesante": {"todos": _div(siguen, episodios)},
    }


def medir_cohorte_motor(grupo: int = 2, *, n: int = 40_000, seed: int = 0) -> dict[str, dict[str, float]]:
    """El motor completo (`engine.simulate`, decisión "seguir" de 18 a 49): proporción
    con `desempleado` y desgaste mediano por tramo ESI. A diferencia de `medir_cohorte`
    incluye el desgaste, que sobre 0,6 suma riesgo de salida."""
    r = simulate(Twin(edad=18, ocupacion=grupo), ["seguir"] * 32, n_runs=n, seed=seed)
    flag: dict[str, list[float]] = {b: [] for b in BANDAS_ESI}
    desgaste: dict[str, list[float]] = {b: [] for b in BANDAS_ESI}
    for anio in r["trayectoria"]:
        edad = anio["edad"] - 1  # la edad durante el año simulado
        for b in BANDAS_ESI:
            if int(b[:2]) <= edad <= int(b[3:]):
                flag[b].append(anio["prob_desempleo"])
                desgaste[b].append(anio["desgaste_p50"])
    return {
        "flag": {b: float(np.mean(v)) for b, v in flag.items()},
        "desgaste_p50": {b: float(np.mean(v)) for b, v in desgaste.items()},
    }


# --------------------------------------------------------------------------- comparación


def _fila(id_: str, metrica: str, banda: str, ref: float, tol: float, justa: bool, valores: dict) -> dict:
    errores = {k: v - ref for k, v in valores.items()}
    return {
        "id": id_,
        "metrica": metrica,
        "banda": banda,
        "referencia": ref,
        "tolerancia": tol,
        "justa": justa,
        "valores": valores,
        "errores": errores,
        "dentro": {k: abs(e) <= tol for k, e in errores.items()},
    }


def comparar(grupo: int | None = None, *, n: int = 40_000, seed: int = 0) -> dict:
    """Actual vs variante A vs variante B contra cada referencia.

    `grupo=None` promedia sobre los grupos con el peso de la ESI. Cada fila trae
    `justa`: False cuando la referencia no mide lo mismo que el motor o cuando sale
    de la misma tabla que el motor usa de insumo (se muestra, no valida).
    """
    elsoc = referencia_elsoc()
    metas = referencias()["metas"]
    regimen = {
        v: {b: medir_regimen(PASOS[v], EDAD_REGIMEN[b], grupo, n=n, seed=seed) for b in BANDAS} for v in VARIANTES
    }
    cohorte = {v: medir_cohorte(PASOS[v], grupo, n=n, seed=seed) for v in VARIANTES}

    def reg(b: str, clave: str) -> dict:
        return {v: regimen[v][b][clave] for v in VARIANTES}

    filas = []
    for b in BANDAS:
        e = elsoc[b]
        filas += [
            _fila(
                f"elsoc_e_a_sin_{b}",
                "Empleado → sin empleo (ELSOC O→D+I)",
                b,
                e["o_a_sin"],
                TOL,
                True,
                reg(b, "e_a_sin"),
            ),
            _fila(f"elsoc_e_a_d_{b}", "Empleado → cesante (ELSOC O→D)", b, e["o_a_d"], TOL, True, reg(b, "e_a_d")),
            _fila(f"elsoc_e_a_i_{b}", "Empleado → inactivo (ELSOC O→I)", b, e["o_a_i"], TOL, True, reg(b, "e_a_i")),
            _fila(
                f"elsoc_sin_a_e_{b}",
                "Sin empleo → empleado (ELSOC, ex ocupados)",
                b,
                e["sin_a_o_ex_ocupado"],
                TOL_RETORNO,
                True,
                reg(b, "sin_a_e"),
            ),
            _fila(
                f"elsoc_sin_empleo_{b}",
                "Proporción sin empleo en régimen (ELSOC, ex ocupados)",
                b,
                e["sin_empleo_ex_ocupado"],
                TOL,
                True,
                reg(b, "sin_empleo"),
            ),
        ]
    for b in BANDAS_ESI:
        m = metas[f"desocupacion_{b}"]
        filas.append(
            _fila(
                f"esi_desocupacion_{b}",
                "Desocupación (ESI), cohorte, solo cesantes",
                b,
                m["valor"],
                m["tolerancia"],
                True,
                {v: cohorte[v]["desocupacion"][b] for v in VARIANTES},
            )
        )
    for b in BANDAS_ESI:
        m = metas[f"desocupacion_{b}"]
        filas.append(
            _fila(
                f"esi_flag_{b}",
                "Desocupación (ESI) vs flag con inactivos",
                b,
                m["valor"],
                m["tolerancia"],
                False,
                {v: cohorte[v]["flag"][b] for v in VARIANTES},
            )
        )
    for b in BANDAS:
        m = metas["cambio_" + b.replace("-", "_")]
        filas.append(
            _fila(
                f"eps_cambio_{b}",
                "Cambio directo de empleador (meta = insumo EPS)",
                b,
                m["valor"],
                m["tolerancia"],
                False,
                {v: cohorte[v]["cambio_directo"][b] for v in VARIANTES},
            )
        )
    m = metas["sigue_cesante_12m"]
    filas.append(
        _fila(
            "eps_sigue_cesante",
            "Sigue cesante al cierre del año siguiente (meta = insumo EPS)",
            "todos",
            m["valor"],
            m["tolerancia"],
            False,
            {v: cohorte[v]["sigue_cesante"]["todos"] for v in VARIANTES},
        )
    )
    return {"grupo": grupo, "n": n, "filas": filas, "regimen": regimen, "cohorte": cohorte}


def error_medio(resultado: dict, prefijo: str = "") -> dict[str, float]:
    """Error absoluto medio de cada variante sobre las filas justas (opcionalmente por prefijo de id)."""
    filas = [f for f in resultado["filas"] if f["justa"] and f["id"].startswith(prefijo)]
    return {v: float(np.mean([abs(f["errores"][v]) for f in filas])) for v in VARIANTES}


# --------------------------------------------------------------------------- salida


def _pct(x: float) -> str:
    return f"{100 * x:5.1f}"


def _imprimir(resultado: dict) -> None:
    titulo = "promedio de grupos (pesos ESI)" if resultado["grupo"] is None else f"grupo {resultado['grupo']}"
    print(
        f"\n== {titulo}, n={resultado['n']} ==  (valores en %, entre paréntesis el error en puntos; * = fuera de tolerancia)"
    )
    print(f"{'métrica':<62}{'tramo':<7}{'ref':>6}{'tol':>5}   {'actual':<16}{'A':<16}{'B':<16}")
    for f in resultado["filas"]:
        celdas = ""
        for v in VARIANTES:
            marca = " " if f["dentro"][v] else "*"
            celdas += f"{_pct(f['valores'][v])} ({100 * f['errores'][v]:+5.1f}){marca} "
        nombre = f["metrica"] + ("" if f["justa"] else " [no valida]")
        print(f"{nombre:<62}{f['banda']:<7}{_pct(f['referencia'])}{100 * f['tolerancia']:5.0f}   {celdas}")
    for prefijo, nombre in (("", "todas las filas justas"), ("elsoc", "solo ELSOC"), ("esi", "solo ESI")):
        em = error_medio(resultado, prefijo)
        print(f"error absoluto medio, {nombre:<24}" + "".join(f"  {v}: {100 * em[v]:.1f}" for v in VARIANTES))


def main() -> None:
    sv, t, elsoc = sobrevida_cesantia(), tablas(), referencia_elsoc()
    print("Insumos derivados de eps_cesantia_duracion (por tramo 18-29, 30-44, 45-59):")
    for k, nombre in (
        ("m1", "m1 sigue cesante al cierre si cae en el año"),
        ("f1", "f1 retorno, cayó el año anterior"),
        ("f2", "f2 retorno, más de un año"),
        ("s12", "sigue_12m (el motor usa 1 − esto)"),
    ):
        print(f"  {nombre:<46}" + "  ".join(f"{x:.3f}" for x in sv[k]))
    print("Hipótesis del paso anual, sin simular: tasa EPS de caer en cesantía × m1 vs ELSOC O→D")
    for i, b in enumerate(BANDAS):
        print(
            f"  {b}: EPS {t.p_cesantia[i]:.4f} × m1 {sv['m1'][i]:.3f} = {t.p_cesantia[i] * sv['m1'][i]:.4f}   ELSOC O→D {elsoc[b]['o_a_d']:.4f}"
            f"   |   EPS a inactividad {t.p_inactividad[i]:.4f}   ELSOC O→I {elsoc[b]['o_a_i']:.4f}"
        )
    print(
        f"Factor de rotación: grupo 2 = {t.mult_rotacion[2]:.3f}; promedio con pesos ESI = {float(pesos_grupo() @ t.mult_rotacion):.3f}"
    )

    for grupo in (None, 2):
        res = comparar(grupo)
        _imprimir(res)
        print(
            "retorno al empleo: rango ELSOC [ex ocupados (piso, la fila I incluye inactivos permanentes) , D→O (techo, solo cesantes)]"
        )
        for b in BANDAS:
            print(
                f"  {b}: [{_pct(elsoc[b]['sin_a_o_ex_ocupado'])} , {_pct(elsoc[b]['d_a_o'])}]   "
                + "   ".join(f"{v} {_pct(res['regimen'][v][b]['sin_a_e'])}" for v in VARIANTES)
            )
        print("retorno al empleo según cuánto lleva sin empleo (primer año / más de un año):")
        for v in VARIANTES:
            print(
                f"  {v:<7}"
                + "   ".join(
                    f"{b}: {_pct(res['regimen'][v][b]['sin_a_e_primer_anio'])} / {_pct(res['regimen'][v][b]['sin_a_e_mas_de_un_anio'])}"
                    for b in BANDAS
                )
            )

    print("\n== motor completo (engine.simulate, 'seguir' de 18 a 49, grupo 2) vs el mismo paso sin desgaste ==")
    motor, sin_desgaste = medir_cohorte_motor(2), medir_cohorte(paso_actual, 2)
    for b in BANDAS_ESI:
        print(
            f"  {b}: flag sin empleo motor {_pct(motor['flag'][b])}   sin desgaste {_pct(sin_desgaste['flag'][b])}"
            f"   desgaste mediano {motor['desgaste_p50'][b]:.2f}"
        )


if __name__ == "__main__":
    main()
