"""
Implementacion de WorkLogRepositoryPort utilizando SQLAlchemy.
"""
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session
from domain.entities.work_log import WorkLog
from domain.ports.repositories.work_log_repository_port import WorkLogRepositoryPort
from infrastructure.persistence.sqlalchemy.mappers.work_log_mapper import SqlAlchemyWorkLogMapper
import models


class SqlAlchemyWorkLogRepository(WorkLogRepositoryPort):

    def __init__(self, db: Session):
        self.db = db

    async def get_by_id(self, log_id: str) -> Optional[WorkLog]:
        orm_log = self.db.query(models.WorkLog).filter(models.WorkLog.id == log_id).first()
        return SqlAlchemyWorkLogMapper.to_domain(orm_log) if orm_log else None

    async def list_logs(
        self,
        company_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        log_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkLog]:
        query = self.db.query(models.WorkLog)
        if company_id:
            query = query.filter(models.WorkLog.company_id == company_id)
        if user_id:
            query = query.filter(models.WorkLog.user_id == user_id)
        if start_date:
            query = query.filter(models.WorkLog.start_date >= start_date)
        if end_date:
            query = query.filter(models.WorkLog.start_date <= end_date)
        if log_type:
            query = query.filter(models.WorkLog.type == log_type)

        orm_logs = query.order_by(models.WorkLog.start_date.desc(), models.WorkLog.start_time.desc()).offset(skip).limit(limit).all()
        return [SqlAlchemyWorkLogMapper.to_domain(log) for log in orm_logs]

    async def save(self, log: WorkLog) -> WorkLog:
        existing = self.db.query(models.WorkLog).filter(models.WorkLog.id == log.id).first()
        if existing:
            # Actualizacion
            existing.type = log.type
            existing.start_date = log.start_date
            existing.end_date = log.end_date
            existing.start_time = log.start_time
            existing.end_time = log.end_time
            existing.duration_hours = log.duration_hours
            existing.description = log.description
            existing.gross_amount = log.gross_amount.to_float()
            existing.net_amount = log.net_amount.to_float()
            existing.extra_data = log.extra_data
            if log.calculation_snapshot:
                existing.calculation_snapshot = log.calculation_snapshot.to_dict()
            self.db.commit()
            self.db.refresh(existing)
            return SqlAlchemyWorkLogMapper.to_domain(existing)
        else:
            # Creacion
            orm_log = SqlAlchemyWorkLogMapper.to_orm(log)
            self.db.add(orm_log)
            self.db.commit()
            self.db.refresh(orm_log)
            return SqlAlchemyWorkLogMapper.to_domain(orm_log)

    async def save_bulk(self, logs: List[WorkLog]) -> List[WorkLog]:
        orm_logs = [SqlAlchemyWorkLogMapper.to_orm(log) for log in logs]
        self.db.add_all(orm_logs)
        self.db.commit()
        for log in orm_logs:
            self.db.refresh(log)
        return [SqlAlchemyWorkLogMapper.to_domain(log) for log in orm_logs]

    async def delete(self, log_id: str) -> bool:
        orm_log = self.db.query(models.WorkLog).filter(models.WorkLog.id == log_id).first()
        if orm_log:
            self.db.delete(orm_log)
            self.db.commit()
            return True
        return False
