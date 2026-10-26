"""Tests de scripts.repair_tax_values (PR-10.R, SQLite, fixtures de tests/conftest.py).

Los backups se escriben en tmp_path, siempre fuera del arbol del repositorio.
"""

import json
import math
import os
import stat

import models
import pytest
from scripts.repair_common import BACKEND_DIR, RepairReport
from scripts.repair_tax_values import main, run

from scripts import repair_tax_values
from tests.factories import make_company, make_member, make_user

# JSONB de PostgreSQL rechaza NaN, que algunos casos reproducen; la migracion se prueba aparte
# en test_migration_tax_keys.py (marcador postgres).
pytestmark = pytest.mark.skipif(
    bool(os.getenv("TEST_DATABASE_URL")),
    reason="el script se prueba con SQLite: JSONB de PostgreSQL no admite NaN",
)


def _company(db, tax_config):
    # make_company sustituye None por un valor por defecto, por eso se asigna el valor despues.
    company = make_company(db, tax_config={})
    company.tax_config = tax_config
    db.commit()
    db.refresh(company)
    return company


def _member(db, company, rates_config):
    return make_member(db, make_user(db), company, rates_config=rates_config)


def _overrides_member(db, company, overrides, tipo="particular"):
    return _member(db, company, {tipo: {"base_rate": 20.0, "is_gross": True, "tax_overrides": overrides}})


def _tax_config_of(db, company):
    db.expire_all()
    return db.get(models.Company, company.id).tax_config


def _rates_of(db, member):
    db.expire_all()
    return db.get(models.CompanyMember, (member.user_id, member.company_id)).rates_config


def _snapshot(db):
    db.expire_all()
    companies = {str(c.id): repr(c.tax_config) for c in db.query(models.Company).all()}
    members = {(str(m.user_id), str(m.company_id)): repr(m.rates_config) for m in db.query(models.CompanyMember).all()}
    return companies, members


def _manual_for(report, company):
    return [item for item in report.manual if item["company_id"] == str(company.id)]


def _info(report, tipo):
    return [item for item in report.informational if item["tipo"] == tipo]


def _files(directory, topic):
    return sorted(directory.glob(f"{topic}_*.json"))


def test_topic_del_script():
    assert repair_tax_values.TOPIC == "tax_values"


# (1) valores correctos


def test_valores_correctos_no_se_tocan(db, tmp_path):
    company = _company(db, {"IRPF": 0.15, "Exento": 0, "Total": 1, "Mitad": 0.5})
    member = _overrides_member(db, company, {"IRPF": 0.2, "Exento": 0.0})
    backup = tmp_path / "backups"

    report = run(db, apply=True, backup_dir=backup)

    assert report.changes == []
    assert report.manual == []
    assert report.backup_files == []
    assert report.exit_code() == 0
    assert _tax_config_of(db, company) == {"IRPF": 0.15, "Exento": 0, "Total": 1, "Mitad": 0.5}
    assert _rates_of(db, member)["particular"]["tax_overrides"] == {"IRPF": 0.2, "Exento": 0.0}
    assert not backup.exists()


def test_tax_config_vacio_y_null_son_validos(db, tmp_path):
    empty = _company(db, {})
    null = _company(db, None)

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert report.changes == []
    assert report.manual == []
    assert _tax_config_of(db, empty) == {}
    assert _tax_config_of(db, null) is None


# (2) cadenas en rango se convierten


def test_apply_convierte_cadena_en_rango_a_float_en_tax_config(db, tmp_path):
    company = _company(db, {"IRPF": "0.15", "Cero": "0", "Bien": 0.1})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    after = _tax_config_of(db, company)
    assert after == {"IRPF": 0.15, "Cero": 0.0, "Bien": 0.1}
    assert all(isinstance(value, float) for value in after.values())
    assert {change["ruta"] for change in report.changes} == {"tax_config.IRPF", "tax_config.Cero"}
    for change in report.changes:
        assert change["company_id"] == str(company.id)
        assert isinstance(change["antes"], str)
    assert report.manual == []


