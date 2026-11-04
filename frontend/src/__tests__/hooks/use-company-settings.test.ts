import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useCompanySettings } from '@/hooks/use-company-settings';
import type { Company } from '@/lib/types';

const baseCompany = (settings?: Record<string, any>): Company => ({
    id: 'c1',
    name: 'Escuela Sierra',
    taxConfig: {},
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...(settings === undefined ? {} : { settings }),
});

describe('useCompanySettings', () => {
    it('devuelve el objeto settings de la empresa tal cual llega', () => {
        const settings = {
            business_logic: { price_type: 'net' },
            worker_experience: { input_mode: 'timer', allow_manual_amount: true },
            ui_customization: { labels: { worklog: 'Turno', client: 'Cliente' } },
            modules: { reports: true, worker_daily_report: false },
            allowed_rates: ['hourly'],
        };
        const company = baseCompany(settings);

        const { result } = renderHook(() => useCompanySettings(company));

        expect(result.current).toBe(company.settings);
        expect(result.current).toEqual(settings);
    });

    it('no aplica valores por defecto propios', () => {
        const company = baseCompany({ modules: { reports: true } });

        const { result } = renderHook(() => useCompanySettings(company));

        expect(result.current.business_logic).toBeUndefined();
        expect(result.current.worker_experience).toBeUndefined();
        expect(result.current.modules).toEqual({ reports: true });
    });

    it('no migra claves antiguas (features, billing, input_mode, cost_markup)', () => {
        const company = baseCompany({
            features: { worker_daily_report: true },
            billing: { price_type: 'gross' },
            input_mode: 'timer',
            business_logic: { price_type: 'net', cost_markup: 10 },
        });

        const { result } = renderHook(() => useCompanySettings(company));

        expect(result.current.modules).toBeUndefined();
        expect(result.current.worker_experience).toBeUndefined();
        expect(result.current.business_logic).toEqual({ price_type: 'net', cost_markup: 10 });
    });

    it('devuelve un objeto vacio si no hay empresa o no tiene settings', () => {
        const withoutCompany = renderHook(() => useCompanySettings(null));
        const withoutSettings = renderHook(() => useCompanySettings(baseCompany()));

        expect(withoutCompany.result.current).toEqual({});
        expect(withoutSettings.result.current).toEqual({});
    });
});
