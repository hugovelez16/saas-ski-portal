"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { Toaster as SonnerToaster } from "sonner";
import posthog from "posthog-js";
import { PostHogProvider } from "posthog-js/react";

import { Toaster } from "@/components/ui/toaster";

type CaptureResult = {
  uuid: string;
  event: string;
  properties: Record<string, unknown>;
};

export function stripUrl(value: unknown): unknown {
  if (typeof value !== "string") {
    return value;
  }

  try {
    const url = new URL(value);
    return url.origin + url.pathname;
  } catch {
    return value;
  }
}

export function sanitizeEvent(event: CaptureResult | null): CaptureResult | null {
  if (!event || !event.properties) {
    return event;
  }

  const urlFields = [
    "$current_url",
    "$referrer",
    "$initial_current_url",
    "$initial_referrer",
  ];

  const sanitizedProperties = { ...event.properties };

  urlFields.forEach((field) => {
    if (field in sanitizedProperties) {
      sanitizedProperties[field] = stripUrl(sanitizedProperties[field]);
    }
  });

  if (
    sanitizedProperties.$set &&
    typeof sanitizedProperties.$set === "object"
  ) {
    const setObj = sanitizedProperties.$set as Record<string, unknown>;
    const sanitizedSet = { ...setObj };
    Object.keys(sanitizedSet).forEach((key) => {
      sanitizedSet[key] = stripUrl(sanitizedSet[key]);
    });
    sanitizedProperties.$set = sanitizedSet;
  }

  if (
    sanitizedProperties.$set_once &&
    typeof sanitizedProperties.$set_once === "object"
  ) {
    const setOnceObj = sanitizedProperties.$set_once as Record<
      string,
      unknown
    >;
    const sanitizedSetOnce = { ...setOnceObj };
    Object.keys(sanitizedSetOnce).forEach((key) => {
      sanitizedSetOnce[key] = stripUrl(sanitizedSetOnce[key]);
    });
    sanitizedProperties.$set_once = sanitizedSetOnce;
  }

  return {
    ...event,
    properties: sanitizedProperties,
  };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // With SSR, we usually want to set some default staleTime
        // to avoid refetching immediately on the client
        staleTime: 60 * 1000,
      },
    },
  })
}

let browserQueryClient: QueryClient | undefined = undefined

function getQueryClient() {
  if (typeof window === 'undefined') {
    // Server: always make a new query client
    return makeQueryClient()
  } else {
    // Browser: make a new query client if we don't already have one
    // This is very important, so we don't re-make a new client if React
    // suspends during initial render. This may not be needed if we
    // have a suspense boundary ABOVE the component but better safe than sorry.
    if (!browserQueryClient) browserQueryClient = makeQueryClient()
    return browserQueryClient
  }
}

function PostHogInit({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const apiKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;

    if (!apiKey || posthog.__loaded) {
      return;
    }

    const isResetPasswordPage =
      typeof window !== "undefined" &&
      window.location.pathname.startsWith("/reset-password");

    posthog.init(apiKey, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com",
      person_profiles: "identified_only",
      capture_pageview: "history_change",
      persistence: "memory",
      session_recording: {
        maskAllInputs: true,
        maskTextSelector: "*",
      },
      disable_session_recording: isResetPasswordPage,
      before_send: (event) => sanitizeEvent(event),
    });
  }, []);

  const apiKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;

  if (!apiKey) {
    return <>{children}</>;
  }

  return (
    <PostHogProvider client={posthog}>
      {children}
    </PostHogProvider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  // NOTE: Avoid useState for QueryClient in Next.js App Router if you encounter SSR issues.
  // Instead, use the singleton pattern or useMemo with careful checks.
  const queryClient = getQueryClient()

  return (
    <PostHogInit>
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster />
        <SonnerToaster />
      </QueryClientProvider>
    </PostHogInit>
  );
}
