/**
 * Value Object Money en el Frontend.
 * Inmutable, con redondeo exacto a 2 decimales para evitar anomalias de coma flotante.
 */
export class Money {
  private readonly _amount: number;

  constructor(amount: number | string | null | undefined) {
    if (amount === null || amount === undefined || amount === '') {
      this._amount = 0;
    } else {
      const num = typeof amount === 'string' ? parseFloat(amount) : amount;
      this._amount = isNaN(num) ? 0 : Math.round(num * 100) / 100;
    }
  }

  static zero(): Money {
    return new Money(0);
  }

  get amount(): number {
    return this._amount;
  }

  add(other: Money): Money {
    return new Money(this._amount + other._amount);
  }

  subtract(other: Money): Money {
    return new Money(this._amount - other._amount);
  }

  multiply(factor: number): Money {
    return new Money(this._amount * factor);
  }

  format(currency: string = '€', locale: string = 'es-ES'): string {
    return `${this._amount.toLocaleString(locale, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} ${currency}`;
  }
}
