import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { LegalFooter } from "@/components/legal-footer";

describe("LegalFooter", () => {
    it("muestra los cuatro enlaces legales con su ruta", () => {
        render(<LegalFooter />);

        const nav = screen.getByRole("navigation", { name: "Información legal" });
        const links = within(nav).getAllByRole("link");

        expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
            ["Aviso legal", "/aviso-legal"],
            ["Privacidad", "/privacidad"],
            ["Cookies", "/cookies"],
            ["Términos", "/terminos"],
        ]);
    });

    it("acepta clases adicionales para adaptarse al contenedor", () => {
        render(<LegalFooter className="text-slate-300" />);

        expect(screen.getByRole("navigation", { name: "Información legal" })).toHaveClass("text-slate-300");
    });
});
