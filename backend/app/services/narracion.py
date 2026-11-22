"""Qué textos de una partida narra Sonnet, armados desde la partida que vuelve a jugar el servidor.

No se confía en texto del cliente: el servidor rejuega (perfil, semilla, duda, elecciones) y saca de ahí
la plantilla y el contexto de cada texto. Sonnet solo reescribe; si falla, queda la plantilla.
"""

from app.services import narrador_ia
from app.services.narrador_ia import Item
from app.sim.motor import gemelos, partida
from app.sim.motor.perfil import Perfil

MAX_ITEMS = 36  # unas tres llamadas a Sonnet como máximo por pedido


def _ficha_oferta(o: dict) -> str:
    emp = o["empresa"]
    cargo = f"ser {emp['cargo']}" if emp.get("cargo") else "un puesto"
    return f"Te ofrecen {cargo} en {emp['nombre']}, {emp['rubro'].lower()}."


def items_pendiente(vista: dict) -> list[Item]:
    p = vista.get("pendiente")
    if not p:
        return []
    items = []
    if p.get("narrativa"):
        items.append(Item(id="situacion", tipo="evento", plantilla=p["narrativa"]["situacion"],
                          contexto={"decision": p["decision"], "pregunta": p["pregunta"], "tono": "neutro",
                                    "edad": vista["estado"]["edad"], "rubro": vista["estado"]["rubro"],
                                    "empresa": vista["estado"].get("empresa"), "cargo": vista["estado"].get("rol")}))
    for o in p["opciones"]:
        if o.get("empresa"):
            emp = o["empresa"]
            items.append(Item(id=f"oferta:{o['opcion']}", tipo="oferta", plantilla=_ficha_oferta(o),
                              contexto={"decision": p["decision"], "opcion": o["nombre"], "empresa": emp["nombre"],
                                        "cargo": emp.get("cargo"), "rubro": emp["rubro"], "tipo_empleador": emp["tipo"],
                                        "pais": emp.get("pais"), "tono": "neutro"}))
    return items


def items_historia(vista: dict) -> list[Item]:
    """Lo que te pasó cada año (decisiones y eventos que no son rutina), del más reciente al más antiguo."""
    items = []
    for a in reversed(vista.get("historia", [])):
        fin = a.get("fin") or {}
        base = {"anio": a["anio"], "edad": a.get("edad"), "empresa": fin.get("empresa"), "cargo": fin.get("rol"),
                "rubro": fin.get("rubro"), "tipo_empleador": fin.get("tipo_empleador"),
                "escenario_ia": gemelos.escenario_ia(fin.get("ia_adopcion", 0.5))}
        for j, d in enumerate(a.get("decisiones", [])):
            if d.get("texto"):
                ctx = d.get("contexto", {})
                items.append(Item(id=f"anio:{a['anio']}:decision:{j}", tipo="evento", plantilla=d["texto"],
                                  contexto={**base, "decision": d["nombre"], "opcion": d["opcion_nombre"], "tono": d["tono"],
                                            "empresa": ctx.get("empresa") or base["empresa"],
                                            "oferta": (ctx.get("oferta") or {}).get("nombre")}))
        for j, ev in enumerate(a.get("eventos", [])):
            if not ev.get("rutina") and ev.get("texto"):
                items.append(Item(id=f"anio:{a['anio']}:evento:{j}", tipo="evento", plantilla=ev["texto"],
                                  contexto={**base, "evento": ev["nombre"], "tono": ev["tono"]}))
    return items[:MAX_ITEMS]


def _plantilla_mundo(o: dict) -> str:
    sucesos = [s["texto"] for a in o["anios"] for s in a["sucesos"] if s.get("texto")]
    final = f" Terminas en {o['empresa_final']}." if o.get("empresa_final") else ""
    return (" ".join(sucesos[:6]) + final).strip() or "En este mundo no pasa nada especial."


def items_mundo(m: dict) -> list[Item]:
    items = []
    for o in m["opciones"]:
        sucesos = [{"anio": a["anio"], "que": s["nombre"], "tono": s["tono"]} for a in o["anios"] for s in a["sucesos"]]
        malo = any(s["tono"] == "malo" for s in sucesos)
        items.append(Item(id=f"mundo:{o['opcion']}", tipo="mundo", plantilla=_plantilla_mundo(o),
                          contexto={"decision": m["decision"], "opcion": o["nombre"], "escenario_ia": m.get("ia", {}).get("escenario"),
                                    "empresa": o.get("empresa_final"), "cargo": o.get("rol_final"),
                                    "estado_final": o["estado_final"], "sucesos": sucesos[:12],
                                    "tono": "malo" if malo else "neutro"}))
    return items


def narrar(perfil: Perfil, semilla: int, duda: str | None, elecciones: list[dict], que: str,
           mundo: int | None = None, parametros: dict | None = None, relato: str = "") -> dict:
    if que == "mundo":
        if mundo is None:
            raise ValueError("falta el número de mundo")
        items = items_mundo(partida.mundo_pendiente(perfil, semilla, duda, elecciones, mundo, parametros))
    else:
        vista = partida.vista(perfil, semilla, duda, elecciones, n_gemelos=0)
        items = items_pendiente(vista) if que == "pendiente" else items_historia(vista)
    return {"items": [n.model_dump() for n in narrador_ia.narrar(items, relato)]}
