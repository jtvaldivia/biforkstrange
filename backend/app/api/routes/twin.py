from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, HTTPException

from app.api.deps import TwinServiceDep
from app.core.llm import LLMError
from app.repositories.twin_profiles import StaleVersionError
from app.schemas.twin import (
    AdaptiveAnswerIn,
    BasicsIn,
    CalibrationIn,
    ContextoIn,
    CreateProfileIn,
    ExamAnswerIn,
    ExamNextIn,
    NoteIn,
    Versioned,
    public_exam_question,
    public_profile,
)
from app.services.twin_service import NotFoundError
from app.twin.dims import DIMS, GROUP_LABELS, TEMA_LABELS

router = APIRouter(prefix="/twin", tags=["twin"])

T = TypeVar("T")


def guard(fn: Callable[[], T]) -> T:
    """Traduce errores de dominio a HTTP."""
    try:
        return fn()
    except NotFoundError:
        raise HTTPException(404, "Perfil no encontrado")
    except StaleVersionError as e:
        raise HTTPException(409, {"message": "Hay una versión más nueva del perfil", "profile": public_profile(e.current)})
    except LLMError as e:
        raise HTTPException(502, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/catalog")
def catalog():
    return {
        "grupos": GROUP_LABELS,
        "dims": [{"key": d.key, "nombre": d.nombre, "grupo": d.grupo, "descripcion": d.descripcion} for d in DIMS.values()],
        "temas": TEMA_LABELS,
    }


@router.post("/profiles")
def create_profile(body: CreateProfileIn, svc: TwinServiceDep):
    return public_profile(svc.create(body.basics))


@router.get("/profiles/{pid}")
def get_profile(pid: str, svc: TwinServiceDep):
    return public_profile(guard(lambda: svc.get(pid)))


@router.put("/profiles/{pid}/basics")
def put_basics(pid: str, body: BasicsIn, svc: TwinServiceDep):
    return public_profile(guard(lambda: svc.update_basics(pid, body.version, body.basics)))


@router.post("/profiles/{pid}/notes")
def add_note(pid: str, body: NoteIn, svc: TwinServiceDep):
    return public_profile(guard(lambda: svc.add_note(pid, body.version, body.q, body.a)))


@router.put("/profiles/{pid}/contexto")
def import_context(pid: str, body: ContextoIn, svc: TwinServiceDep):
    """Lo que tu propio LLM sabe de ti (pegado o subido como archivo)."""
    return public_profile(guard(lambda: svc.import_context(pid, body.version, body.texto, body.estimar)))


@router.post("/profiles/{pid}/prior")
def run_prior(pid: str, body: Versioned, svc: TwinServiceDep):
    return public_profile(guard(lambda: svc.run_prior(pid, body.version)))


@router.post("/profiles/{pid}/adaptive/next")
def adaptive_next(pid: str, body: Versioned, svc: TwinServiceDep):
    p, q = guard(lambda: svc.next_adaptive(pid, body.version))
    question = None if q is None else {"id": q.id, "q": q.q, "dims": q.dims, "opts": [o.t for o in q.opts]}
    return {"profile": public_profile(p), "question": question}


@router.post("/profiles/{pid}/adaptive/answer")
def adaptive_answer(pid: str, body: AdaptiveAnswerIn, svc: TwinServiceDep):
    p, deltas = guard(lambda: svc.answer_adaptive(pid, body.version, body.qid, body.ans, body.note))
    return {"profile": public_profile(p), "deltas": deltas}


@router.post("/profiles/{pid}/exam/next")
def exam_next(pid: str, body: ExamNextIn, svc: TwinServiceDep):
    p, e = guard(lambda: svc.next_exam(pid, body.version, body.tema))
    return {"profile": public_profile(p), "question": public_exam_question(e)}


@router.post("/profiles/{pid}/exam/answer")
def exam_answer(pid: str, body: ExamAnswerIn, svc: TwinServiceDep):
    p, e = guard(lambda: svc.answer_exam(pid, body.version, body.eid, body.ans, body.ans_text, body.why))
    return {"profile": public_profile(p), "reveal": e.model_dump()}


@router.post("/profiles/{pid}/calibration/propose")
def propose_calibration(pid: str, svc: TwinServiceDep):
    return {"patrones": [x.model_dump() for x in guard(lambda: svc.propose_calibration(pid))]}


@router.put("/profiles/{pid}/calibration")
def save_calibration(pid: str, body: CalibrationIn, svc: TwinServiceDep):
    return public_profile(guard(lambda: svc.save_calibration(pid, body.version, body.patrones)))


@router.post("/profiles/{pid}/report")
def report(pid: str, body: Versioned, svc: TwinServiceDep):
    return public_profile(guard(lambda: svc.generate_report(pid, body.version)))


@router.get("/profiles/{pid}/summary")
def summary(pid: str, svc: TwinServiceDep):
    return guard(lambda: svc.summary(pid))
