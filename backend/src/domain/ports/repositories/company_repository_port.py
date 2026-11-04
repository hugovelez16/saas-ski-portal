"""
Puertos de Repositorio para Company y CompanyMember.
Contratos abstractos de persistencia; todos los metodos son async.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from domain.entities.company import Company
from domain.entities.company_member import CompanyMember


class CompanyRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, company_id: str) -> Optional[Company]:
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Company]:
        pass

    @abstractmethod
    async def list_companies(self, *, skip: int = 0, limit: int = 100) -> List[Company]:
        pass

    @abstractmethod
    async def count_companies(self) -> int:
        pass

    @abstractmethod
    async def save(self, company: Company) -> Company:
        pass

    @abstractmethod
    async def delete(self, company_id: str) -> None:
        pass

    @abstractmethod
    async def count_dependencies(self, company_id: str) -> Dict[str, int]:
        """Devuelve las claves: members, work_logs, subscriptions."""
        pass


class CompanyMemberRepositoryPort(ABC):
    @abstractmethod
    async def get_membership(
        self, user_id: str, company_id: str, *, for_update: bool = False
    ) -> Optional[CompanyMember]:
        """`for_update=True` bloquea la fila hasta el fin de la transaccion (borrado de membresia)."""
        pass

    @abstractmethod
    async def list_members_by_company(self, company_id: str, is_active: Optional[bool] = None) -> List[CompanyMember]:
        pass

    @abstractmethod
    async def list_companies_by_user(self, user_id: str) -> List[CompanyMember]:
        pass

    @abstractmethod
    async def save(self, member: CompanyMember) -> CompanyMember:
        pass

    @abstractmethod
    async def delete(self, user_id: str, company_id: str) -> None:
        pass

    @abstractmethod
    async def reorder(self, company_id: str, user_ids: List[str]) -> None:
        """Fija `sort_order` = posicion en `user_ids` para los miembros de la empresa; ignora los ajenos."""
        pass

    @abstractmethod
    async def count_work_logs(self, user_id: str, company_id: str) -> int:
        pass
