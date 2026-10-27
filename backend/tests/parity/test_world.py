"""Comprueba que la fixture `parity_world` crea los 6 actores/empresas del escenario comun (PA-16.4)."""

import models


def test_parity_world_creates_six_actors_and_companies(db, parity_world):
    actors = [parity_world.pa, parity_world.manager, parity_world.worker]
    companies = [parity_world.autonoma, parity_world.gestionada, parity_world.suspendida]

    for actor in actors:
        assert db.get(models.User, actor.id) is not None
    for company in companies:
        assert db.get(models.Company, company.id) is not None

    assert parity_world.pa.role == models.UserRole.admin
    assert parity_world.autonoma.is_managed is False
    assert parity_world.gestionada.is_managed is True
    assert parity_world.suspendida.is_active is False
