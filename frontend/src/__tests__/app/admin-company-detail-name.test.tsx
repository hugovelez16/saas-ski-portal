import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { getCompaniesDetailed, updateCompany, toast, permissions } = vi.hoisted(() => ({
    getCompaniesDetailed: vi.fn(),
    updateCompany: vi.fn(),
    toast: vi.fn(),
    permissions: { canEditCompany: true, canManageMembers: true },
}));

vi.mock("@/lib/api/companies", () => ({
    getCompaniesDetailed,
    updateCompany,
    updateMemberStatus: vi.fn(),
    updateMemberRole: vi.fn(),
    getCompanyRates: vi.fn().mockResolvedValue([]),
}));

vi.mock("@/hooks/use-permissions", () => ({
    usePermissions: () => ({
        canEditCompany: permissions.canEditCompany,
        canManageMembers: permissions.canManageMembers,
    }),
}));

vi.mock("@/context/AuthContext", () => ({
    useAuth: () => ({ user: { role: "admin" } }),
}));

vi.mock("next/navigation", () => ({
    useParams: () => ({ companyId: "c-1" }),
    useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/hooks/use-toast", () => ({
    useToast: () => ({ toast }),
}));

// Componentes pesados de las pestanas: no se renderizan en estos tests.
vi.mock("@/components/admin/add-member-dialog", () => ({ AddMemberDialog: () => null }));
vi.mock("@/components/admin/company-configuration-tab", () => ({ CompanyConfigurationTab: () => null }));
vi.mock("@/components/admin/daily-report-view", () => ({ DailyReportView: () => null }));
vi.mock("@/components/admin/json-editor", () => ({ JsonEditor: () => null }));
vi.mock("@/components/admin/tax-config-builder", () => ({ TaxConfigBuilder: () => null }));
vi.mock("@/components/admin/worklog-definition-builder", () => ({ WorklogDefinitionBuilder: () => null }));
vi.mock("@/components/admin/user-rates-edit-dialog", () => ({ UserRatesEditDialog: () => null }));

import CompanyDetailsPage from "@/app/(app)/admin/companies/[companyId]/page";

// jsdom no implementa ResizeObserver, que usan los componentes Radix.
class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

const EDIT_BUTTON_LABEL = "Editar nombre de la empresa";
const SAVE_BUTTON_LABEL = "Guardar nombre";
const NAME_INPUT_LABEL = "Nombre de la empresa";

function buildCompany(overrides: Record<string, unknown> = {}) {
    return {
        id: "c-1",
        name: "Escuela Sierra",
        isActive: true,
        isManaged: false,
        taxConfig: {},
        settings: {},
        worklogDefinitions: {},
        createdAt: "2026-01-01T00:00:00Z",
        updatedAt: "2026-01-01T00:00:00Z",
        members: [],
        ...overrides,
    };
}

function renderPage() {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return render(
        <QueryClientProvider client={client}>
            <CompanyDetailsPage />
        </QueryClientProvider>
    );
}

