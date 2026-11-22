"""Subcomandos del juego (motor del paquete): dudas, comparar, prompt, jugar, validar, supuestos."""

import argparse
import importlib
import json
import random
import textwrap

from app.cli.formato import ANCHO, EntradaInvalida
from app.cli.juego_entrada import (
    _elegir,
    _flags_perfil,
    _gemelos,
    _guion,
    _perfil,
    _preguntar,
    _texto_dudas,
    _texto_perfil_juego,
    _validar_duda,
)
from app.cli.juego_formato import (
    GEMELOS_POR_DEFECTO,
    _ahorros,
    _cabecera_anio,
    _envolver,
    _situacion,
    _supuestos_internos,
    _texto_cierre,
    _texto_comparacion,
    _texto_evento,
    _texto_pendiente,
    _texto_pie,
    _texto_resultado_decision,
)

# ── el juego: subcomandos ────────────────────────────────────────────────────


def cmd_dudas(args: argparse.Namespace) -> str:
    from app.sim.motor.partida import dudas_posibles

    perfil = _perfil(args)
    dudas = dudas_posibles(perfil)
    if args.json:
        return json.dumps(dudas, ensure_ascii=False, indent=2)
    return "\n".join([
        *_texto_perfil_juego(perfil), "",
        "Dudas con las que puedes empezar la partida (usa el nombre de la izquierda en --duda):", "",
        *_texto_dudas(dudas), "",
        *_envolver("Entre corchetes, la calidad de los números de cada decisión: dato (medido), mixto, o "
                   "supuesto del equipo."),
    ])


def cmd_comparar(args: argparse.Namespace) -> str:
    from app.sim.motor.partida import vista

    perfil = _perfil(args)
    n = _gemelos(args, minimo=1)
    _validar_duda(perfil, args.duda)
    try:
        pendiente = vista(perfil, args.semilla, args.duda, [], n)["pendiente"]
    except (ValueError, KeyError) as error:
        raise EntradaInvalida(str(error)) from error
    comp = pendiente["comparacion"]
    if args.json:
        return json.dumps(comp, ensure_ascii=False, indent=2)
    lineas = [*_texto_perfil_juego(perfil), "", *_envolver(pendiente["pregunta"]), ""]
    if comp is None:
        lineas.append("Esta decisión tiene demasiadas opciones: no se simulan copias para ella.")
        return "\n".join(lineas)
    for i, o in enumerate(pendiente["opciones"], 1):
        detalle = f": {o['detalle']}" if o["detalle"] else ""
        lineas += _envolver(f"{i}. {o['nombre']}{detalle}", "     ", "  ")
    lineas += ["", *_texto_comparacion(comp, _supuestos_internos(pendiente)),
               *_texto_pie(comp["creencia_vs_dato"], comp["calidad"])]
    return "\n".join(lineas)


def cmd_prompt(args: argparse.Namespace) -> str:
    from app.services.ia.perfil_doc import prompt

    return prompt()


