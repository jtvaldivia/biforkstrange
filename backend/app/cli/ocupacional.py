"""Subcomandos del motor por tablas de ocupación: ocupaciones, perfil y simular."""

import argparse
import json

from app.cli.formato import (
    ANCHO,
    EDAD_MAX,
    EDAD_MIN,
    FUENTES,
    EntradaInvalida,
    _barras,
    _cortar,
    _de_cada_100,
    _duracion,
    _miles,
    _pct,
    _pesos,
)
from app.sim.ocupacional import labor
from app.sim.ocupacional.decisions import all_decisions, get_decision
from app.sim.ocupacional.engine import simulate
from app.sim.ocupacional.state import Twin
from app.sim.ocupacional.tables import N_GRUPOS, tablas

# ── validación de entrada ────────────────────────────────────────────────────


def _validar_ocupacion(grupo: int) -> None:
    if not 0 <= grupo < N_GRUPOS:
        raise EntradaInvalida(
            f"No existe el tipo de trabajo {grupo}. Elige un número entre 0 y {N_GRUPOS - 1} "
            "(míralos con: python -m app.cli ocupaciones)."
        )


def _validar_edad(edad: int) -> None:
    if not EDAD_MIN <= edad <= EDAD_MAX:
        raise EntradaInvalida(f"La edad debe estar entre {EDAD_MIN} y {EDAD_MAX} años (recibí {edad}).")


def _decisiones(args: argparse.Namespace) -> list[str]:
    conocidas = [d.key for d in all_decisions()]
    if args.decisiones is None:
        anios = 5 if args.anios is None else args.anios
        if anios < 1:
            raise EntradaInvalida("--anios debe ser 1 o más.")
        return ["seguir"] * anios
    if args.anios is not None:
        raise EntradaInvalida("Usa --decisiones o --anios, no los dos: hay una decisión por año.")
    claves = [c.strip() for c in args.decisiones.split(",") if c.strip()]
    if not claves:
        raise EntradaInvalida("--decisiones está vacío. Opciones: " + ", ".join(conocidas) + ".")
    for c in claves:
        if c not in conocidas:
            raise EntradaInvalida(f"No conozco la decisión '{c}'. Opciones: " + ", ".join(conocidas) + ".")
    return claves


# ── subcomandos ──────────────────────────────────────────────────────────────


def cmd_ocupaciones(args: argparse.Namespace) -> str:
    lineas = ["Tipos de trabajo (usa el número en --ocupacion):", ""]
    lineas += [f"  {g}  {nombre}" for g, nombre in enumerate(tablas().nombres)]
    return "\n".join(lineas)


def texto_perfil(p: dict) -> str:
    termino = p["termino_anual"]
    directo, cesantia, inactividad = _de_cada_100(
        [termino["cambio_directo"], termino["cesantia"], termino["inactividad"]]
    )
    total = directo + cesantia + inactividad
    dur = p["duracion_anios"]
    destinos = [
        (s["nombre"] + (" (el mismo)" if s["grupo"] == p["grupo"] else ""), s["prob"])
        for s in p["siguiente"]
    ]
    return "\n".join(
        [
            f"Tu último trabajo: {p['nombre']} (tipo {p['grupo']})",
            f"Tu edad: {p['edad']} años",
            "",
            "¿Qué tan probable es que tu trabajo termine este año?",
            f"  De cada 100 personas como tú, a {total} se les termina el trabajo este año:",
            f"    {directo:>3}  se cambian directo a otro trabajo",
            f"    {cesantia:>3}  quedan cesantes (sin trabajo y buscando)",
            f"    {inactividad:>3}  dejan de trabajar y no buscan",
            f"  Las otras {100 - total} siguen en el mismo trabajo.",
            "",
            "¿Cuánto suele durar un trabajo de este tipo?",
            f"  1 de cada 4 dura menos de {_duracion(dur['p25'])}.",
            f"  La mitad dura menos de {_duracion(dur['p50'])}.",
            f"  1 de cada 4 dura más de {_duracion(dur['p75'])}.",
            "",
            "¿A qué tipo de trabajo pasas después?",
            "  De cada 100 personas que venían de un trabajo como el tuyo, así se reparte el siguiente:",
            "",
            *_barras(destinos),
            "",
            FUENTES,
        ]
    )


