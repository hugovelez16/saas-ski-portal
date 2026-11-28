"""API v2 de administracion de plataforma (`/api/v2/admin/...`), partida por seccion.

Cada sub-router declara la guarda unica `deps.require_platform_admin` en su entrada (R-ACC-25).
El orden de inclusion fija el orden de registro de las rutas.
"""

from fastapi import APIRouter

from routers.v2.admin import audit_logs, companies, invitations, members, modules, users

router = APIRouter()
router.include_router(companies.router)
router.include_router(members.router)
router.include_router(invitations.router)
router.include_router(users.router)
router.include_router(modules.router)
router.include_router(audit_logs.router)
