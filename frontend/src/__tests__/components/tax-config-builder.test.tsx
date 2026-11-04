import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
    TaxConfigBuilder,
    validateTaxRows,
    taxRowsToConfig,
    taxConfigToRows,
} from "@/components/admin/tax-config-builder";

describe("validateTaxRows", () => {
    it("acepta el valor 0 y el valor 100", () => {
        const { errors } = validateTaxRows([
            { key: "A", value: "0" },
            { key: "B", value: "100" },
        ]);
        expect(errors).toEqual({});
    });

    it("rechaza nombre vacio, solo espacios y de mas de 50 caracteres", () => {
        const { errors } = validateTaxRows([
            { key: "", value: "1" },
            { key: "   ", value: "1" },
            { key: "x".repeat(51), value: "1" },
        ]);
        expect(errors[0]?.key).toBeDefined();
        expect(errors[1]?.key).toBeDefined();
        expect(errors[2]?.key).toBeDefined();
    });

    it("rechaza duplicados tras trim", () => {
        const { errors } = validateTaxRows([
            { key: "IRPF", value: "1" },
            { key: "IRPF ", value: "2" },
        ]);
        expect(errors[0]).toBeUndefined();
        expect(errors[1]?.key).toMatch(/duplicado/i);
    });

    it("rechaza valor vacio, NaN y fuera de rango", () => {
        const { errors } = validateTaxRows([
            { key: "A", value: "" },
            { key: "B", value: "abc" },
            { key: "C", value: "-1" },
            { key: "D", value: "100.5" },
        ]);
        expect(errors[0]?.value).toBeDefined();
        expect(errors[1]?.value).toBeDefined();
        expect(errors[2]?.value).toBeDefined();
        expect(errors[3]?.value).toBeDefined();
    });

    it("rechaza mas de 20 entradas", () => {
        const rows = Array.from({ length: 21 }, (_, i) => ({ key: `T${i}`, value: "1" }));
        expect(validateTaxRows(rows).global).toBeDefined();
    });
});

describe("conversion de escala", () => {
    it("pasa de 0..1 a 0..100 y vuelta sin ruido de coma flotante", () => {
        expect(taxConfigToRows({ SS: 0.0648, Cero: 0 })).toEqual([
            { key: "SS", value: "6.48" },
            { key: "Cero", value: "0" },
        ]);
        expect(taxRowsToConfig([{ key: " SS ", value: "6.48" }, { key: "Cero", value: "0" }])).toEqual({
            SS: 0.0648,
            Cero: 0,
        });
    });
});

describe("TaxConfigBuilder", () => {
    it("no precarga valores y guarda {} cuando no hay filas", () => {
        const onSave = vi.fn();
        render(<TaxConfigBuilder initialValue={{}} onSave={onSave} />);
        expect(screen.queryByLabelText(/Nombre del impuesto/i)).not.toBeInTheDocument();
        fireEvent.click(screen.getByRole("button", { name: /Guardar/i }));
        expect(onSave).toHaveBeenCalledWith({});
    });

    it("anade una fila vacia, valida y no guarda hasta ser correcta", () => {
        const onSave = vi.fn();
        render(<TaxConfigBuilder initialValue={{}} onSave={onSave} />);
        fireEvent.click(screen.getByRole("button", { name: /Anadir impuesto/i }));
        const name = screen.getByLabelText(/Nombre del impuesto/i) as HTMLInputElement;
        const value = screen.getByLabelText(/Valor/i) as HTMLInputElement;
        expect(name.value).toBe("");
        expect(value.value).toBe("");

        fireEvent.click(screen.getByRole("button", { name: /Guardar/i }));
        expect(onSave).not.toHaveBeenCalled();
        expect(screen.getByText(/nombre no puede estar vacio/i)).toBeInTheDocument();

        fireEvent.change(name, { target: { value: "IRPF" } });
        fireEvent.change(value, { target: { value: "0" } });
        fireEvent.click(screen.getByRole("button", { name: /Guardar/i }));
        expect(onSave).toHaveBeenCalledWith({ IRPF: 0 });
    });

    it("permite renombrar y quitar", () => {
        const onSave = vi.fn();
        render(<TaxConfigBuilder initialValue={{ IRPF: 0.15, SS: 0.0648 }} onSave={onSave} />);
        const names = screen.getAllByLabelText(/Nombre del impuesto/i);
        fireEvent.change(names[0], { target: { value: "Retencion" } });
        fireEvent.click(screen.getByRole("button", { name: /Quitar impuesto SS/i }));
        fireEvent.click(screen.getByRole("button", { name: /Guardar/i }));
        expect(onSave).toHaveBeenCalledWith({ Retencion: 0.15 });
    });

    it("bloquea el guardado con nombres duplicados", () => {
        const onSave = vi.fn();
        render(<TaxConfigBuilder initialValue={{ A: 0.1, B: 0.2 }} onSave={onSave} />);
        const names = screen.getAllByLabelText(/Nombre del impuesto/i);
        fireEvent.change(names[1], { target: { value: "A" } });
        fireEvent.click(screen.getByRole("button", { name: /Guardar/i }));
        expect(onSave).not.toHaveBeenCalled();
        expect(screen.getByText(/duplicado/i)).toBeInTheDocument();
    });
});
