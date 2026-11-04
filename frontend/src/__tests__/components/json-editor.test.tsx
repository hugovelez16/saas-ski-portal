import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { JsonEditor, findNonFiniteNumber } from "@/components/admin/json-editor";

describe("findNonFiniteNumber", () => {
    it("devuelve null si todos los numeros son finitos", () => {
        expect(findNonFiniteNumber({ a: 1, b: [0, -2.5, { c: 3 }], d: "x", e: true, f: null })).toBeNull();
    });

    it("devuelve null para valores no numericos y primitivos sin numeros", () => {
        expect(findNonFiniteNumber(null)).toBeNull();
        expect(findNonFiniteNumber("texto")).toBeNull();
        expect(findNonFiniteNumber(false)).toBeNull();
        expect(findNonFiniteNumber([])).toBeNull();
        expect(findNonFiniteNumber({})).toBeNull();
    });

    it("detecta NaN en la raiz", () => {
        expect(findNonFiniteNumber(NaN)).toBe("$");
    });

    it("detecta Infinity y -Infinity", () => {
        expect(findNonFiniteNumber(Infinity)).toBe("$");
        expect(findNonFiniteNumber({ a: -Infinity })).toBe("$.a");
    });

    it("devuelve la ruta del primer valor invalido en objetos anidados", () => {
        const value = { tax_config: { iva: 0.21, irpf: NaN } };
        expect(findNonFiniteNumber(value)).toBe("$.tax_config.irpf");
    });

    it("devuelve la ruta con indices cuando el valor invalido esta en un array", () => {
        const value = { rates: [{ base_rate: 10 }, { base_rate: NaN }] };
        expect(findNonFiniteNumber(value)).toBe("$.rates[1].base_rate");
    });

    it("devuelve el primer invalido en orden de recorrido", () => {
        const value = { a: NaN, b: Infinity };
        expect(findNonFiniteNumber(value)).toBe("$.a");
    });
});

describe("JsonEditor", () => {
    it("llama a onSave con el valor parseado si todos los numeros son finitos", () => {
        const onSave = vi.fn();
        render(<JsonEditor initialValue={{ a: 1 }} onSave={onSave} />);

        fireEvent.change(screen.getByRole("textbox"), { target: { value: '{"a": 2.5}' } });
        fireEvent.click(screen.getByRole("button", { name: "Guardar Configuración" }));

        expect(onSave).toHaveBeenCalledTimes(1);
        expect(onSave).toHaveBeenCalledWith({ a: 2.5 });
    });

    it("no llama a onSave y muestra el error si un numero es Infinity (literal 1e400)", () => {
        const onSave = vi.fn();
        render(<JsonEditor initialValue={{}} onSave={onSave} />);

        fireEvent.change(screen.getByRole("textbox"), { target: { value: '{"rates": [{"base_rate": 1e400}]}' } });
        fireEvent.click(screen.getByRole("button", { name: "Guardar Configuración" }));

        expect(onSave).not.toHaveBeenCalled();
        expect(screen.getByText(/\$\.rates\[0\]\.base_rate/)).toBeInTheDocument();
        expect(screen.getByText("Valor no válido")).toBeInTheDocument();
    });

    it("oculta el error de valor al corregir el texto y guardar de nuevo", () => {
        const onSave = vi.fn();
        render(<JsonEditor initialValue={{}} onSave={onSave} />);
        const textarea = screen.getByRole("textbox");

        fireEvent.change(textarea, { target: { value: '{"a": 1e400}' } });
        fireEvent.click(screen.getByRole("button", { name: "Guardar Configuración" }));
        expect(screen.getByText("Valor no válido")).toBeInTheDocument();

        fireEvent.change(textarea, { target: { value: '{"a": 1}' } });
        expect(screen.queryByText("Valor no válido")).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole("button", { name: "Guardar Configuración" }));
        expect(onSave).toHaveBeenCalledWith({ a: 1 });
    });
});
