import api from "@/lib/api";
import {
    CompanyCreateV2,
    CompanyFull,
    CompanyFullWithMembers,
    CompanyFullWithMembership,
    CompanyManagerSettings,
    CompanyManagerSettingsUpdate,
    CompanyReduced,
    CompanyUpdateV2,
    ListCompaniesParams,
    MyCompanyItem,
    Page,
    WorklogDefinitionUsage,
} from "@/lib/api/v2/types";

/** GET /v2/companies (solo platform admin). */
export const listCompanies = async (params?: ListCompaniesParams): Promise<Page<CompanyFullWithMembers>> => {
    const response = await api.get<Page<CompanyFullWithMembers>>("/v2/companies", { params });
    return response.data;
};

/** GET /v2/companies/{companyId}. Devuelve vista completa o reducida segun el rol. */
export const getCompany = async (
    companyId: string,
    config?: { meta?: { silent?: boolean } },
): Promise<CompanyFull | CompanyReduced> => {
    const response = config
        ? await api.get<CompanyFull | CompanyReduced>(`/v2/companies/${companyId}`, config)
        : await api.get<CompanyFull | CompanyReduced>(`/v2/companies/${companyId}`);
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

/** GET /v2/me/companies. Empresas activas del usuario autenticado (solo id, name y role). */
export const listMyCompanies = async (): Promise<MyCompanyItem[]> => {
    const response = await api.get<MyCompanyItem[]>("/v2/me/companies");
    return response.data;
};

/** GET /v2/users/{userId}/companies. PA: vista completa con la membresia del usuario; manager: vista reducida. */
export const listUserCompanies = async (userId: string): Promise<(CompanyFullWithMembership | CompanyReduced)[]> => {
    const response = await api.get<(CompanyFullWithMembership | CompanyReduced)[]>(`/v2/users/${userId}/companies`);
    return response.data;
};

/** GET /v2/companies/{companyId}/settings (manager de la empresa activa). */
export const getCompanyManagerSettings = async (companyId: string): Promise<CompanyManagerSettings> => {
    const response = await api.get<CompanyManagerSettings>(`/v2/companies/${companyId}/settings`);
    return response.data;
};

/** PUT /v2/companies/{companyId}/settings (manager de la empresa activa). */
export const updateCompanyManagerSettings = async (
    companyId: string,
    body: CompanyManagerSettingsUpdate,
): Promise<CompanyManagerSettings> => {
    const response = await api.put<CompanyManagerSettings>(`/v2/companies/${companyId}/settings`, body);
    return response.data;
};

/** GET /v2/companies/{companyId}/worklog-definitions/usage o /v2/admin/companies/{companyId}/worklog-definitions/usage. */
export const getWorklogDefinitionsUsage = async (
    companyId: string,
    options?: { asAdmin?: boolean },
): Promise<Record<string, WorklogDefinitionUsage>> => {
    const url = options?.asAdmin
        ? `/v2/admin/companies/${companyId}/worklog-definitions/usage`
        : `/v2/companies/${companyId}/worklog-definitions/usage`;
    const response = await api.get<Record<string, WorklogDefinitionUsage>>(url);
    return response.data;
};
