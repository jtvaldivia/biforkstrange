"""Explicaciones en texto de lo que pasó en la simulación. Salen del modelo mismo, así que cuadran con los números."""

from app.sim.decisions.base import Decision, get_decision
from app.sim.personality import Params

PARAM_NAMES = {"growth": "crecimiento", "risk": "riesgo de desempleo", "wear": "desgaste"}


def pts(x: float) -> str:
    """0.034 → '+3,4 pts'."""
    v = x * 100
    s = f"{abs(v):.1f}".replace(".", ",").replace(",0", "")
    return f"{'+' if v > 0 else '−' if v < 0 else ''}{s} pts"


def pct(x: float, signed: bool = False) -> str:
    v = round(x * 100)
    return f"{'+' if signed and v > 0 else '−' if v < 0 else ''}{abs(v)}%"


def effect_label(param: str, delta: float) -> str:
    return f"{pts(delta)} de {PARAM_NAMES[param]}"


def explain_step(
    decision: Decision, params: Params | None, factores: list[dict], before: dict, prev: dict, now: dict
) -> dict:
    items: list[dict] = []

    # 1. la decisión
    if params is not None:
        base = getattr(decision, "params", params)
        items.append({
            "fuente": "decision",
            "texto": getattr(decision, "why", "") or decision.label,
            "efecto": f"sueldo {pct(base.growth, True)} esperado · riesgo {pct(base.risk)} · desgaste {pts(base.wear)}",
        })

    # 2. tus rasgos
    for f in factores:
        items.append({"fuente": "rasgo", "texto": f["texto"], "efecto": effect_label(f["param"], f["delta"])})

    # 3. lo que arrastras del año anterior
    if before["quemados"] >= 0.05 and before["riesgo_extra"] >= 0.005:
        items.append({
            "fuente": "estado",
            "texto": f"Llegas con desgaste alto en el {pct(before['quemados'])} de tus vidas, y eso aumenta el riesgo de quedar sin pega",
            "efecto": f"{pts(before['riesgo_extra'])} de riesgo de desempleo",
        })
    if now["prob_desempleo"] >= 0.08:
        items.append({
            "fuente": "estado",
            "texto": f"En el {pct(now['prob_desempleo'])} de tus vidas quedas sin pega este año y cobras el 60% del sueldo",
            "efecto": "baja el sueldo típico y ensancha el rango hacia abajo",
        })

    d_sueldo = now["sueldo_p50"] / prev["sueldo_p50"] - 1 if prev["sueldo_p50"] else 0.0
    d_desgaste = now["desgaste_p50"] - prev["desgaste_p50"]
    return {
        "titular": headline(decision, params, factores, d_sueldo, d_desgaste, before, now),
        "cambio_sueldo": d_sueldo,
        "cambio_desgaste": d_desgaste,
        "parametros": None if params is None else {"growth": params.growth, "risk": params.risk, "wear": params.wear},
        "factores": items,
        "_rasgos": [{k: f[k] for k in ("rasgo", "valor", "param", "delta")} for f in factores],
    }


def headline(decision, params, factores, d_sueldo, d_desgaste, before, now) -> str:
    if abs(d_desgaste) < 0.01:
        desgaste = "el desgaste se mantiene"
    else:
        desgaste = f"el desgaste {'sube' if d_desgaste > 0 else 'baja'} {pts(abs(d_desgaste)).lstrip('+')}"
    if d_sueldo <= -0.01:
        if params is not None and params.growth < 0:
            why = "esta decisión cuesta plata este año"
        else:
            why = f"en más vidas quedas sin pega ({pct(now['prob_desempleo'])})"
        text = f"Tu sueldo típico baja {pct(abs(d_sueldo))} porque {why}; {desgaste}."
    elif d_sueldo >= 0.01:
        cost = f"pero {desgaste}" if d_desgaste > 0.04 else f"y {desgaste}"
        text = f"Tu sueldo típico sube {pct(d_sueldo)}, {cost}."
    else:
        text = f"El sueldo casi no se mueve y {desgaste}."
    if before["quemados"] >= 0.2:
        text += f" Ojo: ya llegas quemado en el {pct(before['quemados'])} de tus vidas."
    else:
        # destaca el rasgo propio de esta decisión (los generales se repiten todos los años)
        specific = [f for f in factores if f.get("especifico")]
        top = max(specific, key=lambda f: abs(f["delta"]), default=None)
        if top is not None:
            text += f" Para ti pesa tu {top['rasgo'].lower()}: {effect_label(top['param'], top['delta'])}."
    return text


