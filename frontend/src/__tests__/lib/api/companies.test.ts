import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '@/lib/api';
import {
    createCompany,
    updateCompany,
    getCompanies,
    getCompany,
    getCompaniesDetailed,
    getMyCompanies,
    updateMemberStatus,
    addCompanyMember,
    updateCompanyMember,
    getCompanyRates,
    getCompanyMembers,
    updateCompanyMembersOrder,
    getCompanyDashboardSummary
} from '@/lib/api/companies';

vi.mock('@/lib/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
    },
}));

const mockedApi = vi.mocked(api);

describe('Companies API Client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('createCompany should POST /companies', async () => {
        const payload = { name: 'Escuela Sierra', isManaged: true };
        (mockedApi.post as any).mockResolvedValue({ data: { id: 'c-1', ...payload } });

        const result = await createCompany(payload);
        expect(mockedApi.post).toHaveBeenCalledWith('/companies', payload);
        expect(result.id).toBe('c-1');
    });

    it('updateCompany should PUT /companies/:id', async () => {
        const payload = { name: 'Escuela Actualizada' };
        (mockedApi.put as any).mockResolvedValue({ data: { id: 'c-1', ...payload } });

        const result = await updateCompany('c-1', payload);
        expect(mockedApi.put).toHaveBeenCalledWith('/companies/c-1', payload);
        expect(result.name).toBe('Escuela Actualizada');
    });

    it('getCompanies should GET /companies', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [{ id: 'c-1', name: 'Escuela 1' }] });

        const result = await getCompanies();
        expect(mockedApi.get).toHaveBeenCalledWith('/companies');
        expect(result).toHaveLength(1);
    });

    it('getCompany should GET /companies/:id', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: { id: 'c-1', name: 'Escuela 1' } });

        const result = await getCompany('c-1');
        expect(mockedApi.get).toHaveBeenCalledWith('/companies/c-1');
        expect(result.id).toBe('c-1');
    });

    it('getCompaniesDetailed should GET /companies/detailed', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [{ id: 'c-1', members: [] }] });

        const result = await getCompaniesDetailed();
        expect(mockedApi.get).toHaveBeenCalledWith('/companies/detailed');
        expect(result).toHaveLength(1);
    });

    it('getMyCompanies should GET /users/me/companies', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [{ id: 'c-1' }] });

        const result = await getMyCompanies();
        expect(mockedApi.get).toHaveBeenCalledWith('/users/me/companies');
        expect(result).toHaveLength(1);
    });

    it('updateMemberStatus should PUT status parameter', async () => {
        (mockedApi.put as any).mockResolvedValue({ data: { status: 'active' } });

        const result = await updateMemberStatus('c-1', 'u-1', 'active');
        expect(mockedApi.put).toHaveBeenCalledWith('/companies/c-1/members/u-1/status?status=active');
        expect(result.status).toBe('active');
    });

    it('addCompanyMember should POST /companies/:id/members/add', async () => {
        (mockedApi.post as any).mockResolvedValue({ data: { userId: 'u-2' } });

        const result = await addCompanyMember('c-1', 'test@test.com');
        expect(mockedApi.post).toHaveBeenCalledWith('/companies/c-1/members/add', { email: 'test@test.com' });
        expect(result.userId).toBe('u-2');
    });

    it('updateCompanyMember should PUT /companies/:id/members/:userId', async () => {
        const payload = { role: 'manager' };
        (mockedApi.put as any).mockResolvedValue({ data: { userId: 'u-1', role: 'manager' } });

        const result = await updateCompanyMember('c-1', 'u-1', payload);
        expect(mockedApi.put).toHaveBeenCalledWith('/companies/c-1/members/u-1', payload);
        expect(result.role).toBe('manager');
    });

    it('getCompanyRates should GET /companies/:id/rates-v2', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [] });

        const result = await getCompanyRates('c-1');
        expect(mockedApi.get).toHaveBeenCalledWith('/companies/c-1/rates-v2');
        expect(result).toEqual([]);
    });

    it('getCompanyMembers should GET /companies/:id/members with optional status', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [] });

        await getCompanyMembers('c-1', 'active');
        expect(mockedApi.get).toHaveBeenCalledWith('/companies/c-1/members', { params: { status: 'active' } });
    });

    it('updateCompanyMembersOrder should PUT /companies/:id/members/order', async () => {
        (mockedApi.put as any).mockResolvedValue({ data: { success: true } });

        const result = await updateCompanyMembersOrder('c-1', ['u-1', 'u-2']);
        expect(mockedApi.put).toHaveBeenCalledWith('/companies/c-1/members/order', { userIds: ['u-1', 'u-2'] });
        expect(result.success).toBe(true);
    });

    it('getCompanyDashboardSummary should GET /companies/:id/dashboard-summary with dates', async () => {
        (mockedApi.get as any).mockResolvedValue({
            data: {
                periodMetrics: { totalHours: 10, totalNet: 200, totalGross: 250, uniqueDays: 2, totalLogs: 5, activeMembersCount: 2 },
                todayMetrics: { todayHours: 4, todayLogsCount: 2, todayActiveMembersCount: 1, activeMembers: [] },
                typeBreakdown: [],
                weekdayBreakdown: [],
                timeSeries: [],
                workersSummary: []
            }
        });

        const result = await getCompanyDashboardSummary('c-1', {
            startDate: '2026-09-01',
            endDate: '2026-09-30'
        });

        expect(mockedApi.get).toHaveBeenCalledWith('/companies/c-1/dashboard-summary', {
            params: {
                start_date: '2026-09-01',
                end_date: '2026-09-30'
            }
        });
        expect(result.periodMetrics.totalHours).toBe(10);
    });
});
