"""La trayectoria laboral desde el terminal, sin levantar el servidor.

    python -m app.cli ocupaciones
    python -m app.cli perfil --ocupacion 2 --edad 30
    python -m app.cli simular --ocupacion 4 --edad 24 --decisiones seguir,cambiar_pega,seguir

`perfil` y `simular` aceptan `--json` para ver el dict crudo del motor.

El juego (motor del paquete, `app/sim/motor/`):

    python -m app.cli dudas
    python -m app.cli comparar --duda unirse_a_startup
    python -m app.cli jugar --duda unirse_a_startup --semilla 7
    python -m app.cli jugar --duda unirse_a_startup --semilla 7 --auto
    python -m app.cli jugar --duda cambiar_de_rubro --elecciones 1:3,2,1 --auto
    python -m app.cli validar
    python -m app.cli supuestos
"""

import argparse
import importlib
import json
import random
import sys
import textwrap
import unicodedata

from app.sim import labor
from app.sim.decisions import all_decisions, get_decision
from app.sim.engine import simulate
from app.sim.state import Twin
from app.sim.tables import N_GRUPOS, tablas

ANCHO = 100
ANCHO_BARRA = 30
EDAD_MIN, EDAD_MAX = 18, 59  # el mismo rango que acepta la API
FUENTES = "Fuentes: EPS 2024, Chile (término del empleo y cesantía); CVs de Flandes (duración y destinos)."


class EntradaInvalida(Exception):
    """Lo que escribió la persona no sirve; el mensaje se le muestra tal cual."""


# ── formato ──────────────────────────────────────────────────────────────────


def _pct(p: float) -> str:
    """Porcentaje entero; lo que existe pero redondea a cero se muestra como <1%."""
    if 0 < p < 0.005:
        return "<1%"
    return f"{round(p * 100)}%"


def _de_cada_100(partes: list[float]) -> list[int]:
    """Reparte round(100 * suma) entre las partes sin que el redondeo descuadre el total."""
    total = round(sum(partes) * 100)
    exactos = [p * 100 for p in partes]
    enteros = [int(x) for x in exactos]
    por_resto = sorted(range(len(partes)), key=lambda i: exactos[i] - enteros[i], reverse=True)
    for i in por_resto[: max(total - sum(enteros), 0)]:
        enteros[i] += 1
    return enteros


def _duracion(anios: float) -> str:
    meses = round(anios * 12)
    a, m = divmod(meses, 12)
    partes = []
    if a:
        partes.append("1 año" if a == 1 else f"{a} años")
    if m or not a:
        partes.append("1 mes" if m == 1 else f"{m} meses")
    return " y ".join(partes)


def _miles(x: float) -> str:
    return f"{round(x / 1000):,}".replace(",", ".")


def _pesos(x: float) -> str:
    return "$" + f"{round(x):,}".replace(",", ".")


def _cortar(texto: str, ancho: int) -> str:
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def _barras(filas: list[tuple[str, float]], sangria: str = "  ") -> list[str]:
    """Una línea por fila: nombre, barra proporcional a la probabilidad y porcentaje."""
    ancho_nombre = max(len(n) for n, _ in filas)
    mayor = max(p for _, p in filas) or 1.0
    ancho_barra = min(ANCHO_BARRA, ANCHO - len(sangria) - ancho_nombre - 2 - 5)
    lineas = []
    for nombre, p in filas:
        barra = "█" * max(round(p / mayor * ancho_barra), 1 if p > 0 else 0)
        lineas.append(f"{sangria}{nombre:<{ancho_nombre}}  {barra:<{ancho_barra}} {_pct(p):>4}")
    return lineas


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


# ── el juego: formato ────────────────────────────────────────────────────────

ANCHO_ETIQUETA = 30
EMPLEADOR = {"grande": "una empresa grande", "pyme": "una pyme", "startup": "una startup",
             "publico": "el Estado", "extranjero": "una empresa de afuera"}
CALIDAD = {"dato": "dato (medido en encuestas o estudios)",
           "mixto": "mixto (parte medido, parte supuesto del equipo)",
           "supuesto": "supuesto (del equipo, sin medición detrás)"}
EMPLEADOR_CORTO = {"grande": "empresa grande", "pyme": "pyme", "startup": "startup", "publico": "Estado",
                   "extranjero": "empresa de afuera"}
TONO = {"bueno": "▲", "malo": "▼"}
EDUCACIONES = ("media", "tecnica", "universitaria", "postgrado")
GEMELOS_MAX = 2000  # el mismo tope que la API
GEMELOS_POR_DEFECTO = 500


def _plata(x: float) -> str:
    """Pesos al mes, redondeados a miles: $1.389.000."""
    return _pesos(round(x / 1000) * 1000)


