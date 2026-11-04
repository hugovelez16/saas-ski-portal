"""Cache de hechos de acceso (usuario x empresa) sobre Redis.

Nunca decide por si sola: si no hay dato o Redis falla, quien llama lee de BD.
No se cachean empresas inexistentes.
"""

import json
import logging

from redis_config import redis_manager

logger = logging.getLogger(__name__)

ACCESS_CACHE_TTL_SECONDS = 60


def _key(user_id: str, company_id: str) -> str:
    return f"access:{user_id}:{company_id}"


def get_access(user_id: str, company_id: str) -> dict | None:
    raw = redis_manager.get(_key(user_id, company_id))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def set_access(user_id: str, company_id: str, facts: dict) -> None:
    """facts: company_active, is_managed, membership_active, membership_role."""
    redis_manager.set(_key(user_id, company_id), json.dumps(facts), ex=ACCESS_CACHE_TTL_SECONDS)


def invalidate_membership(user_id, company_id) -> None:
    redis_manager.delete(_key(str(user_id), str(company_id)))


def invalidate_company(company_id) -> None:
    redis_manager.delete_pattern(f"access:*:{company_id}")
