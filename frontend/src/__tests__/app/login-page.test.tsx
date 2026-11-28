import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const { loginMock, devLoginMock, verify2FAMock, pushMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
  devLoginMock: vi.fn(),
  verify2FAMock: vi.fn(),
  pushMock: vi.fn(),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    login: loginMock,
    devLogin: devLoginMock,
    verify2FA: verify2FAMock,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("next/image", () => ({
  default: ({ alt, priority: _priority, ...props }: React.ImgHTMLAttributes<HTMLImageElement> & { priority?: boolean }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={alt} {...props} />
  ),
}));

import LoginPage from "@/app/(auth)/login/page";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ dev_bypass: false }),
    }) as unknown as typeof fetch;
  });

  it("muestra el mensaje de cuenta suspendida cuando el backend responde 403 (R-ACC-10)", async () => {
    loginMock.mockRejectedValueOnce({ response: { status: 403 } });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "suspendido@vesotel.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secreta123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(
        screen.getByText("Tu cuenta ha sido suspendida. Contacta con soporte")
      ).toBeInTheDocument();
    });
  });

  it("muestra el mensaje generico cuando el backend responde 401", async () => {
    loginMock.mockRejectedValueOnce({ response: { status: 401 } });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "mal@vesotel.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "incorrecta" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(
        screen.getByText("Credenciales inválidas, código incorrecto o error de conexión")
      ).toBeInTheDocument();
    });
  });
});
