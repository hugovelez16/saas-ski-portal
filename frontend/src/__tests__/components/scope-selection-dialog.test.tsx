import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const { authState, switchScope, apiGet, getMyCompanies } = vi.hoisted(() => ({
  authState: { user: null as any },
  switchScope: vi.fn(),
  apiGet: vi.fn(),
  getMyCompanies: vi.fn(),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: authState.user, switchScope }),
}));

vi.mock("@/lib/api", () => ({
  default: { get: apiGet },
  SUSPENDED_COMPANY_MESSAGE: "Tu empresa esta suspendida. Contacta con el administrador",
}));

// getCompanies (PA) se ejecuta real: GET /v2/companies sobre el apiGet mockeado.
vi.mock("@/lib/api/companies", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/companies")>();
  return { ...actual, getMyCompanies };
});

import { ScopeSelectionDialog } from "@/components/auth/scope-selection-dialog";

const renderDialog = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ScopeSelectionDialog open onOpenChange={vi.fn()} />
    </QueryClientProvider>
  );
};

describe("ScopeSelectionDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("muestra tres botones por empresa al PA y envia el ambito elegido", async () => {
    authState.user = {
      id: "admin1",
      email: "admin@b.c",
      role: "admin",
      isPlatformAdmin: true,
      isActive: true,
      activeCompanyId: null,
      activeRole: null,
      createdAt: "2026-01-01T00:00:00",
    };
    apiGet.mockResolvedValue({ data: { items: [{ id: "c1", name: "Querkus", is_active: true }], total: 1 } });

    renderDialog();

    await waitFor(() => expect(screen.getByText("Querkus")).toBeTruthy());
    expect(apiGet).toHaveBeenCalledWith("/v2/companies", { params: { limit: 2000 } });

    expect(screen.getByRole("button", { name: "Gestionar" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Ver como manager/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Ver como worker/ })).toBeTruthy();
    expect(screen.getAllByText("Solo lectura")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: /Ver como worker/ }));
    expect(switchScope).toHaveBeenCalledTimes(1);
    expect(switchScope.mock.calls[0][0]).toBe("c1");
    expect(switchScope.mock.calls[0][1]).toBe("worker");

    fireEvent.click(screen.getByRole("button", { name: /Ver como manager/ }));
    expect(switchScope.mock.calls[1][0]).toBe("c1");
    expect(switchScope.mock.calls[1][1]).toBe("manager");

    fireEvent.click(screen.getByRole("button", { name: "Gestionar" }));
    expect(switchScope.mock.calls[2][0]).toBe("c1");
    expect(switchScope.mock.calls[2][1]).toBeUndefined();
  });

  it("muestra un unico boton Entrar a un manager y no ofrece cambio de rol", async () => {
    authState.user = {
      id: "u1",
      email: "m@b.c",
      role: "user",
      isManager: true,
      isPlatformAdmin: false,
      isActive: true,
      activeCompanyId: "c1",
      activeRole: "manager",
      createdAt: "2026-01-01T00:00:00",
    };
    getMyCompanies.mockResolvedValue([{ id: "c1", name: "Querkus", role: "manager" }]);

    renderDialog();

    await waitFor(() => expect(screen.getByText("Querkus")).toBeTruthy());

    const entrar = screen.getAllByRole("button", { name: "Entrar" });
    expect(entrar).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /Ver como/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Gestionar" })).toBeNull();
    expect(screen.getByText("Tu Rol: manager")).toBeTruthy();

    fireEvent.click(entrar[0]);
    expect(switchScope).toHaveBeenCalledWith("c1", undefined);
  });

  it("no ofrece empresas suspendidas a un manager y muestra el aviso si no queda ninguna", async () => {
    authState.user = {
      id: "u1",
      email: "m@b.c",
      role: "user",
      isManager: true,
      isPlatformAdmin: false,
      isActive: true,
      activeCompanyId: null,
      activeRole: null,
      createdAt: "2026-01-01T00:00:00",
    };
    getMyCompanies.mockResolvedValue([
      { id: "c1", name: "Suspendida SL", role: "manager", isActive: false },
    ]);

    renderDialog();

    await waitFor(() => expect(screen.getByText(/Tu empresa esta suspendida/)).toBeTruthy());
    expect(screen.queryByText("Suspendida SL")).toBeNull();
    expect(screen.queryByRole("button", { name: "Entrar" })).toBeNull();
  });

  it("el PA si ve las empresas suspendidas", async () => {
    authState.user = {
      id: "admin1",
      email: "admin@b.c",
      role: "admin",
      isPlatformAdmin: true,
      isActive: true,
      activeCompanyId: null,
      activeRole: null,
      createdAt: "2026-01-01T00:00:00",
    };
    apiGet.mockResolvedValue({ data: { items: [{ id: "c1", name: "Suspendida SL", is_active: false }], total: 1 } });

    renderDialog();

    await waitFor(() => expect(screen.getByText("Suspendida SL")).toBeTruthy());
  });
});
