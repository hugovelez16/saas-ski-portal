import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

// La UI muestra la version desplegada leida de NEXT_PUBLIC_APP_VERSION.
// config.ts evalua la variable al importarse, por eso se recarga el modulo tras stubEnv.
async function renderAppVersion(props: { className?: string } = {}) {
    vi.resetModules();
    const { AppVersion } = await import("@/components/app-version");
    return render(<AppVersion {...props} />);
}

afterEach(() => {
    vi.unstubAllEnvs();
});

describe("AppVersion", () => {
    it("muestra la version con prefijo v cuando NEXT_PUBLIC_APP_VERSION esta definida", async () => {
        vi.stubEnv("NEXT_PUBLIC_APP_VERSION", "0.30.0-dev.2");

        await renderAppVersion();

        expect(screen.getByTestId("app-version")).toHaveTextContent(/^v0\.30\.0-dev\.2$/);
    });

    it("muestra 'dev' sin prefijo cuando la variable no esta definida", async () => {
        delete process.env.NEXT_PUBLIC_APP_VERSION;

        await renderAppVersion();

        expect(screen.getByTestId("app-version").textContent).toBe("dev");
    });

    it("muestra 'dev' sin prefijo cuando la variable vale 'dev'", async () => {
        vi.stubEnv("NEXT_PUBLIC_APP_VERSION", "dev");

        await renderAppVersion();

        expect(screen.getByTestId("app-version").textContent).toBe("dev");
    });

    it("acepta clases adicionales para adaptarse al contenedor", async () => {
        vi.stubEnv("NEXT_PUBLIC_APP_VERSION", "0.30.0-dev.2");

        await renderAppVersion({ className: "text-slate-300" });

        expect(screen.getByTestId("app-version")).toHaveClass("text-slate-300");
    });
});
