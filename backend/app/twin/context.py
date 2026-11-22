"""Ensamblado del contexto del gemelo. El orden importa: lo respondido va antes que lo autodeclarado."""

from app.twin.dims import DIMS
from app.twin.profile import CALIBRATION_PREFIX, TwinProfile

REGLAS_GEMELO = (
    "Si algo del perfil choca con lo que respondió de verdad en el examen o en sus correcciones, "
    "manda lo que respondió de verdad. No caricaturices: no la pintes más cautelosa, tranquila o "
    "predecible de lo que muestran sus respuestas reales. No metas temas del perfil que no vengan "
    "al caso y no uses muletillas repetidas."
)

CONTEXTO_LLM_CHARS = 12000  # lo que entra al prompt; se guarda completo

V_LABEL = {"yes": "correcto", "part": "parcial", "no": "incorrecto"}


def build_context(p: TwinProfile, max_chars: int | None = None) -> str:
    b = p.basics
    parts: list[str] = []
    if b.nombre:
        parts.append(f"Nombre: {b.nombre}")

    calib = [n for n in p.notes if n.q.startswith(CALIBRATION_PREFIX)]
    if calib:
        parts.append(
            "PATRONES CALIBRADOS CON SUS RESPUESTAS REALES (pesan más que los rasgos, dilemas y gustos autodeclarados):\n"
            + "\n".join(f"- {n.q.removeprefix(CALIBRATION_PREFIX).strip()}: {n.a}" for n in calib)
        )

    if b.rasgos:
        parts.append(f"Rasgos autodeclarados: {b.rasgos}")

    measured = [f"{DIMS[k].nombre} {d.m:.0f}±{d.sd:.0f}" for k, d in p.dims.items() if k in DIMS and d.sd <= 20]
    if measured:
        parts.append("Perfil laboral medido (0–100, 50 = promedio): " + ", ".join(measured))

    if b.valores:
        parts.append(f"Valores y dilemas: {b.valores}")
    if b.gustos:
        parts.append(f"Gustos: {b.gustos}")

    if p.contexto_llm:
        parts.append("LO QUE SU PROPIO ASISTENTE DE IA SABE DE ELLA (memorias importadas; pesa menos que lo respondido):\n"
                     + p.contexto_llm[:CONTEXTO_LLM_CHARS])

    other = [n for n in p.notes if not n.q.startswith(CALIBRATION_PREFIX)]
    if other:
        parts.append("Contexto y entrevistas:\n" + "\n".join(f"- {n.q}: {n.a}" for n in other[-40:]))

    if p.corrections:
        parts.append(
            "Últimas evaluaciones (situación · lo que dijo el gemelo · resultado · lo que la persona dice de verdad):\n"
            + "\n".join(
                f"- {c.s} · {c.r} · {V_LABEL.get(c.v, c.v)}" + (f" · {c.fix}" if c.fix else "")
                for c in p.corrections[-15:]
            )
        )

    text = "\n\n".join(parts) or "(sin información todavía)"
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "…"
    return text


def has_context(p: TwinProfile) -> bool:
    b = p.basics
    return bool(b.nombre or b.rasgos or b.valores or b.gustos or p.notes or p.corrections or p.contexto_llm)
