import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { SessionRedirect } from "@/components/landing/session-redirect";
import { homePathFor, useAuth } from "@/context/AuthContext";
import type { UserProfile } from "@/lib/types";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
    useRouter: () => ({ replace }),
}));

vi.mock("@/context/AuthContext", async () => {
    const actual = await vi.importActual<typeof import("@/context/AuthContext")>("@/context/AuthContext");
    return { ...actual, useAuth: vi.fn() };
});

const baseUser = {
    id: "u1",
    email: "a@b.c",
    firstName: "A",
    lastName: "B",
    role: "user",
    isActive: true,
    isManager: false,
    createdAt: "2026-01-01T00:00:00",
} as UserProfile;

const withAuth = (user: UserProfile | null, loading = false) =>
    vi.mocked(useAuth).mockReturnValue({ user, loading } as ReturnType<typeof useAuth>);

describe("homePathFor", () => {
    it("lleva al administrador a empresas", () => {
        expect(homePathFor({ ...baseUser, role: "admin" })).toBe("/admin/companies");
        expect(homePathFor({ ...baseUser, isPlatformAdmin: true })).toBe("/admin/companies");
    });

    it("lleva al responsable al parte diario", () => {
        expect(homePathFor({ ...baseUser, isManager: true })).toBe("/manager/daily-reports");
    });

    it("lleva al resto al dashboard", () => {
        expect(homePathFor(baseUser)).toBe("/dashboard");
        expect(homePathFor(null)).toBe("/dashboard");
    });
});

describe("SessionRedirect", () => {
    beforeEach(() => {
        replace.mockClear();
    });

    it("no redirige ni tapa la landing sin sesion", () => {
        withAuth(null);
        const { container } = render(<SessionRedirect />);
        expect(replace).not.toHaveBeenCalled();
        expect(container).toBeEmptyDOMElement();
    });

    it("no redirige mientras se comprueba la sesion", () => {
        withAuth(baseUser, true);
        const { container } = render(<SessionRedirect />);
        expect(replace).not.toHaveBeenCalled();
        expect(container).toBeEmptyDOMElement();
    });

    it("con sesion redirige al inicio del rol y tapa la landing", () => {
        withAuth({ ...baseUser, isManager: true });
        const { container } = render(<SessionRedirect />);
        expect(replace).toHaveBeenCalledWith("/manager/daily-reports");
        expect(container.firstChild).not.toBeNull();
    });
});
