"""Cuánto conoce el gemelo a la persona: métricas del examen a ciegas."""

import math

from app.twin.dims import TEMA_LABELS
from app.twin.profile import ExamItem

CAL_BINS = [(0, 40), (40, 60), (60, 80), (80, 101)]
P_FLOOR = 1.0  # para que un 0% no dé log-score infinito


def brier(item: ExamItem) -> float:
    return sum((p / 100 - (1.0 if i == item.ans else 0.0)) ** 2 for i, p in enumerate(item.probs))


def exam_metrics(items: list[ExamItem], window: int = 10) -> dict:
    done = [e for e in items if e.ans is not None]
    n = len(done)
    if not n:
        return {"n": 0, "acierto": None, "azar": None, "p_media": None, "log_score": None,
                "brier": None, "calibracion": [], "por_tema": [], "tendencia": []}

    hits = [1.0 if e.hit else 0.0 for e in done]
    calibracion = []
    for lo, hi in CAL_BINS:
        b = [e for e in done if lo <= e.probs[e.top] < hi]
        if b:
            calibracion.append({
                "rango": f"{lo}–{min(hi, 100)}%",
                "n": len(b),
                "confianza": round(sum(e.probs[e.top] for e in b) / len(b), 1),
                "acierto": round(100 * sum(1 for e in b if e.hit) / len(b), 1),
            })

    por_tema = []
    for tema, label in TEMA_LABELS.items():
        t = [e for e in done if e.tema == tema]
        if t:
            por_tema.append({"tema": tema, "label": label, "n": len(t),
                             "acierto": round(100 * sum(1 for e in t if e.hit) / len(t), 1)})

    tendencia = [round(100 * sum(hits[max(0, i - window + 1): i + 1]) / len(hits[max(0, i - window + 1): i + 1]), 1)
                 for i in range(n)]

    return {
        "n": n,
        "acierto": round(100 * sum(hits) / n, 1),
        "azar": round(100 * sum(1 / len(e.opts) for e in done) / n, 1),
        "p_media": round(sum(e.p_ans or 0 for e in done) / n, 1),
        "log_score": round(sum(-math.log(max(e.p_ans or 0, P_FLOOR) / 100) for e in done) / n, 3),
        "brier": round(sum(brier(e) for e in done) / n, 3),
        "calibracion": calibracion,
        "por_tema": por_tema,
        "tendencia": tendencia,
    }


def next_tema(items: list[ExamItem]) -> str:
    """'Auto': primero los temas con menos de 2 preguntas, después el de menor acierto."""
    done = [e for e in items if e.ans is not None]
    counts = {t: sum(1 for e in done if e.tema == t) for t in TEMA_LABELS}
    few = [t for t, c in counts.items() if c < 2]
    if few:
        return min(few, key=lambda t: counts[t])
    return min(TEMA_LABELS, key=lambda t: sum(1 for e in done if e.tema == t and e.hit) / counts[t])
