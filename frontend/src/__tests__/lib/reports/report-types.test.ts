import { describe, it, expect } from 'vitest';
import type { WorkLogSummary } from '@/lib/types';
import {
    resolveUnit,
    resolveLabel,
    buildTypeBlocks,
    blockQuantityText,
    netByMonth,
} from '@/lib/reports/report-types';
import { generateTextReport } from '@/lib/reports/textGenerators';

const defs = {
    particular: { label: 'Clase particular', unit: 'hours' },
    campamento: { label: 'Campamento', unit: 'days' },
    evento: { label: 'Evento', unit: 'fixed' },
};

const summary: WorkLogSummary = {
    startDate: '2026-01-01',
    endDate: '2026-01-31',
    totals: { logsCount: 4, totalHours: 12, totalNet: 400, totalGross: 450, uniqueDays: 3, activeUsers: 1 },
    byType: [
        { type: 'particular', logsCount: 2, hours: 8, net: 200, gross: 220 },
        { type: 'campamento', logsCount: 1, hours: 4, net: 150, gross: 170 },
        { type: 'tutorial', logsCount: 1, hours: 0, net: 50, gross: 60 },
    ],
    byDay: [
        { date: '2026-01-05', logsCount: 2, hours: 8, net: 200, gross: 220 },
        { date: '2026-01-06', logsCount: 2, hours: 4, net: 200, gross: 230 },
    ],
    byUser: [],
};

describe('report-types', () => {
    describe('resolveUnit', () => {
        it('uses the company unit when defined', () => {
            expect(resolveUnit(defs.particular)).toBe('hours');
            expect(resolveUnit(defs.campamento)).toBe('days');
            expect(resolveUnit(defs.evento)).toBe('fixed');
        });

        it('falls back to hours when there is no definition', () => {
            expect(resolveUnit(undefined)).toBe('hours');
        });

        it('derives days from is_range when unit is missing', () => {
            expect(resolveUnit({ label: 'Rango', is_range: true })).toBe('days');
            expect(resolveUnit({ label: 'Normal' })).toBe('hours');
        });
    });

    describe('resolveLabel', () => {
        it('uses the definition label or the capitalised type', () => {
            expect(resolveLabel('particular', defs.particular)).toBe('Clase particular');
            expect(resolveLabel('tutorial', undefined)).toBe('Tutorial');
        });
    });

    describe('buildTypeBlocks', () => {
        it('builds one block per type in byType with label and unit from the definitions', () => {
            const blocks = buildTypeBlocks(summary.byType, defs);

            expect(blocks.map(b => [b.label, b.unit])).toEqual([
                ['Clase particular', 'hours'],
                ['Campamento', 'days'],
                ['Tutorial', 'hours'],
            ]);
            expect(blocks[0]).toMatchObject({ logsCount: 2, hours: 8, net: 200 });
        });
    });

    describe('blockQuantityText', () => {
        it('formats hours, days and fixed blocks', () => {
            const [hoursBlock, daysBlock] = buildTypeBlocks(summary.byType, defs);
            const fixedBlock = buildTypeBlocks(
                [{ type: 'evento', logsCount: 3, hours: 0, net: 90, gross: 100 }],
                defs
            )[0];

            expect(blockQuantityText(hoursBlock)).toBe('8 horas');
            expect(blockQuantityText(daysBlock)).toBe('4 días');
            expect(blockQuantityText(fixedBlock)).toBe('3 turnos');
        });
    });

    describe('netByMonth', () => {
        it('sums the daily net by month key', () => {
            const totals = netByMonth(summary.byDay, date => date.slice(0, 7));

            expect(totals.get('2026-01')).toBe(400);
        });
    });

    describe('generateTextReport', () => {
        const context = {
            companyId: 'c-1',
            userId: 'me',
            startDate: new Date(2026, 0, 1),
            endDate: new Date(2026, 0, 31),
            summary,
            worklogDefinitions: defs,
        };
        const oneLog = [{ id: 'l1', type: 'particular', date: '2026-01-05', startDate: '2026-01-05' } as any];

        it('writes the per-type summary with the company unit', () => {
            const text = generateTextReport(oneLog, context);

            expect(text).toContain('Clase particular: 2 (8 horas)');
            expect(text).toContain('Campamento: 1 (4 días)');
            expect(text).toContain('Tutorial: 1 (0 horas)');
        });

        it('writes fixed types as turnos', () => {
            const text = generateTextReport(oneLog, {
                ...context,
                summary: {
                    ...summary,
                    byType: [{ type: 'evento', logsCount: 3, hours: 0, net: 90, gross: 100 }],
                },
            });

            expect(text).toContain('Evento: 3 (3 turnos)');
        });
    });
});