def test_apply_convierte_cadena_en_rango_en_tax_overrides(db, tmp_path):
    company = _company(db, {"IRPF": 0.15})
    member = _overrides_member(db, company, {"IRPF": "0.2"})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    overrides = _rates_of(db, member)["particular"]["tax_overrides"]
    assert overrides == {"IRPF": 0.2}
    assert isinstance(overrides["IRPF"], float)
    assert len(report.changes) == 1
    change = report.changes[0]
    assert change["ruta"] == "rates_config.particular.tax_overrides.IRPF"
    assert change["company_id"] == str(company.id)
    assert change["user_id"] == str(member.user_id)


# (3) valores invalidos en tax_config: manual y sin modificar


@pytest.mark.parametrize(
    "value",
    [15, -0.1, "abc", "15", True, False, float("nan"), float("inf"), None],
    ids=["15", "negativo", "abc", "cadena-15", "true", "false", "nan", "inf", "null"],
)
def test_valor_invalido_en_tax_config_es_manual_y_no_se_modifica(db, tmp_path, value):
    company = _company(db, {"IRPF": value, "Bien": 0.1})
    before = repr(_tax_config_of(db, company))

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    manual = _manual_for(report, company)
    assert [item["ruta"] for item in manual] == ["tax_config.IRPF"]
    assert "motivo" in manual[0]
    assert "valor" in manual[0]
    assert report.changes == []
    assert report.exit_code() == 2
    assert repr(_tax_config_of(db, company)) == before


def test_tax_config_que_no_es_dict_es_manual(db, tmp_path):
    company = _company(db, [0.1, 0.2])

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert len(_manual_for(report, company)) == 1
    assert _tax_config_of(db, company) == [0.1, 0.2]


@pytest.mark.parametrize("value", [15, -0.1, "abc", "15", True, float("nan")])
def test_valor_invalido_en_tax_overrides_es_manual_y_no_se_modifica(db, tmp_path, value):
    company = _company(db, {"IRPF": 0.15})
    member = _overrides_member(db, company, {"IRPF": value})
    before = repr(_rates_of(db, member))

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    manual = _manual_for(report, company)
    assert [item["ruta"] for item in manual] == ["rates_config.particular.tax_overrides.IRPF"]
    assert manual[0]["user_id"] == str(member.user_id)
    assert report.changes == []
    assert repr(_rates_of(db, member)) == before


# (4) null en tax_overrides


def test_null_en_tax_overrides_se_acepta(db, tmp_path):
    company = _company(db, {"IRPF": 0.15})
    member = _overrides_member(db, company, {"IRPF": None})
    sin_overrides = _member(db, company, {"particular": {"base_rate": 20.0, "tax_overrides": None}})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert report.changes == []
    assert report.manual == []
    assert report.exit_code() == 0
    assert _rates_of(db, member)["particular"]["tax_overrides"] == {"IRPF": None}
    assert _rates_of(db, sin_overrides)["particular"]["tax_overrides"] is None


# (5) nombres y numero de entradas


def test_nombre_vacio_o_solo_espacios_es_manual(db, tmp_path):
    empty = _company(db, {"": 0.1})
    spaces = _company(db, {"   ": 0.1})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert len(_manual_for(report, empty)) == 1
    assert len(_manual_for(report, spaces)) == 1
    assert _tax_config_of(db, empty) == {"": 0.1}
    assert _tax_config_of(db, spaces) == {"   ": 0.1}


def test_nombre_de_50_caracteres_es_valido_y_de_51_es_manual(db, tmp_path):
    ok = _company(db, {"A" * 50: 0.1})
    long_name = _company(db, {"A" * 51: 0.1})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert _manual_for(report, ok) == []
    assert len(_manual_for(report, long_name)) == 1
    assert _tax_config_of(db, long_name) == {"A" * 51: 0.1}


def test_nombre_se_mide_tras_strip(db, tmp_path):
    company = _company(db, {"  " + "A" * 50 + "  ": 0.1})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert _manual_for(report, company) == []


def test_mas_de_20_entradas_es_un_solo_item_manual(db, tmp_path):
    over = _company(db, {f"T{i}": 0.01 for i in range(21)})
    limit = _company(db, {f"T{i}": 0.01 for i in range(20)})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert len(_manual_for(report, over)) == 1
    assert _manual_for(report, limit) == []
    assert len(_tax_config_of(db, over)) == 21


