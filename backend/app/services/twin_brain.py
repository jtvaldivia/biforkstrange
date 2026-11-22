"""El 'cerebro' del gemelo: las llamadas al LLM. Claude con API key; un stub determinista sin ella.

Roles separados (spec §10): quien genera la pregunta del examen no ve la predicción,
y la predicción nunca ve la respuesta.
"""

import random
from typing import Protocol

from pydantic import BaseModel

from app.core.llm import ClaudeJSON
from app.twin import prompts
from app.twin.dims import DIMS, TEMA_LABELS
from app.twin.profile import Dim, ExamItem, Option


# ---- Formatos de salida (structured outputs: listas en vez de dicts con claves dinámicas) ----

class DimEstimate(BaseModel):
    key: str
    m: float
    sd: float
    ev: str


class PriorOut(BaseModel):
    dims: list[DimEstimate]


class Nivel(BaseModel):
    dim: str
    nivel: float


class OpcionAdaptativa(BaseModel):
    texto: str
    niveles: list[Nivel]


class AdaptiveOut(BaseModel):
    pregunta: str
    opciones: list[OpcionAdaptativa]


class ExamQOut(BaseModel):
    pregunta: str
    opciones: list[str]


class PredictOut(BaseModel):
    probs: list[float]
    por_que: str


class Patron(BaseModel):
    tema: str
    patron: str
    evidencia: str


class RecalOut(BaseModel):
    patrones: list[Patron]


class ReportOut(BaseModel):
    resumen: str
    fortalezas: list[str]
    riesgos: list[str]
    ambientes: list[str]
    vida: str
    dudas: list[str]


class GeneratedQ(BaseModel):
    q: str
    opts: list[Option]


class Brain(Protocol):
    def prior(self, context: str, keys: list[str]) -> dict[str, Dim]: ...
    def adaptive_question(self, targets: list[str], dims: dict[str, Dim], previous: list[str], context: str) -> GeneratedQ: ...
    def exam_question(self, tema: str, previous: list[str], context: str) -> ExamQOut: ...
    def predict(self, q: str, opts: list[str], context: str) -> PredictOut: ...
    def recalibrate(self, items: list[ExamItem], corrections_text: str, context: str) -> list[Patron]: ...
    def report(self, dims_text: str, fit_text: str, context: str) -> ReportOut: ...


def normalize(probs: list[float], n: int) -> list[float]:
    probs = [max(0.0, float(p)) for p in probs[:n]] + [0.0] * max(0, n - len(probs))
    total = sum(probs)
    if total <= 0:
        return [round(100 / n, 1)] * n
    return [round(100 * p / total, 1) for p in probs]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---- Claude ----

class ClaudeBrain:
    def __init__(self, llm: ClaudeJSON):
        self.llm = llm

    def prior(self, context, keys):
        def check(o: PriorOut):
            if not {d.key for d in o.dims} & set(keys):
                raise ValueError("El prior no trae ninguna dimensión conocida")

        out = self.llm.ask(prompts.prior(context, keys), PriorOut, effort="medium", check=check)
        return {
            d.key: Dim(m=_clamp(d.m, 0, 100), sd=_clamp(d.sd, 8, 30), ev=d.ev)
            for d in out.dims
            if d.key in keys
        }

    def adaptive_question(self, targets, dims, previous, context):
        def check(o: AdaptiveOut):
            if not 2 <= len(o.opciones) <= 4:
                raise ValueError("Se esperaban 3–4 opciones")
            for op in o.opciones:
                if not {n.dim for n in op.niveles} >= set(targets):
                    raise ValueError("Una opción no trae nivel para todas las dimensiones objetivo")

        out = self.llm.ask(prompts.adaptive_question(targets, dims, previous, context), AdaptiveOut, check=check)
        opts = [
            Option(t=op.texto, lv={n.dim: _clamp(n.nivel, 0, 100) for n in op.niveles if n.dim in targets})
            for op in out.opciones
        ]
        return GeneratedQ(q=out.pregunta, opts=opts)

    def exam_question(self, tema, previous, context):
        def check(o: ExamQOut):
            if not 2 <= len(o.opciones) <= 4:
                raise ValueError("Se esperaban 3–4 opciones")

        return self.llm.ask(prompts.exam_question(tema, previous, context), ExamQOut, check=check)

    def predict(self, q, opts, context):
        out = self.llm.ask(prompts.predict(q, opts, context), PredictOut)
        return PredictOut(probs=normalize(out.probs, len(opts)), por_que=out.por_que)

    def recalibrate(self, items, corrections_text, context):
        out = self.llm.ask(prompts.recalibrate(items, corrections_text, context), RecalOut, effort="medium")
        return out.patrones[:8]

    def report(self, dims_text, fit_text, context):
        return self.llm.ask(prompts.report(dims_text, fit_text, context), ReportOut, effort="medium", max_tokens=12000)


