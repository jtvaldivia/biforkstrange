"""Entrada del juego: perfil desde flags o archivo, guion de elecciones y preguntas."""

import argparse
import sys

from app.cli.formato import ANCHO, EntradaInvalida, _cortar
from app.cli.juego_formato import (
    EDUCACIONES,
    EMPLEADOR,
    GEMELOS_MAX,
    _envolver,
    _plata,
    _por_defecto,
    _sin_tildes,
)

# ── el juego: entrada ────────────────────────────────────────────────────────


def _perfil(args: argparse.Namespace):
    """Valida los flags del perfil y arma el `Perfil` del motor."""
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import NIVELES, Perfil

    pq = paquete()
    _leer_archivo_de_perfil(args)
    if not 18 <= args.edad <= 50:
        raise EntradaInvalida(f"--edad debe estar entre 18 y 50 años (recibí {args.edad}).")
    if args.sexo not in ("h", "m"):
        raise EntradaInvalida(f"--sexo debe ser h (hombre) o m (mujer); recibí '{args.sexo}'.")
    if args.edu not in EDUCACIONES:
        raise EntradaInvalida(f"--edu debe ser una de: {', '.join(EDUCACIONES)} (recibí '{args.edu}').")
    tipos = [t for t in pq.variables["tipo_empleador"]["dominio"] if t]
    if args.tipo_empleador not in tipos:
        raise EntradaInvalida(f"--tipo-empleador debe ser uno de: {', '.join(tipos)} (recibí '{args.tipo_empleador}').")
    if not 0 <= args.nivel < len(NIVELES):
        niveles = ", ".join(f"{i} {n}" for i, n in enumerate(NIVELES))
        raise EntradaInvalida(f"--nivel debe ser un número entre 0 y {len(NIVELES) - 1} ({niveles}).")
    if not 0 < args.sueldo <= 30_000_000:
        raise EntradaInvalida("--sueldo debe ser mayor que 0 y hasta 30.000.000 (pesos líquidos al mes).")
    if not 0 <= args.riesgo <= 10:
        raise EntradaInvalida(f"--riesgo va de 0 (nada de riesgo) a 10 (todo el riesgo); recibí {args.riesgo}.")
    rubros = [r for r in pq.variables["rubro"]["dominio"] if r]
    buscado = _sin_tildes(args.rubro.strip())
    calzan = [r for r in rubros if _sin_tildes(r) == buscado] or [r for r in rubros if buscado and buscado in _sin_tildes(r)]
    if len(calzan) != 1:
        raise EntradaInvalida(f"No conozco el rubro '{args.rubro}'. Opciones: {'; '.join(rubros)}.")
    if args.carrera_id is not None and not 0 <= args.carrera_id <= 251:
        raise EntradaInvalida("--carrera-id va de 0 a 251 (el catálogo de carreras de mifuturo).")
    if args.ocupacion is not None and not 0 <= args.ocupacion <= 9:
        raise EntradaInvalida("--ocupacion va de 0 a 9 (míralas con: python -m app.cli ocupaciones).")
    if args.region not in (None, "rm", "otra"):
        raise EntradaInvalida("--region debe ser rm (Región Metropolitana) u otra.")
    opcionales = {campo: valor for campo, valor in (("carrera_id", args.carrera_id), ("ocupacion", args.ocupacion),
                                                     ("antiguedad", args.antiguedad), ("region", args.region))
                  if valor is not None}
    return Perfil(edad=args.edad, sexo=args.sexo, edu=args.edu, rubro=calzan[0], tipo_empleador=args.tipo_empleador,
                  nivel=args.nivel, sueldo=args.sueldo, riesgo=args.riesgo, **opcionales)


# Valores por defecto de los flags del perfil: un flag distinto de esto lo escribió la persona
PERFIL_POR_DEFECTO = {"edad": 30, "sexo": "m", "edu": "universitaria", "rubro": "Servicios profesionales",
                      "tipo_empleador": "pyme", "nivel": 1, "sueldo": 1_400_000, "riesgo": 5,
                      "carrera_id": None, "ocupacion": None, "antiguedad": None, "region": None}


