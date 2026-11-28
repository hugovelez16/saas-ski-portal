"""Piezas compartidas de los casos de uso de invitaciones (R-MEM-07, R-MEM-23 a R-MEM-25)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Optional

import email_utils
from domain.entities.company_invitation import CompanyInvitation
from domain.exceptions.domain_exceptions import (
    ConflictException,
    EntityNotFoundException,
    ValidationDomainException,
)

MSG_INVITATION_NOT_FOUND = "Invitacion no encontrada"
MSG_INVITATION_LINK_INVALID = "Invitacion no encontrada o enlace no valido"
MSG_INVITATION_WRONG_EMAIL = "Esta invitacion es para otro correo"
MSG_INVITATION_EXPIRED = "Esta invitacion ha caducado"
MSG_INVITATION_USED = "Esta invitacion ya ha sido utilizada"
MSG_INVITATION_CANCELLED = "Esta invitacion ha sido cancelada"


class InvitationEmailDeliveryError(Exception):
    """Error al enviar el correo de invitacion tras registrar la invitacion en la transaccion."""


EmailSenderFn = Callable[..., Awaitable[None]]


async def default_email_sender(
    *, email: str, company_name: str, inviter_name: str, token: str
) -> None:
    await email_utils.send_company_invitation_email(
        email,
        company_name=company_name,
        inviter_name=inviter_name,
        token=token,
    )


@dataclass(frozen=True)
class InvitationView:
    invitation: CompanyInvitation
    invited_by_name: Optional[str] = None


def resolve_inviter_name(user) -> str:
    if user is None:
        return "Un responsable"
    return user.full_name or user.email


def validate_active_invitation(invitation: Optional[CompanyInvitation], *, now: datetime) -> CompanyInvitation:
    if invitation is None:
        raise EntityNotFoundException(MSG_INVITATION_LINK_INVALID)
    if invitation.cancelled_at is not None:
        raise ConflictException(MSG_INVITATION_CANCELLED)
    if invitation.accepted_at is not None:
        raise ConflictException(MSG_INVITATION_USED)
    if invitation.is_expired(now):
        raise ValidationDomainException(MSG_INVITATION_EXPIRED)
    return invitation
