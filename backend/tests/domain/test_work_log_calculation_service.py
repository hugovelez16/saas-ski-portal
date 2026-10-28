"""
Pruebas unitarias de caja negra para el motor de calculo salarial y fiscal WorkLogCalculationService.
"""

from decimal import Decimal

from domain.services.work_log_calculation_service import WorkLogCalculationService
from domain.value_objects.rate_definition import RateDefinition, RateExtra
from domain.value_objects.tax_configuration import TaxConfiguration
from domain.value_objects.work_duration import WorkDuration, WorkUnit


def test_calculate_hourly_rate_net_to_gross():
    # Duracion de 2 horas con tarifa neta de 20 EUR/h e IRPF del 15%
    duration = WorkDuration(unit=WorkUnit.HOURS, value=2.0)
    rate_def = RateDefinition(base_rate=Decimal("20.00"), is_gross=False)
    tax_config = TaxConfiguration(taxes={"IRPF": Decimal("0.15")})

    snapshot = WorkLogCalculationService.calculate(
        duration=duration,
        rate_definition=rate_def,
        tax_configuration=tax_config,
    )

    # Base neta = 2 * 20 = 40 EUR
    # Bruto = 40 / (1 - 0.15) = 47.06 EUR
    assert snapshot.net_amount == Decimal("40.00")
    assert snapshot.gross_amount == Decimal("47.06")
    assert snapshot.duration == 2.0
    assert len(snapshot.display_lines) >= 4


def test_calculate_daily_rate_gross_to_net_with_extras():
    # Duracion de 3 dias a 100 EUR/dia bruto, con suplemento de 10 EUR/dia y SS del 5% + IRPF del 10%
    duration = WorkDuration(unit=WorkUnit.DAYS, value=3.0)
    extras = {
        "transporte": RateExtra(name="transporte", value=Decimal("10.00"), per_unit=True),
        "dietas": RateExtra(name="dietas", value=Decimal("15.00"), per_unit=False),
    }
    rate_def = RateDefinition(base_rate=Decimal("100.00"), is_gross=True, extras=extras)
    tax_config = TaxConfiguration(taxes={"IRPF": Decimal("0.10"), "Seguridad Social": Decimal("0.05")})

    options = {"transporte": True, "dietas": True}

    snapshot = WorkLogCalculationService.calculate(
        duration=duration,
        rate_definition=rate_def,
        tax_configuration=tax_config,
        options=options,
    )

    # Base = 3 * 100 = 300 EUR
    # Extras = (10 * 3) + 15 = 45 EUR
    # Total Bruto = 345 EUR
    # Total deducciones (15%) = 345 * 0.15 = 51.75 EUR
    # Neto = 345 - 51.75 = 293.25 EUR
    assert snapshot.gross_amount == Decimal("345.00")
    assert snapshot.net_amount == Decimal("293.25")


def test_manual_override_amount():
    duration = WorkDuration(unit=WorkUnit.HOURS, value=4.0)
    rate_def = RateDefinition(base_rate=Decimal("25.00"), is_gross=False)
    tax_config = TaxConfiguration(taxes={"IRPF": Decimal("0.15")})

    snapshot = WorkLogCalculationService.calculate(
        duration=duration,
        rate_definition=rate_def,
        tax_configuration=tax_config,
        manual_net_amount=Decimal("150.00"),
    )

    assert snapshot.net_amount == Decimal("150.00")
    assert snapshot.gross_amount == Decimal("150.00")
    assert snapshot.metadata.get("type") == "manual_override"
    assert snapshot.tax_applied == {}


def test_tax_configuration_resolves_free_keys_like_resolve_taxes():
    config = TaxConfiguration.from_dict(
        {"IRPF": 0.15, "Seguridad Social": 0.0648},
        {"IRPF": 0.10, "Otros": 0.02, "Seguridad Social": None},
    )

    assert config.taxes == {"IRPF": Decimal("0.1"), "Seguridad Social": Decimal("0.0648"), "Otros": Decimal("0.02")}
    assert config.total_tax_rate == Decimal("0.1848")


def test_tax_configuration_dirty_values_count_as_zero():
    config = TaxConfiguration.from_dict({"A": "abc", "B": float("nan"), "C": {}, "D": "", "E": 0.1})

    assert config.taxes == {
        "A": Decimal("0"),
        "B": Decimal("0"),
        "C": Decimal("0"),
        "D": Decimal("0"),
        "E": Decimal("0.1"),
    }


def test_tax_configuration_empty_is_valid():
    assert TaxConfiguration.from_dict({}, None).taxes == {}
    assert TaxConfiguration.from_dict(None, None).total_tax_rate == Decimal("0")


def test_gross_rate_deducts_all_free_taxes_and_reports_tax_applied():
    rate_def = RateDefinition(base_rate=Decimal("100.00"), is_gross=True)
    tax_config = TaxConfiguration(taxes={"A": Decimal("0.10"), "B": Decimal("0.05"), "C": Decimal("0.05")})

    snapshot = WorkLogCalculationService.calculate(
        duration=WorkDuration(unit=WorkUnit.FIXED, value=1.0), rate_definition=rate_def, tax_configuration=tax_config
    )

    assert snapshot.gross_amount == Decimal("100.00")
    assert snapshot.net_amount == Decimal("80.00")
    assert snapshot.tax_applied == {"A": Decimal("0.10"), "B": Decimal("0.05"), "C": Decimal("0.05")}
    assert [line.code for line in snapshot.display_lines if line.type == "tax"] == ["A", "B", "C"]


def test_net_rate_does_not_deduct_taxes():
    rate_def = RateDefinition.from_dict({"base_rate": 50})
    tax_config = TaxConfiguration(taxes={"IRPF": Decimal("0.20")})

    snapshot = WorkLogCalculationService.calculate(
        duration=WorkDuration(unit=WorkUnit.FIXED, value=1.0), rate_definition=rate_def, tax_configuration=tax_config
    )

    assert rate_def.is_gross is False
    assert snapshot.net_amount == Decimal("50.00")
    assert snapshot.gross_amount == Decimal("62.50")
