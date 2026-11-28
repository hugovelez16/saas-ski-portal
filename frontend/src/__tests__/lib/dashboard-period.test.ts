import { beforeEach, describe, expect, it, vi } from "vitest";
import { getDashboardPeriod, setDashboardPeriod } from "@/lib/dashboard-period";

describe("dashboard-period", () => {
    beforeEach(() => localStorage.clear());

    it("guarda y lee la preferencia por empresa, incluyendo fechas personalizadas", () => {
        setDashboardPeriod("empresa-1", { period: "custom", from: "2026-01-02", to: "2026-01-31" });
        expect(getDashboardPeriod("empresa-1")).toEqual({ period: "custom", from: "2026-01-02", to: "2026-01-31" });
        expect(localStorage.getItem("dashboardPeriod:empresa-1")).toContain('"period":"custom"');
    });

    it("omite valores corruptos, periodos invalidos y fechas incorrectas", () => {
        localStorage.setItem("dashboardPeriod:empresa-1", "no-json");
        expect(getDashboardPeriod("empresa-1")).toBeNull();
        localStorage.setItem("dashboardPeriod:empresa-1", JSON.stringify({ period: "year" }));
        expect(getDashboardPeriod("empresa-1")).toBeNull();
        localStorage.setItem("dashboardPeriod:empresa-1", JSON.stringify({ period: "custom", from: "2026-02-30", to: "2026-03-01" }));
        expect(getDashboardPeriod("empresa-1")).toBeNull();
        localStorage.setItem("dashboardPeriod:empresa-1", JSON.stringify({ period: "custom", from: "2026-03-02", to: "2026-03-01" }));
        expect(getDashboardPeriod("empresa-1")).toBeNull();
    });

    it("omite los errores de localStorage al leer y escribir", () => {
        const getItem = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
        const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
        expect(() => getDashboardPeriod("empresa-1")).not.toThrow();
        expect(getDashboardPeriod("empresa-1")).toBeNull();
        expect(() => setDashboardPeriod("empresa-1", { period: "month" })).not.toThrow();
        getItem.mockRestore();
        setItem.mockRestore();
    });
});
