import api from "@/lib/api";
import { MemberDeleteOut, MemberOut, MemberRoleV2 } from "@/lib/api/v2/types";

/** GET /v2/companies/{companyId}/members. */
export const listMembers = async (
    companyId: string,
    params?: { is_active?: boolean },
    config?: { meta?: { silent?: boolean } }
): Promise<MemberOut[]> => {
    const response = await api.get<MemberOut[]>(`/v2/companies/${companyId}/members`, { params, ...config });
    return response.data;
};

/** POST /v2/companies/{companyId}/members. */
export const addMember = async (companyId: string, email: string): Promise<MemberOut> => {
    const response = await api.post<MemberOut>(`/v2/companies/${companyId}/members`, { email });
    return response.data;
};

/** DELETE /v2/companies/{companyId}/members/{userId}. */
export const removeMember = async (companyId: string, userId: string): Promise<MemberDeleteOut> => {
    const response = await api.delete<MemberDeleteOut>(`/v2/companies/${companyId}/members/${userId}`);
    return response.data;
};

/** PUT /v2/companies/{companyId}/members/{userId}/status. */
export const setMemberStatus = async (companyId: string, userId: string, isActive: boolean): Promise<MemberOut> => {
    const response = await api.put<MemberOut>(`/v2/companies/${companyId}/members/${userId}/status`, { is_active: isActive });
    return response.data;
};

/** PUT /v2/companies/{companyId}/members/{userId}/role. */
export const setMemberRole = async (companyId: string, userId: string, role: MemberRoleV2): Promise<MemberOut> => {
    const response = await api.put<MemberOut>(`/v2/companies/${companyId}/members/${userId}/role`, { role });
    return response.data;
};

/** PUT /v2/companies/{companyId}/members/{userId}/rates. */
export const setMemberRates = async (companyId: string, userId: string, ratesConfig: Record<string, any>): Promise<MemberOut> => {
    const response = await api.put<MemberOut>(`/v2/companies/${companyId}/members/${userId}/rates`, { rates_config: ratesConfig });
    return response.data;
};

/** PUT /v2/companies/{companyId}/members/{userId}/settings. */
export const setMemberSettings = async (companyId: string, userId: string, settings: Record<string, any>): Promise<MemberOut> => {
    const response = await api.put<MemberOut>(`/v2/companies/${companyId}/members/${userId}/settings`, { settings });
    return response.data;
};

/** PUT /v2/companies/{companyId}/members/order. */
export const reorderMembers = async (companyId: string, userIds: string[]): Promise<{ message: string }> => {
    const response = await api.put<{ message: string }>(`/v2/companies/${companyId}/members/order`, { user_ids: userIds });
    return response.data;
};

/** GET /v2/companies/{companyId}/rates. */
export const listRates = async (companyId: string): Promise<MemberOut[]> => {
    const response = await api.get<MemberOut[]>(`/v2/companies/${companyId}/rates`);
    return response.data;
};