# ---- Sin API key: preguntas genéricas para poder probar el flujo completo ----

_EXAM_BANK = {
    "trabajo": ("Te ofrecen liderar un proyecto nuevo y visible, pero con poco equipo. ¿Qué haces?",
                ["Lo tomo y armo el equipo en el camino", "Lo tomo si me dan al menos dos personas más",
                 "Prefiero aportar como especialista, no liderar", "Lo rechazo: estoy bien donde estoy"]),
    "plata": ("Te llega un bono inesperado equivalente a dos sueldos. ¿Qué haces con él?",
              ["Lo invierto casi todo", "Lo ahorro en algo seguro", "Viajo o me doy un gusto grande", "Mitad y mitad"]),
    "gustos": ("Tienes un sábado libre en Santiago. ¿Qué te tienta más?",
               ["Un museo o una librería", "Un cerro o la bici", "Un asado con amigos", "Quedarme en casa con una serie"]),
    "relaciones": ("Un amigo cercano te pide plata prestada por segunda vez. ¿Qué haces?",
                   ["Se la presto sin preguntar", "Le presto pero conversamos", "Le ayudo de otra forma", "Le digo que no"]),
    "tiempo_libre": ("Entre semana, después de la pega, lo más probable es que...",
                     ["Vaya al gimnasio o a hacer deporte", "Me junte con gente", "Lea o estudie algo", "Descanse en casa"]),
    "valores": ("Descubres que un compañero infló sus resultados en un informe. ¿Qué haces?",
                ["Hablo con él primero", "Lo reporto a la jefatura", "Lo dejo pasar si no daña a nadie", "Depende de cuánto lo infló"]),
}


class OfflineBrain:
    """Sin ANTHROPIC_API_KEY. Determinista por semilla para tests."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def prior(self, context, keys):
        return {}  # sin LLM no hay evidencia: todo queda en m=50, sd=30

    def adaptive_question(self, targets, dims, previous, context):
        names = " vs ".join(DIMS[k].nombre.lower() for k in targets)
        if len(targets) == 1:
            k = targets[0]
            opts = [Option(t=f"{DIMS[k].nombre}: nivel {lv}", lv={k: lv}) for lv in (15, 50, 85)]
        else:  # contrapone: cada opción es alta en una dimensión y baja en las otras
            opts = [
                Option(t=f"Lo que más pesa: {DIMS[top].nombre.lower()}", lv={k: 85 if k == top else 25 for k in targets})
                for top in targets
            ]
        return GeneratedQ(q=f"[Modo sin IA] Pregunta de prueba sobre {names}", opts=opts)

    def exam_question(self, tema, previous, context):
        q, opts = _EXAM_BANK[tema]
        return ExamQOut(pregunta=f"[Modo sin IA] {q}", opciones=opts)

    def predict(self, q, opts, context):
        raw = [self.rng.uniform(1, 3) for _ in opts]
        return PredictOut(probs=normalize(raw, len(opts)), por_que="(Modo sin IA: predicción al azar.)")

    def recalibrate(self, items, corrections_text, context):
        misses = [e for e in items if not e.hit]
        return [
            Patron(tema=TEMA_LABELS.get(e.tema, e.tema), patron=f"Cuando me preguntan \"{e.q}\", elijo: {e.ans_text}",
                   evidencia="examen a ciegas (modo sin IA)")
            for e in misses[:8]
        ]

    def report(self, dims_text, fit_text, context):
        return ReportOut(
            resumen="Modo sin IA: configura ANTHROPIC_API_KEY para generar el informe.",
            fortalezas=[], riesgos=[], ambientes=[], vida="", dudas=["Todo, hasta que haya un LLM conectado."],
        )
