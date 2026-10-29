"""Arnes de paridad entre la API v1 y la API v2 (PR-16.4).

- to_snake(obj): convierte las claves camelCase (tambien dentro de dicts anidados y listas) a snake_case.
  No modifica la entrada ni transforma valores.
- assert_parity(v1, v2, *, ignore): compara dos payloads tras quitar las claves de `ignore` a cualquier
  nivel. Las claves se comparan tal cual llegan: quien compara debe aplicar `to_snake` antes si hace falta.
- call_both(client, method, v1_path, v2_path, *, v1_body, v2_body): ejecuta la misma peticion contra v1 y
  contra v2 y devuelve la tupla (respuesta_v1, respuesta_v2). Cada cuerpo se envia con `json=`.
- build_parity_world(db) / fixture `parity_world` (en `tests/parity/conftest.py`): escenario comun con
  PA, manager, worker, empresa autonoma, empresa gestionada y empresa suspendida.

Convencion: las diferencias intencionadas entre v1 y v2 (renombrados de X3, formas de respuesta distintas,
codigos de estado distintos) NO se ocultan en el helper. Se declaran en una tabla `KNOWN_DIFFERENCES`
dentro del propio test que las usa, para que cada excepcion quede visible y revisable.
"""

import json
import re
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Any

import models

from tests.factories import make_company, make_member, make_user

_CAMEL_BOUNDARY = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_LOWER_UPPER = re.compile(r"([a-z0-9])([A-Z])")


def _snake_key(key: Any) -> Any:
    if not isinstance(key, str):
        return key
    partial = _CAMEL_BOUNDARY.sub(r"\1_\2", key)
    return _CAMEL_LOWER_UPPER.sub(r"\1_\2", partial).lower()


def to_snake(obj: Any) -> Any:
    """Devuelve una copia de `obj` con las claves de dict en snake_case (recursivo)."""
    if isinstance(obj, dict):
        return {_snake_key(key): to_snake(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [to_snake(item) for item in obj]
    return obj


def _without_keys(obj: Any, ignore: AbstractSet[str]) -> Any:
    if isinstance(obj, dict):
        return {key: _without_keys(value, ignore) for key, value in obj.items() if key not in ignore}
    if isinstance(obj, list):
        return [_without_keys(item, ignore) for item in obj]
    return obj


def assert_parity(v1: Any, v2: Any, *, ignore: AbstractSet[str] = frozenset()) -> None:
    """Falla con AssertionError si v1 y v2 difieren tras quitar las claves de `ignore` a cualquier nivel."""
    left = _without_keys(v1, ignore)
    right = _without_keys(v2, ignore)
    if left != right:
        raise AssertionError(
            "Payloads v1 y v2 difieren:\n"
            f"v1: {json.dumps(left, default=str, sort_keys=True)}\n"
            f"v2: {json.dumps(right, default=str, sort_keys=True)}"
        )


def call_both(
    client,
    method: str,
    v1_path: str,
    v2_path: str,
    *,
    v1_body: Any = None,
    v2_body: Any = None,
) -> tuple[Any, Any]:
    """Ejecuta la misma peticion en v1 y en v2 y devuelve (respuesta_v1, respuesta_v2)."""
    v1_resp = client.request(method, v1_path, json=v1_body)
    v2_resp = client.request(method, v2_path, json=v2_body)
    return v1_resp, v2_resp


@dataclass(frozen=True)
class ParityWorld:
    pa: models.User
    manager: models.User
    worker: models.User
    autonoma: models.Company
    gestionada: models.Company
    suspendida: models.Company


def build_parity_world(db) -> ParityWorld:
    """Crea el escenario comun. Manager y worker son miembros de las tres empresas."""
    pa = make_user(db, role="admin")
    manager = make_user(db)
    worker = make_user(db)
    autonoma = make_company(db, name="Parity autonoma", is_managed=False)
    gestionada = make_company(db, name="Parity gestionada", is_managed=True)
    suspendida = make_company(db, name="Parity suspendida", is_active=False)
    for company in (autonoma, gestionada, suspendida):
        make_member(db, manager, company, role="manager")
        make_member(db, worker, company, role="worker")
    return ParityWorld(
        pa=pa,
        manager=manager,
        worker=worker,
        autonoma=autonoma,
        gestionada=gestionada,
        suspendida=suspendida,
    )
