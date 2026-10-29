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
    updateMemberRole,
    updateMemberRates,
    updateMemberSettings,
    removeCompanyMember,
    getCompanyRates,
    getCompanyMembers,
    updateCompanyMembersOrder,
    getCompanyDashboardSummary,
    getDailyReport
} from '@/lib/api/companies';
import type { CompanyResponse } from '@/lib/types';

vi.mock('@/lib/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
    },
}));

const mockedApi = vi.mocked(api);

const REDUCED_COMPANY_KEYS = [
    'id', 'name', 'isManaged', 'role', 'isActiveMember', 'ratesConfig',
    'worklogDefinitions', 'taxConfig', 'settings'
].sort();

// Respuesta v2 (snake_case) de la vista reducida.
const reducedCompanyV2 = {
    id: 'c-1',
    name: 'Escuela 1',
    is_managed: true,
    role: 'worker',
    is_active_member: true,
    rates_config: {},
    worklog_definitions: {},
    tax_config: { iva: 21 },
    settings: {
        worker_experience: { input_mode: 'timer', allow_manual_amount: false },
        ui_customization: { labels: {} },
        modules: { reports: true },
        business_logic: { price_type: 'net' },
    },
};

const memberV2 = {
    user_id: 'u-1',
    company_id: 'c-1',
    role: 'worker',
    is_active: true,
    sort_order: 0,
    rates_config: { particular: { base_rate: 10 } },
    settings: { allow_tutorial: false },
    joined_at: '2026-01-01T00:00:00',
    updated_at: null,
    user: { id: 'u-1', email: 'ana@b.c', first_name: 'Ana', last_name: 'Lopez', is_active: true },
};

// Vista reducida (sin is_active) de una empresa donde el usuario es manager o worker.
const reducedManagerV2 = { ...reducedCompanyV2, id: 'c-1', role: 'manager' };
const reducedWorkerV2 = { ...reducedCompanyV2, id: 'c-2', name: 'Escuela 2', role: 'worker' };

// Responde a cada GET segun la URL; una URL no prevista falla el test.
const mockGetRoutes = (routes: Record<string, unknown>) => {
    (mockedApi.get as any).mockImplementation(async (url: string) => {
        if (!(url in routes)) throw new Error(`GET no esperado: ${url}`);
        return { data: routes[url] };
    });
};

// Empresa manager en la vista reducida; GET de miembros falla con `error`.
const mockRejectMembers = (error: unknown) => {
    (mockedApi.get as any).mockImplementation(async (url: string) => {
        if (url === '/v2/me/companies') return { data: [reducedManagerV2] };
        if (url === '/v2/companies/c-1/members') throw error;
        throw new Error(`GET no esperado: ${url}`);
    });
};

