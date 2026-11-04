import { describe, it, expect, vi, beforeEach } from 'vitest';

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
    getUsers,
    getUser,
    getUserCompanies,
    createUser,
    updateUser,
    updateMe,
    changePassword,
    updateUserStatus,
    getUserSessions,
    revokeUserSession,
    impersonateUser,
    resetPasswordEmail,
    forgotPassword,
    resetPassword,
} from '@/lib/api/users';

const mockedApi = vi.mocked(api);

describe('Users API Client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('getUsers', () => {
        it('should GET /users', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [] });
            const result = await getUsers();
            expect(mockedApi.get).toHaveBeenCalledWith('/users');
            expect(result).toEqual([]);
        });
    });

    describe('getUser', () => {
        it('should GET /users/:id', async () => {
            const mockUser = { id: 'u-1', email: 'test@test.com' };
            (mockedApi.get as any).mockResolvedValue({ data: mockUser });
            const result = await getUser('u-1');
            expect(mockedApi.get).toHaveBeenCalledWith('/users/u-1');
            expect(result).toEqual(mockUser);
        });
    });

    describe('getUserCompanies', () => {
        it('should GET /v2/users/:id/companies', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [] });
            await getUserCompanies('u-1');
            expect(mockedApi.get).toHaveBeenCalledWith('/v2/users/u-1/companies');
        });

        it('should return camelCase companies with the user membership', async () => {
            (mockedApi.get as any).mockResolvedValue({
                data: [
                    {
                        id: 'c-1',
                        name: 'Escuela Sierra',
                        is_active: true,
                        is_managed: false,
                        tax_config: { iva: 21 },
                        worklog_definitions: {},
                        settings: {},
                        created_at: null,
                        updated_at: null,
                        role: 'manager',
                        is_active_member: false,
                        rates_config: { particular: { base_rate: 10 } },
                    },
                ],
            });
            const result = await getUserCompanies('u-1');
            expect(result).toHaveLength(1);
            expect(result[0].role).toBe('manager');
            expect(result[0].isActiveMember).toBe(false);
            expect(result[0].ratesConfig).toEqual({ particular: { base_rate: 10 } });
            expect(result[0].taxConfig).toEqual({ iva: 21 });
            expect(result[0]).not.toHaveProperty('is_active_member');
        });
    });

    describe('createUser', () => {
        it('should POST /users with camelCase data', async () => {
            const userData = {
                email: 'new@test.com',
                firstName: 'New',
                lastName: 'User',
                role: 'user',
            };
            (mockedApi.post as any).mockResolvedValue({ data: { id: 'u-new', ...userData } });
            const result = await createUser(userData);
            expect(mockedApi.post).toHaveBeenCalledWith('/users', userData);
            expect(result.id).toBe('u-new');
        });
    });

    describe('updateUser', () => {
        it('should PUT /users/:id', async () => {
            const update = { firstName: 'Updated' };
            (mockedApi.put as any).mockResolvedValue({ data: { id: 'u-1', ...update } });
            await updateUser('u-1', update);
            expect(mockedApi.put).toHaveBeenCalledWith('/users/u-1', update);
        });
    });

    describe('updateMe', () => {
        it('should PUT /users/me', async () => {
            const update = { firstName: 'Me' };
            (mockedApi.put as any).mockResolvedValue({ data: update });
            await updateMe(update);
            expect(mockedApi.put).toHaveBeenCalledWith('/users/me', update);
        });
    });

    describe('changePassword', () => {
        it('should POST /users/me/change-password', async () => {
            (mockedApi.post as any).mockResolvedValue({});
            await changePassword({ oldPassword: 'old', newPassword: 'new' });
            expect(mockedApi.post).toHaveBeenCalledWith('/users/me/change-password', {
                oldPassword: 'old',
                newPassword: 'new',
            });
        });
    });

    describe('updateUserStatus', () => {
        it('should PUT /users/:id/status with isActive query param', async () => {
            (mockedApi.put as any).mockResolvedValue({ data: {} });
            await updateUserStatus('u-1', false);
            expect(mockedApi.put).toHaveBeenCalledWith('/users/u-1/status?isActive=false');
        });
    });

    describe('Session Management', () => {
        it('getUserSessions should GET /users/:id/sessions', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [] });
            await getUserSessions('u-1');
            expect(mockedApi.get).toHaveBeenCalledWith('/users/u-1/sessions');
        });

        it('revokeUserSession should DELETE /users/:id/sessions/:sessionId', async () => {
            (mockedApi.delete as any).mockResolvedValue({ data: {} });
            await revokeUserSession('u-1', 's-1');
            expect(mockedApi.delete).toHaveBeenCalledWith('/users/u-1/sessions/s-1');
        });
    });

    describe('Admin Functions', () => {
        it('impersonateUser should POST /admin/impersonate/:id', async () => {
            (mockedApi.post as any).mockResolvedValue({ data: { accessToken: 'tok' } });
            const result = await impersonateUser('u-1');
            expect(mockedApi.post).toHaveBeenCalledWith('/admin/impersonate/u-1');
            expect(result.accessToken).toBe('tok');
        });


        it('resetPasswordEmail should POST /users/:id/reset-password-email', async () => {
            (mockedApi.post as any).mockResolvedValue({ data: {} });
            await resetPasswordEmail('u-1');
            expect(mockedApi.post).toHaveBeenCalledWith('/users/u-1/reset-password-email');
        });

        it('forgotPassword should POST /auth/forgot-password', async () => {
            (mockedApi.post as any).mockResolvedValue({ data: { message: 'sent' } });
            const result = await forgotPassword('test@test.com');
            expect(mockedApi.post).toHaveBeenCalledWith('/auth/forgot-password', { email: 'test@test.com' });
            expect(result.message).toBe('sent');
        });

        it('resetPassword should POST /auth/reset-password', async () => {
            (mockedApi.post as any).mockResolvedValue({ data: { message: 'success' } });
            const result = await resetPassword({ token: 't1', newPassword: 'p1' });
            expect(mockedApi.post).toHaveBeenCalledWith('/auth/reset-password', { token: 't1', newPassword: 'p1' });
            expect(result.message).toBe('success');
        });
    });

});
