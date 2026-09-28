import api from '../api';
import { CompanyMember } from '@/lib/types';
import { getCompaniesDetailed } from './companies';

export const getUserRates = async (companyId?: string): Promise<CompanyMember[]> => {
    try {
        const companies = await getCompaniesDetailed();
        const { data: user } = await api.get('/users/me');

        const membersList: CompanyMember[] = [];

        for (const company of companies) {
            if (companyId && company.id !== companyId) continue;

            const myMembership = company.members?.find(m => m.userId === user.id);
            if (myMembership) {
                membersList.push(myMembership);
            }
        }

        return membersList;
    } catch (e) {
        console.warn("Failed to fetch granular rates from detailed endpoint", e);
        return [];
    }
};

// Deprecated alias
export const getUserSettings = async () => {
    const rates = await getUserRates();
    return rates.length > 0 ? rates[0] : null;
}

export const updateUserRates = async (companyId: string, userId: string, data: any) => {
    // Note: To update rates, we now update the member's ratesConfig via the companies endpoint
    const response = await api.put(`/companies/${companyId}/members/${userId}`, { ratesConfig: data });
    return response.data;
};

// Deprecated alias
export const updateUserSettings = updateUserRates;

export const getCompanies = async () => {
    const response = await api.get('/companies');
    return response.data;
};
