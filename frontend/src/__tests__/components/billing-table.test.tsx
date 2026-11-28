import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BillingTable } from "@/components/manager/billing-table";
import { DynamicBillingRow } from "@/lib/types";

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

describe("BillingTable", () => {
    it("muestra la etiqueta Inactivo para miembros inactivos con turnos en el periodo", () => {
        const rows: DynamicBillingRow[] = [
            {
                userId: "u-1",
                userName: "Ana Activa",
                userEmail: "ana@test.com",
                isActive: true,
                byType: {},
                totalNet: 100,
                totalGross: 120,
                logsCount: 1,
            },
            {
                userId: "u-2",
                userName: "Luis Inactivo",
                userEmail: "luis@test.com",
                isActive: false,
                byType: {},
                totalNet: 80,
                totalGross: 100,
                logsCount: 1,
            },
        ];

        render(<BillingTable data={rows} worklogDefs={{}} />);

        expect(screen.getByText("Ana Activa")).toBeInTheDocument();
        expect(screen.getByText("Luis Inactivo")).toBeInTheDocument();
        expect(screen.getAllByText("Inactivo")).toHaveLength(1);
    });
});
