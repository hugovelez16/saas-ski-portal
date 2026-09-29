"""
Caso de Uso: Creacion y Liquidacion de Jornada / WorkLog.
Orquesta reglas de aplicacion y negocio sin depender de frameworks web ni ORMs.
"""
import uuid
from datetime import date, time, datetime, timezone
from typing import Optional, Dict, Any
from domain.entities.work_log import WorkLog
from domain.value_objects.money import Money
from domain.value_objects.work_duration import WorkDuration, WorkUnit
from domain.value_objects.tax_configuration import TaxConfiguration
from domain.value_objects.rate_definition import RateDefinition
from domain.services.work_log_calculation_service import WorkLogCalculationService
from domain.ports.repositories.work_log_repository_port import WorkLogRepositoryPort, CompanyRepositoryPort, CompanyMemberRepositoryPort
from domain.exceptions.domain_exceptions import EntityNotFoundException, InactiveMembershipException


class CreateWorkLogUseCase:

    def __init__(
        self,
        work_log_repo: WorkLogRepositoryPort,
        company_repo: CompanyRepositoryPort,
        member_repo: CompanyMemberRepositoryPort,
    ):
        self.work_log_repo = work_log_repo
        self.company_repo = company_repo
        self.member_repo = member_repo

    async def execute(
        self,
        user_id: str,
        company_id: str,
        log_type: str,
        start_date: date,
        end_date: Optional[date] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        duration_hours: Optional[float] = None,
        description: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        manual_amount: Optional[float] = None,
    ) -> WorkLog:
        # 1. Validar membresia
        member = await self.member_repo.get_membership(user_id=user_id, company_id=company_id)
        if not member or not member.is_active:
            raise InactiveMembershipException("El usuario no tiene una membresia activa en la empresa indicada")

        # 2. Obtener configuraciones de empresa
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise EntityNotFoundException("Empresa no encontrada")

        company_defs = company.worklog_definitions or {}
        type_def = company_defs.get(log_type, {})

        # Determinar unidad de trabajo
        unit_str = type_def.get("unit")
        if not unit_str:
            unit_str = "days" if type_def.get("is_range") else "hours"

        work_unit = WorkUnit(unit_str) if unit_str in ("hours", "days", "fixed") else WorkUnit.HOURS

        # 3. Calcular duracion
        duration = WorkDuration.calculate(
            unit=work_unit,
            duration_hours=duration_hours,
            start_time=start_time,
            end_time=end_time,
            start_date=start_date,
            end_date=end_date,
        )

        # 4. Extraer definiciones de tarifas e impuestos
        rates_config = member.rates_config or {}
        user_rate_dict = rates_config.get(log_type, {})
        rate_definition = RateDefinition.from_dict(user_rate_dict)
        tax_config = TaxConfiguration.from_dict(
            company_tax_config=company.tax_config,
            user_tax_overrides=rate_definition.tax_overrides,
        )

        # Extraer opciones adicionales de extra_data
        extras_payload = extra_data or {}
        options = extras_payload.get("opciones", {})

        manual_money = Money.from_float_or_str(manual_amount) if manual_amount is not None else None

        # 5. Ejecutar servicio de dominio de calculo
        snapshot = WorkLogCalculationService.calculate(
            duration=duration,
            rate_definition=rate_definition,
            tax_configuration=tax_config,
            options=options,
            manual_net_amount=manual_money.amount if manual_money else None,
        )

        # 6. Crear y persistir entidad
        work_log = WorkLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            company_id=company_id,
            type=log_type,
            start_date=start_date,
            end_date=end_date or start_date,
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration.value if duration.unit == WorkUnit.HOURS else None,
            description=description,
            gross_amount=Money(snapshot.gross_amount),
            net_amount=Money(snapshot.net_amount),
            extra_data=extras_payload,
            calculation_snapshot=snapshot,
            created_at=datetime.now(timezone.utc),
        )

        return await self.work_log_repo.save(work_log)
