import api from '../api';
import { WorkLog, WorkLogCreate, BillingSummaryItem, WorkLogSummary } from '@/lib/types';

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

export const updateWorkLog = async (id: string, data: Partial<WorkLogCreate>, applyToGroup: boolean = false): Promise<WorkLog> => {
    const response = await api.put(`/work-logs/${id}?apply_to_group=${applyToGroup}`, data);
    return response.data;
};

export const deleteWorkLog = async (id: string): Promise<void> => {
    await api.delete(`/work-logs/${id}`);
};
