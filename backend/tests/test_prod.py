"""El arranque de producción (scripts/prod.sh) y las variables que lee en Render. No levanta el servidor."""

import os
import subprocess
from pathlib import Path

from app.core.config import Settings

SCRIPT = Path(__file__).parents[1] / "scripts" / "prod.sh"


def _argumentos(tmp_path, **env) -> list[str]:
    """Corre prod.sh con un `uv` falso que solo imprime con qué argumentos lo llamaron."""
    falso = tmp_path / "uv"
    falso.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    falso.chmod(0o755)
    entorno = {k: v for k, v in os.environ.items() if k not in ("PORT", "WEB_CONCURRENCY")}
    entorno |= {"PATH": f"{tmp_path}:{os.environ['PATH']}", **env}
    salida = subprocess.run(["sh", str(SCRIPT)], env=entorno, capture_output=True, text=True, check=True, timeout=30)
    return salida.stdout.splitlines()


def test_prod_usa_varios_procesos_sin_reload_en_el_puerto_de_render(tmp_path):
    args = _argumentos(tmp_path, PORT="10000", WEB_CONCURRENCY="3")
    assert args[:3] == ["run", "uvicorn", "app.main:app"]
    assert args[args.index("--host") + 1] == "0.0.0.0" and args[args.index("--port") + 1] == "10000"
    assert args[args.index("--workers") + 1] == "3"
    assert "--reload" not in args


def test_prod_sin_variables_parte_con_dos_procesos_en_el_8000(tmp_path):
    args = _argumentos(tmp_path)
    assert args[args.index("--port") + 1] == "8000" and args[args.index("--workers") + 1] == "2"


def test_cors_origins_se_lee_como_json(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://bifurca.onrender.com", "http://localhost:5173"]')
    assert Settings(_env_file=None).cors_origins == ["https://bifurca.onrender.com", "http://localhost:5173"]
