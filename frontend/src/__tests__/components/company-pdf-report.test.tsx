import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';

vi.mock('@react-pdf/renderer', () => ({
    Document: ({ children }: any) => <div data-testid="pdf-document">{children}</div>,
    Page: ({ children }: any) => <div>{children}</div>,
    View: ({ children }: any) => <div>{children}</div>,
    Text: ({ children }: any) => <span>{children}</span>,
    Image: () => null,
    StyleSheet: { create: (styles: any) => styles },
    Font: { register: vi.fn() },
}));

import { CompanyPDFReport, summarizeCompanyTaxes } from '@/components/reports/CompanyPDFReport';

describe('CompanyPDFReport (R-EMP-37)', () => {
    it('recorre cualquier impuesto existente en taxConfig y suma sus tasas', () => {
        const summary = summarizeCompanyTaxes({ IRPF: 0.15, Mutua: 0.05 });

        expect(summary.totalRate).toBeCloseTo(0.2);
        expect(summary.label).toBe('IRPF: 15.0% | Mutua: 5.0%');
    });

    it('indica sin retenciones globales cuando taxConfig esta vacio', () => {
        const summary = summarizeCompanyTaxes({});

        expect(summary.totalRate).toBe(0);
        expect(summary.label).toBe('Sin retenciones globales');
    });

    it('renderiza los impuestos dinamicos de la empresa en lugar de claves fijas', () => {
        render(
            <CompanyPDFReport
                company={{
                    id: 'c-1',
                    name: 'Escuela Libre',
                    taxConfig: { Retencion: 0.12, Seguro: 0.03 },
                }}
                employeeStats={[
                    {
                        userId: 'u-1',
                        name: 'Ana Lopez',
                        totalHours: 10,
                        totalAmount: 85,
                        totalGross: 100,
                        totalNet: 85,
                        totalDays: 2,
                    },
                ]}
                title="Informe Mensual"
                startDate={new Date('2026-01-01')}
                endDate={new Date('2026-01-31')}
            />
        );

        expect(screen.getByText('Retencion: 12.0% | Seguro: 3.0%')).toBeInTheDocument();
        expect(screen.queryByText(/SS:/)).toBeNull();
    });
});
