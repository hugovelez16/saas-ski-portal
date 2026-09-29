"""
Value Object Money: Manejo inmutable y de precision para importes monetarios.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Union


@dataclass(frozen=True)
class Money:
    """Objeto de valor inmutable para representar montos monetarios."""
    amount: Decimal

    @classmethod
    def from_float_or_str(cls, value: Union[float, int, str, Decimal, None]) -> "Money":
        if value is None or value == "":
            return cls(Decimal("0.00"))
        if isinstance(value, Decimal):
            return cls(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return cls(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @classmethod
    def zero(cls) -> "Money":
        return cls(Decimal("0.00"))

    def to_float(self) -> float:
        return float(self.amount)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            raise TypeError("Operacion solo permitida entre instancias de Money")
        return Money((self.amount + other.amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            raise TypeError("Operacion solo permitida entre instancias de Money")
        return Money((self.amount - other.amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def __mul__(self, factor: Union[int, float, Decimal]) -> "Money":
        dec_factor = Decimal(str(factor))
        return Money((self.amount * dec_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def __truediv__(self, divisor: Union[int, float, Decimal]) -> "Money":
        dec_divisor = Decimal(str(divisor))
        if dec_divisor == Decimal("0"):
            raise ZeroDivisionError("No se puede dividir Money entre cero")
        return Money((self.amount / dec_divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def __repr__(self) -> str:
        return f"Money({self.amount})"
