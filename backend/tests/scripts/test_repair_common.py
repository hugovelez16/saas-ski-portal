"""Tests de scripts.repair_common.write_backup: sincronizacion a disco y limpieza del fichero parcial."""

import json
import os
import stat

import pytest

from scripts import repair_common


def test_write_backup_escribe_json_con_permisos_0600_y_sincroniza(tmp_path, monkeypatch):
    synced: list[int] = []
    real_fsync = os.fsync

    def registrar_fsync(fd):
        synced.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(repair_common.os, "fsync", registrar_fsync)

    path = repair_common.write_backup(tmp_path, "tema", {"empresa": "x"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"empresa": "x"}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert len(synced) == 1


def test_write_backup_borra_el_fichero_parcial_si_falla_la_escritura(tmp_path, monkeypatch):
    def fsync_con_error(fd):
        raise OSError(5, "Error de E/S")

    monkeypatch.setattr(repair_common.os, "fsync", fsync_con_error)

    with pytest.raises(OSError):
        repair_common.write_backup(tmp_path, "tema", {"empresa": "x"})

    assert list(tmp_path.glob("tema_*.json")) == []
