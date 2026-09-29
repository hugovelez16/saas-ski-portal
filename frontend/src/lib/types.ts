/**
 * User Profile Interface.
 */
export interface UserProfile {
    id: string;
    email: string;
    firstName: string | null;
    lastName: string | null;
    role: string;
    isActive: boolean;
    isActiveWorker?: boolean;
    isManager?: boolean;
    mustChangePassword?: boolean;
    is2faEnabled?: boolean;
    isImpersonated?: boolean;
    isPlatformAdmin?: boolean;
    activeCompanyId?: string | null;
    activeRole?: string | null;
    defaultCompanyId?: string | null;
    createdAt: string;
}

export type User = UserProfile;
export type UserSettings = any; // Placeholder for legacy references

/**
 * Company Interface
 */
export interface Company {
    id: string;
    name: string;
    fiscalId?: string | null;
    taxConfig: {
        social_security: number;
        irpf_base: number;
        [key: string]: number;
    };
    worklogDefinitions?: Record<string, any>;
    settings?: Record<string, any>;
    createdAt: string;
    updatedAt: string;

    // UI specific
    role?: string;
    isActiveMember?: boolean;
    isManaged?: boolean;
    isActive?: boolean;
}

export type CompanyResponse = Company;

export interface CompanySettings {
    modules?: Record<string, boolean>;
    business_logic?: {
        price_type?: 'net' | 'gross';
        cost_markup?: number;
    };
    worker_experience?: {
        input_mode?: 'manual_single' | 'timer' | 'bulk';
        allow_manual_amount?: boolean;
    };
    ui_customization?: {
        labels?: {
            worklog?: string;
            client?: string;
        };
    };
    // Legacy support (to be removed after complete migration)
    /** @deprecated Use modules instead */
    features?: Record<string, boolean>;
    /** @deprecated Use business_logic.price_type instead */
    billing?: {
        price_type?: 'net' | 'gross';
    };
    /** @deprecated Use worker_experience.input_mode instead */
    input_mode?: 'manual_single' | 'timer' | 'bulk';
}

export interface DynamicRateEntry {
    base_rate: number;
    is_gross: boolean;
    tax_overrides: {
        ss?: number | null;
        irpf?: number | null;
        extra?: number | null;
    };
}

export type DynamicRateConfig = Record<string, DynamicRateEntry>;

/**
 * Company Member Interface
 */
export interface CompanyMember {
    userId: string;
    companyId: string;
    role: string;
    isActive: boolean;
    status?: string;
    ratesConfig?: DynamicRateConfig | null;
    settings?: Record<string, any>;
    joinedAt: string;
    user?: UserProfile;
}

export type CompanyMemberResponse = CompanyMember;

export interface CompanyWithMembers extends Company {
    members: CompanyMember[];
}

export interface WorkLogExtraData {
    datos?: Record<string, string | number>;
    opciones?: Record<string, boolean>;
    client?: string;
    group_id?: string;
}

/**
 * WorkLog Interface (Refactored for SaaS Dynamic Engine)
 */
export interface WorkLog {
    id: string;
    userId: string;
    companyId: string;
    type: string;
    startDate: string;
    endDate: string;
    startTime?: string | null;
    endTime?: string | null;
    duration?: number;

    // Financials (Unified with Backend)
    netAmount: number;
    grossAmount: number;

    // Historical Snapshot
    calculationSnapshot?: Record<string, any>;

    extraData: WorkLogExtraData;
    description?: string | null;
    pickupPoint?: string | null;
    groupId?: string | null;

    createdAt: string;
    updatedAt: string;

    // Legacy / UI compat
    date?: string;
    durationHours?: number;
    amount?: number;
    hasCoordination?: boolean;
    hasNight?: boolean;
    arrivesPrior?: boolean;
    isGrossCalculation?: boolean;
}

export interface UserDevice {
    id: string;
    userId: string;
    name: string;
    deviceIdentifier: string;
    lastUsed: string;
    expiresAt: string;
}

/**
 * API Request Schemas
 */
export interface WorkLogCreate {
    type: string;
    companyId: string;
    userId: string;
    startDate: string;
    endDate: string;
    startTime?: string | null;
    endTime?: string | null;
    description?: string | null;
    pickupPoint?: string | null;
    extraData?: WorkLogExtraData;
    amount?: number; // Manual override
    date?: string | null;
    hasCoordination?: boolean;
    hasNight?: boolean;
    arrivesPrior?: boolean;
    isGrossCalculation?: boolean;
    groupId?: string | null;
}

export interface WorkLogBulkCreate extends Omit<WorkLogCreate, 'userId'> {
    userIds: string[];
}

/**
 * Authentication & Sessions
 */
export interface Token {
    accessToken: string;
    tokenType: string;
    requires2Fa?: boolean;
    deviceToken?: string;
}

export interface Session {
    id: string;
    deviceName?: string | null;
    ipAddress?: string | null;
    isActive: boolean;
    lastActive: string;
    createdAt: string;
}

/**
 * @deprecated Use CompanyMember.ratesConfig instead for the new SaaS dynamic structure.
 * This remains for legacy components during migration.
 */
export interface UserCompanyRate {
    userId: string;
    companyId: string;
    hourlyRate: number;
    dailyRate: number;
    nightRate: number;
    coordinationRate: number;
    isGross: boolean;
    deductionSs?: number;
    deductionIrpf?: number;
    deductionExtra?: number;
    user?: UserProfile;
}

// ─── Módulos y Suscripciones ──────────────────────────────────────────────

export interface AppModule {
    id: string;
    codeName: string;
    name: string;
    description?: string | null;
    isActive: boolean;
    targetScope: 'company' | 'user' | 'both';
    priceMonthly?: number | null;
    createdAt: string;
    updatedAt: string;
}

export interface ModuleSubscription {
    id: string;
    moduleId: string;
    companyId?: string | null;
    userId?: string | null;
    scope: 'company' | 'user';
    status: 'active' | 'trial' | 'cancelled' | 'expired';
    expiresAt?: string | null;
    notes?: string | null;
    createdAt: string;
    updatedAt: string;
    module?: AppModule;
    company?: Company;
    user?: User;
}

// ─── Dynamic Billing ──────────────────────────────────────────────────────

export interface WorklogTypeSummary {
    typeKey: string;
    label: string;
    unit: "hours" | "days" | string;
    quantity: number;   // horas o días, según unit
    netAmount: number;
    grossAmount: number;
}

export interface BillingSummaryItem {
    userId: string;
    firstName: string | null;
    lastName: string | null;
    email: string;
    type: string | null;
    totalHours: number;
    totalNet: number;
    totalGross: number;
    uniqueDays: number;
    logsCount: number;
}

export interface DynamicBillingRow {
    userId: string;
    userName: string;
    userEmail: string;
    byType: Record<string, WorklogTypeSummary>;  // typeKey → summary
    totalNet: number;
    totalGross: number;
    logsCount: number;
}

