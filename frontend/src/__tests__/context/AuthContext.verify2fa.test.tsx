import { useEffect } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";

vi.mock("posthog-js", () => ({
  default: { init: vi.fn(), identify: vi.fn(), reset: vi.fn(), __loaded: true },
}));

vi.mock("posthog-js/react", () => ({
  PostHogProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/api", () => ({
  default: { get: vi.fn(), post: vi.fn() },
  setAuthToken: vi.fn(),
}));

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { AuthProvider, useAuth } from "@/context/AuthContext";
import api, { setAuthToken } from "@/lib/api";

describe("AuthContext verify2FA", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderProvider = async () => {
    vi.mocked(api.get).mockRejectedValueOnce({ response: { status: 401 } });

    const authRef = { current: null as ReturnType<typeof useAuth> | null };
    const Probe = () => {
      const auth = useAuth();
      useEffect(() => {
        authRef.current = auth;
      });
      return <div data-testid="ready">ready</div>;
    };

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("ready")).toBeTruthy());
    vi.clearAllMocks();
    return authRef;
  };

  it("posts only the code to /verify-2fa and redirects a worker to the dashboard", async () => {
    const ref = await renderProvider();
    vi.mocked(api.post).mockResolvedValue({ data: { accessToken: "cookie", requires2fa: false } });
    vi.mocked(api.get).mockResolvedValue({ data: { id: "u1", role: "user", isManager: false } });

    await act(async () => {
      await ref.current!.verify2FA("123456");
    });

    expect(api.post).toHaveBeenCalledWith("/verify-2fa", { code: "123456" });
    expect(setAuthToken).toHaveBeenCalledWith("cookie");
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("propagates the error so the login page can show the right message", async () => {
    const ref = await renderProvider();
    vi.mocked(api.post).mockRejectedValue({ response: { status: 429 } });

    await expect(
      act(async () => {
        await ref.current!.verify2FA("000000");
      })
    ).rejects.toEqual({ response: { status: 429 } });
    expect(push).not.toHaveBeenCalled();
  });

  it("no longer exposes resend2FA", async () => {
    const ref = await renderProvider();
    expect("resend2FA" in ref.current!).toBe(false);
  });
});
