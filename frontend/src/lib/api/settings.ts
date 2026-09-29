import api from '../api';
import { CompanyMember } from '@/lib/types';
import { getMyCompanies } from './companies';

export const getUserRates = async (companyId?: string): Promise<CompanyMember[]> => {
    try {
        const { data: user } = await api.get('/users/me');

        // Si se especifica companyId, intentamos consultar directamente la membresia propia
        if (companyId) {
            try {
                const { data: member } = await api.get(`/companies/${companyId}/members/me`);
                if (member) {
                    return [member];
                }
            } catch {
                // Fallback a getMyCompanies si el endpoint /members/me no estuviera disponible
            }
        }

        // Obtener tarifas directamente desde getMyCompanies() sin llamar a /companies/detailed (que da 403 a trabajadores)
        const companies = await getMyCompanies();
        const membersList: CompanyMember[] = [];

        for (const company of companies) {
            if (companyId && company.id !== companyId) continue;

            const myMembership = (company as any).members?.find((m: any) => m.userId === user.id);
            if (myMembership) {
                membersList.push(myMembership);
            }
        }

        return membersList;
    } catch (e) {
        console.warn("Failed to fetch rates from companies/membership", e);
        return [];
    }
};

// Deprecated alias
export const getUserSettings = async () => {
    const rates = await getUserRates();
    return rates.length > 0 ? rates[0] : null;
};

export const updateUserRates = async (companyId: string, userId: string, data: any) => {
    // Asegurar que acepte y envie existingSettings (si existen) junto a ratesConfig para que el backend no borre member.settings
    const { existingSettings, ratesConfig, ...rest } = data;
    const payload: Record<string, any> = {
        ratesConfig: ratesConfig !== undefined ? ratesConfig : rest,
    };
    if (existingSettings !== undefined) {
        payload.settings = existingSettings;
    }

    const response = await api.put(`/companies/${companyId}/members/${userId}`, payload);
    return response.data;
};

// Deprecated alias
export const updateUserSettings = updateUserRates;

export const getCompanies = async () => {
    const response = await api.get('/companies');
    return response.data;
};
