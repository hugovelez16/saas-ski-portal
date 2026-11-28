import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AppLayout from '@/app/(app)/layout';
import { useAuth } from '@/context/AuthContext';
import { useModules } from '@/hooks/useModules';
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';

// Mock Next.js Navigation
vi.mock('next/navigation', () => {
    const pushMock = vi.fn();
    return {
        usePathname: vi.fn(() => '/dashboard'),
        useRouter: vi.fn(() => ({
            push: pushMock,
        })),
        useSearchParams: vi.fn(() => ({
            get: vi.fn(() => null),
        })),
    };
});

// Mock Auth Context
vi.mock('@/context/AuthContext', () => ({
    useAuth: vi.fn(),
}));

// Mock Modules Hook
vi.mock('@/hooks/useModules', () => ({
    useModules: vi.fn(),
}));

// Mock React Query
vi.mock('@tanstack/react-query', () => ({
    useQuery: vi.fn(),
}));

// Mock ScopeSelectionDialog and Button to isolate Sidebar testing
vi.mock('@/components/auth/scope-selection-dialog', () => ({
    ScopeSelectionDialog: () => <div data-testid="scope-dialog" />,
}));

vi.mock('@/components/ui/button', () => ({
    Button: ({ children, ...props }: React.ComponentPropsWithoutRef<'button'>) => <button {...props}>{children}</button>,
}));

