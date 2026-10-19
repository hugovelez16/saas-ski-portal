import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProfilePage from "@/app/(app)/profile/page";

const authState = vi.hoisted(() => ({
    user: null as Record<string, unknown> | null,
}));

vi.mock("@/context/AuthContext", () => ({
    useAuth: () => ({ user: authState.user, checkAuth: vi.fn() }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/hooks/use-toast", () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/components/auth/two-factor-card", () => ({
    TwoFactorCard: () => null,
}));

vi.mock("@/lib/api/settings", () => ({
    getUserRates: vi.fn(async () => []),
    updateUserRates: vi.fn(),
    getCompanies: vi.fn(async () => []),
}));

vi.mock("@/lib/api/companies", () => ({
    getMyCompanies: vi.fn(async () => [
        { id: "company-1", name: "Escuela Norte", worklogDefinitions: {} },
    ]),
}));

vi.mock("@/lib/api/users", () => ({
    updateMe: vi.fn(),
    changePassword: vi.fn(),
}));

// jsdom no implementa ResizeObserver, que usan los componentes Radix (Switch).
class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

function renderProfile() {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={queryClient}>
            <ProfilePage />
        </QueryClientProvider>
    );
}

describe("ProfilePage", () => {
    it("no muestra el selector de empresa por defecto", async () => {
        authState.user = {
            id: "user-1",
            email: "ana@test.com",
            firstName: "Ana",
            lastName: "Monitora",
            role: "worker",
            isActive: true,
            activeCompanyId: "company-1",
        };

        renderProfile();

        expect(await screen.findByText("User Information")).toBeInTheDocument();
        expect(screen.queryByText("Empresa de Inicio (Login)")).not.toBeInTheDocument();
        expect(screen.queryByText("Seleccionar empresa de inicio")).not.toBeInTheDocument();
    });
});
