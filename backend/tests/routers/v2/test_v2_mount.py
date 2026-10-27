"""
Montaje de la API v2 y traduccion de excepciones de dominio (PR-16.3).

- GET /v2/ping -> 200 {"status": "ok", "version": "v2"}.
- GET /health (v1) sigue respondiendo 200.
- DomainException lanzada en un endpoint de v2 se traduce a su codigo HTTP:
  EntityNotFoundException 404, ConflictException 409, ValidationDomainException 422,
  UnauthorizedDomainActionException 403.

El endpoint de prueba se monta en main.app solo durante cada test (fixture `probe`) y se
retira al terminar. Sin handlers, la excepcion llega al test tal cual (TestClient
raise_server_exceptions=True), lo que hace legible el fallo.

ConflictException y ValidationDomainException existen en domain_exceptions desde PR-16.2.
"""

import main
import pytest
from domain.exceptions import domain_exceptions

PROBE_PATH = "/v2/__probe__/domain-error"


def _probe_endpoint(name: str):
    """Lanza la excepcion de dominio indicada por nombre, resuelta al ejecutar la peticion."""
    exception_class = getattr(domain_exceptions, name)
    raise exception_class(f"probe {name}")


@pytest.fixture
def probe():
    main.app.add_api_route(PROBE_PATH, _probe_endpoint, methods=["GET"])
    try:
        yield
    finally:
        main.app.router.routes[:] = [
            route for route in main.app.router.routes if getattr(route, "path", None) != PROBE_PATH
        ]


def test_v2_ping_returns_ok_and_version(client):
    resp = client.get("/v2/ping")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok", "version": "v2"}


def test_v1_health_still_returns_ok(client):
    resp = client.get("/health")

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"


def test_new_domain_exception_classes_exist():
    from domain.exceptions.domain_exceptions import ConflictException, DomainException, ValidationDomainException

    assert issubclass(ConflictException, DomainException)
    assert issubclass(ValidationDomainException, DomainException)


@pytest.mark.parametrize(
    ("exception_name", "expected_status"),
    [
        ("EntityNotFoundException", 404),
        ("ConflictException", 409),
        ("ValidationDomainException", 422),
        ("UnauthorizedDomainActionException", 403),
        ("InactiveMembershipException", 403),
        ("ModuleAccessDeniedException", 403),
        ("InvalidRateConfigurationException", 422),
    ],
)
def test_domain_exception_is_translated_to_http_status(client, probe, exception_name, expected_status):
    resp = client.get(PROBE_PATH, params={"name": exception_name})

    assert resp.status_code == expected_status, resp.text