// Mock Framer Motion to avoid any animation related issues in jsdom
vi.mock('framer-motion', () => ({
    motion: {
        span: ({ children, ...props }: React.ComponentPropsWithoutRef<'span'>) => <span {...props}>{children}</span>,
        div: ({ children, ...props }: React.ComponentPropsWithoutRef<'div'>) => <div {...props}>{children}</div>,
        aside: ({ children, ...props }: React.ComponentPropsWithoutRef<'aside'>) => <aside {...props}>{children}</aside>,
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('AppLayout Sidebar Integration for Platform Admin', () => {
    const mockCompanies = [
        { id: 'querkus-id', name: 'Querkus' },
        { id: 'surf-id', name: 'Surf in Comporta' }
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        
        // Mock getMyCompanies query response
        vi.mocked(useQuery).mockReturnValue({
            data: mockCompanies,
            isLoading: false,
        } as unknown as UseQueryResult<unknown, unknown>);
    });

    it('Scenario 1: Platform Admin with NO company context should see Administration items', () => {
        // Mock user as Platform Admin with no active role or company
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'admin-id',
                email: 'hugo@vesotel.com',
                role: 'admin',
                isPlatformAdmin: true,
                activeRole: null,
                activeCompanyId: null,
            },
            loading: false,
            logout: vi.fn(),
        } as unknown as ReturnType<typeof useAuth>);

        // Mock empty modules since no company context
        vi.mocked(useModules).mockReturnValue({
            modules: [],
            isLoading: false,
            hasModule: () => true,
        } as unknown as ReturnType<typeof useModules>);

        render(
            <AppLayout>
                <div>Content</div>
            </AppLayout>
        );

        // Should see Platform Administration section and its links
        expect(screen.getByText('Administración Plataforma')).toBeInTheDocument();
        expect(screen.getByText('Gestión de Empresas')).toBeInTheDocument();
        expect(screen.getByText('Usuarios')).toBeInTheDocument();
        expect(screen.getByText('Módulos')).toBeInTheDocument();
    });

    it('Scenario 2: Platform Admin in Querkus context (sin modulos activos) debe ver Facturación y NO Parte Diario ni Informes', () => {
        // Mock Search Params returning Querkus ID
        vi.mocked(useSearchParams).mockReturnValue({
            get: vi.fn((key) => key === 'companyId' ? 'querkus-id' : null),
        } as unknown as ReturnType<typeof useSearchParams>);

        // Mock user switched context to manager in Querkus
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'admin-id',
                email: 'hugo@vesotel.com',
                role: 'admin',
                isPlatformAdmin: true,
                activeRole: 'manager',
                activeCompanyId: 'querkus-id',
            },
            loading: false,
            logout: vi.fn(),
        } as unknown as ReturnType<typeof useAuth>);

        // Sin modulos contratados en Querkus: Facturación sigue visible por ser basica
        vi.mocked(useModules).mockReturnValue({
            modules: [],
            isLoading: false,
            hasModule: () => false,
        } as unknown as ReturnType<typeof useModules>);

        render(
            <AppLayout>
                <div>Content</div>
            </AppLayout>
        );

        // Group label should be active company name
        expect(screen.getByText('Querkus')).toBeInTheDocument();

        // Manager default items (incluye Facturación sin modulo billing)
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
        expect(screen.getByText('Calendario')).toBeInTheDocument();
        expect(screen.getByText('Usuarios')).toBeInTheDocument();
        expect(screen.getByText('Turnos')).toBeInTheDocument();
        expect(screen.getByText('Facturación')).toBeInTheDocument();

        // Parte Diario and Informes should NOT be in the document
        expect(screen.queryByText('Parte Diario')).not.toBeInTheDocument();
        expect(screen.queryByText('Informes')).not.toBeInTheDocument();
    });

    it('Scenario 3: Platform Admin in Surf in Comporta context (all modules active) should see everything', () => {
        // Mock Search Params returning Surf in Comporta ID
        vi.mocked(useSearchParams).mockReturnValue({
            get: vi.fn((key) => key === 'companyId' ? 'surf-id' : null),
        } as unknown as ReturnType<typeof useSearchParams>);

        // Mock user switched context to manager in Surf in Comporta
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'admin-id',
                email: 'hugo@vesotel.com',
                role: 'admin',
                isPlatformAdmin: true,
                activeRole: 'manager',
                activeCompanyId: 'surf-id',
            },
            loading: false,
            logout: vi.fn(),
        } as unknown as ReturnType<typeof useAuth>);

        // Mock Surf in Comporta modules: reports y worker_daily_report activos
        vi.mocked(useModules).mockReturnValue({
            modules: [
                { id: 'm-reports', codeName: 'reports', name: 'Informes', isActive: true },
                { id: 'm-daily', codeName: 'worker_daily_report', name: 'Parte Diario', isActive: true }
            ],
            isLoading: false,
            hasModule: () => true,
        } as unknown as ReturnType<typeof useModules>);

        render(
            <AppLayout>
                <div>Content</div>
            </AppLayout>
        );

        // Group label should be active company name
        expect(screen.getByText('Surf in Comporta')).toBeInTheDocument();

        // Manager items
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
        expect(screen.getByText('Calendario')).toBeInTheDocument();
        expect(screen.getByText('Usuarios')).toBeInTheDocument();
        expect(screen.getByText('Turnos')).toBeInTheDocument();

        // Active modules + Facturación basica in the sidebar
        expect(screen.getByText('Parte Diario')).toBeInTheDocument();
        expect(screen.getByText('Facturación')).toBeInTheDocument();
        expect(screen.getByText('Informes')).toBeInTheDocument();
    });

    it('Manager regular sin modulos contratados ve Facturación y no ve Informes ni Parte Diario', () => {
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'manager-id',
                email: 'laura@vesotel.com',
                firstName: 'Laura',
                role: 'user',
                isPlatformAdmin: false,
                activeRole: 'manager',
                activeCompanyId: 'querkus-id',
            },
            loading: false,
            logout: vi.fn(),
        } as unknown as ReturnType<typeof useAuth>);

        vi.mocked(useModules).mockReturnValue({
            modules: [],
            isLoading: false,
            hasModule: () => false,
        } as unknown as ReturnType<typeof useModules>);

        render(
            <AppLayout>
                <div>Contenido manager</div>
            </AppLayout>
        );

        expect(screen.getByText('Facturación')).toBeInTheDocument();
        expect(screen.queryByText('Parte Diario')).not.toBeInTheDocument();
        expect(screen.queryByText('Informes')).not.toBeInTheDocument();
    });

    it('Worker regular sin modulo reports no ve Facturación ni Informes Personales', () => {
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'worker-id',
                email: 'ana@vesotel.com',
                firstName: 'Ana',
                role: 'user',
                isPlatformAdmin: false,
                activeRole: 'worker',
                activeCompanyId: 'querkus-id',
            },
            loading: false,
            logout: vi.fn(),
        } as unknown as ReturnType<typeof useAuth>);

        vi.mocked(useModules).mockReturnValue({
            modules: [],
            isLoading: false,
            hasModule: () => false,
        } as unknown as ReturnType<typeof useModules>);

        render(
            <AppLayout>
                <div>Contenido worker</div>
            </AppLayout>
        );

        expect(screen.queryByText('Facturación')).not.toBeInTheDocument();
        expect(screen.queryByText('Informes Personales')).not.toBeInTheDocument();
    });

    it('omite LegalFooter del pie del layout operativo pero mantiene AppVersion y el enlace legal directo en Sidebar', () => {
        vi.mocked(useAuth).mockReturnValue({
            user: {
                id: 'worker-id',
                email: 'ana@vesotel.com',
                firstName: 'Ana',
                role: 'worker',
                isPlatformAdmin: false,
                activeRole: 'worker',
                activeCompanyId: 'querkus-id',
            },
            loading: false,
            logout: vi.fn(),
        } as unknown as ReturnType<typeof useAuth>);

        vi.mocked(useModules).mockReturnValue({
            modules: [],
            isLoading: false,
            hasModule: () => false,
        } as unknown as ReturnType<typeof useModules>);

        render(
            <AppLayout>
                <div>Contenido operativo</div>
            </AppLayout>
        );

        expect(screen.queryByRole('navigation', { name: 'Información legal' })).not.toBeInTheDocument();
        expect(screen.getByTestId('app-version')).toBeInTheDocument();

        const legalLink = screen.getByRole('link', { name: 'Información legal' });
        expect(legalLink).toHaveAttribute('href', '/aviso-legal');
    });
});
