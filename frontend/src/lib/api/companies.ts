import api from "@/lib/api";
import { CompanyResponse, CompanyWithMembers, CompanyMemberResponse, DailyReportResponse, DashboardSummaryResponse } from "@/lib/types";

export const createCompany = async (data: {
    name: string;
    taxConfig: Record<string, number>;
    worklogDefinitions?: Record<string, any>;
    isManaged?: boolean;
    isActive?: boolean;
}) => {
    const response = await api.post("/companies", data);
    return response.data;
};

/**
 * Payload de PUT /companies/:id (solo platform admin).
 * `reason` es opcional y solo se registra en auditoria.
 */
export type CompanyUpdatePayload = {
    name?: string;
    isActive?: boolean;
    isManaged?: boolean;
    taxConfig?: Record<string, number>;
    settings?: Record<string, any>;
    worklogDefinitions?: Record<string, any>;
    reason?: string;
};

export const updateCompany = async (companyId: string, data: CompanyUpdatePayload): Promise<CompanyResponse> => {
    const response = await api.put<CompanyResponse>(`/companies/${companyId}`, data);
    return response.data;
};

// Solo platform admin. Los demas roles deben usar getMyCompanies.
export const getCompanies = async (): Promise<CompanyResponse[]> => {
    const response = await api.get<CompanyResponse[]>("/companies");
    return response.data;
};

export const getCompany = async (companyId: string): Promise<CompanyResponse> => {
    const response = await api.get<CompanyResponse>(`/companies/${companyId}`);
    return response.data;
};

export const getCompaniesDetailed = async (): Promise<CompanyWithMembers[]> => {
    const response = await api.get<CompanyWithMembers[]>("/companies/detailed");
    return response.data;
};

// Parte diario de un dia (date: YYYY-MM-DD). Los importes solo vienen a manager y platform admin.
export const getDailyReport = async (companyId: string, date: string): Promise<DailyReportResponse> => {
    const response = await api.get<DailyReportResponse>(`/companies/${companyId}/daily-report`, {
        params: { date }
    });
    return response.data;
};



export const getMyCompanies = async (): Promise<CompanyResponse[]> => {
    const response = await api.get<CompanyResponse[]>("/users/me/companies");
    return response.data;
};

// Admin & Manager actions
export const updateMemberStatus = async (companyId: string, userId: string, status: string): Promise<CompanyMemberResponse> => {
    const response = await api.put<CompanyMemberResponse>(`/companies/${companyId}/members/${userId}/status?status=${status}`);
    return response.data;
};

export const addCompanyMember = async (companyId: string, email: string): Promise<CompanyMemberResponse> => {
    const response = await api.post<CompanyMemberResponse>(`/companies/${companyId}/members/add`, { email });
    return response.data;
};

export type MemberRole = 'worker' | 'manager';

export const updateMemberRole = async (companyId: string, userId: string, role: MemberRole): Promise<CompanyMemberResponse> => {
    const response = await api.put<CompanyMemberResponse>(`/companies/${companyId}/members/${userId}/role`, { role });
    return response.data;
};

export const updateMemberRates = async (companyId: string, userId: string, ratesConfig: Record<string, any>): Promise<CompanyMemberResponse> => {
    const response = await api.put<CompanyMemberResponse>(`/companies/${companyId}/members/${userId}/rates`, { ratesConfig });
    return response.data;
};

export const updateMemberSettings = async (companyId: string, userId: string, settings: Record<string, any>): Promise<CompanyMemberResponse> => {
    const response = await api.put<CompanyMemberResponse>(`/companies/${companyId}/members/${userId}/settings`, { settings });
    return response.data;
};

export type MemberDeleteResponse = {
    deleted: boolean;
    deactivated: boolean;
    reason: string | null;
};

export const removeCompanyMember = async (companyId: string, userId: string): Promise<MemberDeleteResponse> => {
    const response = await api.delete(`/companies/${companyId}/members/${userId}`);
    return response.data;
};

export const getCompanyRates = async (companyId: string): Promise<any[]> => {
    const response = await api.get<any[]>(`/companies/${companyId}/rates-v2`);
    return response.data;
};

export const getCompanyMembers = async (companyId: string, status?: string): Promise<CompanyMemberResponse[]> => {
    const response = await api.get<CompanyMemberResponse[]>(`/companies/${companyId}/members`, {
        params: { status }
    });
    return response.data;
};

export const updateCompanyMembersOrder = async (companyId: string, userIds: string[]): Promise<any> => {
    const response = await api.put(`/companies/${companyId}/members/order`, { userIds });
    return response.data;
};

export const getCompanyDashboardSummary = async (
    companyId: string,
    params?: { startDate?: string; endDate?: string }
): Promise<DashboardSummaryResponse> => {
    const queryParams: Record<string, string> = {};
    if (params?.startDate) queryParams.start_date = params.startDate;
    if (params?.endDate) queryParams.end_date = params.endDate;

    const response = await api.get<DashboardSummaryResponse>(`/companies/${companyId}/dashboard-summary`, {
        params: queryParams
    });
    return response.data;
};


