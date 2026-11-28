"""Tests del script idempotente de creacion de empresa propia (R-EMP-15)."""

import json

import contracts
import models

from scripts import create_personal_companies
from tests.factories import make_company, make_member, make_user


def test_dry_run_detecta_usuarios_sin_empresa_y_no_escribe(db):
    sin_empresa = make_user(db, email="solo@ejemplo.es", role="user")
    sin_empresa.first_name = "Ana"
    sin_empresa.last_name = "Lopez"
    con_empresa = make_user(db, email="con@ejemplo.es", role="user")
    empresa = make_company(db, name="Escuela Existente")
    make_member(db, con_empresa, empresa, role="worker")
    pa = make_user(db, email="admin@ejemplo.es", role="admin")
    db.commit()

    before_companies = db.query(models.Company).count()
    before_members = db.query(models.CompanyMember).count()
    before_audits = db.query(models.AuditLog).count()

    report = create_personal_companies.run(db, apply=False)

    assert report.exit_code() == 0
    assert len(report.changes) == 1
    assert report.changes[0]["user_id"] == str(sin_empresa.id)
    assert report.changes[0]["company_name"] == "Empresa de Ana Lopez"
    assert db.query(models.Company).count() == before_companies
    assert db.query(models.CompanyMember).count() == before_members
    assert db.query(models.AuditLog).count() == before_audits
    assert db.query(models.CompanyMember).filter_by(user_id=pa.id).count() == 0


def test_apply_crea_empresa_autonoma_valida_y_es_idempotente(db, tmp_path):
    u1 = make_user(db, email="uno@ejemplo.es", role="user")
    u1.first_name = "Carlos"
    u1.last_name = "Ruiz"
    u2 = make_user(db, email="dos@ejemplo.es", role="user")
    u2.first_name = None
    u2.last_name = None
    pa = make_user(db, email="pa@ejemplo.es", role="admin")
    db.commit()

    first = create_personal_companies.run(db, apply=True, backup_dir=tmp_path)

    assert first.exit_code() == 0
    assert len(first.changes) == 2
    assert len(first.backup_files) == 1
    backup_data = json.loads(first.backup_files[0].read_text(encoding="utf-8"))
    assert len(backup_data) == 2

    # Verificar que las empresas y membresias creadas cumplen el contrato de dominio.
    for user, expected_name in ((u1, "Empresa de Carlos Ruiz"), (u2, "Empresa de dos")):
        memberships = db.query(models.CompanyMember).filter_by(user_id=user.id).all()
        assert len(memberships) == 1
        membership = memberships[0]
        assert membership.role == models.CompanyRole.worker
        assert membership.is_active is True

        company = db.get(models.Company, membership.company_id)
        assert company is not None
        assert company.name == expected_name
        assert company.is_active is True
        assert company.is_managed is False
        assert company.tax_config == {}
        contracts.TaxConfig.model_validate(company.tax_config)
        contracts.WorklogDefinitions.model_validate(company.worklog_definitions)
        contracts.CompanySettings.model_validate(company.settings)
        assert db.query(models.CompanyMember).filter_by(company_id=company.id).count() == 1

    # El PA nunca recibe membresia ni empresa propia (R-ACC-26).
    assert db.query(models.CompanyMember).filter_by(user_id=pa.id).count() == 0

    # Segunda ejecucion: completamente idempotente.
    companies_after_first = db.query(models.Company).count()
    members_after_first = db.query(models.CompanyMember).count()
    audits_after_first = db.query(models.AuditLog).count()

    second = create_personal_companies.run(db, apply=True, backup_dir=tmp_path)

    assert second.exit_code() == 0
    assert second.changes == []
    assert db.query(models.Company).count() == companies_after_first
    assert db.query(models.CompanyMember).count() == members_after_first
    assert db.query(models.AuditLog).count() == audits_after_first


def test_apply_omite_usuarios_con_membresia_inactiva_y_recorta_nombre_largo(db):
    inactivo = make_user(db, email="inactivo@ejemplo.es", role="user")
    empresa = make_company(db, name="Otra")
    make_member(db, inactivo, empresa, role="worker", is_active=False)

    largo = make_user(db, email="largo@ejemplo.es", role="user")
    largo.first_name = "A" * 80
    largo.last_name = "B" * 80
    db.commit()

    report = create_personal_companies.run(db, apply=True)

    assert len(report.changes) == 1
    assert report.changes[0]["user_id"] == str(largo.id)
    assert len(report.changes[0]["company_name"]) <= 120
    membership = db.query(models.CompanyMember).filter_by(user_id=largo.id).one()
    company = db.get(models.Company, membership.company_id)
    assert len(company.name) <= 120


def test_main_dry_run_y_apply_por_cli(monkeypatch, db):
    user = make_user(db, email="cli@ejemplo.es", role="user")
    user.first_name = "Lucia"
    user.last_name = "Gomez"
    db.commit()

    monkeypatch.setattr(create_personal_companies.database, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)

    code_dry = create_personal_companies.main(["--dry-run"])
    assert code_dry == 0
    assert db.query(models.CompanyMember).filter_by(user_id=user.id).count() == 0

    code_apply = create_personal_companies.main(["--apply"])
    assert code_apply == 0
    assert db.query(models.CompanyMember).filter_by(user_id=user.id).count() == 1
