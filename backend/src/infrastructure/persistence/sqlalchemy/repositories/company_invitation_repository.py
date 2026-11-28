"""Repositorio SQLAlchemy para `company_invitations`."""

from datetime import UTC, datetime
from typing import List, Optional

import models
from domain.entities.company_invitation import CompanyInvitation, ensure_utc, normalize_invitation_email
from domain.ports.repositories.company_invitation_repository_port import CompanyInvitationRepositoryPort
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class SqlAlchemyCompanyInvitationMapper:
    @staticmethod
    def to_domain(orm: models.CompanyInvitation) -> CompanyInvitation:
        return CompanyInvitation(
            id=str(orm.id),
            company_id=str(orm.company_id),
            email=orm.email,
            token_hash=orm.token_hash,
            invited_by_user_id=str(orm.invited_by_user_id),
            expires_at=ensure_utc(orm.expires_at),
            accepted_at=ensure_utc(orm.accepted_at) if orm.accepted_at is not None else None,
            accepted_by_user_id=str(orm.accepted_by_user_id) if orm.accepted_by_user_id is not None else None,
            cancelled_at=ensure_utc(orm.cancelled_at) if orm.cancelled_at is not None else None,
            created_at=ensure_utc(orm.created_at) if orm.created_at is not None else None,
            updated_at=ensure_utc(orm.updated_at) if orm.updated_at is not None else None,
        )

    @staticmethod
    def to_orm(entity: CompanyInvitation) -> models.CompanyInvitation:
        kwargs = {
            "id": entity.id,
            "company_id": entity.company_id,
            "email": normalize_invitation_email(entity.email),
            "token_hash": entity.token_hash,
            "invited_by_user_id": entity.invited_by_user_id,
            "expires_at": ensure_utc(entity.expires_at),
            "accepted_at": ensure_utc(entity.accepted_at) if entity.accepted_at is not None else None,
            "accepted_by_user_id": entity.accepted_by_user_id,
            "cancelled_at": ensure_utc(entity.cancelled_at) if entity.cancelled_at is not None else None,
        }
        if entity.created_at is not None:
            kwargs["created_at"] = ensure_utc(entity.created_at)
        if entity.updated_at is not None:
            kwargs["updated_at"] = ensure_utc(entity.updated_at)
        return models.CompanyInvitation(**kwargs)


class SqlAlchemyCompanyInvitationRepository(CompanyInvitationRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    async def get_by_id(self, invitation_id: str, company_id: str) -> Optional[CompanyInvitation]:
        orm = (
            self.db.query(models.CompanyInvitation)
            .filter(
                models.CompanyInvitation.id == invitation_id,
                models.CompanyInvitation.company_id == company_id,
            )
            .first()
        )
        return SqlAlchemyCompanyInvitationMapper.to_domain(orm) if orm else None

    async def get_by_token_hash(self, token_hash: str, *, for_update: bool = False) -> Optional[CompanyInvitation]:
        query = self.db.query(models.CompanyInvitation).filter(models.CompanyInvitation.token_hash == token_hash)
        if for_update:
            query = query.with_for_update().populate_existing()
        orm = query.first()
        return SqlAlchemyCompanyInvitationMapper.to_domain(orm) if orm else None

    async def get_pending_by_company_and_email(self, company_id: str, email: str) -> Optional[CompanyInvitation]:
        normalized = normalize_invitation_email(email)
        orm = (
            self.db.query(models.CompanyInvitation)
            .filter(
                models.CompanyInvitation.company_id == company_id,
                func.lower(models.CompanyInvitation.email) == normalized,
                models.CompanyInvitation.accepted_at.is_(None),
                models.CompanyInvitation.cancelled_at.is_(None),
            )
            .first()
        )
        return SqlAlchemyCompanyInvitationMapper.to_domain(orm) if orm else None

    async def list_by_company(
        self,
        company_id: str,
        *,
        status: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> List[CompanyInvitation]:
        ref = ensure_utc(now) if now is not None else datetime.now(UTC)
        query = self.db.query(models.CompanyInvitation).filter(models.CompanyInvitation.company_id == company_id)

        if status is None:
            query = query.filter(
                models.CompanyInvitation.accepted_at.is_(None),
                models.CompanyInvitation.cancelled_at.is_(None),
            )
        elif status == "pending":
            query = query.filter(
                models.CompanyInvitation.accepted_at.is_(None),
                models.CompanyInvitation.cancelled_at.is_(None),
                models.CompanyInvitation.expires_at > ref,
            )
        elif status == "expired":
            query = query.filter(
                models.CompanyInvitation.accepted_at.is_(None),
                models.CompanyInvitation.cancelled_at.is_(None),
                models.CompanyInvitation.expires_at <= ref,
            )
        elif status == "accepted":
            query = query.filter(models.CompanyInvitation.accepted_at.is_not(None))
        elif status == "cancelled":
            query = query.filter(models.CompanyInvitation.cancelled_at.is_not(None))

        rows = query.order_by(models.CompanyInvitation.created_at.desc(), models.CompanyInvitation.id.desc()).all()
        return [SqlAlchemyCompanyInvitationMapper.to_domain(row) for row in rows]

    async def save(self, invitation: CompanyInvitation, *, commit: bool = True) -> CompanyInvitation:
        existing = (
            self.db.query(models.CompanyInvitation)
            .filter(models.CompanyInvitation.id == invitation.id)
            .first()
        )
        try:
            if existing:
                existing.email = normalize_invitation_email(invitation.email)
                existing.token_hash = invitation.token_hash
                existing.invited_by_user_id = invitation.invited_by_user_id
                existing.expires_at = ensure_utc(invitation.expires_at)
                existing.accepted_at = (
                    ensure_utc(invitation.accepted_at) if invitation.accepted_at is not None else None
                )
                existing.accepted_by_user_id = invitation.accepted_by_user_id
                existing.cancelled_at = (
                    ensure_utc(invitation.cancelled_at) if invitation.cancelled_at is not None else None
                )
                target = existing
            else:
                target = SqlAlchemyCompanyInvitationMapper.to_orm(invitation)
                self.db.add(target)

            if commit:
                self.db.commit()
                self.db.refresh(target)
            else:
                self.db.flush()
                self.db.refresh(target)
            return SqlAlchemyCompanyInvitationMapper.to_domain(target)
        except SQLAlchemyError:
            self.db.rollback()
            raise

    async def commit(self) -> None:
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    async def rollback(self) -> None:
        self.db.rollback()
