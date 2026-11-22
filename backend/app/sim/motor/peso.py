"""Cuánto pesa cada línea de tu CV en tu duda, y cuál de tus dudas tiene más en juego.

Todo sale de repetir `gemelos.comparar` con la misma semilla: los mismos dados,
otro perfil. Así la diferencia es el efecto de ese dato y no de otra suerte.
Aquí no se narra nada; el cliente arma las frases con estos números.
"""

from dataclasses import replace
from functools import lru_cache

from app.sim.motor import gemelos, partida
from app.sim.motor.perfil import Perfil

MAX_DATOS = 4  # cuántas líneas del CV se muestran: las que más mueven
MIN_CAMBIO = 0.01  # bajo esto (1 mundo de 100, o 1% del sueldo) el dato no mueve la duda
GANA_VISIBLE = 0.05  # desde 5 mundos de 100, lo que se cuenta es en cuántos gana (se entiende mejor que un sueldo)


def _neutro(campo: str, perfil: Perfil):
    """El valor que el motor usaría si el CV no dijera nada de ese campo; None si la persona ya lo tiene."""
    valor = getattr(perfil, campo)
    if campo in ("ingles", "usa_ia", "remoto", "parcial", "empresa_fondos"):
        return 0 if valor else None
    if campo in ("skill", "red", "anos_por_empleo"):
        return None if valor is None else "sin_dato"
    if campo == "nivel":  # sin el último ascenso: el cargo de entrada típico (Semi senior)
        return 1 if valor > 1 else None
    if campo == "edu":  # sin el último título
        return {"postgrado": "universitaria", "universitaria": "media", "tecnica": "media"}.get(valor)
    return None


CAMPOS = ("ingles", "skill", "red", "usa_ia", "remoto", "anos_por_empleo", "nivel", "edu", "parcial", "empresa_fondos")


def _sin(perfil: Perfil, campo: str, neutro) -> Perfil:
    cambios = {campo: None if neutro == "sin_dato" else neutro}
    if campo == "edu" and neutro == "media":
        cambios["carrera_id"] = -1  # sin título no hay carrera
    return replace(perfil, **cambios)


@lru_cache(maxsize=256)
def _comparar(perfil: Perfil, duda: str, semilla: int, n: int) -> dict | None:
    """La comparación de la duda al empezar la partida; None si con este perfil la duda no queda pendiente."""
    try:
        p = partida.jugar(perfil, semilla, [], duda)
    except ValueError:
        return None
    if p.pendiente is None or p.pendiente.decision["id"] != duda:
        return None
    return partida.comparar_pendiente(p, semilla, n)


def _por_opcion(c: dict) -> dict[str, dict]:
    ganadores = c["ganador_por_mundo"]
    return {
        o["opcion"]: {"nombre": o["nombre"], "gana": ganadores.count(o["opcion"]) / len(ganadores),
                      "sueldo": o["sueldo"]["p50"]}
        for o in c["opciones"]
    }


