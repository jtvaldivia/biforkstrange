"""Prompts del gemelo (spec, secciones 4–7). Funciones puras: reciben datos, devuelven texto."""

from app.twin.context import REGLAS_GEMELO
from app.twin.dims import DIMS, TEMA_LABELS
from app.twin.profile import Dim, ExamItem

PRIVACIDAD = (
    "No preguntes ni registres datos de salud, datos de terceros identificables ni cifras exactas de patrimonio."
)


def prior(context: str, keys: list[str]) -> str:
    dims = "\n".join(f"{k}: {DIMS[k].nombre}. {DIMS[k].descripcion}" for k in keys)
    return f"""Eres un psicólogo organizacional. Estima, para la persona descrita, su posición (0–100, donde 50 es el promedio de profesionales jóvenes) en cada dimensión, y tu incertidumbre como desviación estándar (sd entre 18 y 30). Usa sd alta (25–30) si el perfil no da evidencia directa; 18–20 solo con evidencia clara y repetida. Prioriza lo que respondió de verdad (examen, correcciones, calibración) por sobre lo autodeclarado. No caricaturices ni rellenes con estereotipos.

PERFIL
{context}

DIMENSIONES
{dims}

Devuelve una entrada por cada clave listada, con "ev" como evidencia breve o "sin evidencia"."""


def adaptive_question(targets: list[str], dims: dict[str, Dim], previous: list[str], context: str) -> str:
    lines = "\n".join(
        f"- {k}: {DIMS[k].nombre}. {DIMS[k].descripcion} (estimación actual {dims[k].m:.0f} ± {dims[k].sd:.0f})"
        for k in targets
    )
    prev = "\n".join(f"- {q}" for q in previous) or "(ninguna)"
    return f"""Diseña UNA pregunta de evaluación laboral para medir estas dimensiones en una persona:
{lines}

Reglas (buenas prácticas de evaluación):
- Una situación laboral concreta y realista, o una elección entre tareas o condiciones de trabajo, en español de Chile, tuteando. Puede inspirarse en su vida, pero varía los contextos.
- 3 o 4 opciones de ELECCIÓN FORZADA: todas socialmente aceptables y atractivas a su manera, sin una respuesta "correcta" evidente.
- Las opciones deben discriminar en las dimensiones objetivo y, cuando tenga sentido, contraponerlas entre sí.
- Para cada opción, indica qué nivel (0–100) de cada dimensión objetivo implica elegirla, usando exactamente las claves {", ".join(targets)}.
- {PRIVACIDAD}
- No repitas ni parafrasees preguntas anteriores:
{prev}

PERFIL (solo para que la pregunta sea relevante, no para responderla)
{context}"""


def exam_question(tema: str, previous: list[str], context: str) -> str:
    prev = "\n".join(f"- {q}" for q in previous) or "(ninguna)"
    return f"""Diseña UNA pregunta de opción múltiple sobre el tema "{TEMA_LABELS[tema]}" para poner a prueba cuánto conoce un gemelo digital a esta persona.

Reglas:
- Una situación o elección concreta de su vida, en español de Chile, tuteando.
- 3 o 4 opciones plausibles PARA ESTA PERSONA: que discrimine justo donde el perfil no deja clara la respuesta.
- Sin respuesta "correcta" evidente ni socialmente obligada.
- {PRIVACIDAD}
- No repitas ni parafrasees preguntas anteriores:
{prev}

PERFIL
{context}"""


def predict(q: str, opts: list[str], context: str) -> str:
    options = "\n".join(f"[{i}] {o}" for i, o in enumerate(opts))
    return f"""Eres el gemelo digital de una persona. Predice cómo respondería ELLA esta pregunta, según su perfil (no lo que sería más sensato).

PERFIL
{context}

PREGUNTA
{q}

OPCIONES
{options}

Reparte 100 puntos de probabilidad entre las opciones (una cifra por opción, en el mismo orden) según qué tan probable es que ella elija cada una. Sé honesto con la incertidumbre. {REGLAS_GEMELO}
En "por_que", 1–2 frases en primera persona."""


def recalibrate(items: list[ExamItem], corrections_text: str, context: str) -> str:
    exam = "\n".join(
        f"- [{TEMA_LABELS.get(e.tema, e.tema)}] {e.q} | gemelo: {e.opts[e.top]} ({e.probs[e.top]:.0f}%) | "
        f"real: {e.ans_text}{' — ' + e.why if e.why else ''} | {'acierto' if e.hit else 'fallo'}"
        for e in items
    )
    return f"""Analiza los aciertos y errores de un gemelo digital al predecir a una persona y encuentra hasta 8 patrones SISTEMÁTICOS de cómo es ella de verdad, escritos en primera persona (como si ella hablara).

- Cada patrón debe apoyarse en evidencia concreta de las respuestas (cita brevemente cuál).
- Si los errores del gemelo van en una dirección clara, incluye un patrón con tema "sesgo del gemelo" que lo describa.
- No inventes nada que no esté en la evidencia. {PRIVACIDAD}

EXAMEN A CIEGAS
{exam or "(sin preguntas)"}

CORRECCIONES
{corrections_text or "(sin correcciones)"}

PERFIL ACTUAL
{context}"""


def report(dims_text: str, fit_text: str, context: str) -> str:
    return f"""Eres un psicólogo organizacional. Escribe un informe breve, en español de Chile y tuteando, sobre esta persona a partir de sus dimensiones medidas (m ± sd, 0–100, 50 = promedio) y su ajuste por tipo de trabajo.

Campos: resumen (3–4 frases), fortalezas, riesgos, ambientes donde rinde más, vida (fuera del trabajo, 2–3 frases) y dudas. Donde sd ≥ 20, di explícitamente que no está claro en vez de afirmarlo. No caricaturices. {REGLAS_GEMELO}

DIMENSIONES
{dims_text}

AJUSTE POR TIPO DE TRABAJO
{fit_text}

PERFIL
{context}"""
