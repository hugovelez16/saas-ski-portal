/**
 * Tarifas publicas de la temporada 2026-2027 (importes sin IVA, por mes de temporada)
 */

export type PlanId = "basico" | "escuela" | "grande";

export interface Plan {
    id: PlanId;
    name: string;
    monthly: number;
    includedMonitors: number;
    extraMonitorFee: number;
    includedManagers: number;
    extraManagerFee: number;
    managers: string;
    modulesIncluded: boolean;
    recommended: boolean;
}

export const PLANS: readonly Plan[] = [
    {
        id: "basico",
        name: "Básico",
        monthly: 129,
        includedMonitors: 10,
        extraMonitorFee: 9,
        includedManagers: 1,
        extraManagerFee: 50,
        managers: "1 responsable",
        modulesIncluded: false,
        recommended: false,
    },
    {
        id: "escuela",
        name: "Escuela",
        monthly: 249,
        includedMonitors: 25,
        extraMonitorFee: 7,
        includedManagers: 2,
        extraManagerFee: 50,
        managers: "2 responsables",
        modulesIncluded: true,
        recommended: true,
    },
    {
        id: "grande",
        name: "Grande",
        monthly: 399,
        includedMonitors: 50,
        extraMonitorFee: 0,
        includedManagers: Infinity,
        extraManagerFee: 0,
        managers: "Responsables ilimitados",
        modulesIncluded: true,
        recommended: false,
    },
];

/** Modulos opcionales; solo se cobran en el plan Basico. */
export const EXTRAS = { sharedSchedule: 5, reports: 15 } as const;
export const SETUP_FEE = 150;
export const OFF_SEASON_FEE = 20;
export const SEASON_MONTHS = 5;
export const MAX_PRICED_MONITORS = 50;

export function getPlan(id: PlanId): Plan {
    const plan = PLANS.find((candidate) => candidate.id === id);
    if (!plan) {
        throw new Error(`Unknown landing plan: ${String(id)}`);
    }
    return plan;
}

export interface QuoteInput {
    planId: PlanId;
    monitors: number;
    /** Responsables por encima de los incluidos; sin efecto en Grande. */
    extraManagers?: number;
    /** Cuadrante compartido; ignorado si el plan lo incluye. */
    sharedSchedule?: boolean;
    /** Informes; ignorado si el plan lo incluye. */
    reports?: boolean;
}

export interface Quote {
    planId: PlanId;
    base: number;
    extraMonitors: number;
    extraMonitorsCost: number;
    extraManagers: number;
    extraManagersCost: number;
    extras: number;
    monthly: number;
    season: number;
    firstSeason: number;
}

/** Entero no negativo: no finito o menor que 0 se convierte en 0; los decimales se truncan. */
function normalizeCount(value: number): number {
    return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

/** null si monitors > MAX_PRICED_MONITORS (a consultar). */
export function quote(input: QuoteInput): Quote | null {
    const plan = getPlan(input.planId);
    const monitors = normalizeCount(input.monitors);
    if (monitors > MAX_PRICED_MONITORS) {
        return null;
    }

    const extraMonitors = Math.max(0, monitors - plan.includedMonitors);
    const extraManagers = Number.isFinite(plan.includedManagers) ? normalizeCount(input.extraManagers ?? 0) : 0;
    const extras = plan.modulesIncluded
        ? 0
        : (input.sharedSchedule ? EXTRAS.sharedSchedule : 0) + (input.reports ? EXTRAS.reports : 0);

    const extraMonitorsCost = extraMonitors * plan.extraMonitorFee;
    const extraManagersCost = extraManagers * plan.extraManagerFee;
    const monthly = plan.monthly + extraMonitorsCost + extraManagersCost + extras;
    const season = monthly * SEASON_MONTHS;

    return {
        planId: plan.id,
        base: plan.monthly,
        extraMonitors,
        extraMonitorsCost,
        extraManagers,
        extraManagersCost,
        extras,
        monthly,
        season,
        firstSeason: season + SETUP_FEE,
    };
}

export interface ExtrasChoice {
    sharedSchedule?: boolean;
    reports?: boolean;
    extraManagers?: number;
}

/**
 * Plan de menor cuota mensual para ese numero de monitores y esos extras.
 * Empate: gana el plan de mayor nivel (orden de PLANS). null si monitors > 50.
 */
export function cheapestPlan(monitors: number, extras: ExtrasChoice = {}): PlanId | null {
    let best: Quote | null = null;
    for (const plan of PLANS) {
        const current = quote({
            planId: plan.id,
            monitors,
            extraManagers: extras.extraManagers,
            sharedSchedule: extras.sharedSchedule,
            reports: extras.reports,
        });
        if (current === null) {
            return null;
        }
        if (best === null || current.monthly <= best.monthly) {
            best = current;
        }
    }
    return best?.planId ?? null;
}

function groupThousands(integerDigits: string): string {
    return integerDigits.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Formato manual: "es-ES" no agrupa los miles en cifras de cuatro digitos (1268,75) y la propuesta usa 1.268,75.
export function formatEuros(amount: number): string {
    const [integer, decimals] = amount.toFixed(2).split(".");
    return `${groupThousands(integer)},${decimals} €`;
}

/** Enteros sin decimales ("129 €", "1.245 €"); el resto usa formatEuros. */
export function formatEurosCompact(amount: number): string {
    if (!Number.isInteger(amount)) {
        return formatEuros(amount);
    }
    return `${groupThousands(String(amount))} €`;
}