def _ahorros(x: float) -> str:
    return f"Ahorros: {_plata(x)}" if x >= 0 else f"Deudas: {_plata(-x)}"


def _de_cada_cien(p: float) -> str:
    if 0 < p < 0.005:
        return "menos de 1 de cada 100"
    if 0.995 < p < 1:
        return "más de 99 de cada 100"
    return f"{round(p * 100)} de cada 100"


def _envolver(texto: str, sangria: str = "", primera: str | None = None) -> list[str]:
    return textwrap.wrap(texto, width=ANCHO, initial_indent=sangria if primera is None else primera,
                         subsequent_indent=sangria, break_long_words=False) or [""]


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _situacion(estado: dict) -> str:
    """La situación laboral en una frase, sin el punto final."""
    tipo = estado["estado"]
    if tipo == "empleado":
        donde = EMPLEADOR.get(estado["tipo_empleador"], "un trabajo")
        rubro = f", rubro {estado['rubro']}" if estado["rubro"] else ""
        return f"{estado['cargo']} en {donde}{rubro}, {_plata(estado['sueldo'])} al mes"
    if tipo == "independiente":
        return f"trabajas por tu cuenta, {_plata(estado['sueldo'])} al mes"
    if tipo == "fundador":
        return f"con tu propia empresa, {_plata(estado['sueldo'])} al mes"
    if tipo == "buscando":
        return f"sin trabajo y buscando (sueldo al que apuntas al volver: {_plata(estado['sueldo_ref'])})"
    if tipo == "estudiando":
        return "estudiando"
    return "sin trabajar y sin buscar"


def _situacion_corta(estado: dict) -> str:
    tipo = estado["estado"]
    if tipo == "empleado":
        return f"{estado['cargo']}, {EMPLEADOR_CORTO.get(estado['tipo_empleador'], 'empleo')}"
    return {"independiente": "Por tu cuenta", "fundador": "Tu empresa", "buscando": "Sin trabajo",
            "estudiando": "Estudiando"}.get(tipo, "Sin trabajar")


def _diferencia(x: float) -> str:
    monto = _plata(abs(x))
    return "$0" if monto == "$0" else f"{'+' if x > 0 else '−'}{monto}"


def _frase_mundos(opcion: dict, base: dict) -> str:
    """Cada gemelo contra sí mismo con la opción base: en cuántos mundos gana más, igual o menos, y por cuánto."""
    mas, igual, menos = opcion["gana_mas_que_base"], opcion["igual_que_base"], opcion["gana_menos_que_base"]
    cabeza = f"«{opcion['nombre']}» frente a «{base['nombre']}»:"
    if igual == 1:
        return f"{cabeza} no cambia tu sueldo en ningún mundo."
    if igual >= 0.95:
        return f"{cabeza} no cambia tu sueldo en casi ningún mundo."
    # décimos que suman 10: se reparte el redondeo entre los tres casos
    exactos = [mas * 10, igual * 10, menos * 10]
    decimos = [int(x) for x in exactos]
    for k in sorted(range(3), key=lambda k: exactos[k] - decimos[k], reverse=True)[: 10 - sum(decimos)]:
        decimos[k] += 1
    partes = []
    for cuantos, fraccion, que in zip(decimos, (mas, igual, menos), ("ganas más", "da lo mismo", "ganas menos")):
        if cuantos == 10 and fraccion < 1:
            partes.append(f"en casi todos los mundos {que}")
        elif cuantos == 10:
            partes.append(f"en todos los mundos {que}")
        elif cuantos:
            partes.append(f"en {cuantos} de cada 10 {'mundos ' if not partes else ''}{que}")
    lista = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]
    return f"{cabeza} {lista}. Diferencia típica: {_diferencia(opcion['diferencia_tipica'])} al mes."


