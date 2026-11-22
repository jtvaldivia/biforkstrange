import os

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """`commit` es el que está corriendo (Render pone RENDER_GIT_COMMIT): el deploy del CI espera a ver el suyo."""
    return {"ok": True, "commit": os.environ.get("RENDER_GIT_COMMIT", "")}
