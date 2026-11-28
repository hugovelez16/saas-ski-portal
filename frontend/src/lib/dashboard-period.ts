import type { DashboardPeriod } from "@/components/manager/dashboard/dashboard-kpis";

export interface SavedDashboardPeriod {
    period: DashboardPeriod;
    from?: string;
    to?: string;
}

const VALID_PERIODS: DashboardPeriod[] = ["today", "week", "month", "last_month", "season", "custom"];
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function isValidDate(value: unknown): value is string {
    if (typeof value !== "string" || !DATE_PATTERN.test(value)) return false;
    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

export function getDashboardPeriod(companyId: string): SavedDashboardPeriod | null {
    try {
        const raw = localStorage.getItem(`dashboardPeriod:${companyId}`);
        if (!raw) return null;
        const value: unknown = JSON.parse(raw);
        if (!value || typeof value !== "object") return null;
        const saved = value as Record<string, unknown>;
        if (!VALID_PERIODS.includes(saved.period as DashboardPeriod)) return null;
        if (saved.period !== "custom") return { period: saved.period as DashboardPeriod };
        if (!isValidDate(saved.from) || !isValidDate(saved.to) || saved.from > saved.to) return null;
        return { period: "custom", from: saved.from, to: saved.to };
    } catch {
        return null;
    }
}

export function setDashboardPeriod(companyId: string, value: SavedDashboardPeriod): void {
    try {
        const saved = value.period === "custom"
            ? { period: value.period, from: value.from, to: value.to }
            : { period: value.period };
        localStorage.setItem(`dashboardPeriod:${companyId}`, JSON.stringify(saved));
    } catch {
        // Storage no disponible: se omite la preferencia sin interrumpir el dashboard.
    }
}
