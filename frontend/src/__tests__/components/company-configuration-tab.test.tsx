import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { permissions } = vi.hoisted(() => ({
    permissions: { isPlatformAdmin: true, role: "manager" as string | null },
}));

vi.mock("@/hooks/use-permissions", () => ({
    usePermissions: () => ({
        isPlatformAdmin: permissions.isPlatformAdmin,
        role: permissions.role,
        canEditCompany: permissions.isPlatformAdmin,
    }),
}));

vi.mock("@/lib/api/companies", () => ({
    updateCompany: vi.fn(),
    getCompanyManagerSettings: vi.fn().mockResolvedValue({
        id: "c-1",
        name: "Escuela Sierra",
        settings: { default_is_gross: false },
        taxConfig: { social_security: 0, irpf_base: 0 },
        worklogDefinitions: {},
    }),
    updateCompanyManagerSettings: vi.fn(),
    getWorklogDefinitionsUsage: vi.fn().mockResolvedValue({ items: {} }),
}));

vi.mock("@/hooks/use-toast", () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/components/modules/CompanyModulesList", () => ({
    CompanyModulesList: () => null,
}));
vi.mock("@/components/admin/worklog-definition-builder", () => ({
    WorklogDefinitionBuilder: () => <div data-testid="worklog-builder" />,
}));
vi.mock("@/components/admin/tax-config-builder", () => ({
    TaxConfigBuilder: () => <div data-testid="tax-builder" />,
}));

import { CompanyConfigurationTab } from "@/components/admin/company-configuration-tab";

const company = {
    id: "c-1",
    name: "Escuela Sierra",
    settings: { default_is_gross: false },
    platformSettings: { plan: "pro", limits: { max_monitors: 10, max_managers: 2 }, modules: {} },
    taxConfig: { social_security: 0, irpf_base: 0 },
    worklogDefinitions: {},
};

function renderTab() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
        <QueryClientProvider client={client}>
            <CompanyConfigurationTab company={company} />
        </QueryClientProvider>
    );
}

describe("CompanyConfigurationTab", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("worker (no manager ni PA) solo ve Modulos Activos y no ve ajustes editables ni JSON", () => {
        permissions.isPlatformAdmin = false;
        permissions.role = "worker";
        renderTab();

        expect(screen.getByText("Módulos Activos")).toBeInTheDocument();
        expect(screen.queryByText("Ajustes de Empresa")).toBeNull();
        expect(screen.queryByText("Tipos de Turno e Impuestos")).toBeNull();
        expect(screen.queryByText("Ajustes de Plataforma")).toBeNull();
        expect(screen.queryByRole("button", { name: /Ver JSON/i })).toBeNull();
        expect(screen.queryByRole("link", { name: /Gestionar Módulos/ })).toBeNull();
    });

    it("manager (no PA) ve Ajustes de Empresa y Tipos de Turno e Impuestos pero no Ajustes de Plataforma ni Ver JSON", () => {
        permissions.isPlatformAdmin = false;
        permissions.role = "manager";
        renderTab();

        expect(screen.getByText("Módulos Activos")).toBeInTheDocument();
        expect(screen.getByText("Ajustes de Empresa")).toBeInTheDocument();
        expect(screen.getByText("Tipos de Turno e Impuestos")).toBeInTheDocument();
        expect(screen.queryByText("Ajustes de Plataforma")).toBeNull();
        expect(screen.queryByRole("button", { name: /Ver JSON/i })).toBeNull();
        expect(screen.queryByRole("link", { name: /Gestionar Módulos/ })).toBeNull();
    });

    it("platform admin ve Ajustes de Empresa, Tipos de Turno e Impuestos, Ajustes de Plataforma y botones Ver JSON", () => {
        permissions.isPlatformAdmin = true;
        permissions.role = "admin";
        renderTab();

        expect(screen.getByText("Módulos Activos")).toBeInTheDocument();
        expect(screen.getByText("Ajustes de Empresa")).toBeInTheDocument();
        expect(screen.getByText("Tipos de Turno e Impuestos")).toBeInTheDocument();
        expect(screen.getByText("Ajustes de Plataforma")).toBeInTheDocument();
        expect(screen.getAllByRole("button", { name: /Ver JSON/i }).length).toBeGreaterThanOrEqual(4);
        expect(screen.getByRole("link", { name: /Gestionar Módulos/ })).toBeInTheDocument();
    });
});
