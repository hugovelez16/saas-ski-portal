import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useCompanySettings } from '@/hooks/use-company-settings';
import type { Company, CompanyFull } from '@/lib/types';

const baseCompany = (settings?: Record<string, any>): Company & { settings?: Record<string, any> } => ({
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
            default_is_gross: true,
        };
        const company = baseCompany(settings);

        const { result } = renderHook(() => useCompanySettings(company));

        expect(result.current).toBe(company.settings);
        expect(result.current).toEqual(settings);
    });

    it('no aplica valores por defecto propios', () => {
        const company = baseCompany({});

        const { result } = renderHook(() => useCompanySettings(company));

        expect(result.current.default_is_gross).toBeUndefined();
    });

    it('devuelve un objeto vacio si no hay empresa o no tiene settings', () => {
        const withoutCompany = renderHook(() => useCompanySettings(null));
        const withoutSettings = renderHook(() => useCompanySettings(baseCompany()));

        expect(withoutCompany.result.current).toEqual({});
        expect(withoutSettings.result.current).toEqual({});
    });
});
