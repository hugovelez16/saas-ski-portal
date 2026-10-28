"""Caso de uso: reordenar los miembros de una empresa (manager o PA; lo decide el router)."""

from typing import List

from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort


class ReorderMembersUseCase:
    def __init__(self, member_repo: CompanyMemberRepositoryPort):
        self.member_repo = member_repo

    async def execute(self, *, company_id: str, user_ids: List[str]) -> None:
        """`sort_order` pasa a ser la posicion en `user_ids`. Los ids que no son miembros se ignoran, como en v1."""
        await self.member_repo.reorder(company_id, user_ids)
