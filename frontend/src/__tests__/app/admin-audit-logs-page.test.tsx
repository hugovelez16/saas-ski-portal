import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { getAuditLogs, getAuditActions, getCompaniesDetailed, replace, auth } = vi.hoisted(() => ({
    getAuditLogs: vi.fn(),
    getAuditActions: vi.fn(),
    getCompaniesDetailed: vi.fn(),
    replace: vi.fn(),
    auth: { user: null as any, loading: false },
}));

vi.mock("@/lib/api/audit-logs", () => ({
    getAuditLogs,
    getAuditActions,
}));

vi.mock("@/lib/api/companies", () => ({
    getCompaniesDetailed,
}));

vi.mock("@/context/AuthContext", () => ({
    useAuth: () => ({ user: auth.user, loading: auth.loading }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), replace }),
}));

import AuditLogsPage from "@/app/(app)/admin/audit-logs/page";

// jsdom no implementa ResizeObserver, que usan los componentes Radix (Select).
class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

function buildItem(overrides: Record<string, unknown> = {}) {
    return {
        id: "log-1",
        action: "company.update",
        createdAt: "2026-03-10T10:00:00Z",
        actorUserId: "a-1",
        actorEmail: "admin@vesotel.com",
        companyId: "c-1",
        targetUserId: null,
        oldValue: { isActive: true },
        newValue: { isActive: false },
        reason: "Impago",
        extraData: null,
        ...overrides,
    };
}

function renderPage() {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return render(
        <QueryClientProvider client={client}>
            <AuditLogsPage />
        </QueryClientProvider>
    );
}

describe("AuditLogsPage (admin/audit-logs)", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        auth.user = { id: "u-1", role: "admin", isPlatformAdmin: true };
        auth.loading = false;
        getCompaniesDetailed.mockResolvedValue([{ id: "c-1", name: "Escuela Sierra" }]);
        getAuditActions.mockResolvedValue(["company.update"]);
        getAuditLogs.mockResolvedValue({ total: 1, items: [buildItem()] });
    });

    it("renderiza los registros con el nombre de la empresa y la accion", async () => {
        renderPage();

        expect(await screen.findByText("admin@vesotel.com")).toBeInTheDocument();
        expect(screen.getByText("Escuela Sierra")).toBeInTheDocument();
        expect(screen.getByText("company.update")).toBeInTheDocument();
        expect(screen.getByText("Impago")).toBeInTheDocument();
        expect(screen.getByText("Mostrando 1-1 de 1")).toBeInTheDocument();
    });

    it("consulta con limit 50 y offset 0 al cargar", async () => {
        renderPage();

        await screen.findByText("admin@vesotel.com");
        expect(getAuditLogs).toHaveBeenCalledWith(expect.objectContaining({ limit: 50, offset: 0 }));
        expect(getAuditActions).toHaveBeenCalled();
    });

    it("muestra el detalle en JSON como texto al desplegar la fila", async () => {
        renderPage();

        await screen.findByText("admin@vesotel.com");
        fireEvent.click(screen.getByRole("button", { name: /ver/i }));

        expect(screen.getByText("Valor anterior")).toBeInTheDocument();
        expect(screen.getByText(/"isActive": true/)).toBeInTheDocument();
        expect(screen.getByText(/"isActive": false/)).toBeInTheDocument();
    });

    it("pagina hacia delante con offset 50 cuando hay mas registros", async () => {
        getAuditLogs.mockResolvedValue({ total: 120, items: [buildItem()] });
        renderPage();

        await screen.findByText("Mostrando 1-1 de 120");
        fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));

        await waitFor(() =>
            expect(getAuditLogs).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 50, limit: 50 }))
        );
    });

    it("redirige a /dashboard y no consulta si el usuario no es platform admin", async () => {
        auth.user = { id: "u-2", role: "manager", isPlatformAdmin: false };
        renderPage();

        await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
        expect(getAuditLogs).not.toHaveBeenCalled();
    });
});
