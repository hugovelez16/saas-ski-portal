import api from "@/lib/api";
import {
    CompanyCreateV2,
    CompanyFull,
    CompanyFullWithMembers,
    CompanyReduced,
    CompanyUpdateV2,
    ListCompaniesParams,
    Page,
} from "@/lib/api/v2/types";

/** GET /v2/companies (solo platform admin). */
export const listCompanies = async (params?: ListCompaniesParams): Promise<Page<CompanyFullWithMembers>> => {
    const response = await api.get<Page<CompanyFullWithMembers>>("/v2/companies", { params });
    return response.data;
};

/** GET /v2/companies/{companyId}. Devuelve vista completa o reducida segun el rol. */
export const getCompany = async (companyId: string): Promise<CompanyFull | CompanyReduced> => {
    const response = await api.get<CompanyFull | CompanyReduced>(`/v2/companies/${companyId}`);
    return response.data;
};

/** POST /v2/companies (solo platform admin). */
export const createCompany = async (body: CompanyCreateV2): Promise<CompanyFull> => {
    const response = await api.post<CompanyFull>("/v2/companies", body);
    return response.data;
};

/** PUT /v2/companies/{companyId} (solo platform admin). */
export const updateCompany = async (companyId: string, body: CompanyUpdateV2): Promise<CompanyFull> => {
    const response = await api.put<CompanyFull>(`/v2/companies/${companyId}`, body);
    return response.data;
};

/** DELETE /v2/companies/{companyId}. */
export const deleteCompany = async (companyId: string): Promise<void> => {
    await api.delete(`/v2/companies/${companyId}`);
};

/** GET /v2/me/companies. Empresas del usuario autenticado. */
export const listMyCompanies = async (): Promise<(CompanyFull | CompanyReduced)[]> => {
    const response = await api.get<(CompanyFull | CompanyReduced)[]>("/v2/me/companies");
    return response.data;
};

/** GET /v2/users/{userId}/companies. */
export const listUserCompanies = async (userId: string): Promise<(CompanyFull | CompanyReduced)[]> => {
    const response = await api.get<(CompanyFull | CompanyReduced)[]>(`/v2/users/${userId}/companies`);
    return response.data;
};
