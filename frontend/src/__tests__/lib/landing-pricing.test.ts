import { describe, it, expect } from 'vitest';
import {
    PLANS,
    quote,
    cheapestPlan,
    getPlan,
    formatEuros,
    formatEurosCompact,
} from '@/lib/landing-pricing';

// Tarifas: Basico 129 + 9 por monitor sobre 10; Escuela 249 + 7 por monitor sobre 25;
// Grande 399 fijo; responsable adicional 50 en Basico y Escuela. Extras (5 y 15) solo en Basico.
// Basico(n) = 39 + 9n para n > 10; Escuela(n) = 74 + 7n para n > 25.

describe('quote', () => {
    it('basico con 10 monitores cuesta la cuota base', () => {
        expect(quote({ planId: 'basico', monitors: 10 })).toMatchObject({
            base: 129,
            extraMonitors: 0,
            extraMonitorsCost: 0,
            extraManagersCost: 0,
            extras: 0,
            monthly: 129,
            season: 645,
            firstSeason: 795,
        });
    });

    it('basico con 11 monitores anade un monitor adicional de 9', () => {
        expect(quote({ planId: 'basico', monitors: 11 })).toMatchObject({
            extraMonitors: 1,
            extraMonitorsCost: 9,
            monthly: 138,
            season: 690,
            firstSeason: 840,
        });
    });

    it('basico con 11 monitores, cuadrante y informes suma 20 de extras', () => {
        expect(
            quote({ planId: 'basico', monitors: 11, sharedSchedule: true, reports: true }),
        ).toMatchObject({ extras: 20, monthly: 158 });
    });

    it('basico con 10 monitores solo con informes suma 15', () => {
        expect(quote({ planId: 'basico', monitors: 10, reports: true })).toMatchObject({
            extras: 15,
            monthly: 144,
        });
    });

    it('basico con 10 monitores solo con cuadrante suma 5', () => {
        expect(quote({ planId: 'basico', monitors: 10, sharedSchedule: true })).toMatchObject({
            extras: 5,
            monthly: 134,
        });
    });

    it('basico con 25 monitores cobra 15 monitores adicionales', () => {
        expect(quote({ planId: 'basico', monitors: 25 })).toMatchObject({
            extraMonitors: 15,
            extraMonitorsCost: 135,
            monthly: 264,
        });
    });

    it('escuela con 25 monitores no tiene monitores adicionales', () => {
        expect(quote({ planId: 'escuela', monitors: 25 })).toMatchObject({
            extraMonitors: 0,
            monthly: 249,
            season: 1245,
            firstSeason: 1395,
        });
    });

    it('escuela con 26 monitores anade uno adicional de 7', () => {
        expect(quote({ planId: 'escuela', monitors: 26 })).toMatchObject({
            extraMonitors: 1,
            extraMonitorsCost: 7,
            monthly: 256,
            season: 1280,
            firstSeason: 1430,
        });
    });

    it('escuela con 25 monitores e incluye cuadrante e informes sin coste extra', () => {
        expect(
            quote({ planId: 'escuela', monitors: 25, sharedSchedule: true, reports: true }),
        ).toMatchObject({ extras: 0, monthly: 249 });
    });

    it('escuela con 50 monitores', () => {
        expect(quote({ planId: 'escuela', monitors: 50 })).toMatchObject({
            extraMonitors: 25,
            extraMonitorsCost: 175,
            monthly: 424,
            season: 2120,
            firstSeason: 2270,
        });
    });

    it('grande no cobra monitores adicionales hasta 50', () => {
        expect(quote({ planId: 'grande', monitors: 26 })).toMatchObject({ monthly: 399 });
        expect(quote({ planId: 'grande', monitors: 50 })).toMatchObject({
            extraMonitors: 0,
            monthly: 399,
            season: 1995,
            firstSeason: 2145,
        });
    });

    it('basico con 2 responsables adicionales cobra 100 extra', () => {
        expect(quote({ planId: 'basico', monitors: 10, extraManagers: 2 })).toMatchObject({
            extraManagers: 2,
            extraManagersCost: 100,
            monthly: 229,
            season: 1145,
            firstSeason: 1295,
        });
    });

    it('escuela con 1 responsable adicional cobra 50 extra', () => {
        expect(quote({ planId: 'escuela', monitors: 25, extraManagers: 1 })).toMatchObject({
            monthly: 299,
        });
    });

    it('grande ignora los responsables adicionales', () => {
        expect(quote({ planId: 'grande', monitors: 25, extraManagers: 3 })).toMatchObject({
            extraManagers: 0,
            extraManagersCost: 0,
            monthly: 399,
        });
    });

    it('normaliza los responsables adicionales: negativos y NaN son 0, decimales se truncan', () => {
        expect(quote({ planId: 'basico', monitors: 10, extraManagers: -1 })?.monthly).toBe(129);
        expect(quote({ planId: 'basico', monitors: 10, extraManagers: NaN })?.monthly).toBe(129);
        expect(quote({ planId: 'basico', monitors: 10, extraManagers: 2.9 })).toMatchObject({
            extraManagers: 2,
            monthly: 229,
        });
    });

    it('devuelve null con 51 o 100 monitores', () => {
        for (const planId of ['basico', 'escuela', 'grande'] as const) {
            expect(quote({ planId, monitors: 51 })).toBeNull();
            expect(quote({ planId, monitors: 100 })).toBeNull();
        }
    });

    it('trunca los monitores decimales: 10.9 equivale a 10', () => {
        expect(quote({ planId: 'basico', monitors: 10.9 })).toMatchObject({
            extraMonitors: 0,
            monthly: 129,
        });
    });

    it('trata 0, negativos y NaN como 0 monitores', () => {
        for (const monitors of [0, -5, NaN]) {
            expect(quote({ planId: 'basico', monitors })).toMatchObject({
                extraMonitors: 0,
                monthly: 129,
            });
        }
    });
});

