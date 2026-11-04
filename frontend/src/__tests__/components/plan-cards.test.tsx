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
            "Ejemplo, 5 meses: 645 €",
            "Ejemplo, 5 meses: 1.245 €",
            "Ejemplo, 5 meses: 1.995 €",
            "Mantenimiento: 15 € por mes inactivo",
            "Mantenimiento: 20 € por mes inactivo",
            "Mantenimiento: 30 € por mes inactivo",
            "Responsables ilimitados",
            "Monitor adicional: 9 € al mes",
            "Monitor adicional: 7 € al mes",
            "Hasta 50 monitores incluidos",
            "Módulos aparte",
            "Cuadrante compartido e Informes incluidos",
        ]) {
            expect(text).toContain(expected);
        }
        expect(text).not.toContain("Monitor adicional: 4");
    });

    it("muestra los nombres Pista Verde, Pista Azul y Pista Roja en sus tarjetas, con su circulo de color", () => {
        const { container } = render(<PlanCards />);

        const articles = container.querySelectorAll("article");
        const expected: [string, string][] = [
            ["Pista Verde", "bg-green-600"],
            ["Pista Azul", "bg-blue-600"],
            ["Pista Roja", "bg-red-600"],
        ];
        expected.forEach(([name, dotClass], index) => {
            expect(articles[index].querySelector("h3")).toHaveTextContent(name);
            const dot = articles[index].querySelector("span[aria-hidden]");
            expect(dot).toHaveClass("h-3", "w-3", "rounded-full", dotClass);
        });
    });

    it("muestra 'Pista Negra' para mas de 50 monitores en la tarjeta Pista Roja", () => {
        const { container } = render(<PlanCards />);

        expect(container.textContent).toContain("Más de 50 monitores: Pista Negra, a consultar");
        expect(container.querySelectorAll("article")[2].textContent).toContain("Pista Negra");
    });

    it("'Recomendado' aparece una sola vez, dentro de la tarjeta Pista Azul", () => {
        const { container } = render(<PlanCards />);

        const text = container.textContent ?? "";
        expect(text.match(/Recomendado/g)).toHaveLength(1);
        const articles = container.querySelectorAll("article");
        expect(articles[1].textContent).toContain("Recomendado");
        expect(screen.getByText("Recomendado")).toHaveClass("absolute", "-top-3", "whitespace-nowrap");
        expect(articles[0].textContent).not.toContain("Recomendado");
        expect(articles[2].textContent).not.toContain("Recomendado");
    });

    it("tres enlaces 'Quiero este plan' apuntan a #contacto y el de Pista Roja anuncia el plan", () => {
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

    it("muestra las condiciones: meses activos a elegir, puesta en marcha de 150 € y mantenimiento sin acceso", () => {
        const { container } = render(<PlanCards />);

        expect(screen.getByText(/Tú eliges qué meses activas la escuela/)).toBeInTheDocument();
        expect(screen.getByText("Puesta en marcha única: 150 € en todos los planes.")).toBeInTheDocument();
        expect(screen.getByText(/Mantenimiento fuera de temporada: en los meses inactivos no hay acceso/)).toBeInTheDocument();
        expect(screen.getByText(/conserva su precio la temporada siguiente/)).toBeInTheDocument();
        expect(container.textContent).not.toMatch(/diciembre|mayo a noviembre/);
    });
});
