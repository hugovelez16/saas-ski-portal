"""Fixtures del arnes de paridad v1/v2 (PR-16.4). La logica de construccion vive en `helpers.py`."""

import pytest

from tests.parity.helpers import ParityWorld, build_parity_world


@pytest.fixture
def parity_world(db) -> ParityWorld:
    """Escenario comun: PA, manager, worker, empresa autonoma, gestionada y suspendida."""
    return build_parity_world(db)
