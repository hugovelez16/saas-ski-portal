import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import LandingPage from "@/app/page";

vi.mock("@/components/landing/session-redirect", () => ({
    SessionRedirect: () => null,
}));

vi.mock("next/image", () => ({
    // eslint-disable-next-line @next/next/no-img-element
    default: (p: { alt: string; src: string }) => <img alt={p.alt} src={p.src} />,
}));

const FORBIDDEN_PATTERNS: RegExp[] = [
    /arrastr/i,
    /al instante/i,
    /al momento/i,
    /4 y 5 horas/i,
    /exportaci[oó]n de tus datos/i,
    /Parte diario del equipo/,
    /fuera del servidor/i,
    /recuper/i,
    /contrase[ñn]a/i,
    /fundador/i,
    /testimonio/i,
    /bonific/i,
    /adelantad/i,
    /\d\s?%/,
    /gratis/i,
    /Sierra/i,
    /bot[oó]n(es)? de gesti/i,
];

const REQUIRED_TEXTS: string[] = [
    "Pide una demo de 20 min",
    "Ver planes",
    "Informes a medida: bajo consulta.",
    "Recomiéndaselo a tu escuela",
    "Enviar por WhatsApp",
    "Enviar por correo",
    "Apúntame a la lista de espera",
    "Escríbeme sin compromiso",
    "La ve en cuanto entra en la app",
];

describe("LandingPage", () => {
    const renderPage = () => {
        const { container } = render(<LandingPage />);
        const text = container.textContent ?? "";
        return { container, text };
    };

    it("no contiene textos prohibidos por las reglas de la landing", () => {
        const { text } = renderPage();
        for (const pattern of FORBIDDEN_PATTERNS) {
            expect(text, `patron prohibido encontrado: ${pattern}`).not.toMatch(pattern);
        }
    });

    it('contiene la palabra "gratuita" exactamente una vez en el texto visible', () => {
        const { text } = renderPage();
        expect(text.match(/gratuit\w*/gi)).toEqual(["gratuita"]);
    });

    it("contiene los textos obligatorios", () => {
        const { text } = renderPage();
        for (const required of REQUIRED_TEXTS) {
            expect(text, `texto obligatorio ausente: ${required}`).toContain(required);
        }
    });

    it('muestra "Cuadrante compartido" como titulo del modulo en la seccion de modulos', () => {
        renderPage();
        const heading = screen.getByRole("heading", { level: 3, name: "Cuadrante compartido" });
        expect(heading).toBeInTheDocument();
        const modules = document.querySelector("#modulos");
        expect(modules).not.toBeNull();
        expect(modules!.contains(heading)).toBe(true);
    });

    it('contiene la frase exacta "Mantenimiento fuera de temporada" en los planes', () => {
        const { text } = renderPage();
        expect(text).toContain("Mantenimiento fuera de temporada");
    });

    it('contiene "Sin permanencia" (sin distinguir mayusculas)', () => {
        const { text } = renderPage();
        expect(text).toMatch(/sin permanencia/i);
    });

    it("la cabecera es sticky y tiene el enlace Acceder a /login", () => {
        const { container } = renderPage();
        const header = container.querySelector("header");
        expect(header).not.toBeNull();
        expect(header!.className).toContain("sticky");
        const acceder = Array.from(header!.querySelectorAll("a")).find(
            (a) => a.textContent?.trim() === "Acceder",
        );
        expect(acceder, "enlace Acceder ausente en la cabecera").toBeDefined();
        expect(acceder!.getAttribute("href")).toBe("/login");
    });

    it('tiene el enlace "Pide una demo" apuntando a #contacto', () => {
        renderPage();
        const demo = screen.getAllByRole("link", { name: /Pide una demo/ });
        expect(demo.some((a) => a.getAttribute("href") === "#contacto")).toBe(true);
    });

    it("existen las anclas #contacto, #precios, #preguntas y #funciones", () => {
        const { container } = renderPage();
        for (const id of ["contacto", "precios", "preguntas", "funciones"]) {
            expect(container.querySelector(`#${id}`), `ancla #${id} ausente`).not.toBeNull();
        }
    });

    it('hay al menos 3 enlaces "Quiero este plan"', () => {
        renderPage();
        const links = screen.getAllByRole("link", { name: /Quiero este plan/ });
        expect(links.length).toBeGreaterThanOrEqual(3);
    });
});
