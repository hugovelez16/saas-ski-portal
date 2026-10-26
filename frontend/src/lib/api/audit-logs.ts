import api from "@/lib/api";

// Solo platform admin. Contrato: JSON camelCase; la query se envia en snake_case.
export interface AuditLogItem {
    id: string;
    action: string;
    createdAt: string;
    actorUserId: string | null;
    actorEmail: string | null;
    companyId: string | null;
    targetUserId: string | null;
    oldValue: Record<string, unknown> | null;
    newValue: Record<string, unknown> | null;
    reason: string | null;
    extraData: Record<string, unknown> | null;
}

export interface AuditLogPage {
    total: number;
    items: AuditLogItem[];
}

export interface AuditLogParams {
    companyId?: string;
    actorUserId?: string;
    targetUserId?: string;
    action?: string;
    /** ISO 8601 datetime (con zona horaria). */
    from?: string;
    /** ISO 8601 datetime (con zona horaria). */
    to?: string;
    /** Rango 1..200. Por defecto 50 en backend. */
    limit?: number;
    offset?: number;
}

export const getAuditLogs = async (params: AuditLogParams = {}): Promise<AuditLogPage> => {
    const query: Record<string, string | number> = {};

    if (params.companyId) query.company_id = params.companyId;
    if (params.actorUserId) query.actor_user_id = params.actorUserId;
    if (params.targetUserId) query.target_user_id = params.targetUserId;
    if (params.action) query.action = params.action;
    if (params.from) query.from = params.from;
    if (params.to) query.to = params.to;
    if (params.limit !== undefined) query.limit = params.limit;
    if (params.offset !== undefined) query.offset = params.offset;

    const response = await api.get<AuditLogPage>("/audit-logs", { params: query });
    return response.data;
};

export const getAuditActions = async (): Promise<string[]> => {
    const response = await api.get<string[]>("/audit-logs/actions");
    return response.data;
};
