import api from "@/lib/api";
import { CompanyFull, CompanyResponse, CompanyUpdatePayload, CompanyWithMembers, CompanyMemberResponse, DailyReportResponse, DashboardSummaryResponse } from "@/lib/types";
import { fromV2Company, fromV2CompanyWithMembers, fromV2Member, toV2CompanyBody } from "@/lib/api/v2/adapters";
import * as v2Companies from "@/lib/api/v2/companies";
import * as v2Members from "@/lib/api/v2/members";
import type { CompanyCreateV2, CompanyUpdateV2, CompanyFull as CompanyFullV2, CompanyReduced } from "@/lib/api/v2/types";

// Las funciones de empresa y miembros consumen la API v2 (`/api/v2/`) y devuelven los tipos
// camelCase actuales mediante `lib/api/v2/adapters.ts` (temporal, hasta migrar a snake_case).

/** Tope de `limit` de `GET /v2/companies`: equivale al listado completo de v1. */
const LIST_ALL_LIMIT = 2000;

export const createCompany = async (data: {
    name: string;
    taxConfig: Record<string, number>;
    worklogDefinitions?: Record<string, any>;
    isManaged?: boolean;
    isActive?: boolean;
}) => {
    const created = await v2Companies.createCompany(toV2CompanyBody<CompanyCreateV2>(data));
    return fromV2Company(created);
};

export type { CompanyUpdatePayload };

/** PUT /v2/companies/:id (solo platform admin). Tipo en lib/types.ts. */
export const updateCompany = async (companyId: string, data: CompanyUpdatePayload): Promise<CompanyFull> => {
    const updated = await v2Companies.updateCompany(companyId, toV2CompanyBody<CompanyUpdateV2>(data));
    return fromV2Company(updated) as CompanyFull;
};

// Solo platform admin. Los demas roles deben usar getMyCompanies.
export const getCompanies = async (): Promise<CompanyFull[]> => {
    const page = await v2Companies.listCompanies({ limit: LIST_ALL_LIMIT });
    return page.items.map((item) => fromV2Company(item) as CompanyFull);
};

export const getCompany = async (companyId: string): Promise<CompanyResponse> => {
    return fromV2Company(await v2Companies.getCompany(companyId));
};

// Empresas con sus miembros. v2 separa los dos casos que v1 servia en /companies/detailed:
// PA actuando (vista completa) -> GET /v2/companies?include=members; resto -> sus empresas
// (/v2/me/companies, vista reducida) y los miembros de aquellas donde es manager.
export const getCompaniesDetailed = async (): Promise<CompanyWithMembers[]> => {
    const mine = await v2Companies.listMyCompanies();
    if (mine.length === 0) return [];

    if (mine.every((company) => "is_active" in company)) {
        const page = await v2Companies.listCompanies({ include: "members", limit: LIST_ALL_LIMIT });
        return page.items.map(fromV2CompanyWithMembers);
    }

    return Promise.all(
        mine.map(async (company): Promise<CompanyWithMembers> => {
            const canListMembers = "role" in company && (company.role === "manager" || company.role === "admin");
            let members: Awaited<ReturnType<typeof v2Members.listMembers>> = [];
            if (canListMembers) {
                try {
                    members = await v2Members.listMembers(company.id, undefined, { meta: { silent: true } });
                } catch (error) {
                    // 403 en empresas que no son la del token (v1 solo devolvia la activa): sin miembros.
                    if ((error as { response?: { status?: number } })?.response?.status !== 403) throw error;
                }
            }
            return { ...fromV2Company(company), members: members.map(fromV2Member) } as CompanyWithMembers;
        })
    );
};

// Parte diario de un dia (date: YYYY-MM-DD). Los importes solo vienen a manager y platform admin.
export const getDailyReport = async (companyId: string, date: string): Promise<DailyReportResponse> => {
    const response = await api.get<DailyReportResponse>(`/companies/${companyId}/daily-report`, {
        params: { date }
    });
    return response.data;
};



export const getMyCompanies = async (): Promise<CompanyResponse[]> => {
    const companies: (CompanyFullV2 | CompanyReduced)[] = await v2Companies.listMyCompanies();
    // v1 marcaba al PA actuando con role "admin" e isActiveMember; la vista completa de v2 no lo trae.
    return companies.map((company) =>
        "is_active" in company ? { ...fromV2Company(company), role: "admin", isActiveMember: true } : fromV2Company(company)
    );
};

// Admin & Manager actions
// `status`: los valores que activaban la membresia en v1 ("active", "approved", "true", "1"); cualquier otro la desactiva.
const ACTIVE_STATUS_VALUES = new Set(["active", "approved", "true", "1"]);

export const updateMemberStatus = async (companyId: string, userId: string, status: string): Promise<CompanyMemberResponse> => {
    return fromV2Member(await v2Members.setMemberStatus(companyId, userId, ACTIVE_STATUS_VALUES.has(status)));
};

export const addCompanyMember = async (companyId: string, email: string): Promise<CompanyMemberResponse> => {
    return fromV2Member(await v2Members.addMember(companyId, email));
};

export type MemberRole = 'worker' | 'manager';

export const updateMemberRole = async (companyId: string, userId: string, role: MemberRole): Promise<CompanyMemberResponse> => {
    return fromV2Member(await v2Members.setMemberRole(companyId, userId, role));
};

export const updateMemberRates = async (companyId: string, userId: string, ratesConfig: Record<string, any>): Promise<CompanyMemberResponse> => {
    return fromV2Member(await v2Members.setMemberRates(companyId, userId, ratesConfig));
};

export const updateMemberSettings = async (companyId: string, userId: string, settings: Record<string, any>): Promise<CompanyMemberResponse> => {
    return fromV2Member(await v2Members.setMemberSettings(companyId, userId, settings));
};

export type MemberDeleteResponse = {
    deleted: boolean;
    deactivated: boolean;
    reason: string | null;
};

export const removeCompanyMember = async (companyId: string, userId: string): Promise<MemberDeleteResponse> => {
    return v2Members.removeMember(companyId, userId);
};

export const getCompanyRates = async (companyId: string): Promise<CompanyMemberResponse[]> => {
    return (await v2Members.listRates(companyId)).map(fromV2Member);
};

// `status`: "active" solo activos, "inactive" solo inactivos, sin valor todos.
export const getCompanyMembers = async (companyId: string, status?: string): Promise<CompanyMemberResponse[]> => {
    const params = status ? { is_active: status === "active" } : undefined;
    return (await v2Members.listMembers(companyId, params)).map(fromV2Member);
};

export const updateCompanyMembersOrder = async (companyId: string, userIds: string[]): Promise<any> => {
    return v2Members.reorderMembers(companyId, userIds);
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
