"""Partida por turnos. El servidor no guarda estado: la suerte es determinista, así que
basta reenviar el perfil, la semilla y las decisiones tomadas para reconstruirla."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from app.schemas.simulation import TurnoIn
from app.sim.game import Partida, ficha
from app.sim.profile import Perfil

router = APIRouter(prefix="/juego", tags=["juego"])


@router.post("/turno")
def turno(body: TurnoIn) -> dict:
    try:
        perfil = Perfil.desde_dict(body.perfil)
        g = Partida.reproducir(perfil, body.decisiones, seed=body.seed, n=body.n_runs, horizonte=body.horizonte)
    except (ValueError, KeyError) as err:
        raise HTTPException(422, str(err)) from err
    return {
        "perfil": {"nombre": perfil.nombre, "arquetipo": perfil.arquetipo, "ocupacion": perfil.ocupacion, "supuestos": perfil.supuestos},
        "yo": ficha(g.yo, perfil),
        "sombra": ficha(g.sombra, perfil),
        "historial": g.historial,
        "logros": g.logros,
        "menu": [asdict(o) for o in g.menu()],
    }
