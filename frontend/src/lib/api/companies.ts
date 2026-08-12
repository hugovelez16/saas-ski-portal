import api from "@/lib/api";
import { CompanyResponse, CompanyWithMembers, CompanyMemberResponse } from "@/lib/types";

export const createCompany = async (data: {
    name: string;
    fiscalId?: string;
    taxConfig?: Record<string, number>;
    worklogDefinitions?: Record<string, any>;
}) => {
    const response = await api.post("/companies", data);
    return response.data;
};

export const updateCompany = async (companyId: string, data: any): Promise<CompanyResponse> => {
    const response = await api.put<CompanyResponse>(`/companies/${companyId}`, data);
    return response.data;
};

export const getCompanies = async (): Promise<CompanyResponse[]> => {
    const response = await api.get<CompanyResponse[]>("/companies");
    return response.data;
};

export const getCompaniesDetailed = async (): Promise<CompanyWithMembers[]> => {
    const response = await api.get<CompanyWithMembers[]>("/companies/detailed");
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

export const updateCompanyMember = async (companyId: string, userId: string, data: any): Promise<CompanyMemberResponse> => {
    const response = await api.put<CompanyMemberResponse>(`/companies/${companyId}/members/${userId}`, data);
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

