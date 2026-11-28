"""Puerto de repositorio para invitaciones de empresa (`company_invitations`)."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from domain.entities.company_invitation import CompanyInvitation


class CompanyInvitationRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, invitation_id: str, company_id: str) -> Optional[CompanyInvitation]:
        pass

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str, *, for_update: bool = False) -> Optional[CompanyInvitation]:
        pass

    @abstractmethod
    async def get_pending_by_company_and_email(self, company_id: str, email: str) -> Optional[CompanyInvitation]:
        pass

    @abstractmethod
    async def list_by_company(
        self,
        company_id: str,
        *,
        status: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> List[CompanyInvitation]:
        pass

    @abstractmethod
    async def save(self, invitation: CompanyInvitation, *, commit: bool = True) -> CompanyInvitation:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass
