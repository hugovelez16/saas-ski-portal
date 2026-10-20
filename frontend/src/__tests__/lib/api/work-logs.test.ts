import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { WorkLog, WorkLogCreate } from '@/lib/types';

// Mock the api module
vi.mock('@/lib/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
    },
}));

import api from '@/lib/api';
import {
    getWorkLogs,
    getWorkLogsPage,
    getAllWorkLogs,
    getWorkLogSummary,
    createWorkLog,
    updateWorkLog,
    deleteWorkLog
} from '@/lib/api/work-logs';

const mockedApi = vi.mocked(api);

const rowsOf = (from: number, count: number): Partial<WorkLog>[] =>
    Array.from({ length: count }, (_, i) => ({ id: `wl-${from + i}`, userId: 'u-1' }));

describe('Work Logs API Client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('getWorkLogsPage', () => {
        it('should return items and the total from X-Total-Count', async () => {
            (mockedApi.get as any).mockResolvedValue({
                data: rowsOf(0, 2),
                headers: { 'x-total-count': '1234' },
            });

            const result = await getWorkLogsPage({ companyId: 'c-1', limit: 50, skip: 100 });

            expect(mockedApi.get).toHaveBeenCalledWith('/work-logs', {
                params: {
                    company_id: 'c-1',
                    user_id: undefined,
                    start_date: undefined,
                    end_date: undefined,
                    limit: 50,
                    skip: 100,
                },
            });
            expect(result.items).toHaveLength(2);
            expect(result.total).toBe(1234);
        });

        it('should throw when the X-Total-Count header is missing', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [], headers: {} });

            await expect(getWorkLogsPage({ companyId: 'c-1' })).rejects.toThrow('X-Total-Count');
        });
    });

    describe('getAllWorkLogs', () => {
        it('should page in chunks of 500 until the total is reached', async () => {
            (mockedApi.get as any)
                .mockResolvedValueOnce({ data: rowsOf(0, 500), headers: { 'x-total-count': '1200' } })
                .mockResolvedValueOnce({ data: rowsOf(500, 500), headers: { 'x-total-count': '1200' } })
                .mockResolvedValueOnce({ data: rowsOf(1000, 200), headers: { 'x-total-count': '1200' } });

            const result = await getAllWorkLogs({ companyId: 'c-1', startDate: '2026-01-01', endDate: '2026-01-31' });

            expect(result).toHaveLength(1200);
            expect(mockedApi.get).toHaveBeenCalledTimes(3);
            expect(mockedApi.get).toHaveBeenNthCalledWith(1, '/work-logs', {
                params: expect.objectContaining({ company_id: 'c-1', start_date: '2026-01-01', end_date: '2026-01-31', limit: 500, skip: 0 }),
            });
            expect(mockedApi.get).toHaveBeenNthCalledWith(2, '/work-logs', {
                params: expect.objectContaining({ limit: 500, skip: 500 }),
            });
            expect(mockedApi.get).toHaveBeenNthCalledWith(3, '/work-logs', {
                params: expect.objectContaining({ limit: 500, skip: 1000 }),
            });
        });

        it('should stop after one request when the total fits in one page', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: rowsOf(0, 3), headers: { 'x-total-count': '3' } });

            const result = await getAllWorkLogs({ companyId: 'c-1' });

            expect(result).toHaveLength(3);
            expect(mockedApi.get).toHaveBeenCalledTimes(1);
        });

        it('should return an empty list without extra requests when there are no rows', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [], headers: { 'x-total-count': '0' } });

            const result = await getAllWorkLogs({ companyId: 'c-1' });

            expect(result).toEqual([]);
            expect(mockedApi.get).toHaveBeenCalledTimes(1);
        });

        it('should throw a clear error instead of truncating when total exceeds maxRows', async () => {
            (mockedApi.get as any).mockResolvedValueOnce({ data: rowsOf(0, 500), headers: { 'x-total-count': '5000' } });

            await expect(getAllWorkLogs({ companyId: 'c-1' }, { maxRows: 700 })).rejects.toThrow('maximo 700');
            expect(mockedApi.get).toHaveBeenCalledTimes(1);
        });

        it('should throw with the default maxRows of 20000 when the total is above it', async () => {
            (mockedApi.get as any).mockResolvedValueOnce({ data: rowsOf(0, 500), headers: { 'x-total-count': '20001' } });

            await expect(getAllWorkLogs({ companyId: 'c-1' })).rejects.toThrow('maximo 20000');
            expect(mockedApi.get).toHaveBeenCalledTimes(1);
        });

        it('should return every row when the total is exactly maxRows', async () => {
            (mockedApi.get as any).mockImplementation(async (_url: string, config: any) => ({
                data: rowsOf(config.params.skip, config.params.limit),
                headers: { 'x-total-count': '20000' },
            }));

            const result = await getAllWorkLogs({ companyId: 'c-1' });

            expect(result).toHaveLength(20000);
            expect(mockedApi.get).toHaveBeenCalledTimes(40);
        });

        it('should honour a custom pageSize', async () => {
            (mockedApi.get as any)
                .mockResolvedValueOnce({ data: rowsOf(0, 100), headers: { 'x-total-count': '150' } })
                .mockResolvedValueOnce({ data: rowsOf(100, 50), headers: { 'x-total-count': '150' } });

            const result = await getAllWorkLogs({ companyId: 'c-1' }, { pageSize: 100 });

            expect(result).toHaveLength(150);
            expect(mockedApi.get).toHaveBeenNthCalledWith(2, '/work-logs', {
                params: expect.objectContaining({ limit: 100, skip: 100 }),
            });
        });
    });

    describe('getWorkLogSummary', () => {
        it('should GET /work-logs/summary with snake_case params and return the body', async () => {
            const summary = {
                startDate: '2026-01-01',
                endDate: '2026-01-31',
                totals: { logsCount: 2, totalHours: 3, totalNet: 90, totalGross: 100, uniqueDays: 1, activeUsers: 1 },
                byType: [],
                byDay: [],
                byUser: [],
            };
            (mockedApi.get as any).mockResolvedValue({ data: summary });

            const result = await getWorkLogSummary({
                companyId: 'c-1',
                userId: 'u-1',
                startDate: '2026-01-01',
                endDate: '2026-01-31',
            });

            expect(mockedApi.get).toHaveBeenCalledWith('/work-logs/summary', {
                params: {
                    company_id: 'c-1',
                    user_id: 'u-1',
                    start_date: '2026-01-01',
                    end_date: '2026-01-31',
                },
            });
            expect(result).toEqual(summary);
        });
    });

    describe('getWorkLogs', () => {
        it('should call /work-logs with no params when none provided', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [] });

            const result = await getWorkLogs();

            expect(mockedApi.get).toHaveBeenCalledWith('/work-logs', {
                params: {
                    company_id: undefined,
                    user_id: undefined,
                    start_date: undefined,
                    end_date: undefined,
                    limit: undefined,
                    skip: undefined,
                },
            });
            expect(result).toEqual([]);
        });

        it('should map camelCase params to snake_case for the backend', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [] });

            await getWorkLogs({
                companyId: 'comp-1',
                userId: 'user-1',
                startDate: '2026-01-01',
                endDate: '2026-01-31',
                limit: 100,
                skip: 0,
            });

            expect(mockedApi.get).toHaveBeenCalledWith('/work-logs', {
                params: {
                    company_id: 'comp-1',
                    user_id: 'user-1',
                    start_date: '2026-01-01',
                    end_date: '2026-01-31',
                    limit: 100,
                    skip: 0,
                },
            });
        });

        it('should return the data from the response', async () => {
            const mockLogs: Partial<WorkLog>[] = [
                { id: 'wl-1', type: 'particular', userId: 'u-1' },
                { id: 'wl-2', type: 'tutorial', userId: 'u-2' },
            ];
            (mockedApi.get as any).mockResolvedValue({ data: mockLogs });

            const result = await getWorkLogs({ companyId: 'c-1' });

            expect(result).toEqual(mockLogs);
            expect(result).toHaveLength(2);
        });
    });

    describe('createWorkLog', () => {
        it('should POST to /work-logs with the data', async () => {
            const newLog: WorkLogCreate = {
                type: 'particular',
                companyId: 'c-1',
                userId: 'u-1',
                startDate: '2026-01-15',
                endDate: '2026-01-15',
            };
            const mockResponse = { id: 'wl-new', ...newLog };
            (mockedApi.post as any).mockResolvedValue({ data: mockResponse });

            const result = await createWorkLog(newLog);

            expect(mockedApi.post).toHaveBeenCalledWith('/work-logs', newLog);
            expect(result).toEqual(mockResponse);
        });
    });

    describe('updateWorkLog', () => {
        it('should PUT to /work-logs/:id with partial data', async () => {
            const update: Partial<WorkLogCreate> = { description: 'Updated' };
            const mockResponse = { id: 'wl-1', description: 'Updated' };
            (mockedApi.put as any).mockResolvedValue({ data: mockResponse });

            const result = await updateWorkLog('wl-1', update);

            expect(mockedApi.put).toHaveBeenCalledWith('/work-logs/wl-1?apply_to_group=false', update);
            expect(result).toEqual(mockResponse);
        });
    });

    describe('deleteWorkLog', () => {
        it('should DELETE /work-logs/:id', async () => {
            (mockedApi.delete as any).mockResolvedValue({});

            await deleteWorkLog('wl-1');

            expect(mockedApi.delete).toHaveBeenCalledWith('/work-logs/wl-1');
        });
    });
});
