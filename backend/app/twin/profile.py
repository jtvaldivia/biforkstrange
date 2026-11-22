"""Documento único por persona: todo lo que el gemelo sabe de ella."""

import time
import uuid

from pydantic import BaseModel, Field

from app.twin.dims import DIM_KEYS

PRIOR_SD = 30.0
CALIBRATION_PREFIX = "Calibración:"
MAX_ADAPTIVE = 120


def now() -> float:
    return time.time()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class Dim(BaseModel):
    m: float = 50.0  # 0–100, 50 = promedio de profesionales jóvenes
    sd: float = PRIOR_SD
    n: int = 0  # respuestas adaptativas que la tocaron
    ev: str | None = None
    updated_at: float | None = None


class Option(BaseModel):
    t: str
    lv: dict[str, float]  # nivel 0–100 que implica elegirla, por dimensión objetivo


class AdaptiveQ(BaseModel):
    id: str = Field(default_factory=new_id)
    q: str
    dims: list[str]
    opts: list[Option]
    ans: int | None = None  # None = pendiente, -1 = ninguna me representa
    note: str | None = None
    at: float = Field(default_factory=now)


class ExamItem(BaseModel):
    id: str = Field(default_factory=new_id)
    q: str
    opts: list[str]
    tema: str
    probs: list[float]  # predicción del gemelo (suma 100), guardada ANTES de responder
    top: int
    pq: str  # razonamiento del gemelo
    ans: int | None = None  # None = pendiente, -1 = escribió otra cosa
    ans_text: str = ""
    why: str | None = None
    hit: bool | None = None
    p_ans: float | None = None
    at: float = Field(default_factory=now)


class Correction(BaseModel):
    s: str  # situación
    r: str  # lo que dijo el gemelo
    v: str  # yes | part | no
    fix: str | None = None  # lo que la persona dice de verdad
    at: float = Field(default_factory=now)


class Note(BaseModel):
    q: str
    a: str


class Basics(BaseModel):
    """Lo autodeclarado. Pesa menos que lo respondido."""

    nombre: str = ""
    rasgos: str = ""
    valores: str = ""
    gustos: str = ""


class Report(BaseModel):
    resumen: str
    fortalezas: list[str]
    riesgos: list[str]
    ambientes: list[str]
    vida: str
    dudas: list[str]
    at: float = Field(default_factory=now)


class TwinProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 0  # control optimista contra pestañas viejas
    basics: Basics = Basics()
    dims: dict[str, Dim] = Field(default_factory=lambda: {k: Dim() for k in DIM_KEYS})
    qs: list[AdaptiveQ] = []
    exam: list[ExamItem] = []
    corrections: list[Correction] = []
    notes: list[Note] = []
    contexto_llm: str = ""  # lo que tu propio LLM (Claude, ChatGPT...) sabe de ti, importado tal cual
    contexto_llm_at: float | None = None
    prior_at: float | None = None
    report: Report | None = None
    created_at: float = Field(default_factory=now)
    updated_at: float = Field(default_factory=now)

    def pending_adaptive(self) -> AdaptiveQ | None:
        return next((q for q in reversed(self.qs) if q.ans is None), None)

    def pending_exam(self) -> ExamItem | None:
        return next((e for e in reversed(self.exam) if e.ans is None), None)

    def answered_exam(self) -> list[ExamItem]:
        return [e for e in self.exam if e.ans is not None]
