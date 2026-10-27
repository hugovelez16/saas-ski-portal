import { useMemo } from 'react';
import { Company, CompanySettings } from '@/lib/types';

/**
 * Devuelve los settings de la empresa tal y como llegan del backend.
 * El backend aplica los valores por defecto, por lo que no hay fallbacks en el cliente.
 */
export function useCompanySettings(company?: Company | null): CompanySettings {
    return useMemo(
        () => (company?.settings ?? {}) as CompanySettings,
        [company]
    );
}
