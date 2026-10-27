"""
Tests del arnes de paridad v1/v2 (PR-16.4), helpers en `tests/parity/helpers.py`:

- to_snake(obj): convierte claves camelCase anidadas (incluidas las de listas de dicts) a snake_case.
- assert_parity(v1, v2, *, ignore): ignora las claves de `ignore` y falla si difieren otras.
- call_both(client, method, v1_path, v2_path, *, v1_body, v2_body): ejecuta la misma peticion
  en v1 y en v2 y devuelve ambas respuestas (v1, v2).

El modulo de helpers no existe hasta PR-16.4: cada test lo importa al ejecutarse, de modo que
falla con ModuleNotFoundError y no rompe la coleccion del resto de la suite.
"""

import importlib
import json

import main
import pytest
from fastapi import Request

HELPERS_MODULE = "tests.parity.helpers"
V1_ECHO = "/__parity__/v1/echo"
V2_ECHO = "/__parity__/v2/echo"


def _helpers():
    return importlib.import_module(HELPERS_MODULE)


def _make_echo(side: str):
    async def echo(request: Request):
        raw = await request.body()
        return {"side": side, "body": json.loads(raw) if raw else None}

    return echo


@pytest.fixture
def echo_routes():
    main.app.add_api_route(V1_ECHO, _make_echo("v1"), methods=["POST"])
    main.app.add_api_route(V2_ECHO, _make_echo("v2"), methods=["POST"])
    try:
        yield
    finally:
        main.app.router.routes[:] = [
            route for route in main.app.router.routes if getattr(route, "path", None) not in {V1_ECHO, V2_ECHO}
        ]


# --- to_snake ---


def test_to_snake_converts_top_level_keys():
    result = _helpers().to_snake({"startDate": "2026-01-10", "isActive": True})

    assert result == {"start_date": "2026-01-10", "is_active": True}


def test_to_snake_converts_nested_dict_keys():
    payload = {"userInfo": {"firstName": "Ana", "homeAddress": {"zipCode": "18001"}}}

    result = _helpers().to_snake(payload)

    assert result == {"user_info": {"first_name": "Ana", "home_address": {"zip_code": "18001"}}}


def test_to_snake_converts_keys_inside_lists_of_dicts():
    payload = {
        "workLogs": [
            {"startTime": "09:00", "netAmount": 40.0},
            {"startTime": "11:00", "netAmount": 20.0},
        ]
    }

    result = _helpers().to_snake(payload)

    assert result == {
        "work_logs": [
            {"start_time": "09:00", "net_amount": 40.0},
            {"start_time": "11:00", "net_amount": 20.0},
        ]
    }


def test_to_snake_converts_top_level_list_of_dicts():
    result = _helpers().to_snake([{"companyId": 1}, {"companyId": 2}])

    assert result == [{"company_id": 1}, {"company_id": 2}]


def test_to_snake_keeps_snake_case_keys_and_string_values_untouched():
    payload = {"already_snake": 1, "label": "camelCaseValue"}

    assert _helpers().to_snake(payload) == {"already_snake": 1, "label": "camelCaseValue"}


def test_to_snake_keeps_scalars_and_lists_of_scalars():
    payload = {"tags": ["alpha", "betaGamma"], "count": 3, "missing": None}

    assert _helpers().to_snake(payload) == {"tags": ["alpha", "betaGamma"], "count": 3, "missing": None}


def test_to_snake_does_not_mutate_its_input():
    payload = {"startDate": "2026-01-10", "members": [{"userId": "u1"}]}

    _helpers().to_snake(payload)

    assert payload == {"startDate": "2026-01-10", "members": [{"userId": "u1"}]}


# --- assert_parity ---


def test_assert_parity_passes_for_equal_payloads():
    _helpers().assert_parity({"a": 1, "b": [{"x": 2}]}, {"a": 1, "b": [{"x": 2}]})


def test_assert_parity_fails_when_values_differ():
    with pytest.raises(AssertionError):
        _helpers().assert_parity({"a": 1}, {"a": 2})


def test_assert_parity_fails_when_keys_differ():
    with pytest.raises(AssertionError):
        _helpers().assert_parity({"a": 1}, {"a": 1, "extra": True})


def test_assert_parity_ignores_listed_top_level_keys():
    _helpers().assert_parity({"id": "v1-1", "name": "Alfa"}, {"id": "v2-9", "name": "Alfa"}, ignore={"id"})


def test_assert_parity_still_fails_for_differences_not_in_ignore():
    with pytest.raises(AssertionError):
        _helpers().assert_parity({"id": "a", "name": "Alfa"}, {"id": "b", "name": "Beta"}, ignore={"id"})


def test_assert_parity_ignores_listed_keys_inside_lists_of_dicts():
    v1 = {"members": [{"userId": "u1", "joinedAt": "2026-01-01T09:00:00"}]}
    v2 = {"members": [{"userId": "u1", "joinedAt": "2026-02-02T10:00:00"}]}

    _helpers().assert_parity(v1, v2, ignore={"joinedAt"})


def test_assert_parity_ignore_is_keyword_only():
    with pytest.raises(TypeError):
        _helpers().assert_parity({"id": 1}, {"id": 2}, {"id"})


# --- call_both ---


def test_call_both_returns_v1_and_v2_responses_in_order(client, echo_routes):
    v1_resp, v2_resp = _helpers().call_both(
        client, "POST", V1_ECHO, V2_ECHO, v1_body={"hours": 2}, v2_body={"hours": 2}
    )

    assert v1_resp.json() == {"side": "v1", "body": {"hours": 2}}
    assert v2_resp.json() == {"side": "v2", "body": {"hours": 2}}


def test_call_both_sends_each_body_to_its_own_side(client, echo_routes):
    v1_resp, v2_resp = _helpers().call_both(client, "POST", V1_ECHO, V2_ECHO, v1_body={"v": 1}, v2_body={"v": 2})

    assert v1_resp.json()["body"] == {"v": 1}
    assert v2_resp.json()["body"] == {"v": 2}


def test_call_both_without_bodies_sends_no_payload(client, echo_routes):
    v1_resp, v2_resp = _helpers().call_both(client, "POST", V1_ECHO, V2_ECHO)

    assert v1_resp.json() == {"side": "v1", "body": None}
    assert v2_resp.json() == {"side": "v2", "body": None}


def test_call_both_on_real_v1_health_and_v2_ping(client):
    v1_resp, v2_resp = _helpers().call_both(client, "GET", "/health", "/v2/ping")

    assert v1_resp.status_code == 200, v1_resp.text
    assert v2_resp.status_code == 200, v2_resp.text
    assert v2_resp.json() == {"status": "ok", "version": "v2"}