def _leer_archivo_de_perfil(args: argparse.Namespace) -> None:
    """Con --desde, Claude lee el archivo y llena el perfil; lo que la persona puso a mano manda."""
    ruta = getattr(args, "desde", None)
    if not ruta or getattr(args, "_desde_leido", False):
        return
    from datetime import date
    from pathlib import Path

    from app.services.ia import perfil as perfil_ia

    try:
        texto = Path(ruta).expanduser().read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise EntradaInvalida(f"No pude leer el archivo '{ruta}' ({type(e).__name__}).") from e
    print(f"Leyendo {ruta}...", file=sys.stderr, flush=True)
    try:
        leido = perfil_ia.perfil_desde_texto(texto, date.today().isoformat())
    except (perfil_ia.ModeloNoDisponible, ValueError) as e:
        raise EntradaInvalida(f"{e} Puedes dar tu perfil con las opciones (--edad, --sueldo, ...).") from e
    a_mano = [c for c, v in PERFIL_POR_DEFECTO.items() if getattr(args, c) != v]
    for campo in PERFIL_POR_DEFECTO:
        if campo not in a_mano:
            setattr(args, campo, leido["perfil"][campo])
    args._desde_leido = True
    if leido.get("duda") and hasattr(args, "duda") and args.duda is None:
        args.duda = leido["duda"]
    origen = "tu documento" if leido["via"] == "documento" else "Claude, desde tu archivo"
    lineas = ["", f"Lo que leímos de {origen} (revísalo: si algo está mal, corrígelo con su opción):"]
    lineas += [f"  · {frase}" for frase in leido["inferido"]] or ["  · Todo estaba escrito tal cual en el archivo."]
    lineas += [f"  ! {aviso}" for aviso in leido.get("avisos", [])]
    if leido.get("duda"):
        lineas.append(f"  · Tu duda: {leido['duda']}.")
    faltan = [s_["nombre"] for s_ in leido["supuestos"] if s_["campo"] not in a_mano]
    if faltan:
        lineas += ["", *_envolver("Tu archivo no dice: " + ", ".join(faltan) + ". Usé un valor por defecto; "
                                  "dilo en el archivo o con su opción para que la simulación sea la tuya.", "  ")]
    if a_mano:
        lineas += ["", "  Lo que pusiste a mano se respetó: " + ", ".join("--" + c.replace("_", "-") for c in a_mano) + "."]
    print("\n".join(lineas) + "\n", file=sys.stderr, flush=True)


def _flags_perfil(perfil) -> list[str]:
    """Los flags que hacen falta para volver a armar este perfil (solo lo que no es el valor por defecto)."""
    from app.sim.motor.perfil import Perfil

    base = Perfil()
    flags = []
    for campo, flag in (("edad", "--edad"), ("sexo", "--sexo"), ("edu", "--edu"), ("rubro", "--rubro"),
                        ("tipo_empleador", "--tipo-empleador"), ("nivel", "--nivel"), ("sueldo", "--sueldo"),
                        ("riesgo", "--riesgo"), ("carrera_id", "--carrera-id"), ("ocupacion", "--ocupacion"),
                        ("antiguedad", "--antiguedad"), ("region", "--region")):
        valor = getattr(perfil, campo)
        if valor != getattr(base, campo):
            if campo == "sueldo":
                valor = f"{valor:g}" if valor != int(valor) else str(int(valor))
            flags.append(f"{flag} '{valor}'" if " " in str(valor) else f"{flag} {valor}")
    return flags


def _gemelos(args: argparse.Namespace, minimo: int = 0) -> int:
    if not minimo <= args.gemelos <= GEMELOS_MAX:
        raise EntradaInvalida(f"--gemelos debe estar entre {minimo} y {GEMELOS_MAX} (recibí {args.gemelos}).")
    return args.gemelos


def _validar_duda(perfil, duda: str) -> None:
    from app.sim.motor.partida import dudas_posibles

    if duda not in [d["decision"] for d in dudas_posibles(perfil)]:
        raise EntradaInvalida(
            f"La duda '{duda}' no existe o no aplica a este perfil. Mira las que sí con: python -m app.cli dudas"
        )


def _texto_perfil_juego(perfil) -> list[str]:
    from app.sim.motor.perfil import NIVELES

    sexo = "mujer" if perfil.sexo == "m" else "hombre"
    return _envolver(
        f"Tú: {sexo}, {perfil.edad} años, educación {perfil.edu}. {NIVELES[perfil.nivel]} en "
        f"{EMPLEADOR[perfil.tipo_empleador]}, rubro {perfil.rubro}, {_plata(perfil.sueldo)} líquidos al mes. "
        f"Tolerancia al riesgo: {perfil.riesgo} de 10."
    )


def _texto_dudas(dudas: list[dict], numeradas: bool = False) -> list[str]:
    ancho_id = max(len(d["decision"]) for d in dudas)
    lineas = []
    for i, d in enumerate(dudas, 1):
        numero = f"{i:>2}. " if numeradas else ""
        cabeza = f"  {numero}{d['decision']:<{ancho_id}}  "
        lineas += _envolver(f"{d['pregunta']} [{d['calidad']}]", " " * len(cabeza), cabeza)
    return lineas


