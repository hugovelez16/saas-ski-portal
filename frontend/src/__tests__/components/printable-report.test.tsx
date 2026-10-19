import { describe, it, expect } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { PrintableReport } from "@/components/reports/PrintableReport";
import type { WorkLog, WorkLogSummary } from "@/lib/types";

const summary: WorkLogSummary = {
    startDate: "2026-01-01",
    endDate: "2026-01-31",
    totals: { logsCount: 3, totalHours: 12, totalNet: 400, totalGross: 450, uniqueDays: 2, activeUsers: 1 },
    byType: [
        { type: "particular", logsCount: 2, hours: 8, net: 200, gross: 220 },
        { type: "evento", logsCount: 3, hours: 0, net: 90, gross: 100 },
        { type: "tutorial", logsCount: 1, hours: 4, net: 110, gross: 130 },
    ],
    byDay: [
        { date: "2026-01-05", logsCount: 2, hours: 8, net: 200, gross: 220 },
        { date: "2026-01-06", logsCount: 1, hours: 4, net: 200, gross: 230 },
    ],
    byUser: [],
};

const definitions = {
    particular: { label: "Clase particular", unit: "hours" },
    evento: { label: "Evento", unit: "fixed" },
};

const workLogs = [
    { id: "l1", type: "particular", date: "2026-01-05", startDate: "2026-01-05", netAmount: 200 },
] as unknown as WorkLog[];

const dateRange = { from: new Date(2026, 0, 1), to: new Date(2026, 0, 31) };

describe("PrintableReport", () => {
    it("renders one block per type with the company label and unit", () => {
        render(
            <PrintableReport
                workLogs={workLogs}
                summary={summary}
                worklogDefinitions={definitions}
                title="Informe"
                dateRange={dateRange}
            />
        );

        expect(screen.getByText("Clase particular")).toBeInTheDocument();
        expect(screen.getByText("8.0 horas")).toBeInTheDocument();
        expect(screen.getByText("Evento")).toBeInTheDocument();
        expect(screen.getByText("3 turnos")).toBeInTheDocument();
    });

    it("uses the capitalised type and hours for types without definition", () => {
        render(
            <PrintableReport
                workLogs={workLogs}
                summary={summary}
                worklogDefinitions={definitions}
                title="Informe"
                dateRange={dateRange}
            />
        );

        expect(screen.getByText("Tutorial")).toBeInTheDocument();
        expect(screen.getByText("4.0 horas")).toBeInTheDocument();
    });

    it("takes the global totals from the summary, not from the rows", () => {
        render(
            <PrintableReport
                workLogs={[]}
                summary={summary}
                worklogDefinitions={definitions}
                title="Informe"
                dateRange={dateRange}
            />
        );

        // Ingresos y horas vienen del resumen aunque no haya filas de detalle
        expect(screen.getByText("12h")).toBeInTheDocument();
        expect(screen.getByText("/31").parentElement).toHaveTextContent("2/31");
    });

    it("shows the monthly subtotal from the daily aggregates", () => {
        render(
            <PrintableReport
                workLogs={workLogs}
                summary={summary}
                worklogDefinitions={definitions}
                title="Informe"
                dateRange={dateRange}
            />
        );

        // 200 + 200 de byDay de enero; las filas de detalle solo suman 200
        expect(screen.getByText(/Total January 2026/i).closest("tr")).toHaveTextContent("400,00");
    });
});
