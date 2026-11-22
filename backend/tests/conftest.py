import os

os.environ["BIFURCA_IA"] = "0"  # antes de importar la app: los fixtures de módulo y los subprocesos la ven apagada

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.sim.motor import ia  # noqa: E402


@pytest.fixture
def client():
    yield TestClient(app)


@pytest.fixture(autouse=True)
def _incertidumbre_ia(request, monkeypatch):
    """Los tests del modelo base corren con la incertidumbre de IA apagada (flag BIFURCA_IA, ia.py), para que sus
    números no dependan de ella. Los que la prueban llevan @pytest.mark.ia y la prenden."""
    prendida = request.node.get_closest_marker("ia") is not None
    monkeypatch.setattr(ia, "ACTIVA", prendida)
    monkeypatch.setenv("BIFURCA_IA", "1" if prendida else "0")  # los subprocesos de la cohorte la leen al importar
