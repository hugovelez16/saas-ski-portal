import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MonitorSection } from "@/components/landing/monitor-section";

describe("MonitorSection", () => {
    it("el enlace de lista de espera abre un mailto con el asunto codificado", () => {
        render(<MonitorSection />);

        const link = screen.getByRole("link", { name: "Apúntame a la lista de espera" });
        expect(link.getAttribute("href")).toMatch(
            /^mailto:hugo@vesotel\.com\?subject=Lista%20de%20espera%20para%20monitores/,
        );
    });

    it("el enlace de contacto abre WhatsApp en una pestana nueva con noopener", () => {
        render(<MonitorSection />);

        const link = screen.getByRole("link", { name: "Escríbeme sin compromiso" });
        expect(link.getAttribute("href")).toMatch(/^https:\/\/wa\.me\/34685710117\?text=/);
        expect(link).toHaveAttribute("target", "_blank");
        expect(link.getAttribute("rel")).toContain("noopener");
    });

    it("muestra el bloque para recomendar a la escuela sin formulario ni campos", () => {
        const { container } = render(<MonitorSection />);

        expect(screen.getByText("Recomiéndaselo a tu escuela")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Ver planes para escuelas" })).toHaveAttribute("href", "#precios");
        expect(container.querySelector("form, input")).toBeNull();
    });

    it("usa la palabra 'gratuita' una sola vez, en el titular", () => {
        const { container } = render(<MonitorSection />);

        expect(container.textContent?.match(/gratuit\w*/gi)).toEqual(["gratuita"]);
        expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Una versión gratuita para monitores, próximamente");
    });
});
