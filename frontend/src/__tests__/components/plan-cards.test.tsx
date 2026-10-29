import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PlanCards } from "@/components/landing/plan-cards";
import { SELECT_PLAN_EVENT } from "@/lib/landing-contact";

describe("PlanCards", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("muestra tres tarjetas con precios, temporada y caracteristicas clave", () => {
        const { container } = render(<PlanCards />);

        expect(container.querySelectorAll("article")).toHaveLength(3);
        const text = container.textContent ?? "";
        for (const expected of [
            "129 €",
            "249 €",
            "399 €",
            "Temporada (5 meses): 645 €",
            "Temporada (5 meses): 1.245 €",
            "Temporada (5 meses): 1.995 €",
            "Responsables ilimitados",
            "Monitor adicional: 9 € al mes",
            "Monitor adicional: 7 € al mes",
            "Hasta 50 monitores incluidos",
        ]) {
            expect(text).toContain(expected);
        }
        expect(text).not.toContain("Monitor adicional: 4");
    });

    it("'Recomendado' aparece una sola vez, dentro de la tarjeta Escuela", () => {
        const { container } = render(<PlanCards />);

        const text = container.textContent ?? "";
        expect(text.match(/Recomendado/g)).toHaveLength(1);
        const articles = container.querySelectorAll("article");
        expect(articles[1].textContent).toContain("Recomendado");
        expect(articles[0].textContent).not.toContain("Recomendado");
        expect(articles[2].textContent).not.toContain("Recomendado");
    });

    it("tres enlaces 'Quiero este plan' apuntan a #contacto y el de Grande anuncia el plan", () => {
        const listener = vi.fn();
        window.addEventListener(SELECT_PLAN_EVENT, listener);
        try {
            render(<PlanCards />);

            const links = screen.getAllByRole("link", { name: /Quiero este plan/ });
            expect(links).toHaveLength(3);
            for (const link of links) {
                expect(link).toHaveAttribute("href", "#contacto");
            }

            fireEvent.click(links[2]);

            expect(listener).toHaveBeenCalledTimes(1);
            expect((listener.mock.calls[0][0] as CustomEvent).detail).toBe("grande");
        } finally {
            window.removeEventListener(SELECT_PLAN_EVENT, listener);
        }
    });

    it("la linea de informes a medida no contiene cifras", () => {
        render(<PlanCards />);

        const line = screen.getByText("Informes a medida: bajo consulta.");
        expect(line.textContent).not.toMatch(/\d/);
    });

    it("muestra las lineas de condiciones con puesta en marcha de 150 € y mantenimiento de 20 €", () => {
        render(<PlanCards />);

        expect(
            screen.getByText("Todos los importes son sin IVA, por mes de temporada (diciembre a abril, 5 meses). Sin permanencia."),
        ).toBeInTheDocument();
        expect(screen.getByText("Puesta en marcha única: 150 € en todos los planes.")).toBeInTheDocument();
        expect(screen.getByText(/Mantenimiento fuera de temporada: 20 € al mes \(mayo a noviembre\)/)).toBeInTheDocument();
    });
});