def test_nombres_duplicados_tras_strip_son_manual(db, tmp_path):
    company = _company(db, {"IRPF": 0.15, "IRPF ": 0.1})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert len(_manual_for(report, company)) >= 1
    assert report.exit_code() == 2
    assert _tax_config_of(db, company) == {"IRPF": 0.15, "IRPF ": 0.1}


# (6) dry-run


def test_dry_run_no_escribe_en_bd_ni_en_disco(db, tmp_path):
    company = _company(db, {"IRPF": "0.15", "Malo": 15})
    member = _overrides_member(db, company, {"ss": 0.06, "IRPF": "0.2"})
    backup = tmp_path / "backups"
    before = _snapshot(db)

    report = run(db, apply=False, backup_dir=backup)

    assert len(report.changes) == 2
    assert len(report.manual) == 1
    assert report.backup_files == []
    assert not backup.exists()
    assert _snapshot(db) == before
    assert _rates_of(db, member)["particular"]["tax_overrides"] == {"ss": 0.06, "IRPF": "0.2"}


def test_main_dry_run_por_defecto_no_escribe(db, tmp_path, capsys):
    company = _company(db, {"IRPF": "0.15"})
    backup = tmp_path / "backups"

    code = main(["--backup-dir", str(backup)])

    assert code == 0
    assert not backup.exists()
    assert _tax_config_of(db, company) == {"IRPF": "0.15"}
    assert "--dry-run" in capsys.readouterr().out


# (7) backups


def test_apply_escribe_backups_before_y_manual_con_permisos_0600(db, tmp_path):
    company = _company(db, {"IRPF": "0.15", "Malo": 15})
    backup = tmp_path / "backups"

    report = run(db, apply=True, backup_dir=backup)

    before_files = _files(backup, "tax_values_before")
    manual_files = _files(backup, "tax_values_manual")
    assert len(before_files) == 1
    assert len(manual_files) == 1
    assert set(report.backup_files) == {before_files[0], manual_files[0]}
    for path in (before_files[0], manual_files[0]):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert path.parent == backup.resolve()
        assert BACKEND_DIR not in path.parents
    assert stat.S_IMODE(backup.stat().st_mode) == 0o700

    before = json.loads(before_files[0].read_text(encoding="utf-8"))
    assert len(before) == 1
    assert before[0]["company_id"] == str(company.id)
    assert before[0]["ruta"] == "tax_config.IRPF"
    assert "0.15" in before[0].values()

    manual = json.loads(manual_files[0].read_text(encoding="utf-8"))
    assert len(manual) == 1
    assert manual[0]["company_id"] == str(company.id)
    assert manual[0]["ruta"] == "tax_config.Malo"
    assert manual[0]["valor"] == 15

    assert _tax_config_of(db, company) == {"IRPF": 0.15, "Malo": 15}


def test_apply_solo_con_cambios_no_escribe_fichero_manual(db, tmp_path):
    _company(db, {"IRPF": "0.15"})
    backup = tmp_path / "backups"

    run(db, apply=True, backup_dir=backup)

    assert len(_files(backup, "tax_values_before")) == 1
    assert _files(backup, "tax_values_manual") == []


def test_apply_solo_con_manual_no_escribe_fichero_before(db, tmp_path):
    _company(db, {"Malo": 15})
    backup = tmp_path / "backups"

    run(db, apply=True, backup_dir=backup)

    assert _files(backup, "tax_values_before") == []
    assert len(_files(backup, "tax_values_manual")) == 1


def test_apply_con_cambios_sin_backup_dir_falla_y_no_escribe(db):
    company = _company(db, {"IRPF": "0.15"})

    with pytest.raises(SystemExit):
        run(db, apply=True, backup_dir=None)

    assert _tax_config_of(db, company) == {"IRPF": "0.15"}


