"""Tests de la propia infraestructura de pruebas: aislamiento de BD, fabricas, cliente y Redis falso."""

import os

import database
import main
import models
import redis_config
from sqlalchemy.engine import make_url

from tests.factories import make_company, make_member, make_user, make_work_log


def test_database_url_is_never_the_real_one():
    test_url = os.getenv("TEST_DATABASE_URL")
    if test_url:
        assert database.engine.url == make_url(test_url)
    else:
        assert str(database.engine.url).startswith("sqlite")


def test_factories_create_rows(db):
    user = make_user(db)
    company = make_company(db)
    member = make_member(db, user, company)
    work_log = make_work_log(db, user, company)

    assert db.get(models.User, user.id) is not None
    assert db.get(models.Company, company.id) is not None
    assert db.get(models.CompanyMember, (user.id, company.id)) is not None
    assert db.get(models.WorkLog, work_log.id) is not None
    assert member.user_id == user.id
    assert member.company_id == company.id
    assert work_log.company_id == company.id


def test_client_uses_db_override(client):
    assert database.get_db in main.app.dependency_overrides

    response = client.get("/health")

    assert response.status_code == 200


# /health expone la version desplegada leida de APP_VERSION en cada peticion
def test_health_sin_app_version_devuelve_dev(client, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "dev"}


# Con APP_VERSION definida, /health devuelve esa version
def test_health_con_app_version_devuelve_la_version(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.2.3"}


def test_fake_redis_is_installed():
    assert redis_config.redis_manager.set("k", "v")
    assert redis_config.redis_manager.get("k") == "v"
