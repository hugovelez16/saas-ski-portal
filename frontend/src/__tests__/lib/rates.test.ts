import { describe, it, expect } from 'vitest';
import { mapMemberToLegacyRate } from '@/lib/utils/rates';

const ratesConfig = {
    particular: { base_rate: 30, is_gross: true, tax_overrides: { ss: 0.05, irpf: 0.1, extra: 0.02 } },
    tutorial: { base_rate: 12, is_gross: false, tax_overrides: {} },
};

describe('mapMemberToLegacyRate', () => {
    it('maps a full member including ids and user', () => {
        const user = { id: 'u-1', email: 'ana@b.c' };
        const result = mapMemberToLegacyRate({
            userId: 'u-1',
            companyId: 'c-1',
            user: user as any,
            ratesConfig,
        });

        expect(result.userId).toBe('u-1');
        expect(result.companyId).toBe('c-1');
        expect(result.user).toBe(user);
        expect(result.hourlyRate).toBe(12);
        expect(result.dailyRate).toBe(30);
        expect(result.nightRate).toBe(0);
        expect(result.coordinationRate).toBe(0);
    });

    it('accepts a partial object with only ratesConfig and returns empty ids', () => {
        const result = mapMemberToLegacyRate({ ratesConfig });

        expect(result.userId).toBe('');
        expect(result.companyId).toBe('');
        expect(result.user).toBeUndefined();
        expect(result.hourlyRate).toBe(12);
        expect(result.dailyRate).toBe(30);
    });

    it('returns zero rates when ratesConfig is null', () => {
        const result = mapMemberToLegacyRate({ ratesConfig: null });

        expect(result.hourlyRate).toBe(0);
        expect(result.dailyRate).toBe(0);
        expect(result.isGross).toBe(false);
        expect(result.deductionIrpf).toBe(0);
    });
});
