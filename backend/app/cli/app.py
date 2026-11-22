"""Parser de argumentos y `main` del CLI."""

import argparse
import sys

from app.cli.formato import EntradaInvalida
from app.cli.juego import (
    cmd_comparar,
    cmd_dudas,
    cmd_jugar,
    cmd_prompt,
    cmd_supuestos,
    cmd_validar,
)
from app.cli.juego_formato import GEMELOS_POR_DEFECTO
from app.cli.ocupacional import cmd_ocupaciones, cmd_perfil, cmd_simular
from app.sim.ocupacional.state import Twin

# ── entrada ──────────────────────────────────────────────────────────────────


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Trayectoria laboral desde el terminal.")
    sub = parser.add_subparsers(dest="comando", required=True)

    oc = sub.add_parser("ocupaciones", help="lista los tipos de trabajo con su número")
    oc.set_defaults(func=cmd_ocupaciones)

    def comunes(p: argparse.ArgumentParser) -> None:
        p.add_argument("--ocupacion", type=int, required=True, help="tipo de tu último trabajo (0 a 9)")
        p.add_argument("--edad", type=int, required=True, help="tu edad en años")
        p.add_argument("--json", action="store_true", help="imprime el resultado crudo en JSON")

    pe = sub.add_parser("perfil", help="qué pasa después de tu último trabajo, según los datos")
    comunes(pe)
    pe.set_defaults(func=cmd_perfil)

    si = sub.add_parser("simular", help="simula varios años, una decisión por año")
    comunes(si)
    si.add_argument("--sueldo", type=float, default=Twin.sueldo, help="sueldo mensual en pesos")
    si.add_argument("--decisiones", help="una por año, separadas por coma (ej: seguir,cambiar_pega)")
    si.add_argument("--anios", type=int, help="años con 'seguir' si no pasas --decisiones (por defecto 5)")
    si.add_argument("--runs", type=int, default=2000, help="cuántas copias simular")
    si.add_argument("--seed", type=int, help="semilla, para repetir el mismo resultado")
    si.set_defaults(func=cmd_simular)

    # el juego: los flags del perfil parten de los valores por defecto de `Perfil`
    def perfil_juego(p: argparse.ArgumentParser) -> None:
        p.add_argument("--edad", type=int, default=30, help="tu edad, 18 a 50 (por defecto 30)")
        p.add_argument("--sexo", default="m", help="h o m (por defecto m)")
        p.add_argument("--edu", default="universitaria", help="media, tecnica, universitaria o postgrado")
        p.add_argument("--rubro", default="Servicios profesionales", help="rubro de tu trabajo (ej: Salud)")
        p.add_argument("--tipo-empleador", default="pyme", help="grande, pyme, startup, publico o extranjero")
        p.add_argument("--nivel", type=int, default=1, help="0 junior, 1 semi senior, 2 senior, 3 jefatura, 4 gerencia")
        p.add_argument("--sueldo", type=float, default=1_400_000, help="sueldo líquido al mes, en pesos")
        p.add_argument("--riesgo", type=int, default=5, help="cuánto riesgo toleras, de 0 a 10")
        p.add_argument("--carrera-id", type=int, help="tu carrera: número del catálogo de mifuturo (0 a 251)")
        p.add_argument("--ocupacion", type=int, help="tu tipo de trabajo, 0 a 9 (míralos con: ocupaciones)")
        p.add_argument("--antiguedad", type=int, help="años en tu trabajo actual")
        p.add_argument("--region", help="rm u otra")
        p.add_argument(
            "--desde",
            metavar="ARCHIVO",
            help="archivo (markdown o texto) con tu información: Claude lo "
            "lee y llena tu perfil; las demás opciones corrigen lo que leyó",
        )

    def gemelos(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--gemelos",
            type=int,
            default=GEMELOS_POR_DEFECTO,
            help=f"cuántas copias simular por opción (por defecto {GEMELOS_POR_DEFECTO})",
        )

    du = sub.add_parser("dudas", help="las dudas con las que tu perfil puede empezar una partida")
    perfil_juego(du)
    du.add_argument("--json", action="store_true", help="imprime la lista cruda en JSON")
    du.set_defaults(func=cmd_dudas)

    co = sub.add_parser("comparar", help="cómo les va a tus copias con cada opción de una decisión, sin jugar")
    perfil_juego(co)
    gemelos(co)
    co.add_argument("--duda", required=True, help="la decisión a comparar (míralas con: dudas)")
    co.add_argument("--semilla", type=int, default=0, help="semilla de los dados (por defecto 0)")
    co.add_argument("--json", action="store_true", help="imprime el dict crudo del motor")
    co.set_defaults(func=cmd_comparar)

    ju = sub.add_parser("jugar", help="juega una partida de 10 años, decisión por decisión")
    perfil_juego(ju)
    gemelos(ju)
    ju.add_argument("--duda", help="la duda con la que empiezas; si falta, se elige de una lista")
    ju.add_argument("--semilla", type=int, help="semilla de los dados, para repetir la partida (si falta, al azar)")
    ju.add_argument(
        "--elecciones", help="opciones en orden, sin teclado: 1,2,1 (2:3 elige también dentro de la opción)"
    )
    ju.add_argument(
        "--auto",
        action="store_true",
        help="sin teclado: nunca busca cambios (y si la vida obliga a elegir, lo más común)",
    )
    ju.set_defaults(func=cmd_jugar)

    pr = sub.add_parser("prompt", help="el prompt para que tu Claude arme tu perfil (pégalo en tu Claude)")
    pr.set_defaults(func=cmd_prompt)

    va = sub.add_parser("validar", help="compara una cohorte simulada con las cifras de Chile")
    va.add_argument("--n", type=int, default=5000, help="personas de la cohorte (por defecto 5000)")
    va.add_argument("--semilla", type=int, default=0, help="semilla de los dados (por defecto 0)")
    va.add_argument("--json", action="store_true", help="imprime el resultado crudo en JSON")
    va.set_defaults(func=cmd_validar)

    su = sub.add_parser("supuestos", help="cada parámetro del motor con su calidad, fuente y país")
    su.add_argument("--calidad", choices=["dato", "mixto", "supuesto"], help="muestra solo esa calidad")
    su.add_argument("--json", action="store_true", help="imprime la lista cruda en JSON")
    su.set_defaults(func=cmd_supuestos)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as e:  # argparse ya imprimió la ayuda o el error
        return e.code if isinstance(e.code, int) else 2
    try:
        salida = args.func(args)
        if salida is not None:
            print(salida)
    except EntradaInvalida as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nPartida interrumpida.", file=sys.stderr)
        return 130
    return 0
