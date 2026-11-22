from fastapi import APIRouter

from app.schemas.simulation import DecisionOut
from app.sim.ocupacional.decisions import all_decisions

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=list[DecisionOut])
def list_decisions():
    return [DecisionOut(key=d.key, label=d.label, description=d.description) for d in all_decisions()]
