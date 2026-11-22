from fastapi import APIRouter

from app.schemas.simulation import DecisionOut
from app.sim.decisions import all_decisions

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=list[DecisionOut])
def list_decisions():
    out = []
    for d in all_decisions():
        p = getattr(d, "params", None)
        out.append(DecisionOut(
            key=d.key, label=d.label, description=d.description, why=getattr(d, "why", ""),
            growth=p.growth if p else None, risk=p.risk if p else None, wear=p.wear if p else None,
        ))
    return out
