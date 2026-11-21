from fastapi import APIRouter

from app.schemas.simulation import DecisionOut
from app.sim.decisions import CATALOGO

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=list[DecisionOut])
def list_decisions():
    # 'reconvertir' necesita una ocupación de destino; esas opciones las arma el menú de /api/juego/turno
    return [DecisionOut(key=d.clave, label=d.nombre, description=d.descripcion) for d in CATALOGO.values() if d.clave != "reconvertir"]
