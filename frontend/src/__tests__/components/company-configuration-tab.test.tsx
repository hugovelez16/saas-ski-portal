import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { permissions } = vi.hoisted(() => ({
    permissions: { isPlatformAdmin: true },
}));

vi.mock("@/hooks/use-permissions", () => ({
    usePermissions: () => ({
        isPlatformAdmin: permissions.isPlatformAdmin,
        canEditCompany: permissions.isPlatformAdmin,
    }),
}));

vi.mock("@/lib/api/companies", () => ({
    updateCompany: vi.fn(),
}));

vi.mock("@/hooks/use-toast", () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/components/modules/CompanyModulesList", () => ({
    CompanyModulesList: () => null,
}));
vi.mock("@/components/admin/business-logic-builder", () => ({
    BusinessLogicBuilder: () => null,
}));
vi.mock("@/components/admin/worker-ux-builder", () => ({
    WorkerUXBuilder: () => null,
}));
vi.mock("@/components/admin/worklog-definition-builder", () => ({
    WorklogDefinitionBuilder: () => null,
}));
vi.mock("@/components/admin/tax-config-builder", () => ({
    TaxConfigBuilder: () => null,
}));

import { CompanyConfigurationTab } from "@/components/admin/company-configuration-tab";

const company = {
    id: "c-1",
    name: "Escuela Sierra",
    settings: {},
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

    it("manager (no PA) solo ve Modulos Activos y no ve enlace a Gestionar Modulos", () => {
        permissions.isPlatformAdmin = false;
        renderTab();

        expect(screen.getByText("Módulos Activos")).toBeInTheDocument();
        expect(screen.queryByText("Reglas de Negocio")).toBeNull();
        expect(screen.queryByText("Experiencia del Trabajador")).toBeNull();
        expect(screen.queryByText("Definiciones Técnicas")).toBeNull();
        expect(screen.queryByRole("link", { name: /Gestionar Módulos/ })).toBeNull();
    });

    it("platform admin ve todos los editores y el enlace a Gestionar Modulos", () => {
        permissions.isPlatformAdmin = true;
        renderTab();

        expect(screen.getByText("Módulos Activos")).toBeInTheDocument();
        expect(screen.getByText("Reglas de Negocio")).toBeInTheDocument();
        expect(screen.getByText("Experiencia del Trabajador")).toBeInTheDocument();
        expect(screen.getByText("Definiciones Técnicas")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /Gestionar Módulos/ })).toBeInTheDocument();
    });
});
