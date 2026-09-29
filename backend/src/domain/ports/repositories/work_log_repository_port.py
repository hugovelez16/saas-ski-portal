"""
Puertos de Repositorio para Company, CompanyMember y WorkLog.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date
from domain.entities.company import Company
from domain.entities.company_member import CompanyMember
from domain.entities.work_log import WorkLog


class CompanyRepositoryPort(ABC):

    @abstractmethod
    async def get_by_id(self, company_id: str) -> Optional[Company]:
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Company]:
        pass

    @abstractmethod
    async def list_companies(self) -> List[Company]:
        pass

    @abstractmethod
    async def save(self, company: Company) -> Company:
        pass


class CompanyMemberRepositoryPort(ABC):

    @abstractmethod
    async def get_membership(self, user_id: str, company_id: str) -> Optional[CompanyMember]:
        pass

    @abstractmethod
    async def list_members_by_company(self, company_id: str) -> List[CompanyMember]:
        pass

    @abstractmethod
    async def list_companies_by_user(self, user_id: str) -> List[CompanyMember]:
        pass

    @abstractmethod
    async def save(self, member: CompanyMember) -> CompanyMember:
        pass


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
