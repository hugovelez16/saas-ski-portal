"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const PERCENT_SCALE = 10000;

export type TaxOverrides = Record<string, number | null>;

interface TaxOverridesFieldsProps {
    /** Impuestos de la empresa (valores 0..1). */
    companyTaxConfig: Record<string, number>;
    /** Overrides del miembro (valores 0..1 o null = sin override). */
    value: TaxOverrides;
    onChange: (value: TaxOverrides) => void;
    disabled?: boolean;
    /** Si true (empresa gestionada), los impuestos propios existentes se conservan sin permitir editarlos. */
    isManaged?: boolean;
}

/** Convierte 0.0648 en "6.48" para mostrarlo en pantalla. */
export function fractionToPercentText(v: number | null | undefined): string {
    if (v === null || v === undefined || Number.isNaN(v)) return "";
    return String(parseFloat((v * 100).toFixed(4)));
}

/**
 * Convierte texto de porcentaje (0..100, con punto o coma decimal) a numero (0..100).
 * Devuelve NaN si no es un numero valido.
 */
export function parsePercentNumber(text: string): number {
    const trimmed = text.trim();
    if (trimmed === "") return NaN;
    if (!/^[+-]?(\d+([.,]\d+)?|[.,]\d+)$/.test(trimmed)) return NaN;
    const n = Number(trimmed.replace(",", "."));
    return Number.isFinite(n) ? n : NaN;
}

/**
 * Convierte el texto en porcentaje (0..100, punto o coma) a fraccion (0..1).
 * Devuelve null si esta vacio y NaN si no es valido o esta fuera de rango.
 */
export function parsePercentText(text: string): number | null {
    if (text.trim() === "") return null;
    const n = parsePercentNumber(text);
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

/** Calcula la suma efectiva (0..100+) combinando impuestos de empresa y overrides no nulos. */
export function calculateEffectiveTaxPercent(
    companyTaxConfig: Record<string, number> | null | undefined,
    overrides: TaxOverrides | null | undefined
): number {
    const effective: Record<string, number> = { ...(companyTaxConfig || {}) };
    for (const [key, val] of Object.entries(overrides || {})) {
        if (val !== null && val !== undefined && Number.isFinite(val)) {
            effective[key] = val;
        }
    }
    let scaledTotal = 0;
    for (const rate of Object.values(effective)) {
        if (typeof rate === "number" && Number.isFinite(rate) && rate >= 0) {
            scaledTotal += Math.round(rate * 100 * PERCENT_SCALE);
        }
    }
    return scaledTotal / PERCENT_SCALE;
}

/** True si la suma efectiva de impuestos supera el 100%. */
export function exceedsMaxTaxSum(
    companyTaxConfig: Record<string, number> | null | undefined,
    overrides: TaxOverrides | null | undefined
): boolean {
    return calculateEffectiveTaxPercent(companyTaxConfig, overrides) > 100;
}

function sameValue(a: number | null, b: number | null | undefined): boolean {
    const bb = b === undefined ? null : b;
    if (a === null || bb === null) return a === bb;
    return a === bb || (Number.isNaN(a) && Number.isNaN(bb));
}

export function TaxOverridesFields({ companyTaxConfig, value, onChange, disabled, isManaged = false }: TaxOverridesFieldsProps) {
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

    const effectivePercent = calculateEffectiveTaxPercent(companyTaxConfig, value);
    const exceedsLimit = effectivePercent > 100;

    return (
        <div className="space-y-3">
            <div className="grid gap-4 md:grid-cols-3">
                {allKeys.map((key) => {
                    const text = texts[key] ?? "";
                    const invalid = Number.isNaN(parsePercentText(text));
                    const isExtra = !companyKeys.includes(key);
                    const isManagedCustomLocked = isManaged && isExtra;
                    const defaultText = isExtra ? null : fractionToPercentText(companyTaxConfig[key]);
                    return (
                        <div key={key} className="space-y-1.5">
                            <Label htmlFor={`tax-override-${key}`}>{key} (%)</Label>
                            <Input
                                id={`tax-override-${key}`}
                                type="text"
                                inputMode="decimal"
                                disabled={disabled || isManagedCustomLocked}
                                placeholder={defaultText !== null ? `Empresa: ${defaultText}` : "Sin valor"}
                                value={text}
                                onChange={(e) => handleChange(key, e.target.value)}
                                aria-invalid={invalid}
                            />
                            {invalid ? (
                                <p className="text-xs text-destructive">Introduce un valor entre 0 y 100.</p>
                            ) : (
                                <p className="text-xs text-muted-foreground">
                                    {isManagedCustomLocked
                                        ? "Impuesto propio conservado (no editable en modo gestionado)."
                                        : isExtra
                                          ? "Impuesto propio de este usuario (no existe en la empresa)."
                                          : `Vacio para usar el valor de la empresa (${defaultText}%).`}
                                </p>
                            )}
                        </div>
                    );
                })}
            </div>

            <div className="space-y-1 pt-1">
                <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Suma efectiva de impuestos</span>
                    <span className={exceedsLimit ? "font-semibold text-destructive" : "font-medium"}>
                        {effectivePercent}%
                    </span>
                </div>
                {exceedsLimit && (
                    <p className="text-xs text-destructive" role="alert">
                        La suma efectiva de impuestos supera el 100% (maximo 100%).
                    </p>
                )}
            </div>
        </div>
    );
}
