"""Un error no manejado del motor sale como 500 con JSON y con las cabeceras de CORS.

Sin eso el navegador lo reporta como error de CORS y se pierde el mensaje (pasó en Render, año 10)."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_un_500_lleva_cors_y_json():
    app = create_app()

    @app.get("/explota")
    def explota():
        raise ZeroDivisionError("división por cero en el motor")

    origen = get_settings().cors_origins[0]
    r = TestClient(app, raise_server_exceptions=False).get("/explota", headers={"Origin": origen})
    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") == origen
    assert "ZeroDivisionError" in r.json()["detail"]
