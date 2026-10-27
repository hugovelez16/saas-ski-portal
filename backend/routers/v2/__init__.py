"""API v2 del area empresa. Los sub-routers de empresa, membresias, tarifas e impuestos llegan en PR-17 y PR-18."""

from fastapi import APIRouter

router = APIRouter(prefix="/v2")


@router.get("/ping", tags=["v2"])
def ping():
    """Comprobacion de montaje de v2 (unica ruta publica de v2)."""
    return {"status": "ok", "version": "v2"}