def test_main_apply_con_cambios_sin_backup_dir_devuelve_1(db, monkeypatch):
    monkeypatch.delenv("REPAIR_BACKUP_DIR", raising=False)
    company = _company(db, {"IRPF": "0.15"})

    assert main(["--apply"]) == 1
    assert _tax_config_of(db, company) == {"IRPF": "0.15"}


def test_se_niega_backup_dir_dentro_del_repo(db):
    dentro = BACKEND_DIR / "tests" / "scripts" / "backup_no_permitido"
    company = _company(db, {"IRPF": "0.15"})

    with pytest.raises(SystemExit):
        run(db, apply=True, backup_dir=dentro)

    assert not dentro.exists()
    assert _tax_config_of(db, company) == {"IRPF": "0.15"}


def test_main_se_niega_backup_dir_dentro_del_repo(db):
    dentro = BACKEND_DIR / "tests" / "scripts" / "backup_no_permitido"
    company = _company(db, {"IRPF": "0.15"})

    assert main(["--apply", "--backup-dir", str(dentro)]) == 1
    assert not dentro.exists()
    assert _tax_config_of(db, company) == {"IRPF": "0.15"}


# (8) idempotencia


def test_segunda_ejecucion_no_cambia_nada(db, tmp_path):
    company = _company(db, {"IRPF": "0.15", "Otro": 0.1})
    _overrides_member(db, company, {"ss": "0.06", "irpf": 0.15, "extra": 0})
    backup = tmp_path / "backups"

    first = run(db, apply=True, backup_dir=backup)
    after_first = _snapshot(db)
    second = run(db, apply=True, backup_dir=backup)

    assert len(first.changes) >= 1
    assert second.changes == []
    assert second.backup_files == []
    assert second.manual == []
    assert _snapshot(db) == after_first
    assert len(_files(backup, "tax_values_before")) == 1


# (9) codigos de salida


def test_codigo_de_salida_2_con_manual_y_0_sin_manual(db, tmp_path, capsys):
    company = _company(db, {"Malo": 15})
    backup = tmp_path / "backups"

    report = run(db, apply=False, backup_dir=None)
    assert report.exit_code() == 2
    assert main(["--apply", "--backup-dir", str(backup)]) == 2
    assert "Codigo de salida: 2" in capsys.readouterr().out

    company.tax_config = {"Bien": 0.1}
    db.commit()

    assert run(db, apply=False, backup_dir=None).exit_code() == 0
    assert main(["--apply", "--backup-dir", str(backup)]) == 0
    assert "Codigo de salida: 0" in capsys.readouterr().out
    assert RepairReport(topic="x").exit_code() == 0


# (10) renombrado de claves


def test_claves_ss_e_irpf_se_avisan_como_renombrara(db, tmp_path):
    company = _company(db, {"social_security": 0.06})
    member = _overrides_member(db, company, {"ss": 0.06, "irpf": 0.15})

    report = run(db, apply=False, backup_dir=None)

    renames = _info(report, "renombrara")
    assert len(renames) == 2
    by_route = {item["ruta"]: item for item in renames}
    ss = by_route["rates_config.particular.tax_overrides.ss"]
    irpf = by_route["rates_config.particular.tax_overrides.irpf"]
    assert ss["nueva"] == "social_security"
    assert irpf["nueva"] == "irpf_base"
    for item in renames:
        assert item["company_id"] == str(company.id)
        assert item["user_id"] == str(member.user_id)
    assert report.manual == []
    assert report.changes == []


def test_renombrara_se_emite_una_vez_por_aparicion(db, tmp_path):
    company = _company(db, {})
    _overrides_member(db, company, {"ss": 0.06})
    _overrides_member(db, company, {"ss": 0.07})

    report = run(db, apply=False, backup_dir=None)

    assert len(_info(report, "renombrara")) == 2


def test_apply_no_renombra_claves_ese_es_trabajo_de_la_migracion(db, tmp_path):
    company = _company(db, {})
    member = _overrides_member(db, company, {"ss": 0.06, "irpf": 0.15})

    run(db, apply=True, backup_dir=tmp_path / "backups")

    assert _rates_of(db, member)["particular"]["tax_overrides"] == {"ss": 0.06, "irpf": 0.15}


