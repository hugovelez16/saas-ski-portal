import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const {
    getAuditLogs,
    getAuditActions,
    getAuditPurgePreview,
    purgeAuditLogs,
    getCompaniesDetailed,
    replace,
    auth,
} = vi.hoisted(() => ({
    getAuditLogs: vi.fn(),
    getAuditActions: vi.fn(),
    getAuditPurgePreview: vi.fn(),
    purgeAuditLogs: vi.fn(),
    getCompaniesDetailed: vi.fn(),
    replace: vi.fn(),
    auth: { user: null as any, loading: false },
}));

vi.mock("@/lib/api/audit-logs", () => ({
    getAuditLogs,
    getAuditActions,
    getAuditPurgePreview,
    purgeAuditLogs,
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
        getAuditPurgePreview.mockResolvedValue({ before: "2026-01-01T00:00:00Z", count: 3 });
        purgeAuditLogs.mockResolvedValue({ before: "2026-01-01T00:00:00Z", deletedCount: 3, auditLogId: "log-p" });
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

    it("permite previsualizar el recuento, confirmar la purga y refresca la tabla", async () => {
        renderPage();
        await screen.findByText("admin@vesotel.com");

        fireEvent.click(screen.getByRole("button", { name: /purgar registros/i }));
        const dateInput = screen.getByLabelText(/eliminar registros anteriores a/i);
        fireEvent.change(dateInput, { target: { value: "2026-01-15" } });

        fireEvent.click(screen.getByRole("button", { name: /consultar recuento/i }));
        expect(await screen.findByText(/se eliminarán 3 registros anteriores al 15\/01\/2026/i)).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText(/motivo \(opcional\)/i), { target: { value: "Limpieza" } });
        fireEvent.click(screen.getByRole("button", { name: /confirmar purga/i }));

        await waitFor(() =>
            expect(purgeAuditLogs).toHaveBeenCalledWith({
                before: new Date("2026-01-15T00:00:00").toISOString(),
                reason: "Limpieza",
            })
        );
        await waitFor(() => expect(getAuditLogs).toHaveBeenCalledTimes(2));
    });
});
