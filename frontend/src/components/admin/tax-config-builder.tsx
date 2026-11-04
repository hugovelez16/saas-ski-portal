"use client";

import * as React from "react";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, Trash2, Save } from "lucide-react";

export const TAX_NAME_MAX = 50;
export const TAX_MAX_ENTRIES = 20;

export interface TaxRow {
    key: string;
    value: string;
}

export interface TaxRowErrors {
    key?: string;
    value?: string;
}

/** Convierte el objeto de la API (0..1) en filas de pantalla (0..100). */
export function taxConfigToRows(config: Record<string, number> | null | undefined): TaxRow[] {
    return Object.entries(config || {}).map(([key, val]) => ({
        key,
        value: typeof val === "number" && Number.isFinite(val) ? String(parseFloat((val * 100).toFixed(4))) : "",
    }));
}

/** Valida las filas. Devuelve errores por indice (vacio si todo es valido) y un error global opcional. */
export function validateTaxRows(rows: TaxRow[]): { errors: Record<number, TaxRowErrors>; global?: string } {
    const errors: Record<number, TaxRowErrors> = {};
    const seen = new Map<string, number>();
    rows.forEach((row, i) => {
        const name = row.key.trim();
        const rowErrors: TaxRowErrors = {};
        if (name.length === 0) {
            rowErrors.key = "El nombre no puede estar vacio.";
        } else if (name.length > TAX_NAME_MAX) {
            rowErrors.key = `El nombre admite como maximo ${TAX_NAME_MAX} caracteres.`;
        } else if (seen.has(name)) {
            rowErrors.key = "Nombre duplicado.";
        } else {
            seen.set(name, i);
        }

        const raw = row.value.trim();
        const n = raw === "" ? NaN : Number(raw);
        if (raw === "" || !Number.isFinite(n)) {
            rowErrors.value = "Introduce un numero.";
        } else if (n < 0 || n > 100) {
            rowErrors.value = "El valor debe estar entre 0 y 100.";
        }
        if (rowErrors.key || rowErrors.value) errors[i] = rowErrors;
    });
    const global = rows.length > TAX_MAX_ENTRIES ? `Maximo ${TAX_MAX_ENTRIES} impuestos.` : undefined;
    return { errors, global };
}

/** Convierte filas validas a payload (0..1, redondeado a 6 decimales, nombre con trim). */
export function taxRowsToConfig(rows: TaxRow[]): Record<string, number> {
    const out: Record<string, number> = {};
    rows.forEach((r) => {
        out[r.key.trim()] = Math.round((Number(r.value) / 100) * 1000000) / 1000000;
    });
    return out;
}

interface TaxConfigBuilderProps {
    initialValue: Record<string, number>;
    onSave: (value: Record<string, number>) => void;
}

export function TaxConfigBuilder({ initialValue, onSave }: TaxConfigBuilderProps) {
    const [rows, setRows] = useState<TaxRow[]>([]);
    const [errors, setErrors] = useState<Record<number, TaxRowErrors>>({});
    const [globalError, setGlobalError] = useState<string | undefined>();

    useEffect(() => {
        setRows(taxConfigToRows(initialValue));
        setErrors({});
        setGlobalError(undefined);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [JSON.stringify(initialValue)]);

    const handleSave = () => {
        const result = validateTaxRows(rows);
        setErrors(result.errors);
        setGlobalError(result.global);
        if (Object.keys(result.errors).length > 0 || result.global) return;
        onSave(taxRowsToConfig(rows));
    };

    const updateRow = (index: number, field: keyof TaxRow, val: string) => {
        setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [field]: val } : r)));
    };

    const addRow = () => {
        setRows((prev) => [...prev, { key: "", value: "" }]);
    };

    const removeRow = (index: number) => {
        setRows((prev) => prev.filter((_, i) => i !== index));
        setErrors({});
    };

    return (
        <div className="space-y-4">
            <div className="grid gap-4">
                {rows.map((row, index) => (
                    <div key={index} className="flex items-start gap-2 p-3 rounded-lg border bg-card">
                        <div className="flex-1 space-y-1.5">
                            <Label htmlFor={`tax-name-${index}`} className="text-xs text-muted-foreground">
                                Nombre del impuesto
                            </Label>
                            <Input
                                id={`tax-name-${index}`}
                                value={row.key}
                                onChange={(e) => updateRow(index, "key", e.target.value)}
                                placeholder="Ej: IRPF"
                                className="h-9 text-sm"
                                aria-invalid={!!errors[index]?.key}
                            />
                            {errors[index]?.key && <p className="text-xs text-destructive">{errors[index]?.key}</p>}
                        </div>
                        <div className="w-32 space-y-1.5">
                            <Label htmlFor={`tax-value-${index}`} className="text-xs text-muted-foreground">
                                Valor (%)
                            </Label>
                            <div className="relative">
                                <Input
                                    id={`tax-value-${index}`}
                                    type="number"
                                    step="0.01"
                                    min={0}
                                    max={100}
                                    value={row.value}
                                    onChange={(e) => updateRow(index, "value", e.target.value)}
                                    className="h-9 pr-7"
                                    aria-invalid={!!errors[index]?.value}
                                />
                                <span className="absolute right-2.5 top-2.5 text-xs text-muted-foreground">%</span>
                            </div>
                            {errors[index]?.value && <p className="text-xs text-destructive">{errors[index]?.value}</p>}
                        </div>
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            aria-label={`Quitar impuesto ${row.key || index + 1}`}
                            className="mt-6 h-9 w-9 text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => removeRow(index)}
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                ))}

                {rows.length === 0 && (
                    <div className="text-center py-6 border border-dashed rounded-lg text-muted-foreground text-sm">
                        No hay impuestos configurados todavia.
                    </div>
                )}
            </div>

            {globalError && <p className="text-sm text-destructive">{globalError}</p>}

            <div className="flex gap-3">
                <Button
                    type="button"
                    variant="outline"
                    onClick={addRow}
                    disabled={rows.length >= TAX_MAX_ENTRIES}
                    className="flex-1 border-dashed"
                >
                    <Plus className="h-4 w-4 mr-2" />
                    Anadir impuesto
                </Button>
                <Button type="button" onClick={handleSave} className="min-w-[120px]">
                    <Save className="h-4 w-4 mr-2" />
                    Guardar
                </Button>
            </div>
        </div>
    );
}