def cmd_jugar(args: argparse.Namespace) -> None:
    from app.sim.motor.paquete import paquete
    from app.sim.motor.partida import dudas_posibles, vista

    perfil = _perfil(args)
    n = _gemelos(args)
    guion = _guion(args.elecciones)
    semilla = args.semilla if args.semilla is not None else random.randrange(1, 100_000)
    internas = frozenset(id_ for id_, d in paquete().decisiones.items() if d["aparicion"]["tipo"] == "interna")

    def decir(lineas: list[str]) -> None:
        print("\n".join(lineas), flush=True)

    decir(["GEMELO LABORAL · 10 años de tu vida laboral, una decisión por año", "",
           *_texto_perfil_juego(perfil)])
    duda = args.duda
    if duda is None:
        dudas = dudas_posibles(perfil)
        if guion or args.auto:
            raise EntradaInvalida("Con --auto o --elecciones hay que decir la duda inicial con --duda ID "
                                  "(míralas con: python -m app.cli dudas).")
        decir(["", "¿Qué duda te trae?", "", *_texto_dudas(dudas, numeradas=True), ""])
        duda = dudas[_preguntar(f"Tu duda (1 a {len(dudas)}): ", len(dudas))]["decision"]
    else:
        _validar_duda(perfil, duda)
    decir(["", f"Semilla de esta partida: {semilla} (con la misma semilla y las mismas elecciones, pasa lo mismo)."])

    elecciones: list[dict] = []
    escritas: list[str] = []
    cabecera = 0                      # último año con cabecera impresa
    vistos: dict[int, list[int]] = {}  # año -> [decisiones impresas, eventos impresos, cierre impreso]
    while True:
        try:
            v = vista(perfil, semilla, duda, elecciones, n)
        except (ValueError, KeyError) as error:
            raise EntradaInvalida(str(error)) from error
        for r in [*v["historia"], *([v["anio_en_curso"]] if v["anio_en_curso"] else [])]:
            visto = vistos.setdefault(r["anio"], [0, 0, 0])
            lineas = []
            for d in r["decisiones"][visto[0]:]:
                lineas += _texto_resultado_decision(d, d["decision"] not in internas)
            for ev in r["eventos"][visto[1]:]:
                if not ev["rutina"]:
                    lineas += _texto_evento(ev)
            visto[0], visto[1] = len(r["decisiones"]), len(r["eventos"])
            if "fin" in r and not visto[2]:
                visto[2] = 1
                if cabecera < r["anio"] and not lineas:
                    lineas.append("  Un año sin sobresaltos.")
                pasaron = r["fin"]["edad"] - r["edad"]
                cuando = "Cierras el año" if pasaron == 1 else f"Pasan {pasaron} años y quedas"
                lineas += _envolver(f"{cuando} con {r['fin']['edad']} años: {_situacion(r['fin'])}. "
                                    f"{_ahorros(r['fin']['ahorro'])}.", "    ", "  → ")
            if lineas or (r is v["anio_en_curso"] and cabecera < r["anio"]):
                if cabecera < r["anio"]:
                    cabecera = r["anio"]
                    lineas = [*_cabecera_anio(r, v["anios"], perfil.edad), *([""] if lineas else []), *lineas]
                decir(lineas)
        if v["terminada"]:
            break
        decir(["", *_envolver(f"Hoy: {_situacion(v['estado'])}."), "", *_texto_pendiente(v["pendiente"])])
        eleccion, escrita = _elegir(v["pendiente"], guion, args.auto)
        elecciones.append(eleccion)
        escritas.append(escrita)
        decir([""])
    if guion:
        raise EntradaInvalida(f"Sobran elecciones: la partida terminó usando {len(elecciones)} y quedaron {len(guion)}.")
    decir(_texto_cierre(v, internas))
    partes = ["python -m app.cli jugar", *_flags_perfil(perfil), f"--duda {duda}", f"--semilla {semilla}",
              *([f"--gemelos {n}"] if n != GEMELOS_POR_DEFECTO else []), f"--elecciones {','.join(escritas)}"]
    decir(["", "Para repetir esta partida:",
           *textwrap.wrap(" ".join(partes), width=ANCHO - 2, initial_indent="  ", subsequent_indent="    ",
                          break_long_words=False, break_on_hyphens=False)])


def cmd_validar(args: argparse.Namespace) -> str | None:
    try:
        validacion = importlib.import_module("app.sim.motor.validacion")
    except ImportError as error:
        raise EntradaInvalida(f"La validación contra Chile todavía no está en este código "
                              f"(falta app.sim.motor.validacion: {error}).") from None
    if args.n < 1:
        raise EntradaInvalida("--n debe ser 1 o más (personas de la cohorte).")
    if not callable(getattr(validacion, "validar", None)):
        raise EntradaInvalida("app.sim.motor.validacion existe, pero todavía no tiene la función validar().")
    resultado = validacion.validar(args.n, args.semilla)
    tabla = getattr(validacion, "tabla", None)
    if args.json or not callable(tabla):
        return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)
    return tabla(resultado)


def cmd_supuestos(args: argparse.Namespace) -> str:
    from app.sim.motor import supuestos

    resultado = supuestos.listar()
    if args.calidad:
        resultado["parametros"] = [p for p in resultado["parametros"] if p["calidad"] == args.calidad]
    if args.json:
        return json.dumps(resultado, ensure_ascii=False, indent=2)
    return supuestos.texto(resultado, ANCHO)
