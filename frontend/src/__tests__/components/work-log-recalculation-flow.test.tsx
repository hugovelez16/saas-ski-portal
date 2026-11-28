import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WorkLogDetailsDialog } from '@/components/work-log/details-dialog';
import { UserCreateWorkLogDialog } from '@/components/work-log/user-dialog';
import { ManagerAddWorkLogDialog } from '@/components/work-log/manager-add-log-dialog';
import { previewWorkLogRecalculation, updateWorkLog } from '@/lib/api/work-logs';
import type { Company, WorkLog, WorkLogRecalculatePreview } from '@/lib/types';

const { authState, toastMock } = vi.hoisted(() => ({
    authState: { user: null as any },
    toastMock: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: authState.user, loading: false }),
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: toastMock }),
}));

vi.mock('@/lib/api/companies', () => ({
    getMyCompanies: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/lib/api/work-logs', () => ({
    createWorkLog: vi.fn(),
    previewWorkLogRecalculation: vi.fn(),
    updateWorkLog: vi.fn(),
}));

const mockedPreview = vi.mocked(previewWorkLogRecalculation);
const mockedUpdate = vi.mocked(updateWorkLog);

const COMPANY: Company = {
    id: 'c-1',
    name: 'Escuela Test',
    isManaged: false,
    role: 'manager',
    taxConfig: {},
    worklogDefinitions: {
        particular: { label: 'Particular', unit: 'hours', fields: [], options: [] },
        tutorial: { label: 'Tutorial', unit: 'days', fields: [], options: [] },
    },
    createdAt: '',
    updatedAt: '',
};

const LOG: WorkLog = {
    id: 'wl-1',
    userId: 'u-1',
    companyId: 'c-1',
    type: 'particular',
    date: '2026-01-10',
    startDate: '2026-01-10',
    endDate: '2026-01-10',
    startTime: '09:00',
    endTime: '11:00',
    duration: 2,
    netAmount: 40,
    grossAmount: 45,
    extraData: { datos: {}, opciones: {} },
    createdAt: '',
    updatedAt: '',
};

const PREVIEW: WorkLogRecalculatePreview = {
    workLogId: 'wl-1',
    currentNetAmount: 40,
    currentGrossAmount: 45,
    currentDuration: 2,
    newNetAmount: 75,
    newGrossAmount: 85,
    newDuration: 2,
    applyToGroup: false,
    groupCount: 1,
};

function renderWithQuery(ui: React.ReactElement) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('Flujo de recálculo y confirmación de turnos', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        authState.user = {
            id: 'u-mgr',
            role: 'user',
            isPlatformAdmin: false,
            activeCompanyId: 'c-1',
            activeRole: 'manager',
        };
    });

    it('WorkLogDetailsDialog previsualiza y solo recalcula tras confirmar', async () => {
        mockedPreview.mockResolvedValue(PREVIEW);
        mockedUpdate.mockResolvedValue(LOG);
        const onUpdated = vi.fn();

        renderWithQuery(
            <WorkLogDetailsDialog
                log={LOG}
                open={true}
                onOpenChange={vi.fn()}
                companies={[COMPANY]}
                onUpdated={onUpdated}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: 'Recalcular con tarifa vigente' }));

        await waitFor(() => {
            expect(mockedPreview).toHaveBeenCalledWith('wl-1', {}, false, {
                recalculateWithCurrentRates: true,
            });
        });

        expect(await screen.findByText('Importe actual')).toBeInTheDocument();
        expect(screen.getByText(/40,00.*neto/)).toBeInTheDocument();
        expect(screen.getByText(/75,00.*neto/)).toBeInTheDocument();
        expect(mockedUpdate).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Confirmar y guardar' }));

        await waitFor(() => {
            expect(mockedUpdate).toHaveBeenCalledWith('wl-1', {}, false, {
                recalculateWithCurrentRates: true,
            });
        });
        expect(onUpdated).toHaveBeenCalledTimes(1);
    });

    it('UserCreateWorkLogDialog exige confirmación con comparativa al cambiar de tipo', async () => {
        mockedPreview.mockResolvedValue(PREVIEW);
        mockedUpdate.mockResolvedValue({ ...LOG, type: 'tutorial', netAmount: 75 });
        const onLogUpdate = vi.fn();

        renderWithQuery(
            <UserCreateWorkLogDialog
                user={{ id: 'u-1', activeCompanyId: 'c-1' }}
                open={true}
                onOpenChange={vi.fn()}
                companies={[COMPANY]}
                logToEdit={LOG}
                onLogUpdate={onLogUpdate}
            />
        );

        // Cambiar el tipo de "particular" a "tutorial"
        fireEvent.click(screen.getByLabelText('Tutorial'));
        fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }));

        await waitFor(() => {
            expect(mockedPreview).toHaveBeenCalledWith(
                'wl-1',
                expect.objectContaining({ type: 'tutorial' }),
                false,
                { recalculateWithCurrentRates: false }
            );
        });

        expect(await screen.findByText('Confirmar cambio de tipo')).toBeInTheDocument();
        expect(screen.getByText(/40,00/)).toBeInTheDocument();
        expect(screen.getByText(/75,00/)).toBeInTheDocument();
        expect(mockedUpdate).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Confirmar y guardar' }));

        await waitFor(() => {
            expect(mockedUpdate).toHaveBeenCalledWith(
                'wl-1',
                expect.objectContaining({ type: 'tutorial' }),
                false,
                { recalculateWithCurrentRates: false }
            );
        });
        expect(onLogUpdate).toHaveBeenCalledTimes(1);
    });

    it('ManagerAddWorkLogDialog previsualiza y recalcula con tarifa vigente al confirmar', async () => {
        mockedPreview.mockResolvedValue(PREVIEW);
        mockedUpdate.mockResolvedValue({ ...LOG, netAmount: 75 });
        const onSuccess = vi.fn();

        renderWithQuery(
            <ManagerAddWorkLogDialog
                companyId="c-1"
                companyName="Escuela Test"
                users={[{ id: 'u-1', firstName: 'Ana', lastName: 'Lopez' }]}
                worklogDefinitions={COMPANY.worklogDefinitions}
                open={true}
                onOpenChange={vi.fn()}
                initialData={LOG}
                onSuccess={onSuccess}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: 'Recalcular con tarifa vigente' }));

        await waitFor(() => {
            expect(mockedPreview).toHaveBeenCalledWith(
                'wl-1',
                expect.objectContaining({ type: 'particular', userId: 'u-1' }),
                false,
                { recalculateWithCurrentRates: true }
            );
        });

        expect(await screen.findByText('Recalcular con tarifa vigente', { selector: 'h2' })).toBeInTheDocument();
        expect(mockedUpdate).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Confirmar y guardar' }));

        await waitFor(() => {
            expect(mockedUpdate).toHaveBeenCalledWith(
                'wl-1',
                expect.objectContaining({ type: 'particular', userId: 'u-1' }),
                false,
                { recalculateWithCurrentRates: true }
            );
        });
        expect(onSuccess).toHaveBeenCalledTimes(1);
    });
});
