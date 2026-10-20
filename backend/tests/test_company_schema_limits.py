"""Tope de tamano del JSON de empresa (settings y worklog_definitions)."""

import pytest
import schemas
from pydantic import ValidationError


def _big():
    return {"k": "x" * (schemas.COMPANY_JSON_MAX_BYTES + 1)}


@pytest.mark.parametrize("field", ["settings", "worklogDefinitions"])
def test_update_rechaza_json_demasiado_grande(field):
    with pytest.raises(ValidationError):
        schemas.CompanyUpdate(**{field: _big()})


@pytest.mark.parametrize("field", ["settings", "worklogDefinitions"])
def test_create_rechaza_json_demasiado_grande(field):
    with pytest.raises(ValidationError):
        schemas.CompanyCreate(name="Empresa", **{field: _big()})


def test_json_normal_se_acepta():
    update = schemas.CompanyUpdate(settings={"modules": {"coordination": True}})
    assert update.settings == {"modules": {"coordination": True}}
