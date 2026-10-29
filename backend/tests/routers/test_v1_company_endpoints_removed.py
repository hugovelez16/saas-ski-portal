"""
Retirada de los endpoints de empresa de la API v1 (PR-21.0).

Los endpoints de /companies y /users/{id}/companies (gestion de empresas, membresias, tarifas y vistas
de empresa) se eliminan de v1; su sustituto es la API v2 (/v2/...). Se comprueba en dos niveles:
el esquema OpenAPI de la aplicacion no contiene la operacion y una peticion real responde 404 o 405.

Los endpoints que se mantienen en v1 (dashboard-summary y daily-report) se comprueban en positivo para
detectar retiradas por error.
"""

import re
import uuid

import main
import pytest

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}
ABSENT_STATUS = (404, 405)

# Plantillas de ruta sin nombres de parametro: "{}" sustituye a cualquier {param}.
RETIRED_OPERATIONS = [
    ("GET", "/companies"),
    ("POST", "/companies"),
    ("PUT", "/companies/{}"),
    ("DELETE", "/companies/{}"),
    ("GET", "/companies/detailed"),
    ("GET", "/companies/{}"),
    ("GET", "/companies/{}/members"),
    ("PUT", "/companies/{}/members/order"),
    ("POST", "/companies/{}/members/add"),
    ("PUT", "/companies/{}/members/{}/status"),
    ("PUT", "/companies/{}/members/{}/role"),
    ("PUT", "/companies/{}/members/{}/rates"),
    ("PUT", "/companies/{}/members/{}/settings"),
    ("DELETE", "/companies/{}/members/{}"),
    ("GET", "/companies/{}/rates-v2"),
    ("GET", "/users/me/companies"),
    ("GET", "/users/{}/companies"),
]

KEPT_OPERATIONS = [
    ("GET", "/companies/{}/dashboard-summary"),
    ("GET", "/companies/{}/daily-report"),
]


def _normalize(path: str) -> str:
    """Sustituye el nombre de cada parametro de ruta por '{}' para comparar plantillas."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def _concrete(path: str) -> str:
    """Rellena cada parametro con un UUID para que la peticion llegue a la ruta si esta existe."""
    return re.sub(r"\{[^}]+\}", lambda _match: str(uuid.uuid4()), path)


def _v1_operations() -> set[tuple[str, str]]:
    schema = main.app.openapi()
    return {
        (method.upper(), _normalize(path))
        for path, operations in schema["paths"].items()
        for method in operations
        if method in HTTP_METHODS
    }


def _op_id(op: tuple[str, str]) -> str:
    method, path = op
    return f"{method} {path}"


@pytest.mark.parametrize("method, path", RETIRED_OPERATIONS, ids=[_op_id(op) for op in RETIRED_OPERATIONS])
def test_retired_operation_is_absent_from_v1_openapi(method, path):
    assert (method, _normalize(path)) not in _v1_operations()


@pytest.mark.parametrize("method, path", RETIRED_OPERATIONS, ids=[_op_id(op) for op in RETIRED_OPERATIONS])
def test_retired_operation_answers_404_or_405(client, method, path):
    resp = client.request(method, _concrete(path))

    assert resp.status_code in ABSENT_STATUS, f"{method} {path}: {resp.status_code} {resp.text}"


@pytest.mark.parametrize("method, path", KEPT_OPERATIONS, ids=[_op_id(op) for op in KEPT_OPERATIONS])
def test_kept_operation_is_still_in_v1_openapi(method, path):
    assert (method, _normalize(path)) in _v1_operations()


@pytest.mark.parametrize("method, path", KEPT_OPERATIONS, ids=[_op_id(op) for op in KEPT_OPERATIONS])
def test_kept_operation_still_routes(client, method, path):
    resp = client.request(method, _concrete(path))

    assert resp.status_code not in ABSENT_STATUS, f"{method} {path}: {resp.status_code} {resp.text}"