def _tabla_gemelos(comp: dict) -> list[str]:
    """Las opciones lado a lado: lo que vivieron los gemelos con cada una (de a 3 si son más de 4)."""
    todas = list(enumerate(comp["opciones"], 1))
    por_bloque = len(todas) if len(todas) <= 4 else 3
    lineas = []
    for desde in range(0, len(todas), por_bloque):
        bloque = todas[desde : desde + por_bloque]
        opciones = [o for _, o in bloque]
        ancho = min(24, (ANCHO - 2 - ANCHO_ETIQUETA) // len(bloque))
        filas = [
            ("", [f"{i}. {o['nombre']}" for i, o in bloque]),
            ("La copia del medio gana", [_plata(o["sueldo"]["p50"]) for o in opciones]),
            ("1 de cada 10 gana menos de", [_plata(o["sueldo"]["p10"]) for o in opciones]),
            ("1 de cada 10 gana más de", [_plata(o["sueldo"]["p90"]) for o in opciones]),
            ("Algún año buscando pega", [_de_cada_cien(o["paso_por_cesantia"]) for o in opciones]),
            ("Terminan en un cargo más alto", [_de_cada_cien(o["sube_de_cargo"]) for o in opciones]),
        ]
        if desde:
            lineas.append("")
        for etiqueta, valores in filas:
            celdas = "".join(f"{_cortar(v, ancho - 2):<{ancho}}" for v in valores)
            lineas.append(f"  {etiqueta:<{ANCHO_ETIQUETA}}{celdas}".rstrip())
    return lineas


def _texto_comparacion(comp: dict, supuestos: list[str] | None = None) -> list[str]:
    n, anios = comp["gemelos"], comp["anios"]
    lineas = _envolver(
        f"Así les fue {anios} años después a {n} copias tuyas (la misma persona y la misma decisión, "
        "con otra suerte):"
    )
    lineas += ["", *_tabla_gemelos(comp), ""]
    lineas += _envolver("Sueldos líquidos al mes, en pesos de hoy (sin inflación); la copia que termina sin trabajo o "
                        "estudiando cuenta con $0.", "  ")
    for s in supuestos or []:
        lineas += _envolver(s, "  ")
    con_dado = [o for o in comp["opciones"] if len(o["por_resultado"]) > 1]
    if con_dado:
        lineas.append("")
    for o in con_dado:
        lineas.append(f"  El dado de «{o['nombre']}», según lo que les salió a las copias:")
        for r in o["por_resultado"]:
            lineas += _envolver(f"{_de_cada_cien(r['prob'])}: {r['texto'] or 'sin novedad'}", "      ", "    ")
    base = next((o for o in comp["opciones"] if o["es_base"]), None)
    frases = [_frase_mundos(o, base) for o in comp["opciones"]
              if base and not o["es_base"] and o["gana_mas_que_base"] is not None]
    if frases:
        frases.insert(0, "Cada copia contra sí misma, según lo que elige (sueldo al final):")
    if frases:
        lineas.append("")
    for k, f in enumerate(frases):
        lineas += _envolver(f, "      " if k else "  ", "    " if k else "  ")
    return lineas


def _texto_pie(creencia: str | None, calidad: str) -> list[str]:
    lineas = []
    if creencia:
        lineas += _envolver(f"Lo que se cree y lo que dice el dato: {creencia}", "  ")
    lineas += _envolver(f"Calidad de estos números: {CALIDAD.get(calidad, calidad)}.", "  ")
    return lineas


def _por_defecto(interna: dict) -> int:
    """Índice de la alternativa que suponen los gemelos: la más frecuente, o la primera."""
    alternativas = interna["alternativas"]
    return max(range(len(alternativas)), key=lambda i: alternativas[i].get("prob", 0))


def _supuestos_internos(pendiente: dict) -> list[str]:
    """Qué eligieron los gemelos dentro de cada opción (a qué rubro, a qué tipo de trabajo)."""
    comp = pendiente["comparacion"] or {"opciones": []}
    usados = {o["opcion"]: o.get("parametros") or {} for o in comp["opciones"]}
    salida = []
    for o in pendiente["opciones"]:
        for interna in o["elecciones_internas"]:
            valor = usados.get(o["opcion"], {}).get(interna["variable"])
            alt = next((a for a in interna["alternativas"] if a["valor"] == valor),
                       interna["alternativas"][_por_defecto(interna)])
            salida.append(f"Las copias de «{o['nombre']}» responden «{interna['pregunta']}» con «{alt['nombre']}».")
    return salida


def _texto_pendiente(pendiente: dict) -> list[str]:
    historia = (pendiente.get("narrativa") or {}).get("situacion")
    lineas = [*(_envolver(historia) + [""] if historia else []), *_envolver(pendiente["pregunta"]), ""]
    for i, o in enumerate(pendiente["opciones"], 1):
        detalle = f": {o['detalle']}" if o["detalle"] else ""
        lineas += _envolver(f"{i}. {o['nombre']}{detalle}", "     ", "  ")
    comp = pendiente["comparacion"]
    if comp:
        lineas += ["", *_texto_comparacion(comp, _supuestos_internos(pendiente))]
    else:
        lineas += ["", "  (Para esta decisión no se simulan copias.)"]
    lineas += _texto_pie(pendiente["creencia_vs_dato"], pendiente["calidad"])
    return lineas


def _texto_resultado_decision(d: dict, elegida: bool) -> list[str]:
    lineas = []
    if elegida:
        lineas += _envolver(f"Elegiste: {d['opcion_nombre']}.", "  ")
    if d["texto"]:
        marca = TONO.get(d["tono"], "•")
        # tu probabilidad en tu mundo (con su recesión y tu situación), no la frecuencia entre las copias de la tabla
        prob = f" (para ti, este año: {_de_cada_cien(d['prob'])})" if d["prob"] < 1 else ""
        lineas += _envolver(f"{marca} El dado: {d['texto']}{prob}", "    ", "  ")
    return lineas


def _texto_evento(ev: dict) -> list[str]:
    marca = TONO.get(ev["tono"], "•")
    directo = ev.get("directo") or ev["prob"] >= 1  # gatillado por otra regla: no tiene probabilidad propia
    prob = "" if directo else f" (probabilidad este año: {_de_cada_cien(ev['prob'])})"
    return _envolver(f"{marca} {ev['nombre']}: {ev['texto']}{prob}", "    ", "  ")


def _cabecera_anio(registro: dict, anios: int, edad_inicial: int) -> list[str]:
    """El año se cuenta por edad: un doctorado ocupa varios años en una sola ronda."""
    recesion = " · el país está en recesión" if registro["recesion"] else ""
    numero = registro["edad"] - edad_inicial + 1
    return ["", "═" * ANCHO, f"AÑO {numero} DE {anios} · tienes {registro['edad']} años{recesion}"]


def _texto_camino(historia: list[dict], internas: frozenset) -> list[str]:
    lineas = ["  Edad  Cómo cerraste el año      Sueldo       Lo que marcó el año", "  " + "-" * (ANCHO - 2)]
    for r in historia:
        fin = r["fin"]
        marcas = [d["opcion_nombre"] for d in r["decisiones"] if d["decision"] not in internas]
        marcas += [ev["nombre"] for ev in r["eventos"] if not ev["rutina"]]
        trabaja = fin["estado"] in ("empleado", "independiente", "fundador")
        sueldo = _plata(fin["sueldo"]) if trabaja and fin["sueldo"] > 0 else "-"
        fila = f"  {fin['edad']:>4}  {_cortar(_situacion_corta(fin), 24):<24}  {sueldo:<11}  "
        lineas.append((fila + _cortar("; ".join(marcas) or "sin novedad", ANCHO - len(fila))).rstrip())
    return lineas


def _texto_cierre(v: dict, internas: frozenset) -> list[str]:
    cierre, estado = v["cierre"], v["cierre"]["estado"]
    sin = cierre["anios_sin_trabajo"]
    pasaron = estado["edad"] - v["historia"][0]["edad"] if v["historia"] else 0
    lineas = ["", "═" * ANCHO, f"EL CIERRE · {pasaron} años después, tienes {estado['edad']} años", ""]
    lineas += _envolver(f"Terminas así: {_situacion(estado)}.", "  ")
    lineas += _envolver(
        "No cerraste ningún año sin trabajo." if sin == 0
        else f"Cerraste {sin} {'año' if sin == 1 else 'años'} sin trabajo y buscando.", "  ")
    lineas += _envolver(f"{_ahorros(estado['ahorro'])}.", "  ")
    lineas += ["", "  Tu camino:", "", *_texto_camino(v["historia"], internas)]
    primera = cierre["primera_decision"]
    if primera:
        comp = primera["comparacion"]
        elegida = next((o["nombre"] for o in comp["opciones"] if o["opcion"] == primera["elegida"]), primera["elegida"])
        lineas += ["", *_envolver(f"Tu primera decisión: {primera['pregunta']} Elegiste «{elegida}».", "  "), ""]
        lineas += _texto_comparacion(comp)
        if "mejor_que_gemelos" in cierre:
            cual = "Tu sueldo final" if estado["sueldo"] > 0 else "El sueldo al que apuntas al volver"
            lineas += ["", *_envolver(
                f"{cual} ({_plata(cierre['sueldo_final'])}) es más alto que el de "
                f"{_de_cada_cien(cierre['mejor_que_gemelos'])} copias que eligieron «{elegida}» como tú.", "  ")]
        lineas += _texto_pie(comp["creencia_vs_dato"], comp["calidad"])
    return lineas


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

    from app.services import perfil_ia

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
    from app.services.perfil_doc import prompt

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


# ── entrada ──────────────────────────────────────────────────────────────────


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description="Trayectoria laboral desde el terminal."
    )
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
        p.add_argument("--desde", metavar="ARCHIVO", help="archivo (markdown o texto) con tu información: Claude lo "
                       "lee y llena tu perfil; las demás opciones corrigen lo que leyó")

    def gemelos(p: argparse.ArgumentParser) -> None:
        p.add_argument("--gemelos", type=int, default=GEMELOS_POR_DEFECTO,
                       help=f"cuántas copias simular por opción (por defecto {GEMELOS_POR_DEFECTO})")

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
    ju.add_argument("--elecciones", help="opciones en orden, sin teclado: 1,2,1 (2:3 elige también dentro de la opción)")
    ju.add_argument("--auto", action="store_true", help="sin teclado: nunca busca cambios (y si la vida obliga a elegir, lo más común)")
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


if __name__ == "__main__":
    sys.exit(main())
