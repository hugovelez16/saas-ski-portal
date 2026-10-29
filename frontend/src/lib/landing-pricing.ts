/**
 * Tarifas publicas de la temporada 2026-2027 (importes sin IVA, por mes de temporada).
 * Fuente: docs/propuesta-iliberis.md.
 */
export const BASE_FEE = 150;
export const EXTRA_MANAGER_FEE = 50;
export const SETUP_FEE = 150;
export const OFF_SEASON_FEE = 20;
export const SEASON_MONTHS = 5;
export const MAX_PRICED_MONITORS = 50;

export const MODULE_FEES = {
    reports: 15,
    teamDailyReport: 5,
} as const;

/** Tramos marginales: cada precio se aplica solo a los monitores que caen en su tramo. */
export const MONITOR_TIERS = [
    { from: 1, to: 10, price: 5 },
    { from: 11, to: 20, price: 4.75 },
    { from: 21, to: 30, price: 4.5 },
    { from: 31, to: 40, price: 4.25 },
    { from: 41, to: 50, price: 4 },
] as const;

export function monitorsMonthlyCost(monitors: number): number {
    const count = Math.min(Math.max(0, Math.floor(monitors)), MAX_PRICED_MONITORS);
    return MONITOR_TIERS.reduce((total, tier) => {
        const inTier = Math.max(0, Math.min(count, tier.to) - tier.from + 1);
        return total + inTier * tier.price;
    }, 0);
}

export interface QuoteInput {
    monitors: number;
    extraManagers?: number;
    reports?: boolean;
    teamDailyReport?: boolean;
}

export interface Quote {
    monitors: number;
    modules: number;
    monthly: number;
    season: number;
    firstSeason: number;
}

export function quote({ monitors, extraManagers = 0, reports = false, teamDailyReport = false }: QuoteInput): Quote {
    const monitorsCost = monitorsMonthlyCost(monitors);
    const modules = (reports ? MODULE_FEES.reports : 0) + (teamDailyReport ? MODULE_FEES.teamDailyReport : 0);
    const monthly = BASE_FEE + Math.max(0, extraManagers) * EXTRA_MANAGER_FEE + monitorsCost + modules;
    const season = monthly * SEASON_MONTHS;
    return { monitors: monitorsCost, modules, monthly, season, firstSeason: season + SETUP_FEE };
}

// Formato manual: "es-ES" no agrupa los miles en cifras de cuatro digitos (1268,75) y la propuesta usa 1.268,75.
export function formatEuros(amount: number): string {
    const [integer, decimals] = amount.toFixed(2).split(".");
    return `${integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${decimals} €`;
}