@lru_cache(maxsize=64)
def peso_cv(perfil: Perfil, duda: str, semilla: int = 0, n: int = gemelos.N_GEMELOS) -> dict:
    """Para cada dato del CV distinto del neutro: la duda con ese dato y sin él, con los mismos dados.

    `gana` es la fracción de mundos donde esa opción termina ganando más; `sueldo`, el sueldo típico (p50).
    `mueve` dice qué cambia más: en cuántos mundos gana la opción clave o su sueldo típico.
    """
    con = _comparar(perfil, duda, semilla, n)
    if con is None:
        raise ValueError(f"la decisión {duda!r} no queda pendiente al empezar con este perfil")
    con_op = _por_opcion(con)
    datos, sin_efecto = [], []
    for campo in CAMPOS:
        neutro = _neutro(campo, perfil)
        if neutro is None:
            continue
        sin = _comparar(_sin(perfil, campo, neutro), duda, semilla, n)
        if sin is None:  # sin ese dato la duda ni aparece: no se puede comparar mundo a mundo
            continue
        sin_op = _por_opcion(sin)
        opciones = [
            {"opcion": o, "nombre": a["nombre"], "gana_con": a["gana"], "gana_sin": sin_op[o]["gana"],
             "sueldo_con": a["sueldo"], "sueldo_sin": sin_op[o]["sueldo"]}
            for o, a in con_op.items() if o in sin_op
        ]
        d_gana = {x["opcion"]: abs(x["gana_con"] - x["gana_sin"]) for x in opciones}
        d_sueldo = {x["opcion"]: abs(x["sueldo_con"] - x["sueldo_sin"]) / max(x["sueldo_con"], 1) for x in opciones}
        cambio = max(d_gana.values(), default=0) + max(d_sueldo.values(), default=0)
        if cambio < MIN_CAMBIO:
            sin_efecto.append(campo)
            continue
        mueve = "gana" if max(d_gana.values()) >= min(GANA_VISIBLE, max(d_sueldo.values())) else "sueldo"
        medida = d_gana if mueve == "gana" else d_sueldo
        # la opción clave: la que se está pensando (no la base) que más cambia; la base solo si ninguna otra se mueve
        otras = [x for x in opciones if x["opcion"] != con["base"] and medida[x["opcion"]] >= MIN_CAMBIO]
        clave = max(otras or opciones, key=lambda x: medida[x["opcion"]])["opcion"]
        tuyo = getattr(perfil, campo)
        datos.append({"campo": campo, "tuyo": tuyo, "neutro": None if neutro == "sin_dato" else neutro,
                      "mueve": mueve, "opcion": clave, "cambio": round(cambio, 4), "opciones": opciones})
    datos.sort(key=lambda d: d["cambio"], reverse=True)
    return {"decision": duda, "nombre": con["nombre"], "pregunta": con["pregunta"], "gemelos": n, "semilla": semilla,
            "base": con["base"], "datos": datos[:MAX_DATOS], "sin_efecto": sin_efecto,
            "otros": [d["campo"] for d in datos[MAX_DATOS:]]}  # mueven algo, pero menos que los que se muestran


@lru_cache(maxsize=64)
def en_juego(perfil: Perfil, dudas: tuple[str, ...], semilla: int = 0, n: int = gemelos.N_GEMELOS) -> dict:
    """De varias dudas, cuánto se juega la persona en cada una y cuál es la que más.

    `mala` es el peor sueldo de mala suerte (p10) entre todas las opciones y `buena` el mejor de buena suerte
    (p90): el rango que abre la decisión. `dispersion` es ese rango sobre el sueldo típico de quedarse como está
    (la opción base), y es lo que ordena. `entre_opciones` es la distancia entre la opción de sueldo típico más
    alto y la de más bajo, sobre esta última. Con una sola duda no hay cuál marcar.
    """
    salida = []
    for duda in dict.fromkeys(dudas):
        c = _comparar(perfil, duda, semilla, n)
        if c is None:
            continue
        ops = c["opciones"]
        base = next(o for o in ops if o["es_base"])
        mala = min(o["sueldo"]["p10"] for o in ops)
        buena = max(o["sueldo"]["p90"] for o in ops)
        tipicos = [o["sueldo"]["p50"] for o in ops]
        salida.append({
            "decision": duda, "nombre": c["nombre"], "pregunta": c["pregunta"],
            "mala": mala, "buena": buena, "tipico": base["sueldo"]["p50"],
            "dispersion": round((buena - mala) / max(base["sueldo"]["p50"], 1), 4),
            "entre_opciones": round((max(tipicos) - min(tipicos)) / max(min(tipicos), 1), 4),
        })
    mas = max(salida, key=lambda d: d["dispersion"])["decision"] if len(salida) > 1 else None
    return {"gemelos": n, "semilla": semilla, "mas_en_juego": mas, "dudas": salida}
