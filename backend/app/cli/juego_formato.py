"""Cómo se muestra el juego en el terminal: comparaciones, cartas, eventos y cierre."""

import textwrap
import unicodedata

from app.cli.formato import ANCHO, _cortar, _pesos

# ── el juego: formato ────────────────────────────────────────────────────────

ANCHO_ETIQUETA = 30
EMPLEADOR = {
    "grande": "una empresa grande",
    "pyme": "una pyme",
    "startup": "una startup",
    "publico": "el Estado",
    "extranjero": "una empresa de afuera",
}
CALIDAD = {
    "dato": "dato (medido en encuestas o estudios)",
    "mixto": "mixto (parte medido, parte supuesto del equipo)",
    "supuesto": "supuesto (del equipo, sin medición detrás)",
}
EMPLEADOR_CORTO = {
    "grande": "empresa grande",
    "pyme": "pyme",
    "startup": "startup",
    "publico": "Estado",
    "extranjero": "empresa de afuera",
}
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
    return textwrap.wrap(
        texto,
        width=ANCHO,
        initial_indent=sangria if primera is None else primera,
        subsequent_indent=sangria,
        break_long_words=False,
    ) or [""]


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
    return {
        "independiente": "Por tu cuenta",
        "fundador": "Tu empresa",
        "buscando": "Sin trabajo",
        "estudiando": "Estudiando",
    }.get(tipo, "Sin trabajar")


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
        f"Así les fue {anios} años después a {n} copias tuyas (la misma persona y la misma decisión, con otra suerte):"
    )
    lineas += ["", *_tabla_gemelos(comp), ""]
    lineas += _envolver(
        "Sueldos líquidos al mes, en pesos de hoy (sin inflación); la copia que termina sin trabajo o "
        "estudiando cuenta con $0.",
        "  ",
    )
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
    frases = [
        _frase_mundos(o, base)
        for o in comp["opciones"]
        if base and not o["es_base"] and o["gana_mas_que_base"] is not None
    ]
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
            alt = next(
                (a for a in interna["alternativas"] if a["valor"] == valor),
                interna["alternativas"][_por_defecto(interna)],
            )
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
        "No cerraste ningún año sin trabajo."
        if sin == 0
        else f"Cerraste {sin} {'año' if sin == 1 else 'años'} sin trabajo y buscando.",
        "  ",
    )
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
            lineas += [
                "",
                *_envolver(
                    f"{cual} ({_plata(cierre['sueldo_final'])}) es más alto que el de "
                    f"{_de_cada_cien(cierre['mejor_que_gemelos'])} copias que eligieron «{elegida}» como tú.",
                    "  ",
                ),
            ]
        lineas += _texto_pie(comp["creencia_vs_dato"], comp["calidad"])
    return lineas
