import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { Providers, sanitizeEvent, stripUrl } from "@/components/providers";
import posthog from "posthog-js";

vi.mock("posthog-js", () => ({
  default: {
    init: vi.fn(),
    identify: vi.fn(),
    reset: vi.fn(),
    __loaded: false,
  },
}));

vi.mock("posthog-js/react", () => ({
  PostHogProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="posthog-provider">{children}</div>
  ),
}));

vi.mock("@tanstack/react-query", () => {
  class MockQueryClient {
    defaultOptions = {};
  }
  return {
    QueryClient: MockQueryClient,
    QueryClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

vi.mock("@/components/ui/toaster", () => ({
  Toaster: () => null,
}));

vi.mock("sonner", () => ({
  Toaster: () => null,
}));

describe("stripUrl utility", () => {
  it("should remove query string and hash from URLs", () => {
    const url = "https://x.com/reset-password?token=abc#section";
    expect(stripUrl(url)).toBe("https://x.com/reset-password");
  });

  it("should return URL with only origin and pathname", () => {
    const url = "https://example.com/path/to/page?foo=bar&baz=qux#anchor";
    expect(stripUrl(url)).toBe("https://example.com/path/to/page");
  });

  it("should return non-string values unchanged", () => {
    expect(stripUrl(null)).toBe(null);
    expect(stripUrl(undefined)).toBe(undefined);
    expect(stripUrl(123)).toBe(123);
    expect(stripUrl(true)).toBe(true);
    expect(stripUrl({ role: "worker" })).toEqual({ role: "worker" });
  });

  it("should return non-URL strings unchanged", () => {
    expect(stripUrl("worker")).toBe("worker");
    expect(stripUrl("admin")).toBe("admin");
  });
});

describe("sanitizeEvent utility", () => {
  it("should sanitize URL fields by removing query string and hash", () => {
    const event = {
      uuid: "evt1",
      event: "pageview",
      properties: {
        $current_url: "https://app.com/dashboard?param=value#top",
        $referrer: "https://app.com/login?from=reset#hash",
        $initial_current_url: "https://app.com/page?id=123#section",
        $initial_referrer: "https://app.com/home?state=active#nav",
      },
    };

    const result = sanitizeEvent(event);

    expect(result?.properties.$current_url).toBe("https://app.com/dashboard");
    expect(result?.properties.$referrer).toBe("https://app.com/login");
    expect(result?.properties.$initial_current_url).toBe("https://app.com/page");
    expect(result?.properties.$initial_referrer).toBe("https://app.com/home");
  });

  it("should sanitize URLs within $set object", () => {
    const event = {
      uuid: "evt1",
      event: "identify",
      properties: {
        $set: {
          custom_url: "https://example.com/path?query=1#hash",
          name: "John",
        } as Record<string, unknown>,
      },
    };

    const result = sanitizeEvent(event);

    expect((result?.properties.$set as any)?.custom_url).toBe("https://example.com/path");
    expect((result?.properties.$set as any)?.name).toBe("John");
  });

  it("should sanitize URLs within $set_once object", () => {
    const event = {
      uuid: "evt1",
      event: "identify",
      properties: {
        $set_once: {
          first_url: "https://app.com/initial?token=abc#section",
          email: "user@example.com",
        } as Record<string, unknown>,
      },
    };

    const result = sanitizeEvent(event);

    expect((result?.properties.$set_once as any)?.first_url).toBe("https://app.com/initial");
    expect((result?.properties.$set_once as any)?.email).toBe("user@example.com");
  });

  it("should leave non-URL values unchanged in all fields", () => {
    const event = {
      uuid: "evt1",
      event: "custom",
      properties: {
        $current_url: "https://app.com/page?x=1#y",
        role: "worker",
        count: 42,
        active: true,
        tags: null,
        $set: {
          name: "Alice",
          role: "admin",
        } as Record<string, unknown>,
        $set_once: {
          timestamp: 1234567890,
          status: undefined,
        } as Record<string, unknown>,
      },
    };

    const result = sanitizeEvent(event);

    expect(result?.properties.role).toBe("worker");
    expect(result?.properties.count).toBe(42);
    expect(result?.properties.active).toBe(true);
    expect(result?.properties.tags).toBe(null);
    expect((result?.properties.$set as any)?.name).toBe("Alice");
    expect((result?.properties.$set as any)?.role).toBe("admin");
    expect((result?.properties.$set_once as any)?.timestamp).toBe(1234567890);
    expect((result?.properties.$set_once as any)?.status).toBeUndefined();
  });

  it("should not mutate the original event object", () => {
    const event = {
      uuid: "evt1",
      event: "pageview",
      properties: {
        $current_url: "https://app.com/page?param=value#hash",
      },
    };

    const originalUrl = event.properties.$current_url;
    sanitizeEvent(event);

    expect(event.properties.$current_url).toBe(originalUrl);
  });

  it("should handle events without URL fields gracefully", () => {
    const event = {
      uuid: "evt1",
      event: "custom_event",
      properties: {
        data: "value",
      },
    };

    expect(() => sanitizeEvent(event)).not.toThrow();
    expect(sanitizeEvent(event)).toEqual(event);
  });

  it("should return null event unchanged", () => {
    expect(sanitizeEvent(null)).toBe(null);
  });

  it("should handle event without properties gracefully", () => {
    const event = {
      uuid: "evt1",
      event: "test",
      properties: {} as Record<string, unknown>,
    };

    const result = sanitizeEvent(event);
    expect(result?.properties).toEqual({});
  });

  it("should handle empty properties object", () => {
    const event = {
      uuid: "evt1",
      event: "test",
      properties: {},
    };

    const result = sanitizeEvent(event);
    expect(result?.properties).toEqual({});
  });
});

describe("PostHogInit component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(posthog, "__loaded", {
      value: false,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("should not call init and render children when NEXT_PUBLIC_POSTHOG_KEY is not set", () => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "");

    render(
      <Providers>
        <div data-testid="test-child">Test Content</div>
      </Providers>
    );

    expect(posthog.init).not.toHaveBeenCalled();
  });

  it("should call init once with correct config when NEXT_PUBLIC_POSTHOG_KEY is set", () => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_HOST", "https://eu.i.posthog.com");

    render(
      <Providers>
        <div data-testid="test-child">Test Content</div>
      </Providers>
    );

    expect(posthog.init).toHaveBeenCalledOnce();
    expect(posthog.init).toHaveBeenCalledWith(
      "phc_test",
      expect.objectContaining({
        person_profiles: "identified_only",
        capture_pageview: "history_change",
        persistence: "memory",
        disable_session_recording: expect.any(Boolean),
        session_recording: expect.objectContaining({
          maskAllInputs: true,
          maskTextSelector: "*",
        }),
        before_send: expect.any(Function),
      })
    );
  });

  it("should not reinitialize when posthog.__loaded is already true", () => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");
    Object.defineProperty(posthog, "__loaded", {
      value: true,
      writable: true,
      configurable: true,
    });

    render(
      <Providers>
        <div data-testid="test-child">Test Content</div>
      </Providers>
    );

    expect(posthog.init).not.toHaveBeenCalled();
  });

  it("should use custom NEXT_PUBLIC_POSTHOG_HOST if provided", () => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_HOST", "https://custom.host.com");

    render(
      <Providers>
        <div>Test</div>
      </Providers>
    );

    expect(posthog.init).toHaveBeenCalledWith(
      "phc_test",
      expect.objectContaining({
        api_host: "https://custom.host.com",
      })
    );
  });

  it("should disable session recording on reset-password page", () => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

    const originalLocation = window.location;
    delete (window as any).location;
    (window as any).location = { ...originalLocation, pathname: "/reset-password" };

    try {
      render(
        <Providers>
          <div>Test</div>
        </Providers>
      );

      expect(posthog.init).toHaveBeenCalledWith(
        "phc_test",
        expect.objectContaining({
          disable_session_recording: true,
        })
      );
    } finally {
      (window as any).location = originalLocation;
    }
  });

  it("should enable session recording on non-reset-password page", () => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

    const originalLocation = window.location;
    delete (window as any).location;
    (window as any).location = { ...originalLocation, pathname: "/dashboard" };

    try {
      render(
        <Providers>
          <div>Test</div>
        </Providers>
      );

      expect(posthog.init).toHaveBeenCalledWith(
        "phc_test",
        expect.objectContaining({
          disable_session_recording: false,
        })
      );
    } finally {
      (window as any).location = originalLocation;
    }
  });

  it("should render PostHogProvider when NEXT_PUBLIC_POSTHOG_KEY is set", () => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");

    const { getByTestId } = render(
      <Providers>
        <div data-testid="test-child">Test Content</div>
      </Providers>
    );

    expect(getByTestId("posthog-provider")).toBeTruthy();
  });

  it("should not render PostHogProvider when NEXT_PUBLIC_POSTHOG_KEY is not set", () => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "");

    const { queryByTestId } = render(
      <Providers>
        <div data-testid="test-child">Test Content</div>
      </Providers>
    );

    expect(queryByTestId("posthog-provider")).toBeNull();
  });
});
