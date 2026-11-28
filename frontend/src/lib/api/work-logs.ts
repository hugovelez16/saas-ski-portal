import api from '../api';
import {
    WorkLog,
    WorkLogCreate,
    BillingSummaryItem,
    WorkLogSummary,
    WorkLogReportResponse,
    WorkLogRecalculatePreview,
} from '@/lib/types';

export interface WorkLogsPageParams {
    companyId?: string;
    userId?: string;
    startDate?: string;
    endDate?: string;
    limit?: number;
    skip?: number;
}

export interface WorkLogsPage {
    items: WorkLog[];
    total: number;
}

const DEFAULT_PAGE_SIZE = 500;
const DEFAULT_MAX_ROWS = 20000;

export const getWorkLogs = async (params?: WorkLogsPageParams): Promise<WorkLog[]> => {
    const apiParams = {
        company_id: params?.companyId,
        user_id: params?.userId,
        start_date: params?.startDate,
        end_date: params?.endDate,
        limit: params?.limit,
        skip: params?.skip
    };
    const response = await api.get('/work-logs', { params: apiParams });
    return response.data;
};

/**
 * Una pagina de turnos y el total de filas que cumplen los filtros (cabecera X-Total-Count).
 * Lanza error si la cabecera no llega: nunca se asume un total.
 */
export const getWorkLogsPage = async (params?: WorkLogsPageParams): Promise<WorkLogsPage> => {
    const apiParams = {
        company_id: params?.companyId,
        user_id: params?.userId,
        start_date: params?.startDate,
        end_date: params?.endDate,
        limit: params?.limit,
        skip: params?.skip
    };
    const response = await api.get('/work-logs', { params: apiParams });
    const raw = response.headers?.['x-total-count'];
    const total = Number(raw);
    if (raw === undefined || raw === null || raw === '' || !Number.isFinite(total)) {
        throw new Error('Cabecera X-Total-Count ausente en la respuesta de /work-logs');
    }
    return { items: response.data, total };
};

/**
 * Descarga todas las filas que cumplen los filtros, paginando de `pageSize` en `pageSize`
 * hasta el total. Uso: detalle de filas (exportaciones, calendario). NUNCA para sumar:
 * los totales salen de getWorkLogSummary.
 * Si el total supera `maxRows` lanza un Error (no trunca en silencio).
 */
export const getAllWorkLogs = async (
    params?: Omit<WorkLogsPageParams, 'limit' | 'skip'>,
    opts?: { pageSize?: number; maxRows?: number }
): Promise<WorkLog[]> => {
    const pageSize = opts?.pageSize ?? DEFAULT_PAGE_SIZE;
    const maxRows = opts?.maxRows ?? DEFAULT_MAX_ROWS;
    const rows: WorkLog[] = [];
    let skip = 0;

    while (true) {
        const page = await getWorkLogsPage({ ...params, limit: pageSize, skip });
        if (page.total > maxRows) {
            throw new Error(
                `Demasiados registros para descargarlos completos: ${page.total} (maximo ${maxRows}). Reduce el rango de fechas.`
            );
        }
        rows.push(...page.items);
        skip += page.items.length;
        if (page.items.length < pageSize || rows.length >= page.total) break;
    }

    return rows;
};

/**
 * Totales, desgloses por tipo, dia y trabajador calculados por el backend sobre el rango completo.
 * Un worker solo recibe sus propios datos.
 */
export const getWorkLogSummary = async (params: {
    companyId?: string;
    userId?: string;
    startDate: string;
    endDate: string;
}): Promise<WorkLogSummary> => {
    const apiParams = {
        company_id: params.companyId,
        user_id: params.userId,
        start_date: params.startDate,
        end_date: params.endDate
    };
    const response = await api.get<WorkLogSummary>('/work-logs/summary', { params: apiParams });
    return response.data;
};

export interface WorkLogReportParams {
    companyId?: string;
    userId?: string;
    startDate: string;
    endDate: string;
    skip?: number;
    limit?: number;
    includeLogs?: boolean;
}

