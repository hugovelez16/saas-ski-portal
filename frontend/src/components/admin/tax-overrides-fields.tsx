"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export type TaxOverrides = Record<string, number | null>;

interface TaxOverridesFieldsProps {
    /** Impuestos de la empresa (valores 0..1). */
    companyTaxConfig: Record<string, number>;
    /** Overrides del miembro (valores 0..1 o null = sin override). */
    value: TaxOverrides;
    onChange: (value: TaxOverrides) => void;
    disabled?: boolean;
}

/** Convierte 0.0648 en "6.48" para mostrarlo en pantalla. */
export function fractionToPercentText(v: number | null | undefined): string {
    if (v === null || v === undefined || Number.isNaN(v)) return "";
    return String(parseFloat((v * 100).toFixed(4)));
}

/**
 * Convierte el texto en porcentaje (0..100) a fraccion (0..1).
 * Devuelve null si esta vacio y NaN si no es valido o esta fuera de rango.
 */
export function parsePercentText(text: string): number | null {
    if (text.trim() === "") return null;
    const n = Number(text);
    if (!Number.isFinite(n) || n < 0 || n > 100) return NaN;
    return Math.round((n / 100) * 1000000) / 1000000;
}

/** True si algun override es NaN (entrada invalida pendiente de corregir). */
export function hasInvalidTaxOverrides(value: TaxOverrides): boolean {
    return Object.values(value).some((v) => typeof v === "number" && Number.isNaN(v));
}

/** Elimina las entradas null/undefined para enviar solo overrides reales. */
export function compactTaxOverrides(value: TaxOverrides): TaxOverrides {
    const out: TaxOverrides = {};
    for (const [k, v] of Object.entries(value)) {
        if (v !== null && v !== undefined) out[k] = v;
    }
    return out;
}

function sameValue(a: number | null, b: number | null | undefined): boolean {
    const bb = b === undefined ? null : b;
    if (a === null || bb === null) return a === bb;
    return a === bb || (Number.isNaN(a) && Number.isNaN(bb));
}

export function TaxOverridesFields({ companyTaxConfig, value, onChange, disabled }: TaxOverridesFieldsProps) {
    const companyKeys = Object.keys(companyTaxConfig || {});
    const extraKeys = Object.keys(value || {}).filter((k) => !companyKeys.includes(k));
    const allKeys = [...companyKeys, ...extraKeys];

    const [texts, setTexts] = useState<Record<string, string>>(() => {
        const t: Record<string, string> = {};
        for (const k of Object.keys(value || {})) t[k] = fractionToPercentText(value[k]);
        return t;
    });

    // Sincroniza con cambios externos (reset del formulario) sin pisar lo que se esta escribiendo.
    useEffect(() => {
        setTexts((prev) => {
            const next: Record<string, string> = {};
            for (const k of allKeys) {
                const current = prev[k] ?? "";
                const parsed = parsePercentText(current);
                const ext = value?.[k];
                next[k] = sameValue(parsed, ext) ? current : fractionToPercentText(ext);
            }
            return next;
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [JSON.stringify(value), JSON.stringify(companyTaxConfig)]);

    const handleChange = (key: string, text: string) => {
        setTexts((prev) => ({ ...prev, [key]: text }));
        onChange({ ...(value || {}), [key]: parsePercentText(text) });
    };

    if (allKeys.length === 0) {
        return (
            <p className="text-sm text-muted-foreground">
                La empresa no tiene impuestos definidos y este usuario no tiene overrides.
            </p>
        );
    }

    return (
        <div className="grid gap-4 md:grid-cols-3">
            {allKeys.map((key) => {
                const text = texts[key] ?? "";
                const invalid = Number.isNaN(parsePercentText(text));
                const isExtra = !companyKeys.includes(key);
                const defaultText = isExtra ? null : fractionToPercentText(companyTaxConfig[key]);
                return (
                    <div key={key} className="space-y-1.5">
                        <Label htmlFor={`tax-override-${key}`}>{key} (%)</Label>
                        <Input
                            id={`tax-override-${key}`}
                            type="number"
                            step="0.01"
                            min={0}
                            max={100}
                            disabled={disabled}
                            placeholder={defaultText !== null ? `Empresa: ${defaultText}` : "Sin valor"}
                            value={text}
                            onChange={(e) => handleChange(key, e.target.value)}
                            aria-invalid={invalid}
                        />
                        {invalid ? (
                            <p className="text-xs text-destructive">Introduce un valor entre 0 y 100.</p>
                        ) : (
                            <p className="text-xs text-muted-foreground">
                                {isExtra
                                    ? "Impuesto propio de este usuario (no existe en la empresa)."
                                    : `Vacio para usar el valor de la empresa (${defaultText}%).`}
                            </p>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
