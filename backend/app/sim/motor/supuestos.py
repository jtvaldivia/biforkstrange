"""De dónde sale cada número del motor: los parámetros del paquete con su calidad, fuente y país.

Idea traída del PR #3 (`make supuestos`): ver de un vistazo qué es dato, qué es mixto
(parte medido, parte supuesto) y qué sigue siendo supuesto del equipo, para saber qué
reemplazar primero y para responder "¿de dónde sale este número?".
"""

from collections import Counter

from app.sim.motor.paquete import Paquete, paquete

ORDEN = {"supuesto": 0, "sintetico": 1, "mixto": 2, "dato": 3}


def listar(pq: Paquete | None = None) -> dict:
    pq = pq or paquete()
    filas = []
    for p in pq.parametros.values():
        f = pq.fuentes.get(p["fuente"], {})
        filas.append({
            "id": p["id"], "valor": p["valor"], "unidad": p.get("unidad", ""), "descripcion": p.get("descripcion", ""),
            "calidad": p.get("calidad", "supuesto"), "fuente": p["fuente"],
            "cita": f.get("cita", "supuesto del equipo" if p["fuente"] == "equipo" else ""), "pais": f.get("pais", ""),
            "rango": p.get("rango"),
        })
    filas.sort(key=lambda x: (ORDEN.get(x["calidad"], 0), x["id"]))
    conteo = Counter(x["calidad"] for x in filas)
    paises = Counter(x["pais"] for x in filas if x["calidad"] != "supuesto" and x["pais"])
    return {"total": len(filas), "por_calidad": dict(conteo), "por_pais": dict(paises), "parametros": filas}


def _valor(v) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{k}: {_valor(x)}" for k, x in v.items())
    if isinstance(v, list):
        return "[" + ", ".join(_valor(x) for x in v) + "]"
    if isinstance(v, float):
        return f"{v:g}".replace(".", ",")
    return str(v)


def texto(r: dict, ancho: int = 100) -> str:
    c = r["por_calidad"]
    lineas = [f"{r['total']} parámetros: {c.get('dato', 0)} dato, {c.get('mixto', 0)} mixtos y {c.get('supuesto', 0)} supuestos del equipo.",
              "Países de las fuentes (dato y mixto): " + ", ".join(f"{p} {n}" for p, n in sorted(r["por_pais"].items(), key=lambda x: -x[1])),
              ""]
    actual = None
    for p in r["parametros"]:
        if p["calidad"] != actual:
            actual = p["calidad"]
            lineas += ["", f"-- {actual.upper()}"]
        valor = _valor(p["valor"])
        if len(valor) > 40:
            valor = valor[:37] + "..."
        origen = p["cita"] or p["fuente"]
        if p["pais"]:
            origen += f" ({p['pais']})"
        lineas.append(f"{p['id']:<26} {valor:<40} {origen[:90]}")
    return "\n".join(lineas)
