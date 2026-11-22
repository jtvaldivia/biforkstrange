from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import StoryServiceDep
from app.core.llm import LLMError
from app.services.story_service import NotFoundError, StaleChapterError, public_story

router = APIRouter(prefix="/stories", tags=["stories"])


class StartIn(BaseModel):
    situacion: str = Field(min_length=3, max_length=2000)
    edad: int = Field(25, ge=18, le=50)
    sueldo: float = Field(900_000, gt=0)  # solo como referencia interna; la historia no muestra montos
    desgaste: float = Field(0.2, ge=0, le=1)
    anios: int = Field(8, ge=1, le=15)
    profile_id: str | None = None


class ChooseIn(BaseModel):
    capitulo: int  # cuántos capítulos ve el cliente; protege del doble clic
    option_id: str | None = None
    texto: str | None = Field(None, max_length=500)


def guard(fn):
    try:
        return public_story(fn())
    except NotFoundError:
        raise HTTPException(404, "Historia no encontrada")
    except StaleChapterError as e:
        raise HTTPException(409, {"message": "La historia ya avanzó", "story": public_story(e.story)})
    except LLMError as e:
        raise HTTPException(502, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("")
def start(body: StartIn, svc: StoryServiceDep):
    return guard(lambda: svc.start(body.situacion, body.edad, body.sueldo, body.desgaste, body.anios, body.profile_id))


@router.get("/{sid}")
def get(sid: str, svc: StoryServiceDep):
    return guard(lambda: svc.get(sid))


@router.post("/{sid}/choose")
def choose(sid: str, body: ChooseIn, svc: StoryServiceDep):
    return guard(lambda: svc.choose(sid, body.capitulo, body.option_id, body.texto))


@router.post("/{sid}/close")
def close(sid: str, svc: StoryServiceDep):
    return guard(lambda: svc.close(sid))
