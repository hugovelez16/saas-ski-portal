import { format } from "date-fns";
import { es } from "date-fns/locale";
import { WorkLog, Company } from "@/lib/types";

export interface ReportContext {
    company?: Company;
    companyId: string;
    userId: string;
    startDate: Date;
    endDate: Date;
}

export type TextReportGenerator = (logs: WorkLog[], context: ReportContext) => string;

/**
 * Generador por defecto (la lógica original)
 */
export const defaultTextGenerator: TextReportGenerator = (logs, context) => {
    if (logs.length === 0) return "No hay registros en el periodo seleccionado.";

    // Sort logs by date ascending
    const sortedLogs = [...logs].sort((a, b) => {
        const dateA = new Date(a.date || a.startDate || a.createdAt).getTime();
        const dateB = new Date(b.date || b.startDate || b.createdAt).getTime();
        return dateA - dateB;
    });

    const summary = new Map<string, { count: number, hours: number, days: number }>();

    const lines = sortedLogs.map(log => {
        // --- SUMMARY CALCULATION ---
        const typeStr = log.type || 'Desconocido';
        if (!summary.has(typeStr)) {
            summary.set(typeStr, { count: 0, hours: 0, days: 0 });
        }
        const s = summary.get(typeStr)!;
        s.count += 1;
        s.hours += (log.durationHours || log.duration || 0);

        if (log.startDate && log.endDate && log.startDate !== log.endDate) {
            const start = new Date(log.startDate);
            const end = new Date(log.endDate);
            const diffDays = Math.round(Math.abs((end.getTime() - start.getTime()) / 86400000)) + 1;
            s.days += diffDays;
        } else {
            s.days += 1;
        }

        // --- LINE GENERATION ---
        let dateInfo = "";

        // Determine if it's a date range or a single day
        if (log.startDate && log.endDate && log.startDate !== log.endDate) {
            const startStr = format(new Date(log.startDate), 'dd/MM/yyyy');
            const endStr = format(new Date(log.endDate), 'dd/MM/yyyy');
            dateInfo = `Del ${startStr} al ${endStr}`;
        } else {
            // Single date
            const d = new Date(log.date || log.startDate || log.createdAt);
            dateInfo = format(d, 'dd/MM/yyyy');
            
            // Add time if available
            if (log.startTime && log.endTime) {
                dateInfo += ` (${log.startTime.slice(0, 5)} - ${log.endTime.slice(0, 5)})`;
            }
        }

        // Description or type
        const description = log.description ? log.description.trim() : `Turno ${log.type}`;

        return `- ${dateInfo}: ${description}`;
    });

    lines.push("\n--- RESUMEN ---");
    summary.forEach((data, type) => {
        // Formatear el nombre del tipo para que se vea "bonito" (ej: fixed_shift -> Fixed Shift)
        const typeFormatted = type
            .replace(/_/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
            
        const units = [];
        
        if (data.hours > 0) {
            units.push(`${data.hours} horas`);
        } else if (data.days > data.count) {
            units.push(`${data.days} días`);
        } else {
            units.push(`${data.count} turnos`);
        }

        lines.push(`${typeFormatted}: ${data.count} (${units.join(', ')})`);
    });

    return lines.join('\n');
};

/**
 * Ejemplo de un generador para una empresa específica.
 * Para usarlo, simplemente mapea el ID de la empresa en textGeneratorsRegistry.
 */
export const customCompanyExampleGenerator: TextReportGenerator = (logs, context) => {
    return `Reporte customizado para ${context.company?.name || 'Empresa'}...\nTotal registros: ${logs.length}\nDesde: ${format(context.startDate, 'dd/MM/yyyy')} Hasta: ${format(context.endDate, 'dd/MM/yyyy')}`;
};

/**
 * Registro central de generadores de texto.
 * La llave es el ID de la empresa (o algún identificador de configuración).
 */
export const textGeneratorsRegistry: Record<string, TextReportGenerator> = {
    'default': defaultTextGenerator,
    // Añade aquí los IDs de las empresas para las que crees formatos específicos:
    // 'id-de-la-empresa': customCompanyExampleGenerator, 
};

/**
 * Función principal para generar el texto del informe.
 * Se encarga de buscar el generador adecuado para la empresa o usa el por defecto.
 */
export function generateTextReport(logs: WorkLog[], context: ReportContext): string {
    const generatorId = context.companyId; // o context.company?.settings?.reports?.textGeneratorId
    
    const generator = textGeneratorsRegistry[generatorId] || textGeneratorsRegistry['default'];
    return generator(logs, context);
}
