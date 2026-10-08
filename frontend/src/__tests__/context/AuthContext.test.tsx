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
});
