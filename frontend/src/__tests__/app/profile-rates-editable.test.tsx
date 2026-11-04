import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProfilePage from "@/app/(app)/profile/page";

const state = vi.hoisted(() => ({
    user: null as Record<string, unknown> | null,
    companies: [] as Array<Record<string, unknown>>,
}));

vi.mock("@/context/AuthContext", () => ({
    useAuth: () => ({ user: state.user, checkAuth: vi.fn() }),
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
    getMyCompanies: vi.fn(async () => state.companies),
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

const EDITABLE_TEXT = "Gestiona tus tarifas para la empresa activa.";
const READ_ONLY_TEXT = "Consulta las tarifas fijadas por la dirección (Modo Gestionado).";
const SAVE_BUTTON = "Guardar Tarifas";

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

function setUser(overrides: Record<string, unknown> = {}) {
    state.user = {
        id: "user-1",
        email: "ana@test.com",
        firstName: "Ana",
        lastName: "Monitora",
        role: "user",
        isActive: true,
        activeCompanyId: "company-1",
        activeRole: "worker",
        ...overrides,
    };
}

describe("ProfilePage: edicion de tarifas", () => {
    beforeEach(() => {
        state.companies = [];
    });

    it("permite editar a un trabajador en empresa autonoma (isManaged false)", async () => {
        state.companies = [{ id: "company-1", name: "Escuela Norte", worklogDefinitions: {}, isManaged: false, role: "worker" }];
        setUser();

        renderProfile();

        expect(await screen.findByText(EDITABLE_TEXT)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: SAVE_BUTTON })).toBeInTheDocument();
    });

    it("es de solo lectura si isManaged no esta confirmado (undefined)", async () => {
        state.companies = [{ id: "company-1", name: "Escuela Norte", worklogDefinitions: {}, role: "worker" }];
        setUser();

        renderProfile();

        expect(await screen.findByText(READ_ONLY_TEXT)).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: SAVE_BUTTON })).not.toBeInTheDocument();
    });

    it("es de solo lectura para un worker en empresa gestionada (isManaged true)", async () => {
        state.companies = [{ id: "company-1", name: "Escuela Norte", worklogDefinitions: {}, isManaged: true, role: "worker" }];
        setUser({ activeRole: "worker" });

        renderProfile();

        expect(await screen.findByText(READ_ONLY_TEXT)).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: SAVE_BUTTON })).not.toBeInTheDocument();
    });

    it("permite editar a un manager en empresa gestionada (isManaged true)", async () => {
        state.companies = [{ id: "company-1", name: "Escuela Norte", worklogDefinitions: {}, isManaged: true, role: "manager" }];
        setUser({ activeRole: "manager" });

        renderProfile();

        expect(await screen.findByText(EDITABLE_TEXT)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: SAVE_BUTTON })).toBeInTheDocument();
    });

    it("es de solo lectura si la empresa activa no esta cargada (currentCompany undefined)", async () => {
        state.companies = [];
        setUser();

        renderProfile();

        expect(await screen.findByText(READ_ONLY_TEXT)).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: SAVE_BUTTON })).not.toBeInTheDocument();
    });
});
