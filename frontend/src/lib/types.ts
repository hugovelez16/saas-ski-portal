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
    viewAs?: 'manager' | 'worker' | null;
    isReadOnlyView?: boolean;
    createdAt: string;
}

export type User = UserProfile;
export type UserSettings = any; // Placeholder for legacy references

/**
 * Settings de empresa en la vista reducida (worker, manager, PA en "ver como").
 * El backend no entrega allowed_rates y puede omitir cualquier clave.
 * Ademas puede traer claves propias del miembro (notifications, ui_preferences...).
 */
export type CompanySettingsReduced = Partial<Omit<CompanySettings, 'allowed_rates'>> & Record<string, any>;

/**
 * Company Interface
 * Vista reducida por defecto. isActive, createdAt y updatedAt solo llegan en la vista completa (PA actuando).
 */
export interface Company {
    id: string;
    name: string;
    taxConfig: Record<string, number>;
    worklogDefinitions?: Record<string, any>;
    settings?: CompanySettingsReduced;
    createdAt?: string;
    updatedAt?: string;

    // UI specific
    role?: string;
    isActiveMember?: boolean;
    isManaged?: boolean;
    isActive?: boolean;
}

/**
 * Vista completa de empresa (solo PA actuando): incluye isActive, fechas y settings completo.
 */
export interface CompanyFull extends Company {
    isActive: boolean;
    createdAt: string;
    updatedAt: string;
    settings?: CompanySettings & Record<string, any>;
}

export type CompanyResponse = Company;

/**
 * Settings de empresa (catalogo CompanySettings del backend).
 * El backend entrega los valores por defecto aplicados.
 */
export interface CompanySettings {
    business_logic: {
        /** Solo afecta a la vista del dashboard. net = un unico precio. */
        price_type: 'net' | 'gross';
    };
    worker_experience: {
        input_mode: 'manual_single' | 'timer' | 'bulk';
        allow_manual_amount: boolean;
    };
    ui_customization: {
        labels: {
            worklog?: string;
            client?: string;
        };
    };
    modules: Record<string, boolean>;
    allowed_rates?: string[];
}

export interface DynamicRateEntry {
    base_rate: number;
    is_gross: boolean;
    tax_overrides: Record<string, number | null>;
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

/**
 * Parte diario (GET /companies/:id/daily-report).
 * netAmount y grossAmount solo llegan a manager y platform admin; para worker las claves estan ausentes.
 */
export interface DailyReportMember {
    userId: string;
    firstName: string | null;
    lastName: string | null;
    role: string;
    isActive: boolean;
    sortOrder: number;
}

export interface DailyReportLog {
    id: string;
    userId: string;
    companyId: string;
    type: string;
    startDate: string;
    endDate: string;
    startTime: string | null;
    endTime: string | null;
    duration: number | null;
    description: string | null;
    netAmount?: number | null;
    grossAmount?: number | null;
}

/**
 * Definicion de un tipo de turno (misma forma que una entrada de Company.worklogDefinitions).
 * label y unit siempre vienen; el resto de claves depende de la definicion de la empresa.
 */
export interface DailyReportWorkType {
    label: string;
    unit: string;
    fields?: string[];
    icon?: string;
    [key: string]: unknown;
}

export interface DailyReportResponse {
    companyId: string;
    date: string;
    members: DailyReportMember[];
    workTypes: Record<string, DailyReportWorkType>;
    logs: DailyReportLog[];
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
    warnings?: WorkLogWarning[];
}

export interface WorkLogWarning {
    code: string;
    message: string;
    conflictingLogIds: string[];
    userId?: string | null;
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

// ─── Manager Dashboard Summary ───────────────────────────────────────────

export interface DashboardPeriodMetrics {
    totalHours: number;
    totalNet: number;
    totalGross: number;
    uniqueDays: number;
    totalLogs: number;
    activeMembersCount: number;
}

export interface DashboardTodayMember {
    userId: string;
    firstName: string | null;
    lastName: string | null;
    email: string | null;
    role: string;
    hours: number;
    logsCount: number;
}

export interface DashboardTodayMetrics {
    todayHours: number;
    todayLogsCount: number;
    todayActiveMembersCount: number;
    todayActiveMembers: DashboardTodayMember[];
}

export interface DashboardTypeBreakdown {
    type: string;
    label: string;
    unit: string;
    hours: number;
    net: number;
    gross: number;
    count: number;
}

export interface DashboardDailyBreakdown {
    date: string;
    dayOfWeek: number;
    dayName: string;
    hours: number;
    net: number;
    gross: number;
    count: number;
}

export interface DashboardWorkerSummary {
    userId: string;
    firstName: string | null;
    lastName: string | null;
    email: string | null;
    role: string;
    sortOrder: number;
    isActive: boolean;
    totalHours: number;
    totalNet: number;
    totalGross: number;
    uniqueDays: number;
    logsCount: number;
    typesBreakdown: Record<string, number>;
}

export interface DashboardSummaryResponse {
    companyId: string;
    companyName: string;
    startDate: string;
    endDate: string;
    periodMetrics: DashboardPeriodMetrics;
    todayMetrics: DashboardTodayMetrics;
    typeBreakdown: DashboardTypeBreakdown[];
    dailyBreakdown: DashboardDailyBreakdown[];
    workersSummary: DashboardWorkerSummary[];
}

/** Totales globales del rango de GET /work-logs/summary (PR-07). */
export interface WorkLogTotals {
    logsCount: number;
    totalHours: number;
    totalNet: number;
    totalGross: number;
    uniqueDays: number;
    activeUsers: number;
}

/** Desglose por tipo de turno de GET /work-logs/summary. */
export interface WorkLogTypeTotals {
    type: string;
    logsCount: number;
    hours: number;
    net: number;
    gross: number;
}

/** Desglose por dia de GET /work-logs/summary (date en formato yyyy-MM-dd). */
export interface WorkLogDayTotals {
    date: string;
    logsCount: number;
    hours: number;
    net: number;
    gross: number;
}

/** Desglose por trabajador de GET /work-logs/summary. */
export interface WorkLogUserTotals {
    userId: string;
    firstName: string | null;
    lastName: string | null;
    email: string | null;
    logsCount: number;
    hours: number;
    net: number;
    gross: number;
    uniqueDays: number;
}

/** Respuesta de GET /work-logs/summary (PR-07). */
export interface WorkLogSummary {
    startDate: string;
    endDate: string;
    totals: WorkLogTotals;
    byType: WorkLogTypeTotals[];
    byDay: WorkLogDayTotals[];
    byUser: WorkLogUserTotals[];
}


