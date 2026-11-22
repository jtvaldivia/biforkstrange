"""Credenciales de Claude: la llave del .env llega al cliente, y la del entorno (Render) sigue sirviendo.

No se llama a la API: se mira con qué llave se arma el cliente.
"""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.services import claude_comun


@pytest.fixture
def sin_credenciales(monkeypatch, tmp_path):
    """Una máquina sin llave en el entorno ni perfil de `ant auth login`."""
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # el cliente se "arma" devolviendo sus argumentos: el SDK real abre hilos que no hacen falta aquí
    monkeypatch.setattr(claude_comun.anthropic, "Anthropic", lambda **k: k)


def _con_env_file(monkeypatch, tmp_path, contenido: str) -> None:
    archivo = tmp_path / ".env"
    archivo.write_text(contenido, encoding="utf-8")
    monkeypatch.setattr(claude_comun, "get_settings", lambda: Settings(_env_file=archivo))


def test_la_llave_del_env_file_llega_al_cliente(monkeypatch, tmp_path, sin_credenciales):
    _con_env_file(monkeypatch, tmp_path, "ANTHROPIC_API_KEY=sk-ant-del-env-file\n")
    assert claude_comun.hay_credenciales()
    assert claude_comun.cliente(5, max_retries=0)["api_key"] == "sk-ant-del-env-file"


def test_la_llave_del_entorno_sigue_sirviendo(monkeypatch, tmp_path, sin_credenciales):
    # Render la define como variable de entorno; pesa más que un .env con la línea vacía
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-de-render")
    _con_env_file(monkeypatch, tmp_path, "ANTHROPIC_API_KEY=\n")
    assert claude_comun.hay_credenciales()
    assert claude_comun.cliente(5, max_retries=0)["api_key"] == "sk-ant-de-render"


def test_sin_llave_no_hay_credenciales(monkeypatch, tmp_path, sin_credenciales):
    _con_env_file(monkeypatch, tmp_path, "ANTHROPIC_API_KEY=\n")
    assert not claude_comun.hay_credenciales()
