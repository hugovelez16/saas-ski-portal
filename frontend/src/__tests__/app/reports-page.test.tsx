import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ReportsPage from '@/app/(app)/reports/page';
import PrintReportPage from '@/app/(app)/reports/print/page';
import { useAuth } from '@/context/AuthContext';
import { useModules } from '@/hooks/useModules';
import { getAllWorkLogReport, getAllWorkLogs, getWorkLogReport, getWorkLogSummary } from '@/lib/api/work-logs';
import { getCompany, getCompanyMembers, getCompaniesDetailed } from '@/lib/api/companies';

vi.mock('next/navigation', () => ({
    useRouter: vi.fn(() => ({ push: vi.fn() })),
    useSearchParams: vi.fn(() => ({
        get: vi.fn((key: string) => {
            if (key === 'start') return '2026-02-01';
            if (key === 'end') return '2026-02-28';
            return null;
        }),
    })),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: vi.fn(),
}));

vi.mock('@/hooks/useModules', () => ({
    useModules: vi.fn(),
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

vi.mock('@/lib/api/companies', () => ({
    getCompany: vi.fn(),
    getCompanyMembers: vi.fn(),
    getCompaniesDetailed: vi.fn(),
}));

vi.mock('@/lib/api/users', () => ({
    getUsers: vi.fn(),
}));

vi.mock('@/lib/api/work-logs', () => ({
    getAllWorkLogs: vi.fn(),
    getWorkLogSummary: vi.fn(),
    getWorkLogReport: vi.fn(),
    getAllWorkLogReport: vi.fn(),
}));

vi.mock('export-to-csv', () => ({
    mkConfig: vi.fn(() => ({})),
    generateCsv: vi.fn(() => vi.fn(() => 'csv')),
    download: vi.fn(() => vi.fn()),
}));

function renderWithQuery(ui: React.ReactElement) {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('ReportsPage y PrintReportPage con modulo reports', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(getCompany).mockResolvedValue({
            id: 'comp-1',
            name: 'Escuela Norte',
            taxConfig: {},
            worklogDefinitions: { particular: { label: 'Particular', unit: 'hours' } },
        });
        vi.mocked(getCompanyMembers).mockResolvedValue([]);
        vi.mocked(getCompaniesDetailed).mockResolvedValue([]);
    });

    it('ReportsPage muestra estado sin modulo cuando useModules no incluye reports', () => {
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'u-1',
                email: 'worker@test.com',
                role: 'user',
                activeRole: 'worker',
                activeCompanyId: 'comp-1',
            },
            loading: false,
        } as unknown as ReturnType<typeof useAuth>);

        vi.mocked(useModules).mockReturnValue({
            modules: [],
            isLoading: false,
            hasModule: () => false,
        } as unknown as ReturnType<typeof useModules>);

        renderWithQuery(<ReportsPage />);

        expect(screen.getByText('Módulo de informes no habilitado')).toBeInTheDocument();
        expect(getCompany).not.toHaveBeenCalled();
    });

    it('ReportsPage usa getAllWorkLogReport (/work-logs/reports) al exportar CSV y no llama a getAllWorkLogs', async () => {
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'u-1',
                email: 'worker@test.com',
                role: 'user',
                activeRole: 'worker',
                activeCompanyId: 'comp-1',
            },
            loading: false,
        } as unknown as ReturnType<typeof useAuth>);

        vi.mocked(useModules).mockReturnValue({
            modules: [{ id: 'm-rep', codeName: 'reports', name: 'Informes', isActive: true }],
            isLoading: false,
            hasModule: (code: string) => code === 'reports',
        } as unknown as ReturnType<typeof useModules>);

        vi.mocked(getAllWorkLogReport).mockResolvedValue({
            items: [
                {
                    id: 'wl-1',
                    userId: 'u-1',
                    companyId: 'comp-1',
                    type: 'particular',
                    startDate: '2026-02-10',
                    endDate: '2026-02-10',
                    duration: 2,
                    netAmount: 40,
                    grossAmount: 50,
                    extraData: {},
                    createdAt: '2026-02-10T10:00:00Z',
                    updatedAt: '2026-02-10T10:00:00Z',
                },
            ],
            total: 1,
            summary: {
                startDate: '2026-02-01',
                endDate: '2026-02-28',
                totals: { logsCount: 1, totalHours: 2, totalNet: 40, totalGross: 50, uniqueDays: 1, activeUsers: 1 },
                byType: [],
                byDay: [],
                byUser: [],
            },
        });

        renderWithQuery(<ReportsPage />);

        const csvBtn = await screen.findByRole('button', { name: /Descargar CSV/i });
        fireEvent.click(csvBtn);

        await waitFor(() => {
            expect(getAllWorkLogReport).toHaveBeenCalledWith(
                expect.objectContaining({
                    companyId: 'comp-1',
                    includeLogs: true,
                })
            );
        });
        expect(getAllWorkLogs).not.toHaveBeenCalled();
        expect(getWorkLogSummary).not.toHaveBeenCalled();
        expect(getWorkLogReport).not.toHaveBeenCalled();
    });

    it('PrintReportPage bloquea el acceso sin modulo reports y no consulta turnos', () => {
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'u-1',
                email: 'worker@test.com',
                role: 'user',
                activeRole: 'worker',
                activeCompanyId: 'comp-1',
            },
            loading: false,
        } as unknown as ReturnType<typeof useAuth>);

        vi.mocked(useModules).mockReturnValue({
            modules: [],
            isLoading: false,
            hasModule: () => false,
        } as unknown as ReturnType<typeof useModules>);

        renderWithQuery(<PrintReportPage />);

        expect(screen.getByText('Módulo de informes no habilitado')).toBeInTheDocument();
        expect(getAllWorkLogReport).not.toHaveBeenCalled();
        expect(getAllWorkLogs).not.toHaveBeenCalled();
    });

    it('PrintReportPage consulta getAllWorkLogReport cuando el usuario tiene modulo reports', async () => {
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'u-1',
                email: 'manager@test.com',
                role: 'user',
                activeRole: 'manager',
                activeCompanyId: 'comp-1',
            },
            loading: false,
        } as unknown as ReturnType<typeof useAuth>);

        vi.mocked(useModules).mockReturnValue({
            modules: [{ id: 'm-rep', codeName: 'reports', name: 'Informes', isActive: true }],
            isLoading: false,
            hasModule: (code: string) => code === 'reports',
        } as unknown as ReturnType<typeof useModules>);

        vi.mocked(getAllWorkLogReport).mockResolvedValue({
            items: [],
            total: 0,
            summary: {
                startDate: '2026-02-01',
                endDate: '2026-02-28',
                totals: { logsCount: 0, totalHours: 0, totalNet: 0, totalGross: 0, uniqueDays: 0, activeUsers: 0 },
                byType: [],
                byDay: [],
                byUser: [],
            },
        });

        renderWithQuery(<PrintReportPage />);

        await waitFor(() => {
            expect(getAllWorkLogReport).toHaveBeenCalledWith({
                companyId: 'comp-1',
                userId: undefined,
                startDate: '2026-02-01',
                endDate: '2026-02-28',
            });
        });
        expect(getAllWorkLogs).not.toHaveBeenCalled();
        expect(getWorkLogSummary).not.toHaveBeenCalled();
    });
});
