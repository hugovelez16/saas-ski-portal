"""Tope de tamano del JSON de empresa (settings y worklog_definitions) en los schemas de escritura de la API v2."""

import pytest
import schemas
from pydantic import ValidationError
from routers.v2 import schemas as v2_schemas


def _big():
    return {"k": "x" * (schemas.COMPANY_JSON_MAX_BYTES + 1)}


@pytest.mark.parametrize("field", ["settings", "worklog_definitions"])
def test_update_rechaza_json_demasiado_grande(field):
    with pytest.raises(ValidationError):
        v2_schemas.CompanyUpdateV2(**{field: _big()})


@pytest.mark.parametrize("field", ["settings", "worklog_definitions"])
def test_create_rechaza_json_demasiado_grande(field):
    with pytest.raises(ValidationError):
        v2_schemas.CompanyCreateV2(name="Empresa", tax_config={}, **{field: _big()})


def test_json_normal_se_acepta():
    update = v2_schemas.CompanyUpdateV2(settings={"modules": {"coordination": True}})
    assert update.settings is not None
    assert update.settings.modules == {"coordination": True}
