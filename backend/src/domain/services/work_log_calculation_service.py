"""
Servicio de Dominio: Motor de calculo de jornadas y liquidacion fiscal.
Completamente aislado de SQLAlchemy, FastAPI, Redis o librerias de infraestructura.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

from domain.value_objects.calculation_snapshot import CalculationSnapshot, DisplayLine
from domain.value_objects.rate_definition import RateDefinition
from domain.value_objects.tax_configuration import TaxConfiguration
from domain.value_objects.work_duration import WorkDuration, WorkUnit


class WorkLogCalculationService:
    """Calcula importes brutos, netos, retenciones fiscales y snapshots estructurados."""

    @staticmethod
    def calculate(
        duration: WorkDuration,
        rate_definition: RateDefinition,
        tax_configuration: TaxConfiguration,
        options: Optional[Dict[str, bool]] = None,
        manual_net_amount: Optional[Decimal] = None,
    ) -> CalculationSnapshot:
        # 1. Anulacion manual directa si el usuario especifica un importe fijo
        if manual_net_amount is not None:
            quantized = manual_net_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return CalculationSnapshot(
                gross_amount=quantized,
                net_amount=quantized,
                rate_applied=Decimal("0.00"),
                duration=0.0,
                display_lines=[
                    DisplayLine(type="income", label="Importe Manual", value=float(quantized)),
                    DisplayLine(type="subtotal", label="Total", value=float(quantized)),
                ],
                metadata={"type": "manual_override", "net_amount": float(quantized)},
            )

        # 2. Calculo base segun unidad y duracion
        base_rate = rate_definition.base_rate
        duration_value = duration.value
        dec_duration = Decimal(str(duration_value))
        unit = duration.unit.value

        if duration.unit == WorkUnit.HOURS:
            amount_base = (dec_duration * base_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            base_label = f"{round(duration_value, 2)}h x {base_rate}€/h"
        elif duration.unit == WorkUnit.DAYS:
            amount_base = (dec_duration * base_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            base_label = f"{round(duration_value, 1)}d x {base_rate}€/d"
        else:
            amount_base = base_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            base_label = f"Tarifa Fija ({base_rate}€)"

        # 3. Aplicacion de Suplementos / Extras
        active_options = options or {}
        extras_total = Decimal("0.00")
        applied_extras: List[DisplayLine] = []

        for extra_key, extra_obj in rate_definition.extras.items():
            if active_options.get(extra_key) is True:
                if extra_obj.per_unit:
                    extra_amt = (extra_obj.value * dec_duration).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                else:
                    extra_amt = extra_obj.value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                extras_total += extra_amt
                applied_extras.append(
                    DisplayLine(
                        type="extra",
                        label=f"Extra: {extra_key}",
                        value=float(extra_amt),
                    )
                )

        # 4. Impuestos y resolucion Bruto <-> Neto
        total_tax_rate = tax_configuration.total_tax_rate
        is_gross = rate_definition.is_gross

        if is_gross:
            gross_total = (amount_base + extras_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            net_total = (gross_total * (Decimal("1.0") - total_tax_rate)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            net_total = (amount_base + extras_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total_tax_rate < Decimal("1.0"):
                gross_total = (net_total / (Decimal("1.0") - total_tax_rate)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                gross_total = net_total

        # 5. Construccion de lineas para visualizacion del ticket
        display_lines: List[DisplayLine] = []

        display_lines.append(
            DisplayLine(
                type="income",
                label=base_label if is_gross else f"{base_label} (Neto)",
                value=float(amount_base),
            )
        )

        display_lines.extend(applied_extras)

        display_lines.append(
            DisplayLine(
                type="subtotal",
                label="Total Bruto",
                value=float(gross_total),
            )
        )

        if tax_configuration.social_security_rate > Decimal("0"):
            ss_val = (gross_total * tax_configuration.social_security_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            display_lines.append(
                DisplayLine(
                    type="tax",
                    code="ss",
                    label=f"Seguridad Social ({round(float(tax_configuration.social_security_rate * 100), 2)}%)",
                    value=-float(ss_val),
                )
            )

        if tax_configuration.irpf_rate > Decimal("0"):
            irpf_val = (gross_total * tax_configuration.irpf_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            display_lines.append(
                DisplayLine(
                    type="tax",
                    code="irpf",
                    label=f"IRPF ({round(float(tax_configuration.irpf_rate * 100), 2)}%)",
                    value=-float(irpf_val),
                )
            )

        if tax_configuration.extra_rate > Decimal("0"):
            extra_val = (gross_total * tax_configuration.extra_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            display_lines.append(
                DisplayLine(
                    type="tax",
                    code="extra",
                    label=f"Otros Impuestos ({round(float(tax_configuration.extra_rate * 100), 2)}%)",
                    value=-float(extra_val),
                )
            )

        display_lines.append(
            DisplayLine(
                type="total",
                label="Total Neto a Percibir",
                value=float(net_total),
            )
        )

        return CalculationSnapshot(
            gross_amount=gross_total,
            net_amount=net_total,
            rate_applied=base_rate,
            duration=duration_value,
            display_lines=display_lines,
            metadata={
                "unit": unit,
                "is_gross": is_gross,
                "tax_rates": {
                    "irpf": float(tax_configuration.irpf_rate),
                    "ss": float(tax_configuration.social_security_rate),
                    "extra": float(tax_configuration.extra_rate),
                },
            },
        )