def summarize_run(twin, steps: list[dict]) -> dict:
    """Lo que más pesó en toda la partida."""
    if not steps:
        return {"titular": "", "puntos": []}
    first, last = twin.sueldo, steps[-1]
    total = last["sueldo_p50"] / first - 1
    best = max(steps, key=lambda s: s["explicacion"]["cambio_sueldo"])
    worst = min(steps, key=lambda s: s["explicacion"]["cambio_sueldo"])
    ancho = (last["sueldo_p90"] - last["sueldo_p10"]) / last["sueldo_p50"] if last["sueldo_p50"] else 0

    puntos = [
        f"El mejor año fue a los {best['edad']} ({get_decision(best['decision']).label.lower()}): sueldo típico {pct(best['explicacion']['cambio_sueldo'], True)}.",
    ]
    if worst is not best and worst["explicacion"]["cambio_sueldo"] < 0:
        puntos.append(
            f"El más duro, a los {worst['edad']} ({get_decision(worst['decision']).label.lower()}): {pct(worst['explicacion']['cambio_sueldo'], True)}."
        )
    if last["desgaste_p50"] > 0.6:
        puntos.append(f"Terminas con desgaste {pct(last['desgaste_p50'])}: sobre 60% el riesgo de quedar sin pega empieza a crecer solo.")
    elif last["desgaste_p50"] < twin.desgaste:
        puntos.append(f"Terminas menos desgastado que al partir ({pct(twin.desgaste)} → {pct(last['desgaste_p50'])}).")
    if ancho > 0.6:
        puntos.append("Tu rango final es ancho: este camino es una apuesta, con vidas muy buenas y muy malas.")
    elif ancho < 0.3:
        puntos.append("Tu rango final es angosto: es un camino predecible.")

    # lo que sumaron tus rasgos en toda la partida
    totals = {"growth": 0.0, "risk": 0.0, "wear": 0.0}
    by_trait: dict[str, float] = {}
    for s in steps:
        for f in s["explicacion"].get("_rasgos", []):
            totals[f["param"]] += f["delta"]
            label = f"{f['rasgo']} {f['valor']}"
            by_trait[label] = by_trait.get(label, 0) + abs(f["delta"])
    if by_trait:
        parts = [effect_label(k, v) for k, v in totals.items() if abs(v) >= 0.005]
        top = max(by_trait, key=by_trait.get)
        if parts:
            puntos.append(f"Tus rasgos sumaron en total {', '.join(parts)}. El que más pesó: {top}.")

    direction = "más" if total >= 0 else "menos"
    return {
        "titular": f"En {len(steps)} {'año' if len(steps) == 1 else 'años'} tu sueldo típico queda {pct(abs(total))} {direction} que hoy.",
        "puntos": puntos,
    }


def compare_runs(plan_a: list[str], plan_b: list[str], a: dict, b: dict) -> dict:
    """Por qué B termina distinto que A (corridos con la misma semilla: la diferencia es solo la decisión)."""
    la, lb = a["trayectoria"][-1], b["trayectoria"][-1]
    d_sueldo = lb["sueldo_p50"] / la["sueldo_p50"] - 1 if la["sueldo_p50"] else 0
    d_desgaste = lb["desgaste_p50"] - la["desgaste_p50"]
    width = lambda s: (s["sueldo_p90"] - s["sueldo_p10"]) / s["sueldo_p50"] if s["sueldo_p50"] else 0  # noqa: E731

    if abs(d_sueldo) < 0.02:
        tit = "A y B terminan con un sueldo típico parecido"
    else:
        tit = f"B termina con un sueldo típico {pct(abs(d_sueldo))} {'mayor' if d_sueldo > 0 else 'menor'} que A"
    if abs(d_desgaste) >= 0.03:
        tit += f", con {pts(abs(d_desgaste)).lstrip('+')} {'más' if d_desgaste > 0 else 'menos'} de desgaste"
    tit += "."

    diffs = []
    for i, (ka, kb) in enumerate(zip(plan_a, plan_b)):
        if ka == kb:
            continue
        sa, sb = a["trayectoria"][i], b["trayectoria"][i]
        da, db = get_decision(ka), get_decision(kb)
        diffs.append(
            f"A los {sb['edad']}: A elige {da.label.lower()} ({pct(sa['explicacion']['cambio_sueldo'], True)} de sueldo, "
            f"desgaste {pct(sa['desgaste_p50'])}) y B {db.label.lower()} ({pct(sb['explicacion']['cambio_sueldo'], True)}, "
            f"desgaste {pct(sb['desgaste_p50'])})."
        )
    if len(plan_a) != len(plan_b):
        diffs.append(f"A dura {len(plan_a)} años y B {len(plan_b)}: se comparan al final de cada uno.")

    puntos = diffs[:6]
    wa, wb = width(la), width(lb)
    if abs(wb - wa) > 0.1:
        puntos.append(f"B es {'más arriesgado' if wb > wa else 'más predecible'} que A: su rango final es {'más ancho' if wb > wa else 'más angosto'}.")
    if (lb["prob_desempleo"] - la["prob_desempleo"]) >= 0.03:
        puntos.append(f"En el último año, B tiene más riesgo de quedar sin pega ({pct(lb['prob_desempleo'])} contra {pct(la['prob_desempleo'])}).")
    elif (la["prob_desempleo"] - lb["prob_desempleo"]) >= 0.03:
        puntos.append(f"En el último año, A tiene más riesgo de quedar sin pega ({pct(la['prob_desempleo'])} contra {pct(lb['prob_desempleo'])}).")
    return {"titular": tit, "puntos": puntos, "diferencia_sueldo": d_sueldo, "diferencia_desgaste": d_desgaste}
