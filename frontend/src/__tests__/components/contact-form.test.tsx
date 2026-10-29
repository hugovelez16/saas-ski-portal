import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ContactForm } from "@/components/landing/contact-form";
import { SELECT_PLAN_EVENT, announcePlan } from "@/lib/landing-contact";

type Field = "school" | "monitors" | "contactName" | "email";

const LABELS: Record<Field, string> = {
    school: "Nombre de la escuela",
    monitors: "Número aproximado de monitores",
    contactName: "Nombre de contacto",
    email: "Correo electrónico",
};

const VALID: Record<Field, string> = {
    school: "Esquí & Nieve #1",
    monitors: "18",
    contactName: "Ana Pérez",
    email: "ana@escuela.es",
};

function fill(values: Partial<Record<Field, string>>) {
    for (const key of Object.keys(values) as Field[]) {
        fireEvent.change(screen.getByLabelText(LABELS[key]), { target: { value: values[key] } });
    }
}

function fillValid(overrides: Partial<Record<Field, string>> = {}) {
    fill({ ...VALID, ...overrides });
}

const clickWhatsApp = () => fireEvent.click(screen.getByRole("button", { name: "Enviar por WhatsApp" }));
const clickMail = () => fireEvent.click(screen.getByRole("button", { name: "Enviar por correo" }));

describe("ContactForm", () => {
    beforeEach(() => {
        vi.spyOn(window, "open").mockImplementation(() => null);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it("renderiza los 5 campos, los dos botones y el select con 4 opciones por defecto en 'no-se'", () => {
        render(<ContactForm />);

        for (const label of Object.values(LABELS)) {
            expect(screen.getByLabelText(label)).toBeInTheDocument();
        }
        const select = screen.getByLabelText("Plan que te interesa") as HTMLSelectElement;
        expect(select.value).toBe("no-se");
        expect(select.options).toHaveLength(4);
        expect(screen.getByRole("button", { name: "Enviar por WhatsApp" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Enviar por correo" })).toBeInTheDocument();
    });

    it("con el formulario vacio no abre nada, muestra 4 errores y enfoca el primer campo", () => {
        render(<ContactForm />);

        clickWhatsApp();

        expect(window.open).not.toHaveBeenCalled();
        expect(screen.getAllByRole("alert")).toHaveLength(4);
        const school = screen.getByLabelText("Nombre de la escuela");
        expect(school).toHaveAttribute("aria-invalid", "true");
        expect(document.activeElement).toBe(school);
    });

    it("correo sin dominio muestra el error de formato y no abre nada", () => {
        render(<ContactForm />);
        fillValid({ email: "ana@escuela" });

        clickWhatsApp();

        expect(screen.getByText("Introduce un correo válido.")).toBeInTheDocument();
        expect(window.open).not.toHaveBeenCalled();
    });

    it("monitores no entero o cero muestra el error de monitores y no abre nada", () => {
        render(<ContactForm />);
        fillValid({ monitors: "0" });

        clickMail();

        expect(screen.getByText("Indica un número entero de monitores mayor que 0.")).toBeInTheDocument();
        expect(window.open).not.toHaveBeenCalled();
    });

    it("al corregir un campo con error se quita su marca de error", () => {
        render(<ContactForm />);
        clickWhatsApp();
        const school = screen.getByLabelText("Nombre de la escuela");
        expect(school).toHaveAttribute("aria-invalid", "true");

        fireEvent.change(school, { target: { value: "Escuela Sol" } });

        expect(school).not.toHaveAttribute("aria-invalid");
        expect(screen.queryByText("Indica el nombre de la escuela.")).not.toBeInTheDocument();
    });

    it("datos validos y WhatsApp: abre wa.me con el mensaje codificado en una sola llamada", () => {
        render(<ContactForm />);
        fillValid();

        clickWhatsApp();

        expect(window.open).toHaveBeenCalledTimes(1);
        const [url, target, features] = vi.mocked(window.open).mock.calls[0];
        expect(url).toEqual(expect.stringMatching(/^https:\/\/wa\.me\/34685710117\?text=/));
        expect(String(url)).toContain("Esqu%C3%AD%20%26%20Nieve%20%231");
        expect(target).toBe("_blank");
        expect(features).toBe("noopener,noreferrer");
    });

    it("datos validos y correo: abre mailto en la misma pestana", () => {
        render(<ContactForm />);
        fillValid();

        clickMail();

        expect(window.open).toHaveBeenCalledTimes(1);
        const [url, target] = vi.mocked(window.open).mock.calls[0];
        expect(String(url)).toMatch(/^mailto:hugo@vesotel\.com\?subject=/);
        expect(target).toBe("_self");

        const parsed = new URL(String(url));
        expect(parsed.searchParams.get("subject")).toBe("Solicitud de demo de Vesotel Jornadas");
        const body = decodeURIComponent(String(url).slice(String(url).indexOf("&body=") + "&body=".length));
        expect(body).toBe(
            [
                "Hola, quiero pedir una demo de Vesotel Jornadas.",
                "Escuela: Esquí & Nieve #1",
                "Monitores (aprox.): 18",
                "Plan: No lo sé",
                "Contacto: Ana Pérez",
                "Correo: ana@escuela.es",
            ].join("\r\n"),
        );
    });

    it("announcePlan('grande') preselecciona el plan Grande en el select", () => {
        render(<ContactForm />);

        act(() => announcePlan("grande"));

        expect((screen.getByLabelText("Plan que te interesa") as HTMLSelectElement).value).toBe("grande");
    });

    it("un evento de plan con un valor fuera de PLAN_CHOICES no cambia el select", () => {
        render(<ContactForm />);

        act(() => {
            window.dispatchEvent(new CustomEvent(SELECT_PLAN_EVENT, { detail: "inventado" }));
        });

        expect((screen.getByLabelText("Plan que te interesa") as HTMLSelectElement).value).toBe("no-se");
    });

    it("el envio no usa fetch ni almacena datos", () => {
        const fetchSpy = vi.fn();
        vi.stubGlobal("fetch", fetchSpy);
        render(<ContactForm />);
        fillValid();

        clickWhatsApp();
        clickMail();

        expect(fetchSpy).not.toHaveBeenCalled();
    });
});
