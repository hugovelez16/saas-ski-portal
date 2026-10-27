"""API v2 del area empresa. Empresa y vistas (PR-17); membresias, tarifas e impuestos llegan en PR-18."""

from fastapi import APIRouter

from routers.v2 import companies

router = APIRouter(prefix="/v2")
router.include_router(companies.router)


@router.get("/ping", tags=["v2"])
def ping():
    """Comprobacion de montaje de v2 (unica ruta publica de v2)."""
    return {"status": "ok", "version": "v2"}
