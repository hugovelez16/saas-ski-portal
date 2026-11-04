import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '@/lib/api';
import {
    listMembers,
    addMember,
    removeMember,
    setMemberStatus,
    setMemberRole,
    setMemberRates,
    setMemberSettings,
    reorderMembers,
    listRates,
} from '@/lib/api/v2/members';
import type { MemberOut, MemberDeleteOut } from '@/lib/api/v2/types';

vi.mock('@/lib/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
    },
}));

const mockedApi = vi.mocked(api);

const memberOut: MemberOut = {
    user_id: 'u-1',
    company_id: 'c-1',
    role: 'worker',
    is_active: true,
    sort_order: 0,
    rates_config: {},
    settings: {},
    joined_at: '2026-01-01T00:00:00Z',
    updated_at: null,
    user: {
        id: 'u-1',
        email: 'ana@example.com',
        first_name: 'Ana',
        last_name: 'Lopez',
        is_active: true,
    },
};

describe('API v2 Members client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('listMembers', () => {
        it('GET /v2/companies/:companyId/members with is_active param', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [memberOut] });

            const result = await listMembers('c-1', { is_active: true });

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/members', { params: { is_active: true } });
            expect(result).toEqual([memberOut]);
        });

        it('passes is_active=false through unchanged', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [] });

            await listMembers('c-1', { is_active: false });

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/members', { params: { is_active: false } });
        });

        it('params undefined when called without filters', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [] });

            await listMembers('c-1');

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/members', { params: undefined });
        });
    });

    describe('addMember', () => {
        it('POST /v2/companies/:companyId/members with { email }', async () => {
            (mockedApi.post as any).mockResolvedValue({ data: memberOut });

            const result = await addMember('c-1', 'ana@example.com');

            expect(mockedApi.post).toHaveBeenCalledWith('/v2/companies/c-1/members', { email: 'ana@example.com' });
            expect(result).toEqual(memberOut);
        });
    });

    describe('removeMember', () => {
        it('DELETE /v2/companies/:companyId/members/:userId and returns the delete report', async () => {
            const report: MemberDeleteOut = { deleted: false, deactivated: true, reason: 'tiene jornadas' };
            (mockedApi.delete as any).mockResolvedValue({ data: report });

            const result = await removeMember('c-1', 'u-1');

            expect(mockedApi.delete).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1');
            expect(result).toEqual(report);
            expect(result.deactivated).toBe(true);
        });
    });

    describe('setMemberStatus', () => {
        it('PUT .../members/:userId/status with { is_active: true }', async () => {
            (mockedApi.put as any).mockResolvedValue({ data: { ...memberOut, is_active: true } });

            const result = await setMemberStatus('c-1', 'u-1', true);

            expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/status', { is_active: true });
            expect(result.is_active).toBe(true);
        });

        it('PUT .../members/:userId/status with { is_active: false }', async () => {
            (mockedApi.put as any).mockResolvedValue({ data: { ...memberOut, is_active: false } });

            const result = await setMemberStatus('c-1', 'u-1', false);

            expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/status', { is_active: false });
            expect(result.is_active).toBe(false);
        });
    });

    describe('setMemberRole', () => {
        it('PUT .../members/:userId/role with { role }', async () => {
            (mockedApi.put as any).mockResolvedValue({ data: { ...memberOut, role: 'manager' } });

            const result = await setMemberRole('c-1', 'u-1', 'manager');

            expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/role', { role: 'manager' });
            expect(result.role).toBe('manager');
        });
    });

    describe('setMemberRates', () => {
        it('PUT .../members/:userId/rates with snake_case { rates_config }', async () => {
            const ratesConfig = { particular: { base_rate: 10 } };
            (mockedApi.put as any).mockResolvedValue({ data: { ...memberOut, rates_config: ratesConfig } });

            const result = await setMemberRates('c-1', 'u-1', ratesConfig);

            expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/rates', {
                rates_config: ratesConfig,
            });
            expect(result.rates_config).toEqual(ratesConfig);
        });

        it('does not send a camelCase ratesConfig key', async () => {
            (mockedApi.put as any).mockResolvedValue({ data: memberOut });

            await setMemberRates('c-1', 'u-1', {});

            const sentBody = (mockedApi.put as any).mock.calls[0][1];
            expect(sentBody).not.toHaveProperty('ratesConfig');
        });
    });

    describe('setMemberSettings', () => {
        it('PUT .../members/:userId/settings with { settings }', async () => {
            const settings = { allow_tutorial: false };
            (mockedApi.put as any).mockResolvedValue({ data: { ...memberOut, settings } });

            const result = await setMemberSettings('c-1', 'u-1', settings);

            expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/u-1/settings', { settings });
            expect(result.settings).toEqual(settings);
        });
    });

    describe('reorderMembers', () => {
        it('PUT /v2/companies/:companyId/members/order with snake_case { user_ids }', async () => {
            const userIds = ['u-2', 'u-1'];
            (mockedApi.put as any).mockResolvedValue({ data: { message: 'OK' } });

            const result = await reorderMembers('c-1', userIds);

            expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1/members/order', { user_ids: userIds });
            expect(result).toEqual({ message: 'OK' });
        });

        it('does not send a camelCase userIds key', async () => {
            (mockedApi.put as any).mockResolvedValue({ data: {} });

            await reorderMembers('c-1', ['u-1']);

            const sentBody = (mockedApi.put as any).mock.calls[0][1];
            expect(sentBody).not.toHaveProperty('userIds');
        });
    });

    describe('listRates', () => {
        it('GET /v2/companies/:companyId/rates and returns data', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [] });

            const result = await listRates('c-1');

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1/rates');
            expect(result).toEqual([]);
        });
    });
});
