import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WorkLogDetailsDialog } from '@/components/work-log/details-dialog';
import CalendarPage from '@/app/(app)/calendar/page';
import { getMyCompanies } from '@/lib/api/companies';
import type { Company, WorkLog } from '@/lib/types';

const authState = vi.hoisted(() => ({ user: null as any }));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: authState.user, loading: false }),
}));

vi.mock('@/lib/api/companies', () => ({
    getMyCompanies: vi.fn(),
}));

vi.mock('@/lib/api/work-logs', () => ({
    getWorkLogs: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/lib/api/settings', () => ({
    getUserRates: vi.fn().mockResolvedValue([]),
}));

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/components/event-calendar', () => ({
    EventCalendar: () => null,
}));

vi.mock('@/components/work-log/user-dialog', () => ({
    UserCreateWorkLogDialog: () => null,
}));

const mockedGetMyCompanies = vi.mocked(getMyCompanies);

const makeWrapper = () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    function Wrapper({ children }: { children: React.ReactNode }) {
        return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
    }
    return Wrapper;
};

const COMPANY_ID = 'c1';

const company = (over: Partial<Company> = {}): Company =>
    ({
        id: COMPANY_ID,
        name: 'Escuela Test',
        taxConfig: { social_security: 0, irpf_base: 0 },
        createdAt: '',
        updatedAt: '',
        ...over,
    }) as Company;

const log = (over: Partial<WorkLog> = {}): WorkLog =>
    ({
        id: 'log-1',
        companyId: COMPANY_ID,
        userId: 'u-self',
        type: 'particular',
        startDate: '2026-01-10',
        endDate: '2026-01-10',
        startTime: '09:00',
        endTime: '17:00',
        extraData: { datos: {}, opciones: {} },
        createdAt: '',
        updatedAt: '',
        ...over,
    }) as WorkLog;

const baseUser = { id: 'u-self', email: 'x@x.com', role: 'user', isPlatformAdmin: false, activeCompanyId: COMPANY_ID };

describe('Permisos de turnos en la UI', () => {
    beforeEach(() => {
        mockedGetMyCompanies.mockReset();
    });

    describe('WorkLogDetailsDialog: editar y borrar', () => {
        const renderDetails = (companyOverrides: Partial<Company>, logOverrides: Partial<WorkLog> = {}) =>
            render(
                <WorkLogDetailsDialog
                    log={log(logOverrides)}
                    open
                    onOpenChange={() => {}}
                    companies={[company(companyOverrides)]}
                    onEdit={() => {}}
                    onDelete={() => {}}
                />,
                { wrapper: makeWrapper() },
            );

        it('worker en empresa gestionada no ve Editar ni Eliminar y ve el aviso del equipo gestor', () => {
            authState.user = { ...baseUser, activeRole: 'worker' };
            renderDetails({ isManaged: true });

            expect(screen.queryByRole('button', { name: 'Editar' })).toBeNull();
            expect(screen.queryByRole('button', { name: 'Eliminar' })).toBeNull();
            expect(
                screen.getByText('En esta empresa los turnos los registra el equipo gestor'),
            ).toBeInTheDocument();
        });

        it('worker en empresa autonoma ve Editar y Eliminar en su propio turno', () => {
            authState.user = { ...baseUser, activeRole: 'worker' };
            renderDetails({ isManaged: false });

            expect(screen.getByRole('button', { name: 'Editar' })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Eliminar' })).toBeInTheDocument();
        });

        it('manager ve Editar y Eliminar en empresa gestionada', () => {
            authState.user = { ...baseUser, activeRole: 'manager' };
            renderDetails({ isManaged: true }, { userId: 'u-otro' });

            expect(screen.getByRole('button', { name: 'Editar' })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Eliminar' })).toBeInTheDocument();
        });

        it('PA en vista de solo lectura no ve Editar ni Eliminar', () => {
            authState.user = { ...baseUser, role: 'admin', isPlatformAdmin: true, activeRole: null, isReadOnlyView: true };
            renderDetails({ isManaged: false });

            expect(screen.queryByRole('button', { name: 'Editar' })).toBeNull();
            expect(screen.queryByRole('button', { name: 'Eliminar' })).toBeNull();
        });
    });

    describe('CalendarPage: alta de turnos', () => {
        it('worker en empresa gestionada no ve Add Work Log y ve el aviso del equipo gestor', async () => {
            authState.user = { ...baseUser, activeRole: 'worker' };
            mockedGetMyCompanies.mockResolvedValue([company({ isManaged: true })]);
            render(<CalendarPage />, { wrapper: makeWrapper() });

            expect(
                await screen.findByText('En esta empresa los turnos los registra el equipo gestor'),
            ).toBeInTheDocument();
            expect(screen.queryByRole('button', { name: 'Add Work Log' })).toBeNull();
        });

        it('worker en empresa autonoma ve Add Work Log', async () => {
            authState.user = { ...baseUser, activeRole: 'worker' };
            mockedGetMyCompanies.mockResolvedValue([company({ isManaged: false })]);
            render(<CalendarPage />, { wrapper: makeWrapper() });

            expect(await screen.findByRole('button', { name: 'Add Work Log' })).toBeInTheDocument();
            await waitFor(() => expect(mockedGetMyCompanies).toHaveBeenCalled());
            expect(screen.getByRole('button', { name: 'Add Work Log' })).toBeInTheDocument();
        });

        it('manager ve Add Work Log en empresa gestionada', async () => {
            authState.user = { ...baseUser, activeRole: 'manager' };
            mockedGetMyCompanies.mockResolvedValue([company({ isManaged: true })]);
            render(<CalendarPage />, { wrapper: makeWrapper() });

            expect(await screen.findByRole('button', { name: 'Add Work Log' })).toBeInTheDocument();
            await waitFor(() => expect(mockedGetMyCompanies).toHaveBeenCalled());
            expect(screen.getByRole('button', { name: 'Add Work Log' })).toBeInTheDocument();
        });

        it('PA en vista de solo lectura nunca ve Add Work Log', async () => {
            authState.user = { ...baseUser, role: 'admin', isPlatformAdmin: true, activeRole: null, isReadOnlyView: true };
            mockedGetMyCompanies.mockResolvedValue([company({ isManaged: false })]);
            render(<CalendarPage />, { wrapper: makeWrapper() });

            await waitFor(() => expect(mockedGetMyCompanies).toHaveBeenCalled());
            expect(screen.queryByRole('button', { name: 'Add Work Log' })).toBeNull();
            expect(
                screen.queryByText('En esta empresa los turnos los registra el equipo gestor'),
            ).toBeNull();
        });
    });
});
