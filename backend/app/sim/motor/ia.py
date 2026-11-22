"""La incertidumbre de la IA: el ritmo de cada mundo y lo que hace con tu pega.

Se prende y se apaga con una sola flag, `ACTIVA` (variable de entorno BIFURCA_IA: "0" la apaga). Apagada, el
juego queda como antes: el escenario de IA solo baja la contratación de jóvenes en áreas expuestas.

Prendida:
- Cada mundo trae un ritmo de IA (lento, medio o rápido), sorteado con los pesos que economistas y
  superforecasters dieron a cada escenario al 2030 (FRI 2026, parámetro P_RITMO_IA). Es igual en todas las vidas
  del mundo, como la recesión.
- Tu cargo tiene un tipo de exposición (OIT 2025): la IA lo automatiza, lo complementa, no se sabe o no lo toca.
- El ritmo baja la contratación de jóvenes donde la IA automatiza (`ia_encontrar`), y el paquete lo usa en los
  eventos y decisiones de IA (empresa que adopta IA, reestructuración, burbuja, cobre) y en la prima de saber usarla.

Ningún número vive aquí: todos son parámetros del paquete con su fuente. Ver docs/COMO-FUNCIONA.md.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

ACTIVA = os.environ.get("BIFURCA_IA", "1").strip().lower() not in ("0", "no", "false", "off", "")

RITMOS = ("lento", "medio", "rapido")
TIPOS = ("automatiza", "aumenta", "incognita", "no_afectado")


def activa() -> bool:
    """Se lee en cada llamada para que los tests puedan cambiarla con monkeypatch."""
    return ACTIVA


def ritmo(pq, u: float) -> str:
    """El ritmo del mundo desde su sorteo uniforme: corta en los pesos acumulados de P_RITMO_IA."""
    pesos = pq.k("P_RITMO_IA")
    acumulado = 0.0
    for r in RITMOS:
        acumulado += pesos[r]
        if u < acumulado:
            return r
    return RITMOS[-1]


def tipo_de_cargo(pq, cargo_id: int) -> str | None:
    if cargo_id is None or cargo_id < 0:
        return None
    if not hasattr(pq, "_ia_tipos"):
        pq._ia_tipos = {int(f["cargo_id"]): f["tipo_ia"] for f in pq.filas("ia_cargos_ciuo08")}
    return pq._ia_tipos.get(int(cargo_id))


def tipo(pq, e: dict) -> str:
    """Cómo te toca la IA: el tipo OIT de tu cargo (o del último que tuviste). Sin cargo del catálogo, por tu
    exposición: expuesta pero sin saber si te reemplaza o te complementa (incógnita), o no afectada.
    Quien hizo un programa largo de IA (`ia_reconvertido`) trabaja con la IA: cuenta como complementado."""
    t = tipo_de_cargo(pq, e.get("cargo_id", -1))
    if t is None:
        t = "incognita" if e.get("exposicion_ia", 0) >= pq.k("IA_EXPUESTA") else "no_afectado"
    if e.get("ia_reconvertido") and t in ("automatiza", "incognita"):
        t = "aumenta"
    return t


def adaptabilidad(pq, e: dict) -> float:
    """Qué tan bien te recuperas si la IA te saca de tu pega (0-1). Componentes de Manning y Aguirre (2026)
    medidos con datos de Chile: edad (meses de cesantía por edad, OCEC UDP con INE), educación (FMI 2024),
    densidad del mercado (Santiago o región), colchón (meses de sueldo ahorrados) y si ya usas IA.
    Promedio simple: los pesos son supuesto del equipo (IA_ADAPT_PESOS)."""
    meses = pq.k("IA_ADAPT_MESES_EDAD")
    banda = "15-24" if e["edad"] < 25 else "25-34" if e["edad"] < 35 else "35-49" if e["edad"] < 50 else "50+"
    lo, hi = min(meses.values()), max(meses.values())
    edad = 1 - (meses[banda] - lo) / (hi - lo)
    edu = pq.k("IA_ADAPT_EDU", e.get("edu", "media"), 0.0)
    region = 1.0 if e.get("region", "rm") == "rm" else pq.k("IA_ADAPT_REGION")
    sueldo_mes = e.get("sueldo_ref") or e.get("sueldo") or 0
    colchon = min(1.0, max(0.0, e.get("ahorro", 0) / (pq.k("IA_ADAPT_MESES_COLCHON") * sueldo_mes))) if sueldo_mes > 0 else 0.0
    usa = 1.0 if e.get("usa_ia") else 0.0
    w = pq.k("IA_ADAPT_PESOS")
    total = sum(w.values())
    valor = (w["edad"] * edad + w["edu"] * edu + w["region"] * region + w["colchon"] * colchon + w["usa_ia"] * usa) / total
    return round(min(1.0, max(0.0, valor)), 4)


def encontrar(pq, e: dict) -> float:
    """Multiplica la probabilidad de encontrar pega (primera pega y cesantía). Hoy los jóvenes en ocupaciones donde
    la IA automatiza ya tienen 19% menos empleo (IA_JOVEN, Canaries 2026); cada año el ritmo del mundo agranda
    la brecha (IA_CONTRATACION_ANUAL × IA_INTENSIDAD) hasta 2030 (IA_RAMPA_ANIOS). Las incógnitas pesan la mitad
    (IA_PESO_TIPO)."""
    if not e.get("ia_v2") or e["edad"] > pq.k("IA_EDAD_JOVEN"):
        return 1.0
    peso = pq.k("IA_PESO_TIPO", e.get("ia_tipo", "no_afectado"), 0.0)
    if peso <= 0:
        return 1.0
    hoy = 1 - (1 - pq.k("IA_JOVEN")) * peso
    # crece hasta el horizonte del FRI (2030, IA_RAMPA_ANIOS) y ahí se queda: más allá nadie lo mide
    anios = min(e.get("ia_anios", 0), pq.k("IA_RAMPA_ANIOS"))
    caida = pq.k("IA_CONTRATACION_ANUAL") * pq.k("IA_INTENSIDAD", e.get("ia_ritmo", "medio")) * anios * peso
    return max(pq.k("IA_PISO_ENCONTRAR"), hoy * (1 - caida))


@lru_cache(maxsize=1)
def escenarios() -> dict:
    """Qué es cada ritmo y las voces del cierre (simulador/escenarios_ia.json), con la cita de cada fuente."""
    raiz = Path(__file__).resolve().parents[3] / "simulador"
    datos = json.loads((raiz / "escenarios_ia.json").read_text(encoding="utf-8"))
    citas = {f["id"]: f for f in json.loads((raiz / "fuentes.json").read_text(encoding="utf-8"))["fuentes"]}
    for x in [*datos["ritmos"].values(), *datos["voces"]]:
        x["cita"], x["url"] = citas[x["fuente"]]["cita"], citas[x["fuente"]]["url"]
    return datos


def por_ritmo(ritmos: list[str], ganadores: list[str | None], sueldos: dict[str, list[float]]) -> dict:
    """La comparación separada por ritmo de la IA: cuántos mundos hay de cada ritmo, en cuántos gana cada opción y
    su sueldo mediano. El cierre la usa para decir cuánto habría ganado tu opción con cada ritmo."""
    from statistics import median

    salida: dict = {"ritmos": {}}
    for r in RITMOS:
        idx = [g for g, x in enumerate(ritmos) if x == r]
        if not idx:
            continue
        gana = {o: sum(1 for g in idx if ganadores[g] == o) for o in sueldos}
        salida["ritmos"][r] = {"mundos": len(idx), "gana": gana,
                               "sueldo_p50": {o: round(median(v[g] for g in idx)) for o, v in sueldos.items()}}
    return salida