@pytest.mark.parametrize(
    "overrides",
    [{"ss": 0.06, "social_security": 0.07}, {"irpf": 0.15, "irpf_base": 0.2}],
    ids=["ss", "irpf"],
)
def test_colision_entre_clave_antigua_y_destino_es_manual(db, tmp_path, overrides):
    company = _company(db, {})
    member = _overrides_member(db, company, overrides)

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert len(_manual_for(report, company)) >= 1
    assert report.exit_code() == 2
    assert _rates_of(db, member)["particular"]["tax_overrides"] == overrides


# (11) extra = 0 que la empresa no define


def test_extra_cero_sin_definir_en_empresa_se_eliminara(db, tmp_path):
    company = _company(db, {"IRPF": 0.15})
    member = _overrides_member(db, company, {"extra": 0})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    removals = _info(report, "extra_se_eliminara")
    assert len(removals) == 1
    assert removals[0]["ruta"] == "rates_config.particular.tax_overrides.extra"
    assert removals[0]["company_id"] == str(company.id)
    assert removals[0]["user_id"] == str(member.user_id)
    summary = _info(report, "resumen_extra")
    assert len(summary) == 1
    assert summary[0]["total"] == 1
    assert summary[0]["a_cero"] == 1
    assert summary[0]["eliminables"] == 1
    assert report.manual == []
    assert report.exit_code() == 0
    # El script solo informa: la eliminacion la hace la migracion.
    assert _rates_of(db, member)["particular"]["tax_overrides"] == {"extra": 0}


def test_resumen_extra_cuenta_total_y_a_cero(db, tmp_path):
    company = _company(db, {})
    _overrides_member(db, company, {"extra": 0})
    _overrides_member(db, company, {"extra": 0.0})
    _overrides_member(db, company, {"extra": 0.05})
    _overrides_member(db, company, {"extra": None})

    report = run(db, apply=False, backup_dir=None)

    summary = _info(report, "resumen_extra")
    assert len(summary) == 1
    assert summary[0]["total"] == 4
    assert summary[0]["a_cero"] == 2
    assert len(_info(report, "extra_se_eliminara")) == 2
    assert len(report.manual) == 1


def test_extra_cadena_que_se_convertira_a_cero_se_convierte_y_se_avisa(db, tmp_path):
    company = _company(db, {})
    member = _overrides_member(db, company, {"extra": "0"})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert report.manual == []
    assert len(report.changes) == 1
    assert len(_info(report, "extra_se_eliminara")) == 1
    assert _rates_of(db, member)["particular"]["tax_overrides"] == {"extra": 0.0}


def test_sin_extra_no_hay_resumen_extra(db):
    company = _company(db, {"IRPF": 0.15})
    _overrides_member(db, company, {"IRPF": 0.2})

    report = run(db, apply=False, backup_dir=None)

    assert _info(report, "resumen_extra") == []
    assert _info(report, "extra_se_eliminara") == []


# (12) extra distinto de 0


@pytest.mark.parametrize(
    "value",
    [0.05, 1, "abc", True, "15", 15, float("nan")],
    ids=["0.05", "uno", "abc", "true", "cadena-15", "15", "nan"],
)
def test_extra_distinto_de_cero_o_no_numerico_es_manual(db, tmp_path, value):
    company = _company(db, {})
    member = _overrides_member(db, company, {"extra": value})
    before = repr(_rates_of(db, member))

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    manual = _manual_for(report, company)
    assert len(manual) == 1  # una sola entrada por valor, sin duplicar
    assert manual[0]["ruta"] == "rates_config.particular.tax_overrides.extra"
    assert report.exit_code() == 2
    assert report.changes == []
    assert repr(_rates_of(db, member)) == before


def test_extra_distinto_de_cero_es_manual_aunque_la_empresa_lo_defina(db, tmp_path):
    company = _company(db, {"extra": 0.1})
    _overrides_member(db, company, {"extra": 0.05})

    report = run(db, apply=False, backup_dir=None)

    assert len(_manual_for(report, company)) == 1


