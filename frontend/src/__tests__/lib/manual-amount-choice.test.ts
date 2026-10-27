import { describe, it, expect } from 'vitest';
import { getManualAmountChoice } from '@/lib/manual-amount-choice';

const httpError = (status: number, data: unknown) => ({ response: { status, data } });

describe('getManualAmountChoice', () => {
    it('returns the backend message for a 409 manual_amount_choice', () => {
        const error = httpError(409, {
            detail: { code: 'manual_amount_choice', message: 'El turno tiene importe manual.' },
        });

        expect(getManualAmountChoice(error)).toEqual({ message: 'El turno tiene importe manual.' });
    });

    it('returns null for a 409 with another code', () => {
        const error = httpError(409, { detail: { code: 'overlap', message: 'Solapado.' } });

        expect(getManualAmountChoice(error)).toBeNull();
    });

    it('returns null for a 409 whose detail is a plain string', () => {
        const error = httpError(409, { detail: 'Conflicto' });

        expect(getManualAmountChoice(error)).toBeNull();
    });

    it('returns null for another status with the same detail', () => {
        const error = httpError(422, {
            detail: { code: 'manual_amount_choice', message: 'Importe manual.' },
        });

        expect(getManualAmountChoice(error)).toBeNull();
    });

    it('returns null when the error has no response', () => {
        expect(getManualAmountChoice(new Error('Network Error'))).toBeNull();
        expect(getManualAmountChoice(undefined)).toBeNull();
        expect(getManualAmountChoice(null)).toBeNull();
    });

    it('returns null when the response has no data', () => {
        expect(getManualAmountChoice({ response: { status: 409 } })).toBeNull();
    });
});
