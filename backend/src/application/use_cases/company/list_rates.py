"""Caso de uso: tarifas de la empresa (manager o PA; lo decide el router). Sustituye a `GET .../rates-v2` de v1 (X3)."""

from typing import List

from application.use_cases.company.common import MemberDetail
from application.use_cases.company.list_members import ListMembersUseCase


class ListRatesUseCase:
    def __init__(self, list_members: ListMembersUseCase):
        self.list_members = list_members

    async def execute(self, *, company_id: str) -> List[MemberDetail]:
        """Las tarifas viven en la membresia: devuelve todos los miembros, activos e inactivos, como v1."""
        return await self.list_members.execute(company_id=company_id, is_active=None)