/**
 * Una pagina de datos de informe (resumen + filas) desde GET /work-logs/reports.
 * Exige modulo 'reports' en backend (salvo PA actuando).
 */
export const getWorkLogReport = async (params: WorkLogReportParams): Promise<WorkLogReportResponse> => {
    const apiParams = {
        company_id: params.companyId,
        user_id: params.userId,
        start_date: params.startDate,
        end_date: params.endDate,
        skip: params.skip,
        limit: params.limit,
        include_logs: params.includeLogs,
    };
    const response = await api.get<WorkLogReportResponse>('/work-logs/reports', { params: apiParams });
    return response.data;
};

/**
 * Descarga el informe completo (summary + todas las filas paginadas) desde GET /work-logs/reports.
 * Si includeLogs es false solo hace una peticion y devuelve items vacio junto al summary.
 */
export const getAllWorkLogReport = async (
    params: Omit<WorkLogReportParams, 'skip' | 'limit'>,
    opts?: { pageSize?: number; maxRows?: number }
): Promise<WorkLogReportResponse> => {
    if (params.includeLogs === false) {
        return getWorkLogReport({ ...params, includeLogs: false });
    }

    const pageSize = opts?.pageSize ?? DEFAULT_PAGE_SIZE;
    const maxRows = opts?.maxRows ?? DEFAULT_MAX_ROWS;
    const items: WorkLog[] = [];
    let skip = 0;

    const firstPage = await getWorkLogReport({ ...params, limit: pageSize, skip: 0, includeLogs: true });
    if (firstPage.total > maxRows) {
        throw new Error(
            `Demasiados registros para descargarlos completos: ${firstPage.total} (maximo ${maxRows}). Reduce el rango de fechas.`
        );
    }
    items.push(...firstPage.items);
    skip += firstPage.items.length;

    while (firstPage.items.length >= pageSize && items.length < firstPage.total) {
        const page = await getWorkLogReport({ ...params, limit: pageSize, skip, includeLogs: true });
        if (page.items.length === 0) break;
        items.push(...page.items);
        skip += page.items.length;
    }

    return {
        items,
        total: firstPage.total,
        summary: firstPage.summary,
    };
};

export const getBillingSummary = async (params: {
    companyId: string;
    startDate?: string;
    endDate?: string;
}): Promise<BillingSummaryItem[]> => {
    const apiParams = {
        company_id: params.companyId,
        start_date: params.startDate,
        end_date: params.endDate
    };
    const response = await api.get('/work-logs/billing-summary', { params: apiParams });
    return response.data;
};


export const createWorkLog = async (data: WorkLogCreate): Promise<WorkLog> => {
    const response = await api.post('/work-logs', data);
    return response.data;
};

export interface UpdateWorkLogOptions {
    /** Recalcula el importe con las tarifas actuales (solo manager y platform admin). */
    recalculateWithCurrentRates?: boolean;
}

export const previewWorkLogRecalculation = async (
    id: string,
    data: Partial<WorkLogCreate> = {},
    applyToGroup: boolean = false,
    options?: UpdateWorkLogOptions
): Promise<WorkLogRecalculatePreview> => {
    const recalculate = options?.recalculateWithCurrentRates ?? true;
    const response = await api.post<WorkLogRecalculatePreview>(
        `/work-logs/${id}/recalculate-preview?apply_to_group=${applyToGroup}&recalculate_with_current_rates=${recalculate}`,
        data
    );
    return response.data;
};

export const updateWorkLog = async (
    id: string,
    data: Partial<WorkLogCreate>,
    applyToGroup: boolean = false,
    options?: UpdateWorkLogOptions
): Promise<WorkLog> => {
    const rateQuery = options?.recalculateWithCurrentRates ? '&recalculate_with_current_rates=true' : '';
    const response = await api.put(`/work-logs/${id}?apply_to_group=${applyToGroup}${rateQuery}`, data);
    return response.data;
};

export const deleteWorkLog = async (id: string): Promise<void> => {
    await api.delete(`/work-logs/${id}`);
};
