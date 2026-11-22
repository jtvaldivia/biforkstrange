from pydantic import BaseModel, Field

from app.services.twin_brain import Patron
from app.twin.profile import Basics, ExamItem, TwinProfile


class Versioned(BaseModel):
    version: int  # la versión que tiene el cliente; si quedó vieja, 409 con el perfil actual


class CreateProfileIn(BaseModel):
    basics: Basics = Basics()


class BasicsIn(Versioned):
    basics: Basics


class NoteIn(Versioned):
    q: str = Field(min_length=1, max_length=300)
    a: str = Field(min_length=1, max_length=2000)


class ContextoIn(Versioned):
    texto: str = Field(max_length=60000)
    estimar: bool = True


class AdaptiveAnswerIn(Versioned):
    qid: str
    ans: int  # -1 = ninguna me representa
    note: str | None = Field(None, max_length=1000)


class ExamNextIn(Versioned):
    tema: str = "auto"


class ExamAnswerIn(Versioned):
    eid: str
    ans: int  # -1 = otra (escrita en ans_text)
    ans_text: str | None = Field(None, max_length=500)
    why: str | None = Field(None, max_length=1000)


class CalibrationIn(Versioned):
    patrones: list[Patron] = Field(max_length=8)


def public_profile(p: TwinProfile) -> dict:
    """El perfil tal como lo ve el cliente: sin spoilers de lo que está pendiente."""
    doc = p.model_dump()
    for e in doc["exam"]:
        if e["ans"] is None:  # la predicción existe pero no se muestra antes de responder
            e["probs"], e["top"], e["pq"] = [], -1, ""
    for q in doc["qs"]:
        if q["ans"] is None:
            for o in q["opts"]:
                o["lv"] = {}
    return doc


def public_exam_question(e: ExamItem) -> dict:
    return {"id": e.id, "q": e.q, "opts": e.opts, "tema": e.tema}
