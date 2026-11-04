import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '@/lib/api';
import { getAuditLogs, getAuditActions } from '@/lib/api/audit-logs';

vi.mock('@/lib/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
    },
}));

const mockedApi = vi.mocked(api);

describe('Audit logs API Client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('getAuditLogs envia los filtros en snake_case', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: { total: 0, items: [] } });

        await getAuditLogs({
            companyId: 'c-1',
            actorUserId: 'a-1',
            targetUserId: 't-1',
            action: 'company.update',
            from: '2026-01-01T00:00:00.000Z',
            to: '2026-01-31T23:59:59.999Z',
            limit: 20,
            offset: 40,
        });

        expect(mockedApi.get).toHaveBeenCalledWith('/audit-logs', {
            params: {
                company_id: 'c-1',
                actor_user_id: 'a-1',
                target_user_id: 't-1',
                action: 'company.update',
                from: '2026-01-01T00:00:00.000Z',
                to: '2026-01-31T23:59:59.999Z',
                limit: 20,
                offset: 40,
            },
        });
    });

    it('getAuditLogs omite los filtros vacios o no informados', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: { total: 1, items: [] } });

        const result = await getAuditLogs({ companyId: '', actorUserId: undefined, action: '', limit: 50 });

        expect(mockedApi.get).toHaveBeenCalledWith('/audit-logs', { params: { limit: 50 } });
        expect(result.total).toBe(1);
    });

    it('getAuditLogs sin parametros no envia query', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: { total: 0, items: [] } });

        await getAuditLogs();

        expect(mockedApi.get).toHaveBeenCalledWith('/audit-logs', { params: {} });
    });

    it('getAuditLogs conserva offset 0 (no es un valor vacio)', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: { total: 0, items: [] } });

        await getAuditLogs({ offset: 0 });

        expect(mockedApi.get).toHaveBeenCalledWith('/audit-logs', { params: { offset: 0 } });
    });

    it('getAuditActions hace GET /audit-logs/actions y devuelve la lista', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: ['company.update', 'user.reset_2fa'] });

        const result = await getAuditActions();

        expect(mockedApi.get).toHaveBeenCalledWith('/audit-logs/actions');
        expect(result).toEqual(['company.update', 'user.reset_2fa']);
    });
});
