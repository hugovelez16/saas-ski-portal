"""
Puerto de Repositorio para la Entidad User.
Define el contrato abstracto de persistencia independiente del ORM o motor de base de datos.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities.user import User


class UserRepositoryPort(ABC):

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        pass

    @abstractmethod
    async def update_status(self, user_id: str, is_active: bool) -> Optional[User]:
        pass
