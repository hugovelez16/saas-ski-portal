import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { DashboardTeamTable } from "@/components/manager/dashboard/dashboard-team-table";
import { DashboardKpis } from "@/components/manager/dashboard/dashboard-kpis";
import { DashboardTodayCard } from "@/components/manager/dashboard/dashboard-today-card";
import { DashboardHeaderActions } from "@/components/manager/dashboard/dashboard-header-actions";

// Mock useModules hook
vi.mock("@/hooks/useModules", () => ({
    useModules: vi.fn((companyId: string) => ({
        hasModule: vi.fn((code: string) => {
            if (code === "worker_daily_report") return true;
            if (code === "billing") return true;
            if (code === "export_pdf") return false;
            return false;
        }),
        modules: [],
        isLoading: false
    }))
}));

describe("Manager Dashboard Components", () => {
    describe("DashboardTeamTable — Strict Order Governance", () => {
        const mockMembers = [
            {
                userId: "user-1",
                role: "manager",
                user: { id: "user-1", firstName: "Carlos", lastName: "Director", email: "carlos@test.com" }
            },
            {
                userId: "user-2",
                role: "worker",
                user: { id: "user-2", firstName: "Ana", lastName: "Monitora", email: "ana@test.com" }
            },
            {
                userId: "user-3",
                role: "worker",
                user: { id: "user-3", firstName: "Beatriz", lastName: "Profesora", email: "beatriz@test.com" }
            }
        ];

        const mockLogs = [
            {
                id: "l1",
                userId: "user-2", // Ana has more hours
                type: "particular",
                startDate: "2026-09-29T10:00:00",
                duration: 20,
                grossAmount: 400,
                netAmount: 350
            },
            {
                id: "l2",
                userId: "user-1", // Carlos has fewer hours
                type: "particular",
                startDate: "2026-09-29T10:00:00",
                duration: 5,
                grossAmount: 100,
                netAmount: 90
            }
        ];

        it("renders staff members in exact manager defined order (NOT a ranking by hours)", () => {
            // Manager configured order: user-3 first, then user-1, then user-2
            const orderedIds = ["user-3", "user-1", "user-2"];

            render(
                <DashboardTeamTable
                    companyId="comp-1"
                    members={mockMembers}
                    orderedMemberIds={orderedIds}
                    workLogs={mockLogs as any}
                />
            );

            const rows = screen.getAllByRole("row");
            // Header is row 0, row 1 is user-3 (Beatriz), row 2 is user-1 (Carlos), row 3 is user-2 (Ana)
            expect(rows[1]).toHaveTextContent("Beatriz Profesora");
            expect(rows[2]).toHaveTextContent("Carlos Director");
            expect(rows[3]).toHaveTextContent("Ana Monitora");
        });
    });

    describe("DashboardKpis — Adaptive Financial Metrics", () => {
        it("renders unified Total Liquidación card when gross and net are equal", () => {
            const kpis = {
                totalHours: 15,
                totalGross: 300,
                totalNet: 300,
                totalLogs: 4,
                activeMembersCount: 2,
                daysCount: 3,
                isSinglePrice: true
            };

            render(
                <DashboardKpis
                    period="month"
                    onPeriodChange={vi.fn()}
                    kpis={kpis}
                />
            );

            expect(screen.getByText("Total Liquidación")).toBeInTheDocument();
            expect(screen.queryByText("Coste Empresa (Bruto)")).not.toBeInTheDocument();
            expect(screen.queryByText("Liquidación Equipo (Neto)")).not.toBeInTheDocument();
        });

        it("renders separate Gross and Net cards when there are tax differences", () => {
            const kpis = {
                totalHours: 20,
                totalGross: 500,
                totalNet: 420,
                totalLogs: 6,
                activeMembersCount: 3,
                daysCount: 4,
                isSinglePrice: false
            };

            render(
                <DashboardKpis
                    period="month"
                    onPeriodChange={vi.fn()}
                    kpis={kpis}
                />
            );

            expect(screen.getByText("Coste Empresa (Bruto)")).toBeInTheDocument();
            expect(screen.getByText("Liquidación Equipo (Neto)")).toBeInTheDocument();
        });
    });

    describe("DashboardTodayCard — Live Operations", () => {
        it("renders today summary and active instructors correctly", () => {
            const todayLogs = [
                {
                    id: "tl1",
                    userId: "u1",
                    type: "particular",
                    startTime: "09:00",
                    endTime: "11:00",
                    duration: 2,
                    startDate: "2026-09-29"
                }
            ];

            const members = [
                {
                    userId: "u1",
                    role: "worker",
                    user: { firstName: "Marcos", lastName: "Esqui", email: "marcos@test.com" }
                }
            ];

            render(
                <DashboardTodayCard
                    companyId="c1"
                    todayLogs={todayLogs as any}
                    members={members}
                    worklogDefinitions={{ particular: { label: "Clase Particular" } }}
                />
            );

            expect(screen.getByText("Operativa en Tiempo Real (Hoy)")).toBeInTheDocument();
            expect(screen.getByText("Marcos Esqui")).toBeInTheDocument();
            expect(screen.getByText("09:00 - 11:00")).toBeInTheDocument();
            expect(screen.getByText("2.0 h")).toBeInTheDocument();
        });
    });

    describe("DashboardHeaderActions — Operational Actions", () => {
        it("renders primary action Añadir Registro and conditional export button", () => {
            const onExport = vi.fn();
            render(
                <DashboardHeaderActions
                    companyId="c1"
                    companyName="Escuela Sierra Nevada"
                    users={[]}
                    onExportCsv={onExport}
                    canExport={true}
                />
            );

            // New shift is always present
            expect(screen.getByRole("button", { name: /Añadir Registro/i })).toBeInTheDocument();
            // Export CSV button is present and enabled
            expect(screen.getByRole("button", { name: /Exportar CSV/i })).toBeInTheDocument();
        });
    });
});
