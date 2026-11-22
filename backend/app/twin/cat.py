"""Loop adaptativo tipo CAT: qué preguntar, cómo actualizar y qué tan claro está el perfil."""

import math
import random

from app.twin.dims import DIMS, FIT_WEIGHTS, GROUP_WEIGHT, INTERESES, VALORES
from app.twin.profile import PRIOR_SD, Dim

SDO = 18.0  # ruido de una respuesta de elección forzada
SD_FLOOR = 6.0
SD_CLEAR = 12.0  # bajo esto la dimensión se da por medida
MIN_ANSWERS = 2  # mínimo de respuestas antes de cerrar una dimensión
SECONDS_PER_MONTH = 30 * 24 * 3600


def is_closed(d: Dim) -> bool:
    return d.sd <= SD_CLEAR and d.n >= MIN_ANSWERS


def select_targets(dims: dict[str, Dim], rng: random.Random | None = None) -> list[str] | None:
    """Dimensiones objetivo de la próxima pregunta, o None si el perfil ya está claro."""
    rng = rng or random.Random()
    open_ = [k for k, d in dims.items() if k in DIMS and not is_closed(d)]
    if not open_:
        return None

    def score(k: str) -> float:
        d = dims[k]
        return d.sd * GROUP_WEIGHT[DIMS[k].grupo] * (1.1 if d.n == 0 else 1.0) + rng.uniform(0, 2)

    top = max(open_, key=score)
    grupo = DIMS[top].grupo
    same = sorted(
        (k for k in open_ if k != top and DIMS[k].grupo == grupo),
        key=lambda k: dims[k].sd,
        reverse=True,
    )
    if grupo in (INTERESES, VALORES):
        return [top, *same[:2]]  # elección entre tareas o valores
    rivals = [k for k in same if dims[k].sd > 14]
    if rivals and rng.random() < 0.5:
        return [top, rivals[0]]  # contrapone rasgos
    return [top]


def update(d: Dim, obs: float, at: float) -> Dim:
    """Actualización bayesiana normal-normal con una observación de ruido SDO."""
    p0, p1 = 1 / d.sd**2, 1 / SDO**2
    m = (d.m * p0 + obs * p1) / (p0 + p1)
    sd = max(SD_FLOOR, math.sqrt(1 / (p0 + p1)))
    return d.model_copy(update={"m": m, "sd": sd, "n": d.n + 1, "updated_at": at})


def apply_drift(dims: dict[str, Dim], at: float) -> bool:
    """+1 de sd por cada mes sin respuestas nuevas (tope 30). Devuelve si cambió algo."""
    changed = False
    for k, d in dims.items():
        if d.updated_at is None:
            continue
        months = int((at - d.updated_at) // SECONDS_PER_MONTH)
        if months > 0:
            dims[k] = d.model_copy(
                update={"sd": min(PRIOR_SD, d.sd + months), "updated_at": d.updated_at + months * SECONDS_PER_MONTH}
            )
            changed = True
    return changed


def clarity(dims: dict[str, Dim]) -> dict:
    vals = [min(1.0, max(0.0, 1 - (d.sd - 8) / 22)) for d in dims.values()]
    return {
        "claridad": round(100 * sum(vals) / len(vals), 1),
        "medidas": sum(1 for d in dims.values() if is_closed(d)),
        "total": len(dims),
    }


def job_fit(dims: dict[str, Dim]) -> list[dict]:
    out = []
    for job, weights in FIT_WEIGHTS.items():
        total_w = sum(abs(w) for w in weights.values())
        contrib = {k: w * (dims[k].m - 50) / 50 for k, w in weights.items()}
        score = 50 + 50 * sum(contrib.values()) / total_w
        margin = min(40.0, 1.6 * 50 * math.sqrt(sum((w * dims[k].sd / 50) ** 2 for k, w in weights.items())) / total_w)
        ranked = sorted(contrib.items(), key=lambda kv: kv[1], reverse=True)
        out.append(
            {
                "trabajo": job,
                "score": round(score, 1),
                "margen": round(margin, 1),
                "suman": [DIMS[k].nombre for k, v in ranked[:3] if v > 0],
                "restan": [DIMS[k].nombre for k, v in ranked[::-1][:2] if v < 0],
            }
        )
    return sorted(out, key=lambda r: r["score"], reverse=True)
