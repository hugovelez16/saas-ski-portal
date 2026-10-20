import { WorkLogTypeTotals } from "@/lib/types";

export type WorklogUnit = "hours" | "days" | "fixed";

/** Definiciones de tipos de turno de la empresa (company.worklogDefinitions), indexadas por type. */
export type WorklogDefinitions = Record<string, any>;

/** Bloque de un tipo de turno con su etiqueta y unidad, a partir de byType del resumen. */
export interface ReportTypeBlock {
    type: string;
    label: string;
    unit: WorklogUnit;
    logsCount: number;
    hours: number;
    net: number;
    gross: number;
}

/**
 * Unidad de un tipo: la de la definicion de la empresa. Si no hay definicion o no tiene unit,
 * se usa 'hours' (o 'days' si la definicion es de rango, como hace el backend).
 */
export function resolveUnit(def: any): WorklogUnit {
    if (!def) return "hours";
    const unit = def.unit ?? (def.is_range ? "days" : "hours");
    if (unit === "fixed" || unit === "days") return unit;
    return "hours";
}

/** Etiqueta de un tipo: la de la definicion, o el type con la inicial en mayuscula. */
export function resolveLabel(type: string, def: any): string {
    return def?.label || type.charAt(0).toUpperCase() + type.slice(1);
}

/** Un bloque por cada tipo presente en byType (etiqueta y unidad de la definicion). */
export function buildTypeBlocks(
    byType: WorkLogTypeTotals[],
    worklogDefinitions?: WorklogDefinitions
): ReportTypeBlock[] {
    return byType.map(item => {
        const def = worklogDefinitions?.[item.type];
        return {
            type: item.type,
            label: resolveLabel(item.type, def),
            unit: resolveUnit(def),
            logsCount: item.logsCount,
            hours: item.hours,
            net: item.net,
            gross: item.gross,
        };
    });
}

/** Cantidad de un bloque segun su unidad: 'fixed' cuenta turnos; 'hours' y 'days' suman horas (duration). */
export function blockQuantity(block: ReportTypeBlock): { value: number; suffix: string } {
    if (block.unit === "fixed") return { value: block.logsCount, suffix: "turnos" };
    if (block.unit === "days") return { value: block.hours, suffix: "días" };
    return { value: block.hours, suffix: "horas" };
}

/** Texto de la cantidad de un bloque, por ejemplo "12 horas", "3 días" o "5 turnos". */
export function blockQuantityText(block: ReportTypeBlock): string {
    const { value, suffix } = blockQuantity(block);
    return `${value} ${suffix}`;
}

/** Ingresos netos por mes (clave 'MMMM yyyy' en ingles, igual que los grupos de filas) a partir de byDay. */
export function netByMonth(byDay: { date: string; net: number }[], formatMonth: (date: string) => string): Map<string, number> {
    const totals = new Map<string, number>();
    byDay.forEach(day => {
        const key = formatMonth(day.date);
        totals.set(key, (totals.get(key) ?? 0) + day.net);
    });
    return totals;
}
