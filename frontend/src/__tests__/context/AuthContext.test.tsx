import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { UserProfile } from "@/lib/types";
import posthog from "posthog-js";

// Mock posthog-js
vi.mock("posthog-js", () => ({
  default: {
    init: vi.fn(),
    identify: vi.fn(),
    reset: vi.fn(),
    __loaded: true,
  },
}));

// Mock posthog-js/react
vi.mock("posthog-js/react", () => ({
  PostHogProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock API
vi.mock("@/lib/api", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
    },
    setAuthToken: vi.fn(),
  };
});

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
  })),
}));

// Import after mocks are set up
import { AuthProvider, useAuth } from "@/context/AuthContext";
import api from "@/lib/api";

// Test component that uses useAuth
const TestComponent = ({ onAuthReady }: { onAuthReady?: (auth: any) => void }) => {
  const auth = useAuth();

  if (onAuthReady && !auth.loading) {
    onAuthReady(auth);
  }

  return (
    <div>
      <div data-testid="user-email">{auth.user?.email || "no-user"}</div>
      <div data-testid="loading">{auth.loading ? "loading" : "ready"}</div>
    </div>
  );
};

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset __loaded to true for all tests
    Object.defineProperty(posthog, "__loaded", {
      value: true,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe("identifyUser integration", () => {
    it("should call posthog.identify with correct user data after fetchUser", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

      const mockUser: UserProfile = {
        id: "u1",
        email: "a@b.c",
        firstName: "A",
        lastName: "B",
        role: "worker",
        activeCompanyId: "c1",
        isActive: true,
        createdAt: "2026-01-01T00:00:00",
      };

      vi.mocked(api.get).mockResolvedValue({ data: mockUser });

      const authCapture: any = { user: null };

      render(
        <AuthProvider>
          <TestComponent
            onAuthReady={(auth) => {
              authCapture.user = auth.user;
            }}
          />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(authCapture.user).not.toBeNull();
      });

      expect(posthog.identify).toHaveBeenCalledWith("u1", {
        role: "worker",
        company_id: "c1",
      });
    });

    it("should not include email, firstName, or lastName in identify payload", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

      const mockUser: UserProfile = {
        id: "u1",
        email: "a@b.c",
        firstName: "A",
        lastName: "B",
        role: "worker",
        activeCompanyId: "c1",
        isActive: true,
        createdAt: "2026-01-01T00:00:00",
      };

      vi.mocked(api.get).mockResolvedValue({ data: mockUser });

      const authCapture: any = { user: null };

      render(
        <AuthProvider>
          <TestComponent
            onAuthReady={(auth) => {
              authCapture.user = auth.user;
            }}
          />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(authCapture.user).not.toBeNull();
      });

      const callArgs = (posthog.identify as any).mock.calls[0];
      expect(callArgs[1]).toEqual({
        role: "worker",
        company_id: "c1",
      });
      expect(callArgs[1]).not.toHaveProperty("email");
      expect(callArgs[1]).not.toHaveProperty("firstName");
      expect(callArgs[1]).not.toHaveProperty("lastName");
    });

    it("should set company_id to null when activeCompanyId is not set", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

      const mockUser: UserProfile = {
        id: "u1",
        email: "a@b.c",
        firstName: "A",
        lastName: "B",
        role: "admin",
        isActive: true,
        createdAt: "2026-01-01T00:00:00",
      };

      vi.mocked(api.get).mockResolvedValue({ data: mockUser });

      const authCapture: any = { user: null };

      render(
        <AuthProvider>
          <TestComponent
            onAuthReady={(auth) => {
              authCapture.user = auth.user;
            }}
          />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(authCapture.user).not.toBeNull();
      });

      expect(posthog.identify).toHaveBeenCalledWith("u1", {
        role: "admin",
        company_id: null,
      });
    });
  });

  describe("logout integration", () => {
    it("should call posthog.reset on logout", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

      const mockUser: UserProfile = {
        id: "u1",
        email: "a@b.c",
        firstName: "A",
        lastName: "B",
        role: "worker",
        activeCompanyId: "c1",
        isActive: true,
        createdAt: "2026-01-01T00:00:00",
      };

      vi.mocked(api.get).mockResolvedValue({ data: mockUser });
      vi.mocked(api.post).mockResolvedValue({});

      const logoutFnRef = { current: null as any };

      const LogoutTestComponent = () => {
        const auth = useAuth();
        logoutFnRef.current = auth.logout;
        return <div data-testid="logout-ready">Ready</div>;
      };

      render(
        <AuthProvider>
          <LogoutTestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("logout-ready")).toBeTruthy();
      });

      vi.clearAllMocks();

      await logoutFnRef.current();

      expect(posthog.reset).toHaveBeenCalledOnce();
    });
  });

  describe("without analytics", () => {
    it("should not call identify or reset when NEXT_PUBLIC_POSTHOG_KEY is not set", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "");

      const mockUser: UserProfile = {
        id: "u1",
        email: "a@b.c",
        firstName: "A",
        lastName: "B",
        role: "worker",
        activeCompanyId: "c1",
        isActive: true,
        createdAt: "2026-01-01T00:00:00",
      };

      vi.mocked(api.get).mockResolvedValue({ data: mockUser });
      vi.mocked(api.post).mockResolvedValue({});

      const authCapture: any = { user: null };
      const logoutFnRef = { current: null as any };

      const TestComponentWithLogout = () => {
        const auth = useAuth();
        logoutFnRef.current = auth.logout;
        if (!auth.loading) {
          authCapture.user = auth.user;
        }
        return <div data-testid="ready">Ready</div>;
      };

      render(
        <AuthProvider>
          <TestComponentWithLogout />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(authCapture.user).not.toBeNull();
      });

      expect(posthog.identify).not.toHaveBeenCalled();

      vi.clearAllMocks();

      await logoutFnRef.current();

      expect(posthog.reset).not.toHaveBeenCalled();
    });

    it("should not call identify or reset when posthog.__loaded is false", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");
      Object.defineProperty(posthog, "__loaded", {
        value: false,
        writable: true,
        configurable: true,
      });

      const mockUser: UserProfile = {
        id: "u1",
        email: "a@b.c",
        firstName: "A",
        lastName: "B",
        role: "worker",
        activeCompanyId: "c1",
        isActive: true,
        createdAt: "2026-01-01T00:00:00",
      };

      vi.mocked(api.get).mockResolvedValue({ data: mockUser });
      vi.mocked(api.post).mockResolvedValue({});

      const authCapture: any = { user: null };
      const logoutFnRef = { current: null as any };

      const TestComponentWithLogout = () => {
        const auth = useAuth();
        logoutFnRef.current = auth.logout;
        if (!auth.loading) {
          authCapture.user = auth.user;
        }
        return <div data-testid="ready">Ready</div>;
      };

      render(
        <AuthProvider>
          <TestComponentWithLogout />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(authCapture.user).not.toBeNull();
      });

      expect(posthog.identify).not.toHaveBeenCalled();

      vi.clearAllMocks();

      await logoutFnRef.current();

      expect(posthog.reset).not.toHaveBeenCalled();
    });
  });

  describe("login method", () => {
    it("should call identifyUser with user data after successful login", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

      const mockUser: UserProfile = {
        id: "u1",
        email: "a@b.c",
        firstName: "A",
        lastName: "B",
        role: "worker",
        activeCompanyId: "c1",
        isActive: true,
        createdAt: "2026-01-01T00:00:00",
      };

      vi.mocked(api.get).mockResolvedValue({ data: mockUser });

      const postMock = vi.mocked(api.post);
      postMock.mockImplementation((url: string) => {
        if (url === "/token") {
          return Promise.resolve({ data: { accessToken: "token123" } });
        }
        return Promise.resolve({});
      });

      const loginFnRef = { current: null as any };

      const TestComponentWithLogin = () => {
        const auth = useAuth();
        loginFnRef.current = auth.login;
        return <div data-testid="ready">Ready</div>;
      };

      render(
        <AuthProvider>
          <TestComponentWithLogin />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("ready")).toBeTruthy();
      });

      vi.clearAllMocks();
      postMock.mockImplementation((url: string) => {
        if (url === "/token") {
          return Promise.resolve({ data: { accessToken: "token123" } });
        }
        return Promise.resolve({});
      });
      vi.mocked(api.get).mockResolvedValue({ data: mockUser });

      await act(async () => {
        await loginFnRef.current("test@example.com", "password123");
      });

      expect(postMock).toHaveBeenCalledWith(
        "/token",
        expect.any(URLSearchParams),
        expect.any(Object)
      );
      expect(posthog.identify).toHaveBeenCalledWith("u1", {
        role: "worker",
        company_id: "c1",
      });
    });

    it("should return requires2FA true when 2FA is required", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

      const error401 = { response: { status: 401 } };
      vi.mocked(api.get).mockRejectedValueOnce(error401);
      vi.mocked(api.post).mockResolvedValue({ data: { requires_2fa: true } });

      const loginFnRef = { current: null as any };
      const resultRef = { current: { requires2FA: false } };

      const TestComponentWithLogin = () => {
        const auth = useAuth();
        loginFnRef.current = auth.login;
        return <div data-testid="ready">Ready</div>;
      };

      render(
        <AuthProvider>
          <TestComponentWithLogin />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId("ready")).toBeTruthy();
      });

      vi.clearAllMocks();
      vi.mocked(api.post).mockResolvedValue({ data: { requires_2fa: true } });

      await act(async () => {
        resultRef.current = await loginFnRef.current("test@example.com", "password123");
      });

      expect(resultRef.current.requires2FA).toBe(true);
      expect(posthog.identify).not.toHaveBeenCalled();
    });
  });

  describe("401 error handling in fetchUser", () => {
    it("should call logout and resetAnalytics when 401 occurs on non-public page", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

      const originalLocation = window.location;
      delete (window as any).location;
      (window as any).location = { ...originalLocation, pathname: "/dashboard" };

      const error401 = {
        response: { status: 401 },
      };

      vi.mocked(api.get).mockRejectedValueOnce(error401);
      vi.mocked(api.post).mockResolvedValue({});

      try {
        render(
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        );

        await waitFor(() => {
          expect(screen.getByTestId("loading")).toHaveTextContent("ready");
        });

        expect(posthog.reset).toHaveBeenCalled();
      } finally {
        (window as any).location = originalLocation;
      }
    });

    it("should not call logout when 401 occurs on public page", async () => {
      vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

      const originalLocation = window.location;
      delete (window as any).location;
      (window as any).location = { ...originalLocation, pathname: "/login" };

      const error401 = {
        response: { status: 401 },
      };

      vi.mocked(api.get).mockRejectedValueOnce(error401);

      try {
        render(
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        );

        await waitFor(() => {
          expect(screen.getByTestId("loading")).toHaveTextContent("ready");
        });

        expect(posthog.reset).not.toHaveBeenCalled();
      } finally {
        (window as any).location = originalLocation;
      }
    });
  });

  describe("company scope (lastCompanyId)", () => {
    const LAST_KEY = "lastCompanyId";

    const workerUser = (over: Partial<UserProfile> = {}): UserProfile => ({
      id: "u1",
      email: "a@b.c",
      firstName: "A",
      lastName: "B",
      role: "user",
      isActive: true,
      isManager: false,
      activeCompanyId: "c1",
      activeRole: "worker",
      createdAt: "2026-01-01T00:00:00",
      ...over,
    });

    const adminUser = (over: Partial<UserProfile> = {}): UserProfile =>
      workerUser({ role: "admin", isPlatformAdmin: true, activeRole: null, ...over });

    // Renderiza el provider con un usuario inicial (o sin sesion si es null)
    const renderAuth = async (initialUser: UserProfile | null) => {
      const ref: { current: any } = { current: null };
      if (initialUser) {
        vi.mocked(api.get).mockResolvedValueOnce({ data: initialUser });
      } else {
        vi.mocked(api.get).mockRejectedValueOnce({ response: { status: 401 } });
      }
      const Probe = () => {
        const auth = useAuth();
        ref.current = auth;
        return <div data-testid="probe">{auth.loading ? "loading" : "ready"}</div>;
      };
      render(
        <AuthProvider>
          <Probe />
        </AuthProvider>
      );
      await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("ready"));
      vi.clearAllMocks();
      return ref;
    };

    const loginWith = async (
      ref: { current: any },
      tokenResponse: Record<string, unknown> = { accessToken: "t1" }
    ) => {
      vi.mocked(api.post).mockImplementation((url: string) => {
        if (url === "/token") return Promise.resolve({ data: tokenResponse });
        if (url === "/verify-2fa") return Promise.resolve({ data: { accessToken: "t2" } });
        return Promise.resolve({});
      });
      vi.mocked(api.get).mockResolvedValue({ data: workerUser() });
      let result: { requires2FA: boolean } | undefined;
      await act(async () => {
        result = await ref.current.login("a@b.c", "password123");
      });
      return result;
    };

    const bodyOf = (url: string) => {
      const call = vi.mocked(api.post).mock.calls.find((c) => c[0] === url);
      return call?.[1] as any;
    };

    // Navegacion simulada: devuelve el href asignado tras switchScope
    const switchAndGetHref = async (
      ref: { current: any },
      companyId: string | null,
      returnedUser: UserProfile,
      viewAs?: "manager" | "worker"
    ) => {
      vi.mocked(api.post).mockResolvedValue({});
      vi.mocked(api.get).mockResolvedValue({ data: returnedUser });
      const originalLocation = window.location;
      delete (window as any).location;
      (window as any).location = { ...originalLocation, href: "" };
      try {
        await act(async () => {
          await ref.current.switchScope(companyId, viewAs);
        });
        return (window as any).location.href as string;
      } finally {
        (window as any).location = originalLocation;
      }
    };

    beforeEach(() => {
      localStorage.clear();
    });

    it("login envia company_id guardado en el formulario de /token", async () => {
      localStorage.setItem(LAST_KEY, "c9");
      const ref = await renderAuth(null);

      await loginWith(ref);

      const form = vi.mocked(api.post).mock.calls.find((c) => c[0] === "/token")![1] as URLSearchParams;
      expect(form.get("company_id")).toBe("c9");
    });

    it("login sin valor guardado no envia company_id", async () => {
      const ref = await renderAuth(null);

      await loginWith(ref);

      const form = vi.mocked(api.post).mock.calls.find((c) => c[0] === "/token")![1] as URLSearchParams;
      expect(form.has("company_id")).toBe(false);
    });

    it("un localStorage que lanza no rompe el login", async () => {
      const ref = await renderAuth(null);
      const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
        throw new Error("SecurityError");
      });
      try {
        const result = await loginWith(ref);
        expect(result?.requires2FA).toBe(false);
      } finally {
        spy.mockRestore();
      }
    });

    it("tras requires_2fa, el paso 2FA envia companyId guardado", async () => {
      localStorage.setItem(LAST_KEY, "c9");
      const ref = await renderAuth(null);

      const result = await loginWith(ref, { requires_2fa: true });
      expect(result?.requires2FA).toBe(true);

      await act(async () => {
        await ref.current.verify2FA("123456", localStorage.getItem(LAST_KEY) ?? undefined);
      });

      expect(bodyOf("/verify-2fa")).toEqual({ code: "123456", companyId: "c9" });
    });

    it("tras requires_2fa, sin valor guardado el paso 2FA no envia companyId", async () => {
      const ref = await renderAuth(null);

      const result = await loginWith(ref, { requires_2fa: true });
      expect(result?.requires2FA).toBe(true);

      await act(async () => {
        await ref.current.verify2FA("123456", localStorage.getItem(LAST_KEY) ?? undefined);
      });

      expect(bodyOf("/verify-2fa")).toEqual({ code: "123456" });
      expect(bodyOf("/verify-2fa")).not.toHaveProperty("companyId");
    });

    it("fetchUser guarda activeCompanyId de un worker", async () => {
      await renderAuth(workerUser({ activeCompanyId: "c5" }));

      expect(localStorage.getItem(LAST_KEY)).toBe("c5");
    });

    it("fetchUser no guarda empresa para un PA", async () => {
      await renderAuth(adminUser({ activeCompanyId: "c5" }));

      expect(localStorage.getItem(LAST_KEY)).toBeNull();
    });

    it("switchScope(id) envia companyId sin companyRole", async () => {
      const ref = await renderAuth(workerUser());

      await switchAndGetHref(ref, "c2", workerUser({ activeCompanyId: "c2" }));

      const body = bodyOf("/auth/switch-scope");
      expect(body).toMatchObject({ companyId: "c2" });
      expect(body).not.toHaveProperty("companyRole");
      expect(body.viewAs).toBeUndefined();
    });

    it("switchScope(id, 'worker') envia viewAs", async () => {
      const ref = await renderAuth(adminUser());

      await switchAndGetHref(ref, "c2", adminUser({ activeCompanyId: "c2" }), "worker");

      expect(api.post).toHaveBeenCalledWith("/auth/switch-scope", { companyId: "c2", viewAs: "worker" });
    });

    it("switchScope guarda la empresa activa en la clave unica", async () => {
      const ref = await renderAuth(workerUser({ activeCompanyId: null }));

      await switchAndGetHref(ref, "c2", workerUser({ activeCompanyId: "c2" }));

      expect(localStorage.getItem(LAST_KEY)).toBe("c2");
    });

    it("switchScope de un PA no guarda empresa", async () => {
      const ref = await renderAuth(adminUser({ activeCompanyId: null }));

      await switchAndGetHref(ref, "c2", adminUser({ activeCompanyId: "c2" }));

      expect(localStorage.getItem(LAST_KEY)).toBeNull();
    });

    it("un localStorage que lanza en setItem no rompe switchScope", async () => {
      const ref = await renderAuth(workerUser({ activeCompanyId: null }));
      const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
        throw new Error("QuotaExceededError");
      });
      try {
        const href = await switchAndGetHref(ref, "c2", workerUser({ activeCompanyId: "c2" }));
        expect(href).toBe("/dashboard?companyId=c2");
      } finally {
        spy.mockRestore();
      }
    });

    it("redirige a /dashboard para un worker", async () => {
      const ref = await renderAuth(workerUser());

      const href = await switchAndGetHref(ref, "c2", workerUser({ activeCompanyId: "c2", activeRole: "worker" }));

      expect(href).toBe("/dashboard?companyId=c2");
    });

    it("redirige a /manager/dashboard cuando el usuario devuelto es manager", async () => {
      const ref = await renderAuth(workerUser());

      const href = await switchAndGetHref(ref, "c2", workerUser({ activeCompanyId: "c2", activeRole: "manager" }));

      expect(href).toBe("/manager/dashboard?companyId=c2");
    });

    it("un PA sin viewAs va a /admin/companies/{id}", async () => {
      const ref = await renderAuth(adminUser());

      const href = await switchAndGetHref(ref, "c2", adminUser({ activeCompanyId: "c2", activeRole: null }));

      expect(href).toBe("/admin/companies/c2");
    });

    it("un PA con viewAs worker va a /dashboard", async () => {
      const ref = await renderAuth(adminUser());

      const href = await switchAndGetHref(
        ref,
        "c2",
        adminUser({ activeCompanyId: "c2", activeRole: "worker", viewAs: "worker", isReadOnlyView: true }),
        "worker"
      );

      expect(href).toBe("/dashboard?companyId=c2");
    });

    it("switchScope(null) vuelve a /admin/companies", async () => {
      const ref = await renderAuth(adminUser());

      const href = await switchAndGetHref(ref, null, adminUser({ activeCompanyId: null, activeRole: null }));

      expect(api.post).toHaveBeenCalledWith("/auth/switch-scope", { companyId: null, viewAs: undefined });
      expect(href).toBe("/admin/companies");
    });
  });
});
