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
}));

vi.mock("@/lib/api/companies", () => ({
  getMyCompanies,
}));

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
    apiGet.mockResolvedValue({ data: [{ id: "c1", name: "Querkus", role: "owner" }] });

    renderDialog();

    await waitFor(() => expect(screen.getByText("Querkus")).toBeTruthy());

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
});
