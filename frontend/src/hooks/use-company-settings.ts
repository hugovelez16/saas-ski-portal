import { useMemo } from 'react';
import { Company, CompanyFull, CompanySettings } from '@/lib/types';

/**
 * Devuelve los settings de la empresa tal y como llegan del backend (vista completa o endpoint de manager).
 */
export function useCompanySettings(
    company?: (Company & { settings?: Partial<CompanySettings> & Record<string, any> }) | CompanyFull | null
): Partial<CompanySettings> & Record<string, any> {
    return useMemo(
        () => (company?.settings ?? {}) as Partial<CompanySettings> & Record<string, any>,
        [company]
    );
}