def _guion(texto: str | None) -> list[list[int]]:
    """`--elecciones 1,2:3,1`: opción por decisión, en orden; `2:3` es opción 2 y, dentro de ella, alternativa 3."""
    if texto is None:
        return []
    guion = []
    for pieza in texto.split(","):
        try:
            numeros = [int(x) for x in pieza.strip().split(":")]
        except ValueError:
            numeros = []
        if not numeros or any(x < 1 for x in numeros):
            raise EntradaInvalida(
                f"--elecciones: no entiendo '{pieza.strip()}'. Van números de opción separados por coma, "
                "desde 1 (ej: 1,2,1). Para elegir dentro de una opción: 2:3."
            )
        guion.append(numeros)
    return guion


def _preguntar(texto: str, maximo: int, por_defecto: int | None = None) -> int:
    """Pide un número entre 1 y `maximo` hasta que la respuesta sirva. Devuelve el índice (desde 0)."""
    while True:
        try:
            respuesta = input(texto).strip()
        except (EOFError, OSError):
            raise EntradaInvalida(
                "No hay teclado para responder. Para jugar sin teclado usa --auto o --elecciones 1,2,1,..."
            ) from None
        if not respuesta and por_defecto is not None:
            return por_defecto
        if respuesta.isdigit() and 1 <= int(respuesta) <= maximo:
            return int(respuesta) - 1
        print(f"  Escribe un número entre 1 y {maximo}.")


def _texto_interna(interna: dict) -> list[str]:
    lineas = ["", f"  {interna['pregunta']}"]
    defecto = _por_defecto(interna)
    for i, alt in enumerate(interna["alternativas"], 1):
        marca = "  ← la más común (la de las copias)" if i - 1 == defecto else ""
        lineas.append(_cortar(f"    {i:>2}. {alt['nombre']}{marca}", ANCHO))
    return lineas


def _base(pendiente: dict) -> str:
    """La opción de no cambiar nada, según el motor (con o sin comparación a la vista)."""
    if pendiente["comparacion"]:
        return pendiente["comparacion"]["base"]
    if pendiente["decision"] == "anio_tranquilo":
        return "seguir"  # en un año tranquilo, no cambiar nada es seguir igual
    from types import SimpleNamespace

    from app.sim.motor.paquete import paquete
    from app.sim.motor.politicas import opcion_base

    return opcion_base(paquete().decisiones[pendiente["decision"]],
                       [SimpleNamespace(id=o["opcion"]) for o in pendiente["opciones"]])


def _elegir(pendiente: dict, guion: list[list[int]], auto: bool) -> tuple[dict, str]:
    """La elección para la decisión pendiente y cómo se escribe en --elecciones.

    `--auto` no busca cambios: toma la opción base del motor (no hacer nada o, cuando la vida
    obliga a elegir, lo que la gente hace más seguido).
    """
    opciones = pendiente["opciones"]
    pieza = guion.pop(0) if guion else None
    if pieza:
        if pieza[0] > len(opciones):
            raise EntradaInvalida(
                f"--elecciones pide la opción {pieza[0]} en «{pendiente['pregunta']}», que tiene {len(opciones)}."
            )
        i = pieza[0] - 1
    elif auto:
        i = next((k for k, o in enumerate(opciones) if o["opcion"] == _base(pendiente)), len(opciones) - 1)
    else:
        print()
        i = _preguntar(f"¿Qué eliges? (1 a {len(opciones)}): ", len(opciones))
    opcion, parametros, escrito = opciones[i], {}, [i + 1]
    internas = opcion["elecciones_internas"]
    if pieza and len(pieza) - 1 > len(internas):
        raise EntradaInvalida(
            f"--elecciones trae '{':'.join(map(str, pieza))}', pero dentro de «{opcion['nombre']}» "
            f"hay {len(internas)} cosas que elegir."
        )
    for k, interna in enumerate(internas):
        alternativas = interna["alternativas"]
        if pieza and len(pieza) > k + 1:
            if pieza[k + 1] > len(alternativas):
                raise EntradaInvalida(
                    f"--elecciones pide la alternativa {pieza[k + 1]} en «{interna['pregunta']}», "
                    f"que tiene {len(alternativas)}."
                )
            j = pieza[k + 1] - 1
        elif pieza or auto:
            j = _por_defecto(interna)
        else:
            print("\n".join(_texto_interna(interna)))
            j = _preguntar(f"  ¿Cuál? (1 a {len(alternativas)}, Enter para la de las copias): ", len(alternativas),
                           _por_defecto(interna))
        parametros[interna["variable"]] = alternativas[j]["valor"]
        escrito.append(j + 1)
        if pieza or auto:
            print(f"  {interna['pregunta']} {alternativas[j]['nombre']}.")
    return ({"decision": pendiente["decision"], "opcion": opcion["opcion"], "parametros": parametros},
            ":".join(map(str, escrito)))