describe("CompanyDetailsPage: edicion del nombre de la empresa", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        permissions.canEditCompany = true;
        permissions.canManageMembers = true;
        getCompaniesDetailed.mockResolvedValue([buildCompany()]);
        updateCompany.mockResolvedValue({ ...buildCompany(), name: "Nuevo" });
    });

    it("no muestra el control de edicion sin canEditCompany", async () => {
        permissions.canEditCompany = false;
        renderPage();

        expect(await screen.findByRole("heading", { name: "Escuela Sierra" })).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: EDIT_BUTTON_LABEL })).not.toBeInTheDocument();
        expect(screen.queryByLabelText(NAME_INPUT_LABEL)).not.toBeInTheDocument();
    });

    it("con permiso, guarda el nombre recortado mediante updateCompany", async () => {
        renderPage();

        fireEvent.click(await screen.findByRole("button", { name: EDIT_BUTTON_LABEL }));
        const input = screen.getByLabelText(NAME_INPUT_LABEL) as HTMLInputElement;
        expect(input.value).toBe("Escuela Sierra");

        fireEvent.change(input, { target: { value: "  Nuevo  " } });
        fireEvent.click(screen.getByRole("button", { name: SAVE_BUTTON_LABEL }));

        await waitFor(() => {
            expect(updateCompany).toHaveBeenCalledTimes(1);
        });
        expect(updateCompany).toHaveBeenCalledWith("c-1", { name: "Nuevo" });
        await waitFor(() => {
            expect(toast).toHaveBeenCalledWith(
                expect.objectContaining({ title: "Nombre de la empresa actualizado" })
            );
        });
    });

    it("no llama a updateCompany si el nombre queda vacio tras recortar", async () => {
        renderPage();

        fireEvent.click(await screen.findByRole("button", { name: EDIT_BUTTON_LABEL }));
        fireEvent.change(screen.getByLabelText(NAME_INPUT_LABEL), { target: { value: "   " } });
        fireEvent.click(screen.getByRole("button", { name: SAVE_BUTTON_LABEL }));

        expect(await screen.findByText("El nombre no puede estar vacío.")).toBeInTheDocument();
        expect(updateCompany).not.toHaveBeenCalled();
    });

    it("no llama a updateCompany si el nombre no ha cambiado", async () => {
        renderPage();

        fireEvent.click(await screen.findByRole("button", { name: EDIT_BUTTON_LABEL }));
        fireEvent.change(screen.getByLabelText(NAME_INPUT_LABEL), { target: { value: "  Escuela Sierra " } });
        fireEvent.click(screen.getByRole("button", { name: SAVE_BUTTON_LABEL }));

        expect(await screen.findByText("El nombre no ha cambiado.")).toBeInTheDocument();
        expect(updateCompany).not.toHaveBeenCalled();
    });

    it("no llama a updateCompany si el nombre supera 120 caracteres", async () => {
        renderPage();

        fireEvent.click(await screen.findByRole("button", { name: EDIT_BUTTON_LABEL }));
        fireEvent.change(screen.getByLabelText(NAME_INPUT_LABEL), { target: { value: "a".repeat(121) } });
        fireEvent.click(screen.getByRole("button", { name: SAVE_BUTTON_LABEL }));

        expect(await screen.findByText("El nombre no puede superar los 120 caracteres.")).toBeInTheDocument();
        expect(updateCompany).not.toHaveBeenCalled();
    });

    it("muestra el detalle del error del servidor en el toast", async () => {
        updateCompany.mockRejectedValue({
            response: { status: 422, data: { detail: "El nombre de la empresa no es válido" } },
        });
        renderPage();

        fireEvent.click(await screen.findByRole("button", { name: EDIT_BUTTON_LABEL }));
        fireEvent.change(screen.getByLabelText(NAME_INPUT_LABEL), { target: { value: "Nuevo" } });
        fireEvent.click(screen.getByRole("button", { name: SAVE_BUTTON_LABEL }));

        await waitFor(() => {
            expect(toast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: "Error al guardar el nombre",
                    description: "El nombre de la empresa no es válido",
                    variant: "destructive",
                })
            );
        });
    });

    it("cancelar sale del modo edicion sin llamar a la API", async () => {
        renderPage();

        fireEvent.click(await screen.findByRole("button", { name: EDIT_BUTTON_LABEL }));
        fireEvent.change(screen.getByLabelText(NAME_INPUT_LABEL), { target: { value: "Otro" } });
        fireEvent.click(screen.getByRole("button", { name: "Cancelar edición de nombre" }));

        expect(screen.queryByLabelText(NAME_INPUT_LABEL)).not.toBeInTheDocument();
        expect(screen.getByRole("heading", { name: "Escuela Sierra" })).toBeInTheDocument();
        expect(updateCompany).not.toHaveBeenCalled();
    });
});
