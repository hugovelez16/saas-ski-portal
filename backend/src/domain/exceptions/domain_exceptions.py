"""
Excepciones de dominio para el negocio.
"""


class DomainException(Exception):
    """Excepcion base para todas las anomalias del dominio."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EntityNotFoundException(DomainException):
    """Lanzada cuando una entidad requerida no existe."""

    pass


class InvalidRateConfigurationException(DomainException):
    """Lanzada cuando la configuracion de tarifa o impuestos es invalida."""

    pass


class UnauthorizedDomainActionException(DomainException):
    """Lanzada cuando una operacion de dominio viola reglas de autorizacion o scope."""

    pass


class InactiveMembershipException(DomainException):
    """Lanzada cuando se intenta operar con una membresia inactiva."""

    pass


class ModuleAccessDeniedException(DomainException):
    """Lanzada cuando no se cuenta con una suscripcion activa para el modulo."""

    pass


class ConflictException(DomainException):
    """Lanzada cuando la operacion choca con el estado actual (p. ej. duplicados o dependencias)."""

    pass


class ValidationDomainException(DomainException):
    """Lanzada cuando los datos de entrada no cumplen las reglas de dominio."""

    pass
