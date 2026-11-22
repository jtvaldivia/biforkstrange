"""Casos de uso del gemelo: orquesta dominio (app.twin), cerebro (LLM) y repositorio."""

import random
import time

from app.repositories.twin_profiles import StaleVersionError, TwinProfileRepository
from app.services.twin_brain import Brain, Patron
from app.twin import cat
from app.twin.context import build_context, has_context
from app.twin.dims import DIM_KEYS, DIMS, TEMA_LABELS
from app.twin.metrics import exam_metrics, next_tema
from app.twin.profile import (
    CALIBRATION_PREFIX,
    MAX_ADAPTIVE,
    AdaptiveQ,
    Basics,
    Correction,
    ExamItem,
    Note,
    Report,
    TwinProfile,
    now,
)

MIN_FOR_RECALIBRATION = 4
QUESTION_CONTEXT_CHARS = 4000


class NotFoundError(Exception):
    pass


class TwinService:
    def __init__(self, repo: TwinProfileRepository, brain: Brain, rng: random.Random | None = None):
        self.repo = repo
        self.brain = brain
        self.rng = rng or random.Random()

    # ---- carga y guardado ----

    def get(self, profile_id: str) -> TwinProfile:
        p = self.repo.get(profile_id)
        if p is None:
            raise NotFoundError(profile_id)
        cat.apply_drift(p.dims, now())  # se persiste en la próxima escritura
        return p

    def _load(self, profile_id: str, version: int) -> TwinProfile:
        """Carga y falla rápido si el cliente trae una versión vieja (antes de gastar en el LLM)."""
        p = self.get(profile_id)
        if p.version != version:
            raise StaleVersionError(p)
        return p

    def _save(self, p: TwinProfile, version: int) -> TwinProfile:
        p.updated_at = now()
        return self.repo.save(p, version)

    # ---- perfil ----

    def create(self, basics: Basics | None = None) -> TwinProfile:
        return self.repo.create(TwinProfile(basics=basics or Basics()))

    def update_basics(self, profile_id: str, version: int, basics: Basics) -> TwinProfile:
        p = self._load(profile_id, version)
        p.basics = basics
        return self._save(p, version)

    def add_note(self, profile_id: str, version: int, q: str, a: str) -> TwinProfile:
        if q.startswith(CALIBRATION_PREFIX):
            raise ValueError("Las notas de calibración se guardan con la recalibración")
        p = self._load(profile_id, version)
        p.notes.append(Note(q=q, a=a))
        return self._save(p, version)

    def import_context(self, profile_id: str, version: int, texto: str, estimar: bool = True) -> TwinProfile:
        """Guarda lo que tu propio LLM sabe de ti y, si se pide, estima los rasgos que aún no respondiste."""
        p = self._load(profile_id, version)
        p.contexto_llm, p.contexto_llm_at = texto.strip(), time.time()
        p = self._save(p, version)
        return self.run_prior(p.id, p.version) if estimar and p.contexto_llm else p

    # ---- flujo A: estimación inicial ----

    def run_prior(self, profile_id: str, version: int) -> TwinProfile:
        p = self._load(profile_id, version)
        if has_context(p):
            pending = [k for k in DIM_KEYS if p.dims[k].n == 0]  # nunca pisar lo ya respondido
            if pending:
                estimates = self.brain.prior(build_context(p), pending)
                for k, d in estimates.items():
                    p.dims[k] = d
        p.prior_at = now()
        return self._save(p, version)

    # ---- flujo B: loop adaptativo ----

    def next_adaptive(self, profile_id: str, version: int) -> tuple[TwinProfile, AdaptiveQ | None]:
        p = self._load(profile_id, version)
        if pending := p.pending_adaptive():
            return p, pending  # no gastar otra llamada si ya hay una pregunta abierta
        targets = cat.select_targets(p.dims, self.rng)
        if targets is None:
            return p, None  # perfil claro
        previous = [q.q for q in p.qs[-30:]]
        gen = self.brain.adaptive_question(targets, p.dims, previous, build_context(p, QUESTION_CONTEXT_CHARS))
        q = AdaptiveQ(q=gen.q, dims=targets, opts=gen.opts)
        p.qs = (p.qs + [q])[-MAX_ADAPTIVE:]
        return self._save(p, version), q

    def answer_adaptive(
        self, profile_id: str, version: int, qid: str, ans: int, note: str | None
    ) -> tuple[TwinProfile, list[dict]]:
        p = self._load(profile_id, version)
        q = next((x for x in p.qs if x.id == qid), None)
        if q is None or q.ans is not None:
            raise ValueError("Pregunta inexistente o ya respondida")
        if not (ans == -1 or 0 <= ans < len(q.opts)):
            raise ValueError("Opción fuera de rango")

        q.ans, q.note = ans, (note or None)
        deltas = []
        if ans >= 0:  # "ninguna me representa" no actualiza
            at = now()
            for k in q.dims:
                obs = q.opts[ans].lv.get(k)
                if obs is None:
                    continue
                before = p.dims[k]
                after = cat.update(before, obs, at)
                p.dims[k] = after
                deltas.append({"key": k, "nombre": DIMS[k].nombre, "antes": round(before.m), "despues": round(after.m),
                               "sd_antes": round(before.sd, 1), "sd_despues": round(after.sd, 1)})
        if note:
            p.notes.append(Note(q=f"Trabajo: {q.q}", a=note))
        return self._save(p, version), deltas

    # ---- flujo C: examen a ciegas ----

    def next_exam(self, profile_id: str, version: int, tema: str = "auto") -> tuple[TwinProfile, ExamItem]:
        p = self._load(profile_id, version)
        if pending := p.pending_exam():
            return p, pending
        if tema == "auto":
            tema = next_tema(p.exam)
        if tema not in TEMA_LABELS:
            raise ValueError(f"Tema desconocido: {tema}")

        context = build_context(p)
        previous = [e.q for e in p.exam[-25:]]
        gen = self.brain.exam_question(tema, previous, context)
        # llamada separada: la predicción ve la pregunta, nunca la respuesta
        pred = self.brain.predict(gen.pregunta, gen.opciones, context)
        top = max(range(len(pred.probs)), key=lambda i: pred.probs[i])
        item = ExamItem(q=gen.pregunta, opts=gen.opciones, tema=tema, probs=pred.probs, top=top, pq=pred.por_que)
        p.exam.append(item)
        # la predicción queda persistida ANTES de que el usuario vea las opciones
        return self._save(p, version), item

    def answer_exam(
        self, profile_id: str, version: int, eid: str, ans: int, ans_text: str | None, why: str | None
    ) -> tuple[TwinProfile, ExamItem]:
        p = self._load(profile_id, version)
        e = next((x for x in p.exam if x.id == eid), None)
        if e is None or e.ans is not None:
            raise ValueError("Pregunta inexistente o ya respondida")
        if ans == -1:
            if not (ans_text or "").strip():
                raise ValueError("Escribe tu respuesta si eliges 'otra'")
            e.ans_text = ans_text.strip()
        elif 0 <= ans < len(e.opts):
            e.ans_text = e.opts[ans]
        else:
            raise ValueError("Opción fuera de rango")

        e.ans, e.why = ans, (why or None)
        e.hit = ans == e.top
        e.p_ans = e.probs[ans] if ans >= 0 else 0.0
        fix = e.ans_text + (f" — {why}" if why else "")
        p.corrections.append(Correction(
            s=e.q, r=f"{e.opts[e.top]} ({e.probs[e.top]:.0f}%)", v="yes" if e.hit else "no", fix=fix,
        ))
        return self._save(p, version), e

    # ---- flujo D: recalibración ----

    def propose_calibration(self, profile_id: str) -> list[Patron]:
        p = self.get(profile_id)
        if len(p.corrections) < MIN_FOR_RECALIBRATION:
            raise ValueError(f"Se necesitan al menos {MIN_FOR_RECALIBRATION} respuestas o correcciones")
        corrections = "\n".join(
            f"- {c.s} · gemelo: {c.r} · {c.v}" + (f" · real: {c.fix}" if c.fix else "") for c in p.corrections[-40:]
        )
        return self.brain.recalibrate(p.answered_exam()[-40:], corrections, build_context(p))

    def save_calibration(self, profile_id: str, version: int, patrones: list[Patron]) -> TwinProfile:
        """Reemplaza (no acumula) las notas Calibración:* con lo que el usuario revisó."""
        p = self._load(profile_id, version)
        p.notes = [n for n in p.notes if not n.q.startswith(CALIBRATION_PREFIX)] + [
            Note(q=f"{CALIBRATION_PREFIX} {x.tema}", a=f"{x.patron} (evidencia: {x.evidencia})")
            for x in patrones[:8]
            if x.patron.strip()
        ]
        return self._save(p, version)

    # ---- salidas ----

    def summary(self, profile_id: str) -> dict:
        p = self.get(profile_id)
        return {
            "claridad": cat.clarity(p.dims),
            "ajuste": cat.job_fit(p.dims),
            "examen": exam_metrics(p.exam),
        }

    def generate_report(self, profile_id: str, version: int) -> TwinProfile:
        p = self._load(profile_id, version)
        dims_text = "\n".join(f"- {DIMS[k].nombre}: {d.m:.0f} ± {d.sd:.0f}" for k, d in p.dims.items() if k in DIMS)
        fit_text = "\n".join(f"- {f['trabajo']}: {f['score']} ± {f['margen']}" for f in cat.job_fit(p.dims))
        out = self.brain.report(dims_text, fit_text, build_context(p))
        p.report = Report(**out.model_dump())
        return self._save(p, version)
