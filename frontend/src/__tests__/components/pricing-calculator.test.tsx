import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PricingCalculator } from "@/components/landing/pricing-calculator";
import { SELECT_PLAN_EVENT } from "@/lib/landing-contact";

const slider = () => screen.getByLabelText("Número de monitores") as HTMLInputElement;
const setMonitors = (value: number) => fireEvent.change(slider(), { target: { value: String(value) } });
const radio = (name: RegExp) => screen.getByRole("radio", { name });
const totalMonthly = () => screen.getByTestId("total-monthly").textContent;

describe("PricingCalculator", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("estado inicial: Escuela marcado con 20 monitores y los totales de 249 €", () => {
        render(<PricingCalculator />);

        expect(radio(/Escuela/)).toBeChecked();
        expect(slider().value).toBe("20");
        expect(totalMonthly()).toBe("249,00 €");
        expect(screen.getByTestId("total-season").textContent).toBe("1.245,00 €");
        expect(screen.getByTestId("total-first-season").textContent).toBe("1.395,00 €");
    });

    it("con Escuela y 26 monitores el total mensual es 256 €", () => {
        render(<PricingCalculator />);

        setMonitors(26);

        expect(totalMonthly()).toBe("256,00 €");
    });

    it("Básico con 26 monitores suma 273 € y los extras aparecen y suman al marcarlos", () => {
        render(<PricingCalculator />);
        setMonitors(26);

        fireEvent.click(radio(/Básico/));

        expect(totalMonthly()).toBe("273,00 €");
        const shared = screen.getByLabelText("Cuadrante compartido (5 € al mes)");
        const reports = screen.getByLabelText("Informes (15 € al mes)");
        expect(shared).toBeInTheDocument();
        expect(reports).toBeInTheDocument();

        fireEvent.click(reports);
        expect(totalMonthly()).toBe("288,00 €");

        fireEvent.click(radio(/Escuela/));
        expect(screen.queryByLabelText("Cuadrante compartido (5 € al mes)")).not.toBeInTheDocument();
        expect(screen.queryByLabelText("Informes (15 € al mes)")).not.toBeInTheDocument();
        expect(screen.getByText("Cuadrante compartido e Informes incluidos en este plan.")).toBeInTheDocument();
    });

    it("responsables adicionales: 2 en Escuela suma 100 € y aparece la fila de desglose", () => {
        render(<PricingCalculator />);

        fireEvent.change(screen.getByLabelText(/Responsables adicionales/), { target: { value: "2" } });

        expect(totalMonthly()).toBe("349,00 €");
        expect(screen.getByText("Responsables adicionales (2 x 50 €)")).toBeInTheDocument();
    });

    it("responsables adicionales negativos se normalizan a 0", () => {
        render(<PricingCalculator />);

        fireEvent.change(screen.getByLabelText(/Responsables adicionales/), { target: { value: "-3" } });

        expect((screen.getByLabelText(/Responsables adicionales/) as HTMLInputElement).value).toBe("0");
        expect(totalMonthly()).toBe("249,00 €");
    });

    it("responsables adicionales se limitan a 20 en el onChange", () => {
        render(<PricingCalculator />);

        fireEvent.change(screen.getByLabelText(/Responsables adicionales/), { target: { value: "25" } });

        expect((screen.getByLabelText(/Responsables adicionales/) as HTMLInputElement).value).toBe("20");
        expect(totalMonthly()).toBe("1.249,00 €");
    });

    it("sugerencia sin depender de extras ocultos: Básico con extras pasa a Escuela, al cambiar a Escuela vuelve a Básico", () => {
        render(<PricingCalculator />);
        setMonitors(22);
        fireEvent.click(radio(/Básico/));
        fireEvent.click(screen.getByLabelText("Cuadrante compartido (5 € al mes)"));
        fireEvent.click(screen.getByLabelText("Informes (15 € al mes)"));

        // Basico con extras: 257 €, Escuela: 249 €.
        expect(screen.getByText("Plan más barato para 22 monitores: Escuela")).toBeInTheDocument();

        fireEvent.click(radio(/Escuela/));

        // Los extras de Basico estan ocultos: la sugerencia no los tiene en cuenta (Basico: 237 €).
        expect(screen.getByText("Plan más barato para 22 monitores: Básico")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Usar Básico" })).toBeInTheDocument();
    });

    it("sugerencia sin depender de responsables ocultos: con Grande no cuentan los responsables de Escuela", () => {
        render(<PricingCalculator />);
        setMonitors(40);
        // Escuela con 1 responsable extra: 404 €; Grande: 399 €.
        fireEvent.change(screen.getByLabelText(/Responsables adicionales/), { target: { value: "1" } });
        expect(screen.getByText("Plan más barato para 40 monitores: Grande")).toBeInTheDocument();

        fireEvent.click(radio(/Grande/));

        // Campo oculto: la sugerencia ignora ese responsable y Escuela cuesta 354 €.
        expect(screen.getByText("Plan más barato para 40 monitores: Escuela")).toBeInTheDocument();
    });

    it("Grande: oculta el campo de responsables, muestra ilimitados y total 399 € con 20 monitores", () => {
        render(<PricingCalculator />);

        fireEvent.click(radio(/Grande/));

        expect(screen.queryByLabelText(/Responsables adicionales/)).not.toBeInTheDocument();
        expect(screen.getByText("Responsables ilimitados incluidos en este plan.")).toBeInTheDocument();
        expect(totalMonthly()).toBe("399,00 €");
    });

    it("sugerencia: con Escuela y 24 monitores no ofrece 'Usar' porque ya es el mas barato", () => {
        render(<PricingCalculator />);

        setMonitors(24);

        expect(screen.getByText("Plan más barato para 24 monitores: Escuela")).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: /^Usar/ })).not.toBeInTheDocument();
    });

    it("sugerencia: con 47 monitores recomienda Grande y ofrece el boton 'Usar Grande'", () => {
        render(<PricingCalculator />);

        setMonitors(47);

        expect(screen.getByText("Plan más barato para 47 monitores: Grande")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Usar Grande" })).toBeInTheDocument();
    });

    it("con 51 monitores muestra 'a consultar' y no hay total mensual", () => {
        render(<PricingCalculator />);

        setMonitors(51);

        expect(screen.getByText("Más de 50 monitores: a consultar.")).toBeInTheDocument();
        expect(screen.queryByTestId("total-monthly")).not.toBeInTheDocument();
    });

    it("con 20 monitores y Escuela sugiere Básico; 'Usar Básico' marca el radio y oculta el boton", () => {
        render(<PricingCalculator />);

        expect(screen.getByText("Plan más barato para 20 monitores: Básico")).toBeInTheDocument();
        fireEvent.click(screen.getByRole("button", { name: "Usar Básico" }));

        expect(radio(/Básico/)).toBeChecked();
        expect(screen.queryByRole("button", { name: "Usar Básico" })).not.toBeInTheDocument();
    });

    it("CTA: envia el plan seleccionado y 'no-se' si hay mas de 50 monitores", () => {
        const listener = vi.fn();
        window.addEventListener(SELECT_PLAN_EVENT, listener);
        try {
            render(<PricingCalculator />);

            fireEvent.click(screen.getByRole("link", { name: "Quiero este plan" }));
            expect(listener).toHaveBeenCalledTimes(1);
            expect((listener.mock.calls[0][0] as CustomEvent).detail).toBe("escuela");

            setMonitors(51);
            fireEvent.click(screen.getByRole("link", { name: "Quiero este plan" }));
            expect(listener).toHaveBeenCalledTimes(2);
            expect((listener.mock.calls[1][0] as CustomEvent).detail).toBe("no-se");
        } finally {
            window.removeEventListener(SELECT_PLAN_EVENT, listener);
        }
    });
});
