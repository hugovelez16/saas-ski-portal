"""
Mapeador de persistencia para WorkLog entre SQLAlchemy ORM y Entidades de Dominio.
"""

from decimal import Decimal

import models
from domain.entities.work_log import WorkLog
from domain.value_objects.calculation_snapshot import CalculationSnapshot, DisplayLine
from domain.value_objects.money import Money


class SqlAlchemyWorkLogMapper:
    @staticmethod
    def to_domain(orm_log: models.WorkLog) -> WorkLog:
        snapshot_obj = None
        if orm_log.calculation_snapshot and isinstance(orm_log.calculation_snapshot, dict):
            raw_lines = orm_log.calculation_snapshot.get("lines", [])
            lines = [
                DisplayLine(
                    type=line.get("type", "item"),
                    label=line.get("label", ""),
                    value=float(line.get("value", 0.0)),
                    code=line.get("code", ""),
                )
                for line in raw_lines
            ]
            snapshot_obj = CalculationSnapshot(
                gross_amount=Decimal(str(orm_log.gross_amount or 0.0)),
                net_amount=Decimal(str(orm_log.net_amount or 0.0)),
                rate_applied=Decimal("0.00"),
                duration=float(orm_log.duration or 0.0),
                display_lines=lines,
                metadata=orm_log.calculation_snapshot.get("metadata", {}),
            )

        return WorkLog(
            id=str(orm_log.id),
            user_id=str(orm_log.user_id),
            company_id=str(orm_log.company_id),
            type=orm_log.type,
            start_date=orm_log.start_date,
            end_date=orm_log.end_date,
            start_time=orm_log.start_time,
            end_time=orm_log.end_time,
            duration_hours=float(orm_log.duration) if orm_log.duration is not None else None,
            description=orm_log.description,
            gross_amount=Money.from_float_or_str(orm_log.gross_amount),
            net_amount=Money.from_float_or_str(orm_log.net_amount),
            extra_data=orm_log.extra_data or {},
            calculation_snapshot=snapshot_obj,
            created_at=orm_log.created_at,
            updated_at=orm_log.updated_at,
        )

    @staticmethod
    def to_orm(domain_log: WorkLog) -> models.WorkLog:
        snapshot_dict = domain_log.calculation_snapshot.to_dict() if domain_log.calculation_snapshot else None
        return models.WorkLog(
            id=domain_log.id,
            user_id=domain_log.user_id,
            company_id=domain_log.company_id,
            type=domain_log.type,
            start_date=domain_log.start_date,
            end_date=domain_log.end_date or domain_log.start_date,
            start_time=domain_log.start_time,
            end_time=domain_log.end_time,
            duration=domain_log.duration_hours,
            description=domain_log.description,
            gross_amount=domain_log.gross_amount.to_float(),
            net_amount=domain_log.net_amount.to_float(),
            extra_data=domain_log.extra_data,
            calculation_snapshot=snapshot_dict,
        )
