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

/** Vista completa (solo PA actuando). */
export interface CompanyFull {
    id: string;
    name: string;
    is_active: boolean;
    is_managed: boolean;
    tax_config: Record<string, any>;
    worklog_definitions: Record<string, any>;
    settings: Record<string, any>;
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

/** Vista reducida (worker, manager y PA en "ver como"). */
export interface CompanyReduced {
    id: string;
    name: string;
    is_managed: boolean;
    role: string | null;
    is_active_member: boolean;
    rates_config: Record<string, any> | null;
    worklog_definitions: Record<string, any>;
    tax_config: Record<string, number>;
    settings: Record<string, any>;
}

export interface CompanyCreateV2 {
    name: string;
    tax_config: Record<string, any>;
    worklog_definitions?: Record<string, any>;
    is_active?: boolean;
    is_managed?: boolean;
    settings?: Record<string, any>;
}

export interface CompanyUpdateV2 {
    name?: string;
    tax_config?: Record<string, any>;
    worklog_definitions?: Record<string, any>;
    is_active?: boolean;
    is_managed?: boolean;
    settings?: Record<string, any>;
    /** Solo auditoria; no se persiste en la empresa. */
    reason?: string;
}

export type MemberRoleV2 = 'worker' | 'manager';

export interface ListCompaniesParams {
    include?: 'members';
    skip?: number;
    limit?: number;
}
