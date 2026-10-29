import { describe, it, expect } from 'vitest';
import { formatEuros, monitorsMonthlyCost, quote } from '@/lib/landing-pricing';

// Valores esperados tomados de los ejemplos de calculo de la propuesta comercial.
describe('monitorsMonthlyCost', () => {
    it('charges 5,00 per monitor in the first tier', () => {
        expect(monitorsMonthlyCost(10)).toBe(50);
    });

    it('applies tiers marginally: 15 monitors are 10 x 5,00 + 5 x 4,75', () => {
        expect(monitorsMonthlyCost(15)).toBeCloseTo(73.75);
    });

    it('matches the proposal for 20 and 30 monitors', () => {
        expect(monitorsMonthlyCost(20)).toBeCloseTo(97.5);
        expect(monitorsMonthlyCost(30)).toBeCloseTo(142.5);
    });

    it('prices the whole scale up to 50 monitors', () => {
        expect(monitorsMonthlyCost(50)).toBeCloseTo(50 + 47.5 + 45 + 42.5 + 40);
    });

    it('costs nothing without monitors', () => {
        expect(monitorsMonthlyCost(0)).toBe(0);
    });
});

describe('quote', () => {
    it('matches the proposal totals with one manager and no modules', () => {
        expect(quote({ monitors: 15 })).toMatchObject({ monthly: 223.75, season: 1118.75, firstSeason: 1268.75 });
        expect(quote({ monitors: 20 })).toMatchObject({ monthly: 247.5, season: 1237.5, firstSeason: 1387.5 });
        expect(quote({ monitors: 30 })).toMatchObject({ monthly: 292.5, season: 1462.5, firstSeason: 1612.5 });
    });

    it('adds 15 for reports and 5 for the team daily report', () => {
        const q = quote({ monitors: 10, reports: true, teamDailyReport: true });
        expect(q.modules).toBe(20);
        expect(q.monthly).toBe(150 + 50 + 20);
    });

    it('adds 50 per extra manager account', () => {
        expect(quote({ monitors: 10, extraManagers: 2 }).monthly).toBe(150 + 50 + 100);
    });
});

describe('formatEuros', () => {
    it('uses Spanish number format with two decimals', () => {
        expect(formatEuros(1268.75)).toBe('1.268,75 €');
        expect(formatEuros(73.75)).toBe('73,75 €');
    });
});