describe('cheapestPlan', () => {
    it('sin extras, cruza de basico a escuela y de escuela a grande en los umbrales', () => {
        expect(cheapestPlan(10)).toBe('basico');
        expect(cheapestPlan(11)).toBe('basico');
        expect(cheapestPlan(23)).toBe('basico');
        expect(cheapestPlan(24)).toBe('escuela');
        expect(cheapestPlan(25)).toBe('escuela');
        expect(cheapestPlan(26)).toBe('escuela');
        expect(cheapestPlan(46)).toBe('escuela');
        expect(cheapestPlan(47)).toBe('grande');
        expect(cheapestPlan(50)).toBe('grande');
    });

    it('devuelve null con mas de 50 monitores', () => {
        expect(cheapestPlan(51)).toBeNull();
    });

    it('basico con cuadrante e informes (base 149) cruza mas pronto', () => {
        const extras = { sharedSchedule: true, reports: true };
        expect(cheapestPlan(10, extras)).toBe('basico');
        expect(cheapestPlan(21, extras)).toBe('basico');
        expect(cheapestPlan(22, extras)).toBe('escuela');
        expect(cheapestPlan(46, extras)).toBe('escuela');
        expect(cheapestPlan(47, extras)).toBe('grande');
    });

    it('solo informes (+15): basico hasta 21 y escuela desde 22', () => {
        expect(cheapestPlan(21, { reports: true })).toBe('basico');
        expect(cheapestPlan(22, { reports: true })).toBe('escuela');
    });

    it('solo cuadrante (+5): basico hasta 22 y escuela desde 23', () => {
        expect(cheapestPlan(22, { sharedSchedule: true })).toBe('basico');
        expect(cheapestPlan(23, { sharedSchedule: true })).toBe('escuela');
    });

    it('con responsables adicionales, el plan mas barato cambia', () => {
        expect(cheapestPlan(10, { extraManagers: 2 })).toBe('basico');
        expect(cheapestPlan(23, { extraManagers: 1 })).toBe('basico');
        expect(cheapestPlan(24, { extraManagers: 1 })).toBe('escuela');
        expect(cheapestPlan(40, { extraManagers: 2 })).toBe('grande');
    });
});

describe('PLANS y getPlan', () => {
    it('lista los tres planes en orden', () => {
        expect(PLANS.map((p) => p.id)).toEqual(['basico', 'escuela', 'grande']);
    });

    it('solo escuela esta marcado como recomendado', () => {
        const recommended = PLANS.filter((p) => p.recommended).map((p) => p.id);
        expect(recommended).toEqual(['escuela']);
    });

    it('getPlan devuelve el plan pedido', () => {
        expect(getPlan('escuela').includedMonitors).toBe(25);
    });

    it('getPlan lanza error con un id desconocido', () => {
        expect(() => getPlan('x' as never)).toThrow();
    });
});

describe('formatEuros', () => {
    it('usa formato espanol con miles y dos decimales', () => {
        expect(formatEuros(1268.75)).toBe('1.268,75 €');
        expect(formatEuros(73.75)).toBe('73,75 €');
        expect(formatEuros(1245)).toBe('1.245,00 €');
        expect(formatEuros(645)).toBe('645,00 €');
    });
});

describe('formatEurosCompact', () => {
    it('omite decimales en importes enteros', () => {
        expect(formatEurosCompact(129)).toBe('129 €');
        expect(formatEurosCompact(1245)).toBe('1.245 €');
    });

    it('usa formatEuros cuando el importe no es entero', () => {
        expect(formatEurosCompact(6.5)).toBe('6,50 €');
    });
});
