"""
Puerto de Repositorio para WorkLog.
Los puertos de Company y CompanyMember viven en company_repository_port.py.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from domain.entities.work_log import WorkLog


class WorkLogRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, log_id: str) -> Optional[WorkLog]:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def save(self, log: WorkLog) -> WorkLog:
        pass

    @abstractmethod
    async def save_bulk(self, logs: List[WorkLog]) -> List[WorkLog]:
        pass

    @abstractmethod
    async def delete(self, log_id: str) -> bool:
        pass
