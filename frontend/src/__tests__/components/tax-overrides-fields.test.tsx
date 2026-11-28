import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
    TaxOverridesFields,
    parsePercentText,
    compactTaxOverrides,
    hasInvalidTaxOverrides,
} from "@/components/admin/tax-overrides-fields";

describe("helpers de overrides", () => {
    it("parsePercentText: vacio es null, 0 es valido, acepta coma o punto y fuera de rango es NaN", () => {
        expect(parsePercentText("")).toBeNull();
        expect(parsePercentText("0")).toBe(0);
        expect(parsePercentText("6.48")).toBe(0.0648);
        expect(parsePercentText("6,48")).toBe(0.0648);
        expect(parsePercentText("6,4,8")).toBeNaN();
        expect(parsePercentText("101")).toBeNaN();
        expect(parsePercentText("-1")).toBeNaN();
        expect(parsePercentText("abc")).toBeNaN();
    });

    it("compactTaxOverrides elimina nulls pero conserva 0", () => {
        expect(compactTaxOverrides({ A: null, B: 0, C: 0.1 })).toEqual({ B: 0, C: 0.1 });
    });

    it("hasInvalidTaxOverrides detecta NaN", () => {
        expect(hasInvalidTaxOverrides({ A: NaN })).toBe(true);
        expect(hasInvalidTaxOverrides({ A: null, B: 0 })).toBe(false);
    });
});

describe("TaxOverridesFields", () => {
    it("muestra un campo por clave de empresa mas las claves extra del override", () => {
        render(
            <TaxOverridesFields
                companyTaxConfig={{ IRPF: 0.15, SS: 0.0648 }}
                value={{ IRPF: 0.1, Extra: 0.02 }}
                onChange={() => {}}
            />
        );
        expect((screen.getByLabelText(/IRPF/) as HTMLInputElement).value).toBe("10");
        expect((screen.getByLabelText(/SS/) as HTMLInputElement).value).toBe("");
        expect((screen.getByLabelText(/Extra/) as HTMLInputElement).value).toBe("2");
    });

    it("sin overrides no precarga nada", () => {
        render(<TaxOverridesFields companyTaxConfig={{ IRPF: 0.15 }} value={{}} onChange={() => {}} />);
        expect((screen.getByLabelText(/IRPF/) as HTMLInputElement).value).toBe("");
    });

    it("emite fracciones 0..1, null al vaciar y acepta 0", () => {
        const onChange = vi.fn();
        render(<TaxOverridesFields companyTaxConfig={{ IRPF: 0.15 }} value={{ IRPF: 0.1 }} onChange={onChange} />);
        const input = screen.getByLabelText(/IRPF/);

        fireEvent.change(input, { target: { value: "0" } });
        expect(onChange).toHaveBeenLastCalledWith({ IRPF: 0 });

        fireEvent.change(input, { target: { value: "7.5" } });
        expect(onChange).toHaveBeenLastCalledWith({ IRPF: 0.075 });

        fireEvent.change(input, { target: { value: "" } });
        expect(onChange).toHaveBeenLastCalledWith({ IRPF: null });
    });

    it("marca error y emite NaN con un valor fuera de rango", () => {
        const onChange = vi.fn();
        render(<TaxOverridesFields companyTaxConfig={{ IRPF: 0.15 }} value={{}} onChange={onChange} />);
        fireEvent.change(screen.getByLabelText(/IRPF/), { target: { value: "150" } });
        const last = onChange.mock.calls.at(-1)?.[0];
        expect(Number.isNaN(last.IRPF)).toBe(true);
        expect(screen.getByText(/entre 0 y 100/i)).toBeInTheDocument();
    });

    it("muestra la suma efectiva y avisa si supera el 100%", () => {
        render(
            <TaxOverridesFields
                companyTaxConfig={{ IRPF: 0.6, SS: 0.2 }}
                value={{ Extra: 0.3 }}
                onChange={() => {}}
            />
        );
        expect(screen.getByText(/110%/)).toBeInTheDocument();
        expect(screen.getByRole("alert")).toHaveTextContent(/100%/);
    });

    it("conserva impuestos propios como no editables cuando isManaged es true", () => {
        render(
            <TaxOverridesFields
                companyTaxConfig={{ IRPF: 0.15 }}
                value={{ Mutua: 0.05 }}
                onChange={() => {}}
                isManaged={true}
            />
        );
        const mutuaInput = screen.getByLabelText(/Mutua/) as HTMLInputElement;
        expect(mutuaInput.disabled).toBe(true);
        expect(screen.getByText(/no editable en modo gestionado/i)).toBeInTheDocument();
    });
});
