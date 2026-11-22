"""Carga el paquete de datos (`backend/simulador/`) y compila sus expresiones.

El paquete trae las decisiones, eventos, parámetros y tablas como datos, y un
evaluador de referencia (`simulador/referencia/expresiones.py`) que recorre el
árbol de cada expresión. Aquí cada expresión se traduce una vez a una función de
Python, que es mucho más rápida; `tests/test_motor_paquete.py` revisa que ambas
den lo mismo.
"""

import ast
import importlib.util
import json
import math
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3] / "simulador"


def _cargar_referencia():
    ruta = RAIZ / "referencia" / "expresiones.py"
    spec = importlib.util.spec_from_file_location("simulador_referencia_expresiones", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ref = _cargar_referencia()

# Parámetros propios de una vida: {parámetro: valor} en el estado, bajo esta clave. Un perfil con historia
# (p. ej. toda su carrera en el Estado) puede tener su propio P_REEMPLEO_PUBLICO; cada k() de esa vida lee
# primero de aquí. Sin la clave, k() es el del paquete y la evaluación es exactamente la de siempre.
K_PROPIOS = "k_propios"
ErrorExpresion = ref.ErrorExpresion

_BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Mod: "%"}
_CMP = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
_AZAR = {"azar": "u", "azar_uniforme": "uniforme", "azar_normal": "normal", "azar_entero": "entero", "azar_lognormal": "lognormal"}


def _fuente(n, propios: bool = False) -> str:
    """Traduce un nodo de la gramática del paquete a código Python sobre `e` (estado) y `R` (dados).

    Con `propios`, k() lee primero los parámetros propios de la vida (`e[K_PROPIOS]`).
    """
    if isinstance(n, ast.Constant):
        return repr(n.value)
    if isinstance(n, ast.Name):
        return f"e[{n.id!r}]"
    if isinstance(n, ast.UnaryOp):
        return f"(-{_fuente(n.operand, propios)})" if isinstance(n.op, ast.USub) else _fuente(n.operand, propios)
    if isinstance(n, ast.BinOp):
        return f"({_fuente(n.left, propios)} {_BIN[type(n.op)]} {_fuente(n.right, propios)})"
    if isinstance(n, ast.Compare):
        return f"(1 if {_fuente(n.left, propios)} {_CMP[type(n.ops[0])]} {_fuente(n.comparators[0], propios)} else 0)"
    f, a = n.func.id, [_fuente(x, propios) for x in n.args]
    lista = ", ".join(a)
    if f == "si":
        return f"({a[1]} if {a[0]} else {a[2]})"
    if f == "y":
        return f"(1 if ({' and '.join(a)}) else 0)"
    if f == "o":
        return f"(1 if ({' or '.join(a)}) else 0)"
    if f == "no":
        return f"(0 if {a[0]} else 1)"
    if f == "en":
        return f"(1 if {a[0]} in ({', '.join(a[1:])},) else 0)"
    if f in ("min", "max"):
        return f"{f}(({lista},))"
    if f == "clamp":
        return f"max({a[1]}, min({a[2]}, {a[0]}))"
    if f == "exp":
        return f"_exp({a[0]})"
    if f == "ln":
        return f"_log({a[0]})"
    if f == "pow":
        return f"({a[0]} ** {a[1]})"
    if f == "abs":
        return f"abs({a[0]})"
    if f == "redondear":
        return f"round({a[0]})"
    if f == "k":
        return f"_kp(e, {lista})" if propios else f"_k({lista})"
    if f == "tabla":
        return f"_tabla({lista})"
    if f == "tabla_o":
        return f"_tabla_o({lista})"
    if f == "q_muerte":
        return f"_q_muerte({lista})"
    if f == "luto":
        return f"_luto({lista}, e)"
    if f == "falso":
        return "0"
    if f in _AZAR:
        return f"R.{_AZAR[f]}({lista})"
    raise ErrorExpresion("función sin implementar: " + f)


class Paquete:
    """El reglamento: decisiones, eventos, parámetros, variables y tablas."""

    def __init__(self, raiz: Path = RAIZ):
        self.raiz = Path(raiz)
        self.ref = ref.Paquete(str(self.raiz))
        lee = lambda nombre: json.loads((self.raiz / nombre).read_text(encoding="utf-8"))  # noqa: E731
        self.decisiones = {d["id"]: d for d in lee("decisiones.json")["decisiones"]}
        self.eventos = {x["id"]: x for x in lee("eventos.json")["eventos"]}
        self.variables = {v["nombre"]: v for v in lee("estado.json")["variables"]}
        self.objetivos = lee("objetivos_validacion.json")["objetivos"]
        self.fuentes = {f["id"]: f for f in lee("fuentes.json")["fuentes"]}
        self.parametros = self.ref.parametros
        self._funciones: dict = {}
        self._entorno = {
            "_exp": math.exp,
            "_log": math.log,
            "_k": self.ref.k,
            "_tabla": self.ref.tabla,
            "_tabla_o": self._tabla_o,
            "_q_muerte": self.ref.q_muerte,
            "_luto": self.ref.luto,
            "_kp": self._k_propio,
        }
        self._funciones_propias: dict = {}

    def _tabla_o(self, respaldo, *args):
        try:
            return self.ref.tabla(*args)
        except ErrorExpresion:
            return respaldo

    def _k_propio(self, e, nombre, clave=None, defecto=None):
        """k() de una vida con parámetros propios: el suyo si lo tiene, si no el del paquete."""
        propio = e[K_PROPIOS].get(nombre)
        if propio is None:
            return self.ref.k(nombre, clave, defecto)
        if clave is None:
            return propio
        return propio[clave] if clave in propio else self.ref.k(nombre, clave, defecto)

    # ------------------------------------------------------------------ expresiones
    def compilar(self, expr, propios: bool = False):
        """Devuelve (función(e, R), usa_azar) para una expresión del paquete.

        Con `propios`, la función lee k() desde los parámetros propios del estado (`K_PROPIOS`).
        """
        cache = self._funciones_propias if propios else self._funciones
        if expr not in cache:
            if isinstance(expr, (int, float)):
                cache[expr] = ((lambda e, R, v=expr: v), False)
            else:
                arbol = ref.parsear(expr)
                usa_azar = any(isinstance(n, ast.Call) and n.func.id in _AZAR for n in ast.walk(arbol))
                codigo = compile(f"lambda e, R: {_fuente(arbol.body, propios)}", f"<expr {expr[:60]}>", "eval")
                cache[expr] = (eval(codigo, self._entorno), usa_azar)  # noqa: S307 (gramática validada por parsear)
        return cache[expr]

    def evaluar(self, expr, estado, dados=None):
        return self.compilar(expr, K_PROPIOS in estado)[0](estado, dados)

    # ------------------------------------------------------------------ datos
    def k(self, nombre, clave=None, defecto=None):
        return self.ref.k(nombre, clave, defecto)

    def tabla(self, nombre, columna, *pares):
        return self.ref.tabla(nombre, columna, *pares)

    def filas(self, nombre):
        return self.ref.filas(nombre)

    def derivar(self, estado: dict) -> dict:
        return self.ref.derivar(estado)


@lru_cache(maxsize=1)
def paquete() -> Paquete:
    return Paquete()
