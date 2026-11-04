import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { usePermissions } from '@/hooks/use-permissions';
import { getMyCompanies } from '@/lib/api/companies';
import type { CompanyResponse } from '@/lib/types';

const authState = vi.hoisted(() => ({ user: null as any }));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: authState.user }),
}));

vi.mock('@/lib/api/companies', () => ({
    getMyCompanies: vi.fn(),
}));

const mockedGetMyCompanies = vi.mocked(getMyCompanies);

const makeWrapper = () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    function Wrapper({ children }: { children: ReactNode }) {
        return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
    }
    return Wrapper;
};

const company = (over: Partial<CompanyResponse> = {}): CompanyResponse => ({
    id: 'c1',
    name: 'Empresa',
    taxConfig: { social_security: 0, irpf_base: 0 },
    createdAt: '',
    updatedAt: '',
    ...over,
} as CompanyResponse);

const baseUser = { id: 'u-self', email: 'x@x.com', role: 'user', isPlatformAdmin: false, activeCompanyId: 'c1' };

describe('usePermissions', () => {
    beforeEach(() => {
        mockedGetMyCompanies.mockReset();
        mockedGetMyCompanies.mockResolvedValue([]);
    });

    it('platform admin sin rol de empresa puede todo', () => {
        authState.user = { ...baseUser, role: 'admin', isPlatformAdmin: true, activeRole: null };
        const { result } = renderHook(() => usePermissions(company()), { wrapper: makeWrapper() });

        expect(result.current.isPlatformAdmin).toBe(true);
        expect(result.current.role).toBe('platform_admin');
        expect(result.current.canManageMembers).toBe(true);
        expect(result.current.canEditCompany).toBe(true);
        expect(result.current.canCreateWorkLog).toBe(true);
        expect(result.current.canEditRates('u-otro')).toBe(true);
        expect(result.current.canEditWorkLog({ userId: 'u-otro' })).toBe(true);
    });

    it('manager edita tarifas de su equipo pero no gestiona miembros ni empresa', () => {
        authState.user = { ...baseUser, activeRole: 'manager' };
        const { result } = renderHook(() => usePermissions(company()), { wrapper: makeWrapper() });

        expect(result.current.role).toBe('manager');
        expect(result.current.canEditRates('u-equipo')).toBe(true);
        expect(result.current.canEditWorkLog({ userId: 'u-equipo' })).toBe(true);
        expect(result.current.canCreateWorkLog).toBe(true);
        expect(result.current.canManageMembers).toBe(false);
        expect(result.current.canEditCompany).toBe(false);
    });

    it('worker en empresa autonoma solo edita lo propio', () => {
        authState.user = { ...baseUser, activeRole: 'worker' };
        const { result } = renderHook(() => usePermissions(company({ isManaged: false })), { wrapper: makeWrapper() });

        expect(result.current.role).toBe('worker');
        expect(result.current.isManaged).toBe(false);
        expect(result.current.canCreateWorkLog).toBe(true);
        expect(result.current.canEditRates('u-self')).toBe(true);
        expect(result.current.canEditRates('u-otro')).toBe(false);
        expect(result.current.canEditWorkLog({ userId: 'u-self' })).toBe(true);
        expect(result.current.canEditWorkLog({ userId: 'u-otro' })).toBe(false);
        expect(result.current.canManageMembers).toBe(false);
    });

    it('worker en empresa gestionada no puede registrar ni editar', () => {
        authState.user = { ...baseUser, activeRole: 'worker' };
        const { result } = renderHook(() => usePermissions(company({ isManaged: true })), { wrapper: makeWrapper() });

        expect(result.current.isManaged).toBe(true);
        expect(result.current.canCreateWorkLog).toBe(false);
        expect(result.current.canEditRates('u-self')).toBe(false);
        expect(result.current.canEditWorkLog({ userId: 'u-self' })).toBe(false);
    });

    it('platform admin en vista de solo lectura tiene todos los can* en false', () => {
        authState.user = {
            ...baseUser,
            role: 'admin',
            isPlatformAdmin: true,
            activeRole: 'worker',
            isReadOnlyView: true,
        };
        const { result } = renderHook(() => usePermissions(company({ isManaged: false })), { wrapper: makeWrapper() });

        expect(result.current.isReadOnlyView).toBe(true);
        expect(result.current.canCreateWorkLog).toBe(false);
        expect(result.current.canEditWorkLog({ userId: 'u-self' })).toBe(false);
        expect(result.current.canManageMembers).toBe(false);
        expect(result.current.canEditCompany).toBe(false);
        expect(result.current.canEditRates('u-self')).toBe(false);
    });

    it('sin empresa pasada usa la empresa activa de getMyCompanies', async () => {
        authState.user = { ...baseUser, activeRole: 'worker' };
        mockedGetMyCompanies.mockResolvedValue([company({ id: 'c1', isManaged: true })]);
        const { result } = renderHook(() => usePermissions(), { wrapper: makeWrapper() });

        await waitFor(() => expect(result.current.isManaged).toBe(true));
        expect(mockedGetMyCompanies).toHaveBeenCalled();
        expect(result.current.canCreateWorkLog).toBe(false);
    });

    it('con empresa pasada no consulta getMyCompanies', () => {
        authState.user = { ...baseUser, activeRole: 'manager' };
        renderHook(() => usePermissions(company()), { wrapper: makeWrapper() });

        expect(mockedGetMyCompanies).not.toHaveBeenCalled();
    });
});
