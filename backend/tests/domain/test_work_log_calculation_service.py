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
    tax_config = TaxConfiguration(
        irpf_rate=Decimal("0.15"),
        social_security_rate=Decimal("0.00"),
        extra_rate=Decimal("0.00"),
    )

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
    tax_config = TaxConfiguration(
        irpf_rate=Decimal("0.10"),
        social_security_rate=Decimal("0.05"),
        extra_rate=Decimal("0.00"),
    )

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
    tax_config = TaxConfiguration(
        irpf_rate=Decimal("0.15"),
        social_security_rate=Decimal("0.00"),
        extra_rate=Decimal("0.00"),
    )

    snapshot = WorkLogCalculationService.calculate(
        duration=duration,
        rate_definition=rate_def,
        tax_configuration=tax_config,
        manual_net_amount=Decimal("150.00"),
    )

    assert snapshot.net_amount == Decimal("150.00")
    assert snapshot.gross_amount == Decimal("150.00")
    assert snapshot.metadata.get("type") == "manual_override"
