import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const {
    previewInvitation,
    acceptInvitation,
    pushMock,
    switchScopeMock,
    logoutMock,
    authState,
    tokenState,
} = vi.hoisted(() => ({
    previewInvitation: vi.fn(),
    acceptInvitation: vi.fn(),
    pushMock: vi.fn(),
    switchScopeMock: vi.fn(),
    logoutMock: vi.fn(),
    authState: { user: null as any, loading: false },
    tokenState: { token: "tok-123" as string | null },
}));

vi.mock("@/lib/api/v2/invitations", () => ({
    previewInvitation,
    acceptInvitation,
}));

vi.mock("@/context/AuthContext", () => ({
    useAuth: () => ({
        user: authState.user,
        loading: authState.loading,
        switchScope: switchScopeMock,
        logout: logoutMock,
    }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: pushMock }),
    useSearchParams: () => ({
        get: (key: string) => (key === "token" ? tokenState.token : null),
    }),
}));

vi.mock("next/image", () => ({
    default: ({ alt, priority: _priority, ...props }: React.ImgHTMLAttributes<HTMLImageElement> & { priority?: boolean }) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img alt={alt} {...props} />
    ),
}));

import AcceptInvitationPage from "@/app/invitations/accept/page";

describe("AcceptInvitationPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        tokenState.token = "tok-123";
        authState.user = null;
        authState.loading = false;
        previewInvitation.mockResolvedValue({
            company_id: "c-1",
            company_name: "Escuela Sierra",
            status: "pending",
            expires_at: "2026-12-05T12:00:00Z",
        });
    });

    it("sin sesion muestra empresa y guia a iniciar sesion con retorno", async () => {
        render(<AcceptInvitationPage />);

        expect(await screen.findByText("Escuela Sierra")).toBeInTheDocument();
        const btn = screen.getByRole("button", { name: "Iniciar sesion para aceptar" });
        fireEvent.click(btn);

        expect(pushMock).toHaveBeenCalledWith(
            `/login?next=${encodeURIComponent("/invitations/accept?token=tok-123")}`
        );
    });

    it("con sesion valida acepta la invitacion y permite entrar en la empresa", async () => {
        authState.user = { id: "u-1", email: "monitor@sierra.es" };
        acceptInvitation.mockResolvedValue({
            company_id: "c-1",
            company_name: "Escuela Sierra",
            membership: { user_id: "u-1", company_id: "c-1", role: "worker", is_active: true },
        });

        render(<AcceptInvitationPage />);

        const acceptBtn = await screen.findByRole("button", { name: "Aceptar invitacion" });
        fireEvent.click(acceptBtn);

        await waitFor(() => {
            expect(acceptInvitation).toHaveBeenCalledWith("tok-123");
        });
        expect(await screen.findByText("Invitacion aceptada")).toBeInTheDocument();

        fireEvent.click(screen.getByRole("button", { name: "Entrar en Escuela Sierra" }));
        expect(switchScopeMock).toHaveBeenCalledWith("c-1");
    });

    it("muestra mensaje especifico y opcion de cambiar cuenta ante error de otro correo", async () => {
        authState.user = { id: "u-2", email: "otro@sierra.es" };
        acceptInvitation.mockRejectedValue({
            response: { status: 403, data: { detail: "Esta invitacion es para otro correo" } },
        });

        render(<AcceptInvitationPage />);

        fireEvent.click(await screen.findByRole("button", { name: "Aceptar invitacion" }));

        expect(await screen.findByText("Esta invitacion es para otro correo")).toBeInTheDocument();
        fireEvent.click(screen.getByRole("button", { name: "Cerrar sesion y cambiar de cuenta" }));
        expect(logoutMock).toHaveBeenCalled();
    });
});
