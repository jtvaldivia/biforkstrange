"""Piezas de la arquitectura fuera del motor: errores HTTP, decisiones, repositorio, dependencias y el CLI."""

import subprocess
import sys

import pytest
from fastapi import HTTPException

from app.api import deps
from app.api.errores import partida_invalida
from app.repositories.simulations import InMemorySimulationRepository
from app.schemas.simulation import SimulationIn
from app.services.simulation_service import SimulationService
from app.sim.ocupacional.decisions import decisiones_desconocidas, get_decision

# ── errores HTTP ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("error", [ValueError("duda inválida"), KeyError("no_existe")])
def test_partida_invalida_es_422(error):
    with pytest.raises(HTTPException) as info, partida_invalida():
        raise error
    assert info.value.status_code == 422
    assert str(error) in info.value.detail


def test_partida_invalida_no_tapa_otros_errores():
    """Un bug del motor (TypeError, etc.) debe seguir siendo un 500, no un 422."""
    with pytest.raises(TypeError), partida_invalida():
        raise TypeError("bug")


def test_partida_invalida_deja_pasar_el_resultado():
    with partida_invalida():
        valor = 1
    assert valor == 1


# ── decisiones del motor por ocupación ───────────────────────────────────────


def test_decisiones_desconocidas_respeta_el_orden():
    assert decisiones_desconocidas(["seguir", "volar", "sabatico", "nadar"]) == ["volar", "nadar"]
    assert decisiones_desconocidas([]) == []


def test_get_decision_desconocida():
    with pytest.raises(ValueError, match="volar"):
        get_decision("volar")


# ── repositorio y servicio ───────────────────────────────────────────────────


def test_repositorio_en_memoria_guarda_y_lee():
    repo = InMemorySimulationRepository()
    sim_id = repo.save({"a": 1}, {"b": 2}, user_id="u")
    assert repo.get(sim_id) == {"id": sim_id, "input": {"a": 1}, "result": {"b": 2}, "user_id": "u"}
    assert repo.get("no-existe") is None


def test_servicio_usa_las_corridas_por_defecto_y_persiste():
    servicio = SimulationService(InMemorySimulationRepository(), default_runs=50)
    salida = servicio.run(SimulationIn(decisiones=["seguir"], seed=1))
    assert salida.edad_final == salida.trayectoria[-1].edad
    assert servicio.get(salida.id) == salida
    assert servicio.get("no-existe") is None


def test_el_repositorio_es_uno_por_proceso():
    """Las corridas guardadas en un pedido se leen en el siguiente: el repositorio no se recrea."""
    assert deps.get_simulation_repo() is deps.get_simulation_repo()
    assert isinstance(deps.get_simulation_repo(), InMemorySimulationRepository)


# ── CLI como paquete ─────────────────────────────────────────────────────────


def test_python_m_app_cli_arranca():
    """`python -m app.cli` (lo que usa el Makefile) sigue funcionando con el CLI dividido en módulos."""
    salida = subprocess.run([sys.executable, "-m", "app.cli", "ocupaciones"], capture_output=True, text=True, check=False)
    assert salida.returncode == 0, salida.stderr
    assert salida.stdout.strip()


def test_cli_sin_subcomando_es_error_de_uso():
    from app.cli import main

    assert main([]) == 2