def test_extra_null_no_se_toca_ni_avisa(db):
    company = _company(db, {})
    _overrides_member(db, company, {"extra": None})

    report = run(db, apply=False, backup_dir=None)

    assert report.manual == []
    assert report.changes == []
    assert _info(report, "extra_se_eliminara") == []


# (13) extra = 0 definido por la empresa


def test_extra_cero_con_empresa_que_lo_define_no_se_elimina_ni_avisa(db, tmp_path):
    company = _company(db, {"extra": 0.02})
    member = _overrides_member(db, company, {"extra": 0})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert _info(report, "extra_se_eliminara") == []
    assert report.manual == []
    assert report.changes == []
    assert report.exit_code() == 0
    assert _rates_of(db, member)["particular"]["tax_overrides"] == {"extra": 0}
    for item in _info(report, "resumen_extra"):
        assert item["eliminables"] == 0


# Otros casos


def test_clave_desconocida_es_informativa_y_no_bloquea(db):
    company = _company(db, {"IRPF": 0.15})
    member = _overrides_member(db, company, {"IRPF": 0.2, "Mutua": 0.01})

    report = run(db, apply=False, backup_dir=None)

    unknown = _info(report, "clave_desconocida")
    assert len(unknown) == 1
    assert unknown[0]["ruta"] == "rates_config.particular.tax_overrides.Mutua"
    assert unknown[0]["company_id"] == str(company.id)
    assert unknown[0]["user_id"] == str(member.user_id)
    assert report.manual == []
    assert report.exit_code() == 0


def test_clave_definida_en_la_empresa_no_es_desconocida(db):
    company = _company(db, {"IRPF": 0.15})
    _overrides_member(db, company, {"IRPF": 0.2})

    report = run(db, apply=False, backup_dir=None)

    assert _info(report, "clave_desconocida") == []


def test_clave_desconocida_no_se_emite_para_ss_irpf_ni_extra(db):
    company = _company(db, {})
    _overrides_member(db, company, {"ss": 0.06, "irpf": 0.15, "extra": 0})

    report = run(db, apply=False, backup_dir=None)

    assert _info(report, "clave_desconocida") == []


def test_entradas_de_rates_config_que_no_son_dict_se_ignoran(db, tmp_path):
    company = _company(db, {"IRPF": 0.15})
    rates = {
        "particular": 30.0,
        "texto": "abc",
        "lista": [1, 2],
        "sin_overrides": {"base_rate": 10.0},
        "overrides_no_dict": {"tax_overrides": "foo"},
        "valida": {"base_rate": 5.0, "tax_overrides": {"IRPF": 0.2}},
    }
    member = _member(db, company, rates)

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert report.changes == []
    assert report.manual == []
    assert _rates_of(db, member) == rates


def test_rates_config_vacio_o_null_se_ignora(db):
    company = _company(db, {})
    empty = _member(db, company, {})
    null = _member(db, company, {})
    null.rates_config = None
    db.commit()

    report = run(db, apply=True, backup_dir=None)

    assert report.changes == []
    assert report.manual == []
    assert _rates_of(db, empty) == {}
    assert _rates_of(db, null) is None


def test_varios_tipos_de_jornada_se_recorren(db, tmp_path):
    company = _company(db, {})
    member = _member(
        db,
        company,
        {
            "particular": {"tax_overrides": {"A": "0.1"}},
            "grupo": {"tax_overrides": {"B": 15}},
        },
    )

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert [c["ruta"] for c in report.changes] == ["rates_config.particular.tax_overrides.A"]
    assert [m["ruta"] for m in report.manual] == ["rates_config.grupo.tax_overrides.B"]
    rates = _rates_of(db, member)
    assert rates["particular"]["tax_overrides"] == {"A": 0.1}
    assert rates["grupo"]["tax_overrides"] == {"B": 15}


def test_cadena_con_nan_o_inf_no_se_convierte(db, tmp_path):
    company = _company(db, {"A": "nan", "B": "inf"})

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    after = _tax_config_of(db, company)
    assert after["A"] == "nan"
    assert after["B"] == "inf"
    assert {item["ruta"] for item in report.manual} >= {"tax_config.A", "tax_config.B"}
    assert not any(isinstance(v, float) and math.isnan(v) for v in after.values())
