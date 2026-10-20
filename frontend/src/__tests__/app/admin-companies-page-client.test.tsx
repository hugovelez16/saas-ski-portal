import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { getCompaniesDetailed, updateCompany, createCompany, permissions } = vi.hoisted(() => ({
    getCompaniesDetailed: vi.fn(),
    updateCompany: vi.fn(),
    createCompany: vi.fn(),
    permissions: { canEditCompany: true },
}));

vi.mock("@/lib/api/companies", () => ({
    getCompaniesDetailed,
    updateCompany,
    createCompany,
}));

vi.mock("@/hooks/use-permissions", () => ({
    usePermissions: () => ({ canEditCompany: permissions.canEditCompany }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/hooks/use-toast", () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

import AdminCompaniesPage from "@/app/(app)/admin/companies/CompaniesPageClient";

// jsdom no implementa ResizeObserver, que usan los componentes Radix (Switch).
class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

function buildCompany(overrides: Record<string, unknown> = {}) {
    return {
        id: "c-1",
        name: "Escuela Sierra",
        isActive: true,
        isManaged: false,
        taxConfig: { social_security: 0.0648, irpf_base: 0 },
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
            <AdminCompaniesPage />
        </QueryClientProvider>
    );
}

describe("AdminCompaniesPage (CompaniesPageClient)", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        permissions.canEditCompany = true;
        updateCompany.mockResolvedValue({});
    });

    it("pide confirmacion antes de suspender y envia el motivo", async () => {
        getCompaniesDetailed.mockResolvedValue([buildCompany()]);
        renderPage();
        await screen.findByText("Escuela Sierra");

        // En vista de tarjetas, cada tarjeta tiene [modo gestionada, activa].
        const switches = screen.getAllByRole("switch");
        fireEvent.click(switches[1]);

        const dialog = await screen.findByRole("dialog");
        expect(updateCompany).not.toHaveBeenCalled();

        fireEvent.change(within(dialog).getByLabelText(/Motivo/), {
            target: { value: "Impago de la licencia" },
        });
        fireEvent.click(within(dialog).getByRole("button", { name: "Suspender" }));

        await waitFor(() => {
            expect(updateCompany).toHaveBeenCalledWith("c-1", {
                isActive: false,
                reason: "Impago de la licencia",
            });
        });
    });

    it("no envia motivo vacio al suspender", async () => {
        getCompaniesDetailed.mockResolvedValue([buildCompany()]);
        renderPage();
        await screen.findByText("Escuela Sierra");

        fireEvent.click(screen.getAllByRole("switch")[1]);
        const dialog = await screen.findByRole("dialog");
        fireEvent.click(within(dialog).getByRole("button", { name: "Suspender" }));

        await waitFor(() => {
            expect(updateCompany).toHaveBeenCalledWith("c-1", { isActive: false });
        });
    });

    it("pide confirmacion antes de reactivar y no pide motivo", async () => {
        getCompaniesDetailed.mockResolvedValue([buildCompany({ isActive: false })]);
        renderPage();
        await screen.findByText("Escuela Sierra");

        fireEvent.click(screen.getAllByRole("switch")[1]);
        const dialog = await screen.findByRole("dialog");
        expect(within(dialog).queryByLabelText(/Motivo/)).toBeNull();
        expect(updateCompany).not.toHaveBeenCalled();

        fireEvent.click(within(dialog).getByRole("button", { name: "Reactivar" }));

        await waitFor(() => {
            expect(updateCompany).toHaveBeenCalledWith("c-1", { isActive: true });
        });
    });

    it("pide confirmacion antes de cambiar el modo gestionada", async () => {
        getCompaniesDetailed.mockResolvedValue([buildCompany()]);
        renderPage();
        await screen.findByText("Escuela Sierra");

        fireEvent.click(screen.getAllByRole("switch")[0]);
        const dialog = await screen.findByRole("dialog");
        expect(updateCompany).not.toHaveBeenCalled();

        fireEvent.click(within(dialog).getByRole("button", { name: "Activar" }));

        await waitFor(() => {
            expect(updateCompany).toHaveBeenCalledWith("c-1", { isManaged: true });
        });
    });

    it("no muestra acciones de edicion sin canEditCompany y no muestra CIF/NIF", async () => {
        permissions.canEditCompany = false;
        getCompaniesDetailed.mockResolvedValue([buildCompany()]);
        renderPage();
        await screen.findByText("Escuela Sierra");

        expect(screen.queryAllByRole("switch")).toHaveLength(0);
        expect(screen.queryByText(/CIF\/NIF/)).toBeNull();
    });
});
