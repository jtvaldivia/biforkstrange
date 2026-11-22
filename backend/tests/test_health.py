from fastapi.testclient import TestClient

from app.main import app


def test_health_dice_que_commit_corre(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    assert TestClient(app).get("/health").json() == {"ok": True, "commit": "abc123"}


def test_health_sin_render(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    assert TestClient(app).get("/health").json() == {"ok": True, "commit": ""}
