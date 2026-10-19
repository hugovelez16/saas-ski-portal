import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NotificationsSection } from "@/components/notifications-section";
import type { UserProfile } from "@/lib/types";

const baseUser: UserProfile = {
    id: "user-1",
    email: "ana@test.com",
    firstName: "Ana",
    lastName: "Monitora",
    role: "worker",
    isActive: true,
    activeCompanyId: "company-1",
    createdAt: "2026-01-01T00:00:00Z",
};

describe("NotificationsSection", () => {
    it("no muestra el aviso de empresa por defecto a un worker", () => {
        const { container } = render(<NotificationsSection user={baseUser} />);

        expect(container).toBeEmptyDOMElement();
        expect(screen.queryByText("Acción Requerida")).not.toBeInTheDocument();
        expect(screen.queryByText(/empresa por defecto/i)).not.toBeInTheDocument();
    });

    it("no muestra el aviso a un manager sin empresa por defecto", () => {
        const manager: UserProfile = { ...baseUser, role: "manager" };
        const { container } = render(<NotificationsSection user={manager} />);

        expect(container).toBeEmptyDOMElement();
        expect(screen.queryByText("Acción Requerida")).not.toBeInTheDocument();
    });
});