def cmd_perfil(args: argparse.Namespace) -> str:
    _validar_ocupacion(args.ocupacion)
    _validar_edad(args.edad)
    p = labor.perfil(args.ocupacion, args.edad)
    return json.dumps(p, ensure_ascii=False, indent=2) if args.json else texto_perfil(p)


def texto_simulacion(twin: Twin, n_runs: int, resultado: dict) -> str:
    anios = resultado["trayectoria"]
    etiquetas = [get_decision(a["decision"]).label for a in anios]
    filas = []
    for a, etiqueta in zip(anios, etiquetas):
        top = a["ocupaciones"][0]
        filas.append(
            [
                str(a["edad"]),
                etiqueta,
                _miles(a["sueldo_p50"]),
                f"{_miles(a['sueldo_p10'])} a {_miles(a['sueldo_p90'])}",
                _pct(a["prob_desempleo"]),
                _pct(a["prob_nuevo_empleo"]),
                (top["nombre"], _pct(top["prob"])),
            ]
        )
    titulos = ["Edad", "Decisión", "Sueldo", "Rango", "Sin trabajo", "Empleo nuevo"]
    anchos = [max(len(t), *(len(f[i]) for f in filas)) for i, t in enumerate(titulos)]
    derecha = [True, False, True, True, True, True]

    def celdas(valores: list[str]) -> str:
        return "  ".join(f"{v:>{w}}" if d else f"{v:<{w}}" for v, w, d in zip(valores, anchos, derecha))

    # el nombre del tipo de trabajo ocupa lo que queda de la línea (más " 100%")
    ancho_tipo = max(ANCHO - len(celdas(titulos)) - 2 - 5, 12)
    lineas = [
        f"Tu último trabajo: {tablas().nombres[twin.ocupacion]} (tipo {twin.ocupacion})",
        f"Partes a los {twin.edad} años con un sueldo de {_pesos(twin.sueldo)} al mes.",
        f"Simulamos {_miles(n_runs * 1000)} versiones de ti (tus copias), una decisión por año.",
        "",
        celdas(titulos) + "  Trabajo más probable",
        "-" * ANCHO,
    ]
    for f in filas:
        nombre, pct = f[6]
        lineas.append(f"{celdas(f[:6])}  {_cortar(nombre, ancho_tipo):<{ancho_tipo}} {pct:>4}")
    final = anios[-1]
    lineas += [
        "",
        "Sueldo: el de la copia del medio, en miles de pesos al mes.",
        "Rango: 8 de cada 10 copias quedan dentro.",
        "Sin trabajo: copias sin empleo al cierre del año.",
        "Empleo nuevo: copias que empezaron un trabajo ese año.",
        "Trabajo más probable: el tipo de trabajo donde hay más copias.",
        "",
        f"¿En qué tipo de trabajo terminan tus copias a los {final['edad']} años?",
        "(los que están sin trabajo cuentan en el tipo de su último empleo)",
        "",
        *_barras([(o["nombre"], o["prob"]) for o in final["ocupaciones"]]),
        "",
        FUENTES,
        "El efecto de cada decisión sobre sueldo y riesgo todavía es un supuesto del equipo.",
    ]
    return "\n".join(lineas)


def cmd_simular(args: argparse.Namespace) -> str:
    _validar_ocupacion(args.ocupacion)
    _validar_edad(args.edad)
    if args.sueldo <= 0:
        raise EntradaInvalida("--sueldo debe ser mayor que 0 (pesos al mes).")
    if args.runs < 1:
        raise EntradaInvalida("--runs debe ser 1 o más.")
    decisiones = _decisiones(args)
    twin = Twin(edad=args.edad, sueldo=args.sueldo, ocupacion=args.ocupacion)
    resultado = simulate(twin, decisiones, n_runs=args.runs, seed=args.seed)
    if args.json:
        return json.dumps(resultado, ensure_ascii=False, indent=2)
    return texto_simulacion(twin, args.runs, resultado)
