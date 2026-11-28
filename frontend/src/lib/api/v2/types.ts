/**
 * Tipos de la API v2 del area empresa (`/api/v2/`). JSON en snake_case sin alias [Q-2].
 * Reflejan `backend/routers/v2/schemas.py`. Las pantallas actuales consumen los tipos
 * camelCase de `lib/types.ts` a traves de `adapters.ts` (temporal).
 */

export interface Page<T> {
    items: T[];
    total: number;
}

export interface UserBrief {
    id: string;
    email: string;
    first_name: string | null;
    last_name: string | null;
    is_active: boolean;
}

/** Membresia incluida en `include=members` (sin `updated_at`). */
export interface CompanyMemberV2 {
    user_id: string;
    company_id: string;
    role: string;
    is_active: boolean;
    sort_order: number;
    rates_config: Record<string, any>;
    settings: Record<string, any>;
    joined_at: string | null;
    user: UserBrief | null;
}

/** Membresia de `/companies/{id}/members` y `/companies/{id}/rates`. */
export interface MemberOut extends CompanyMemberV2 {
    updated_at: string | null;
}

export interface MemberDeleteOut {
    deleted: boolean;
    deactivated: boolean;
    reason: string | null;
}

/** Elemento minimo del selector de empresas (`GET /v2/me/companies`, R-ACC-81). */
export interface MyCompanyItem {
    id: string;
    name: string;
    role: string;
}

/** Ajustes de empresa editables por manager y PA (`companies.settings`, R-EMP-45). */
export interface CompanySettingsV2 {
    default_is_gross: boolean;
}

/** Limites de plataforma de una empresa (solo PA, R-EMP-45). */
export interface PlatformLimitsV2 {
    max_monitors: number | null;
    max_managers: number | null;
}

/** Ajustes de plataforma de una empresa (solo PA, R-EMP-45, R-EMP-49). */
export interface PlatformSettingsV2 {
    plan: string | null;
    limits: PlatformLimitsV2;
    modules: Record<string, boolean>;
}

/** Vista completa (solo PA actuando). */
export interface CompanyFull {
    id: string;
    name: string;
    is_active: boolean;
    is_managed: boolean;
    tax_config: Record<string, any>;
    worklog_definitions: Record<string, any>;
    settings: CompanySettingsV2 & Record<string, any>;
    platform_settings: PlatformSettingsV2;
    created_at: string | null;
    updated_at: string | null;
}

/** Vista completa de `/users/{id}/companies` para PA: la empresa mas la membresia del usuario consultado. */
export interface CompanyFullWithMembership extends CompanyFull {
    role: string | null;
    is_active_member: boolean;
    rates_config: Record<string, any> | null;
}

export interface CompanyFullWithMembers extends CompanyFull {
    /** Solo presente con `include=members`. */
    members?: CompanyMemberV2[];
}

/** Vista reducida (worker, manager y PA en "ver como"): no expone settings ni platform_settings (R-ACC-55). */
export interface CompanyReduced {
    id: string;
    name: string;
    is_managed: boolean;
    role: string | null;
    is_active_member: boolean;
    rates_config: Record<string, any> | null;
    worklog_definitions: Record<string, any>;
    tax_config: Record<string, number>;
}

export interface CompanyManagerSettings {
    tax_config: Record<string, number>;
    worklog_definitions: Record<string, any>;
    settings: CompanySettingsV2;
}

export interface CompanyManagerSettingsUpdate {
    tax_config?: Record<string, number>;
    worklog_definitions?: Record<string, any>;
    settings?: Partial<CompanySettingsV2>;
}

export interface WorklogDefinitionUsage {
    work_logs_count: number;
    member_rates_count: number;
}

export interface CompanyCreateV2 {
    name: string;
    tax_config: Record<string, any>;
    worklog_definitions?: Record<string, any>;
    is_active?: boolean;
    is_managed?: boolean;
    settings?: Partial<CompanySettingsV2> & Record<string, any>;
    platform_settings?: Partial<PlatformSettingsV2>;
}

export interface CompanyUpdateV2 {
    name?: string;
    tax_config?: Record<string, any>;
    worklog_definitions?: Record<string, any>;
    is_active?: boolean;
    is_managed?: boolean;
    settings?: Partial<CompanySettingsV2> & Record<string, any>;
    platform_settings?: Partial<PlatformSettingsV2>;
    /** Solo auditoria; no se persiste en la empresa. */
    reason?: string;
}

export type MemberRoleV2 = 'worker' | 'manager';

export interface ListCompaniesParams {
    include?: 'members';
    skip?: number;
    limit?: number;
}

export type InvitationStatus = 'pending' | 'accepted' | 'cancelled' | 'expired';

export interface InvitationOut {
    id: string;
    company_id: string;
    email: string;
    status: InvitationStatus;
    invited_by_user_id: string;
    invited_by_name: string | null;
    expires_at: string;
    accepted_at: string | null;
    cancelled_at: string | null;
    created_at: string | null;
}

export interface InvitationPreviewOut {
    company_id: string;
    company_name: string;
    status: 'pending';
    expires_at: string;
}

export interface InvitationAcceptOut {
    company_id: string;
    company_name: string;
    membership: MemberOut;
}
