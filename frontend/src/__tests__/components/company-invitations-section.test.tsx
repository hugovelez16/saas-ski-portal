import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { listInvitations, createInvitation, resendInvitation, cancelInvitation, toast } = vi.hoisted(() => ({
    listInvitations: vi.fn(),
    createInvitation: vi.fn(),
    resendInvitation: vi.fn(),
    cancelInvitation: vi.fn(),
    toast: vi.fn(),
}));

vi.mock("@/lib/api/v2/invitations", () => ({
    listInvitations,
    createInvitation,
    resendInvitation,
    cancelInvitation,
}));

vi.mock("@/hooks/use-toast", () => ({
    useToast: () => ({ toast }),
}));

import { CompanyInvitationsSection } from "@/components/company/company-invitations-section";

function renderSection(props: Partial<React.ComponentProps<typeof CompanyInvitationsSection>> = {}) {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return render(
        <QueryClientProvider client={client}>
            <CompanyInvitationsSection companyId="c-1" {...props} />
        </QueryClientProvider>
    );
}

describe("CompanyInvitationsSection", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        listInvitations.mockResolvedValue([
            {
                id: "inv-1",
                company_id: "c-1",
                email: "monitor@escuela.es",
                status: "pending",
                invited_by_user_id: "u-mgr",
                invited_by_name: "Ana Gestora",
                expires_at: "2026-12-05T12:00:00Z",
                accepted_at: null,
                cancelled_at: null,
                created_at: "2026-11-28T12:00:00Z",
            },
        ]);
        createInvitation.mockResolvedValue({ id: "inv-2" });
        resendInvitation.mockResolvedValue({ id: "inv-1" });
        cancelInvitation.mockResolvedValue({ id: "inv-1", status: "cancelled" });
    });

    it("lista invitaciones pendientes y permite enviar, reenviar y cancelar", async () => {
        renderSection();

        expect(await screen.findByText("monitor@escuela.es")).toBeInTheDocument();
        expect(screen.getByText("Pendiente")).toBeInTheDocument();

        const input = screen.getByLabelText("Correo del trabajador a invitar");
        fireEvent.change(input, { target: { value: "nuevo@escuela.es" } });
        fireEvent.click(screen.getByRole("button", { name: "Enviar invitacion" }));

        await waitFor(() => {
            expect(createInvitation).toHaveBeenCalledWith("c-1", "nuevo@escuela.es", { asAdmin: false });
        });

        fireEvent.click(screen.getByRole("button", { name: "Reenviar" }));
        await waitFor(() => {
            expect(resendInvitation).toHaveBeenCalledWith("c-1", "inv-1", { asAdmin: false });
        });

        fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
        await waitFor(() => {
            expect(cancelInvitation).toHaveBeenCalledWith("c-1", "inv-1", { asAdmin: false });
        });
    });

    it("oculta acciones de escritura cuando canInvite es false", async () => {
        renderSection({ canInvite: false });

        expect(await screen.findByText("monitor@escuela.es")).toBeInTheDocument();
        expect(screen.queryByLabelText("Correo del trabajador a invitar")).not.toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Reenviar" })).not.toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Cancelar" })).not.toBeInTheDocument();
    });
});