describe('Companies API Client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('createCompany should POST /v2/companies with snake_case body and return camelCase', async () => {
        const payload = { name: 'Escuela Sierra', taxConfig: { iva: 21 }, isManaged: true };
        (mockedApi.post as any).mockResolvedValue({
            data: { id: 'c-1', name: 'Escuela Sierra', is_active: true, is_managed: true, tax_config: { iva: 21 }, worklog_definitions: {}, settings: {}, created_at: null, updated_at: null },
        });

        const result = await createCompany(payload);
        expect(mockedApi.post).toHaveBeenCalledWith('/v2/companies', { name: 'Escuela Sierra', tax_config: { iva: 21 }, is_managed: true });
        expect(result.id).toBe('c-1');
        expect(result.isManaged).toBe(true);
        expect(result.taxConfig).toEqual({ iva: 21 });
        expect(result).not.toHaveProperty('tax_config');
    });

    it('updateCompany should PUT /v2/companies/:id with snake_case body and return camelCase', async () => {
        const payload = { name: 'Escuela Actualizada' };
        (mockedApi.put as any).mockResolvedValue({ data: { id: 'c-1', name: 'Escuela Actualizada', is_active: true } });

        const result = await updateCompany('c-1', payload);
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1', { name: 'Escuela Actualizada' });
        expect(result.name).toBe('Escuela Actualizada');
        expect(result.isActive).toBe(true);
    });

    it('updateCompany should send reason only as audit payload field', async () => {
        const payload = { isActive: false, reason: 'Impago' };
        (mockedApi.put as any).mockResolvedValue({ data: { id: 'c-1', is_active: false } });

        const result = await updateCompany('c-1', payload);
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1', { is_active: false, reason: 'Impago' });
        expect(result.isActive).toBe(false);
        expect(result).not.toHaveProperty('is_active');
    });

    it('getCompanies should GET /v2/companies with limit 2000 and return camelCase items', async () => {
        (mockedApi.get as any).mockResolvedValue({
            data: { items: [{ id: 'c-1', name: 'Escuela 1', is_active: false }], total: 1 },
        });

        const result = await getCompanies();
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies', { params: { limit: 2000 } });
        expect(result).toHaveLength(1);
        expect(result[0].isActive).toBe(false);
    });

    it('getCompany should GET /v2/companies/:id', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: { id: 'c-1', name: 'Escuela 1', is_active: true } });

        const result = await getCompany('c-1');
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1');
        expect(result.id).toBe('c-1');
        expect(result.isActive).toBe(true);
    });

    it('getCompany should keep the reduced view shape without PA-only fields', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: reducedCompanyV2 });

        const result: CompanyResponse = await getCompany('c-1');
        expect(Object.keys(result).sort()).toEqual(REDUCED_COMPANY_KEYS);
        expect(result).not.toHaveProperty('isActive');
        expect(result).not.toHaveProperty('createdAt');
        expect(result).not.toHaveProperty('updatedAt');
        expect(result.settings).not.toHaveProperty('allowed_rates');
    });

    it('getCompaniesDetailed should GET /v2/companies with include=members for PA (full view) and map members to camelCase', async () => {
        mockGetRoutes({
            '/v2/me/companies': [{
                id: 'c-1', name: 'Escuela 1', is_active: true, is_managed: true,
                tax_config: {}, worklog_definitions: {}, settings: {}, created_at: null, updated_at: null,
            }],
            '/v2/companies': {
                items: [{
                    id: 'c-1', name: 'Escuela 1', is_active: true, is_managed: true,
                    tax_config: {}, worklog_definitions: {}, settings: {}, created_at: null, updated_at: null,
                    members: [memberV2],
                }],
                total: 1,
            },
        });

        const result = await getCompaniesDetailed();
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/me/companies');
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies', { params: { include: 'members', limit: 2000 } });
        expect(mockedApi.get).not.toHaveBeenCalledWith('/v2/companies/c-1/members', expect.anything());
        expect(result).toHaveLength(1);
        expect(result[0].isManaged).toBe(true);

        const member = result[0].members[0];
        expect(member.userId).toBe('u-1');
        expect(member.companyId).toBe('c-1');
        expect(member.isActive).toBe(true);
        expect(member.ratesConfig).toEqual({ particular: { base_rate: 10 } });
        expect(member.joinedAt).toBe('2026-01-01T00:00:00');
        expect(member.user?.firstName).toBe('Ana');
        expect(member.user?.isActive).toBe(true);
        expect(member).not.toHaveProperty('user_id');
    });

    it('getCompaniesDetailed should return members as [] when the PA company has no members key', async () => {
        mockGetRoutes({
            '/v2/me/companies': [{ id: 'c-2', name: 'Sin miembros', is_active: true }],
            '/v2/companies': { items: [{ id: 'c-2', name: 'Sin miembros', is_active: true }], total: 1 },
        });

        const result = await getCompaniesDetailed();
        expect(result[0].members).toEqual([]);
    });

    it('getCompaniesDetailed should GET /v2/companies/:id/members for manager companies (reduced view) and map members to camelCase', async () => {
        mockGetRoutes({
            '/v2/me/companies': [reducedManagerV2],
            '/v2/companies/c-1/members': [memberV2],
        });

        const result = await getCompaniesDetailed();
        expect(mockedApi.get).toHaveBeenCalledTimes(2);
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/members', { params: undefined, meta: { silent: true } });
        expect(mockedApi.get).not.toHaveBeenCalledWith('/v2/companies', expect.anything());
        expect(result).toHaveLength(1);
        expect(result[0].id).toBe('c-1');
        expect(result[0].members).toHaveLength(1);
        expect(result[0].members[0].userId).toBe('u-1');
        expect(result[0].members[0].isActive).toBe(true);
        expect(result[0].members[0].user?.firstName).toBe('Ana');
        expect(result[0].members[0]).not.toHaveProperty('user_id');
    });

    it('getCompaniesDetailed should return members as [] for worker companies without requesting members', async () => {
        mockGetRoutes({
            '/v2/me/companies': [reducedWorkerV2],
        });

        const result = await getCompaniesDetailed();
        expect(mockedApi.get).toHaveBeenCalledTimes(1);
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/me/companies');
        expect(result).toHaveLength(1);
        expect(result[0].members).toEqual([]);
    });

    it('getCompaniesDetailed should request members only for manager companies in a mixed reduced list', async () => {
        mockGetRoutes({
            '/v2/me/companies': [reducedManagerV2, reducedWorkerV2],
            '/v2/companies/c-1/members': [memberV2],
        });

        const result = await getCompaniesDetailed();
        const memberCalls = (mockedApi.get as any).mock.calls.filter(([url]: [string]) => url.endsWith('/members'));
        expect(memberCalls).toEqual([['/v2/companies/c-1/members', { params: undefined, meta: { silent: true } }]]);
        expect(result.map((company) => company.id)).toEqual(['c-1', 'c-2']);
        expect(result[0].members).toHaveLength(1);
        expect(result[1].members).toEqual([]);
    });

    it('getCompaniesDetailed should load members for a reduced company with role admin', async () => {
        mockGetRoutes({
            '/v2/me/companies': [{ ...reducedCompanyV2, id: 'c-3', role: 'admin' }],
            '/v2/companies/c-3/members': [memberV2],
        });

        const result = await getCompaniesDetailed();
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-3/members', { params: undefined, meta: { silent: true } });
        expect(result).toHaveLength(1);
        expect(result[0].members).toHaveLength(1);
        expect(result[0].members[0].userId).toBe('u-1');
        expect(result[0].members[0]).not.toHaveProperty('user_id');
    });

    it('getCompaniesDetailed should return members as [] when listMembers answers 403', async () => {
        const forbidden = Object.assign(new Error('Forbidden'), { response: { status: 403 } });
        mockRejectMembers(forbidden);

        const result = await getCompaniesDetailed();
        expect(result).toHaveLength(1);
        expect(result[0].id).toBe('c-1');
        expect(result[0].members).toEqual([]);
    });

    it('getCompaniesDetailed should propagate listMembers errors other than 403', async () => {
        const serverError = Object.assign(new Error('Internal Server Error'), { response: { status: 500 } });
        mockRejectMembers(serverError);

        await expect(getCompaniesDetailed()).rejects.toBe(serverError);
    });

    it('getCompaniesDetailed should return [] without calling /v2/companies when the user has no companies', async () => {
        mockGetRoutes({ '/v2/me/companies': [] });

        const result = await getCompaniesDetailed();
        expect(result).toEqual([]);
        expect(mockedApi.get).toHaveBeenCalledTimes(1);
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/me/companies');
        expect(mockedApi.get).not.toHaveBeenCalledWith('/v2/companies', expect.anything());
    });

    it('getMyCompanies should GET /v2/me/companies', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [{ id: 'c-1', name: 'Escuela 1', is_managed: false }] });

        const result = await getMyCompanies();
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/me/companies');
        expect(result).toHaveLength(1);
        expect(result[0].isManaged).toBe(false);
    });

    it('getMyCompanies should keep the reduced view shape without PA-only fields', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [reducedCompanyV2] });

        const result: CompanyResponse[] = await getMyCompanies();
        expect(result).toHaveLength(1);
        expect(Object.keys(result[0]).sort()).toEqual(REDUCED_COMPANY_KEYS);
        expect(result[0]).not.toHaveProperty('isActive');
        expect(result[0]).not.toHaveProperty('createdAt');
        expect(result[0]).not.toHaveProperty('updatedAt');
        expect(result[0].settings).not.toHaveProperty('allowed_rates');
    });

    it('getMyCompanies should add role admin and isActiveMember true to the full view', async () => {
        (mockedApi.get as any).mockResolvedValue({
            data: [{
                id: 'c-1', name: 'Escuela 1', is_active: true, is_managed: true,
                tax_config: {}, worklog_definitions: {}, settings: {}, created_at: null, updated_at: null,
            }],
        });

        const result = await getMyCompanies();
        expect(result).toHaveLength(1);
        expect(result[0].role).toBe('admin');
        expect(result[0].isActiveMember).toBe(true);
        expect(result[0].isActive).toBe(true);
        expect(result[0].isManaged).toBe(true);
        expect(result[0]).not.toHaveProperty('is_active');
    });

    it('updateMemberStatus should PUT /v2/companies/:id/members/:userId/status with { is_active: true }', async () => {
        (mockedApi.put as any).mockResolvedValue({ data: memberV2 });

        const result = await updateMemberStatus('c-1', 'u-1', 'active');
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/status', { is_active: true });
        expect(result.userId).toBe('u-1');
        expect(result.isActive).toBe(true);
    });

    it.each(['approved', 'true', '1'])('updateMemberStatus should map status "%s" to is_active true', async (status) => {
        (mockedApi.put as any).mockResolvedValue({ data: memberV2 });

        await updateMemberStatus('c-1', 'u-1', status);
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/status', { is_active: true });
    });

    it.each(['inactive', 'false', ''])('updateMemberStatus should map status "%s" to is_active false', async (status) => {
        (mockedApi.put as any).mockResolvedValue({ data: { ...memberV2, is_active: false } });

        const result = await updateMemberStatus('c-1', 'u-1', status);
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/status', { is_active: false });
        expect(result.isActive).toBe(false);
    });

    it('addCompanyMember should POST /v2/companies/:id/members with { email }', async () => {
        (mockedApi.post as any).mockResolvedValue({ data: { ...memberV2, user_id: 'u-2' } });

        const result = await addCompanyMember('c-1', 'test@test.com');
        expect(mockedApi.post).toHaveBeenCalledWith('/v2/companies/c-1/members', { email: 'test@test.com' });
        expect(result.userId).toBe('u-2');
    });

    it('updateMemberRole should PUT /v2/companies/:id/members/:userId/role with { role }', async () => {
        (mockedApi.put as any).mockResolvedValue({ data: { ...memberV2, role: 'manager' } });

        const result = await updateMemberRole('c-1', 'u-1', 'manager');
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/role', { role: 'manager' });
        expect(result.role).toBe('manager');
    });

    it('updateMemberRates should PUT /v2/companies/:id/members/:userId/rates with { rates_config }', async () => {
        const ratesConfig = { particular: { base_rate: 10 } };
        (mockedApi.put as any).mockResolvedValue({ data: memberV2 });

        const result = await updateMemberRates('c-1', 'u-1', ratesConfig);
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/rates', { rates_config: ratesConfig });
        expect(result.userId).toBe('u-1');
        expect(result.ratesConfig).toEqual(ratesConfig);
    });

    it('updateMemberSettings should PUT /v2/companies/:id/members/:userId/settings with { settings }', async () => {
        const settings = { allow_tutorial: false };
        (mockedApi.put as any).mockResolvedValue({ data: { ...memberV2, settings } });

        const result = await updateMemberSettings('c-1', 'u-1', settings);
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/settings', { settings });
        expect(result.settings).toEqual(settings);
    });

    it('removeCompanyMember should DELETE /v2/companies/:id/members/:userId', async () => {
        const body = { deleted: true, deactivated: false, reason: null };
        (mockedApi.delete as any).mockResolvedValue({ data: body });

        const result = await removeCompanyMember('c-1', 'u-1');
        expect(mockedApi.delete).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1');
        expect(result).toEqual(body);
    });

    it('getCompanyRates should GET /v2/companies/:id/rates and map members to camelCase', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [memberV2] });

        const result = await getCompanyRates('c-1');
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/rates');
        expect(result).toHaveLength(1);
        expect(result[0].userId).toBe('u-1');
        expect(result[0].ratesConfig).toEqual({ particular: { base_rate: 10 } });
    });

    it('getCompanyMembers should GET /v2/companies/:id/members with is_active true for status "active"', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [memberV2] });

        const result = await getCompanyMembers('c-1', 'active');
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/members', { params: { is_active: true } });
        expect(result[0].isActive).toBe(true);
    });

    it('getCompanyMembers should send is_active false for status "inactive"', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [] });

        await getCompanyMembers('c-1', 'inactive');
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/members', { params: { is_active: false } });
    });

    it('getCompanyMembers should send no filter when status is omitted', async () => {
        (mockedApi.get as any).mockResolvedValue({ data: [] });

        await getCompanyMembers('c-1');
        expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/members', { params: undefined });
    });

    it('updateCompanyMembersOrder should PUT /v2/companies/:id/members/order with { user_ids }', async () => {
        (mockedApi.put as any).mockResolvedValue({ data: { message: 'ok' } });

        const result = await updateCompanyMembersOrder('c-1', ['u-1', 'u-2']);
        expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/order', { user_ids: ['u-1', 'u-2'] });
        expect(result).toEqual({ message: 'ok' });
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

    it('getDailyReport should GET /companies/:id/daily-report with date param', async () => {
        const body = {
            companyId: 'c-1',
            date: '2026-10-25',
            members: [],
            workTypes: {},
            logs: []
        };
        (mockedApi.get as any).mockResolvedValue({ data: body });

        const result = await getDailyReport('c-1', '2026-10-25');
        expect(mockedApi.get).toHaveBeenCalledWith('/companies/c-1/daily-report', {
            params: { date: '2026-10-25' }
        });
        expect(result).toEqual(body);
    });

    it('getDailyReport should keep amount keys absent for worker responses', async () => {
        const workerLog = {
            id: 'l-1',
            userId: 'u-1',
            type: 'particular',
            startDate: '2026-10-25',
            endDate: '2026-10-25',
            startTime: '09:00',
            endTime: '13:00',
            duration: 4,
            description: null
        };
        (mockedApi.get as any).mockResolvedValue({
            data: {
                companyId: 'c-1',
                date: '2026-10-25',
                members: [{ userId: 'u-1', firstName: 'Ana', lastName: 'Lopez', role: 'worker', isActive: true, sortOrder: 0 }],
                workTypes: { particular: { label: 'Particular', unit: 'hours' } },
                logs: [workerLog]
            }
        });

        const result = await getDailyReport('c-1', '2026-10-25');
        expect(result.logs[0]).toEqual(workerLog);
        expect('netAmount' in result.logs[0]).toBe(false);
        expect('grossAmount' in result.logs[0]).toBe(false);
    });
});
