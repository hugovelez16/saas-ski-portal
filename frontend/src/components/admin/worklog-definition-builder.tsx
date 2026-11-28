"use client";

import * as React from "react";
import { useState } from "react";
import { AlertTriangle, Plus, Save, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { WorklogDefinitionUsage } from "@/lib/api/v2/types";

interface WorklogDefinitionItem {
    key: string;
    isNew?: boolean;
    data: {
        label: string;
        unit: "hours" | "days" | "fixed";
        options: string[];
        is_active: boolean;
    };
}

interface WorklogDefinitionBuilderProps {
    initialValue: Record<string, any>;
    usage?: Record<string, WorklogDefinitionUsage>;
    onSave: (value: Record<string, any>) => void;
}

function toItems(initialValue: Record<string, any>): WorklogDefinitionItem[] {
    return Object.entries(initialValue || {}).map(([key, raw]) => {
        const def = raw && typeof raw === "object" ? raw : {};
        return {
            key,
            isNew: false,
            data: {
                label: typeof def.label === "string" ? def.label : key,
                unit: def.unit === "days" || def.unit === "fixed" ? def.unit : "hours",
                options: Array.isArray(def.options) ? def.options.filter((o: unknown) => typeof o === "string") : [],
                is_active: def.is_active !== false,
            },
        };
    });
}

function serializeItems(items: WorklogDefinitionItem[]): Record<string, any> {
    const out: Record<string, any> = {};
    items.forEach((item) => {
        const cleanKey = item.key.trim();
        if (!cleanKey) return;
        out[cleanKey] = {
            label: item.data.label.trim() || cleanKey,
            unit: item.data.unit || "hours",
            options: item.data.options || [],
            is_active: item.data.is_active !== false,
        };
    });
    return out;
}

export function WorklogDefinitionBuilder({ initialValue, usage = {}, onSave }: WorklogDefinitionBuilderProps) {
    const [types, setTypes] = useState<WorklogDefinitionItem[]>(() => toItems(initialValue));
    const [pendingDelete, setPendingDelete] = useState<{ index: number; key: string; label: string; memberRatesCount: number } | null>(null);

    const initialValueString = JSON.stringify(initialValue || {});
    React.useEffect(() => {
        setTypes(toItems(initialValue));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialValueString]);

    const handleSaveClick = () => {
        onSave(serializeItems(types));
    };

    const handleAddType = () => {
        setTypes((prev) => [
            ...prev,
            {
                key: `nuevo_turno_${prev.length + 1}`,
                isNew: true,
                data: { label: "Nuevo Turno", unit: "hours", options: [], is_active: true },
            },
        ]);
    };

    const handleRequestDelete = (index: number, item: WorklogDefinitionItem) => {
        if (item.isNew) {
            setTypes((prev) => prev.filter((_, i) => i !== index));
            return;
        }
        const info = usage[item.key];
        if (info && info.work_logs_count > 0) {
            return;
        }
        setPendingDelete({
            index,
            key: item.key,
            label: item.data.label || item.key,
            memberRatesCount: info?.member_rates_count ?? 0,
        });
    };

    const handleConfirmDelete = () => {
        if (!pendingDelete) return;
        const nextTypes = types.filter((_, i) => i !== pendingDelete.index);
        setTypes(nextTypes);
        setPendingDelete(null);
        onSave(serializeItems(nextTypes));
    };

    const handleKeyChange = (index: number, newKey: string) => {
        setTypes((prev) => prev.map((t, i) => (i === index ? { ...t, key: newKey } : t)));
    };

    const handleDataChange = (index: number, field: keyof WorklogDefinitionItem["data"], value: any) => {
        setTypes((prev) =>
            prev.map((t, i) => (i === index ? { ...t, data: { ...t.data, [field]: value } } : t)),
        );
    };

    const handleAddOption = (index: number, val: string) => {
        const clean = val.trim();
        if (!clean) return;
        setTypes((prev) => {
            const currentItem = prev[index];
            const currentArray = currentItem.data.options || [];
            if (currentArray.includes(clean)) return prev;
            return prev.map((t, i) =>
                i === index ? { ...t, data: { ...t.data, options: [...currentArray, clean] } } : t,
            );
        });
    };

    const handleRemoveOption = (index: number, itemToRemove: string) => {
        setTypes((prev) =>
            prev.map((t, i) =>
                i === index
                    ? {
                          ...t,
                          data: {
                              ...t.data,
                              options: (t.data.options || []).filter((item) => item !== itemToRemove),
                          },
                      }
                    : t,
            ),
        );
    };

    return (
        <div className="space-y-4">
            {types.length === 0 && (
                <div className="text-center p-8 border border-dashed rounded-lg bg-slate-50 dark:bg-slate-900/20">
                    <p className="text-muted-foreground mb-4">
                        No hay tipos de turno definidos. Los trabajadores no podrán crear partes.
                    </p>
                </div>
            )}

            {types.map((typeObj, index) => {
                const info = usage[typeObj.key];
                const workLogsCount = info?.work_logs_count ?? 0;
                const canDelete = typeObj.isNew || workLogsCount === 0;
                const isActive = typeObj.data.is_active !== false;

                return (
                    <Card
                        key={typeObj.isNew ? `new-${index}` : typeObj.key}
                        className={`relative border-l-4 ${isActive ? "border-l-primary" : "border-l-slate-300 opacity-80"}`}
                    >
                        <div className="absolute right-3 top-3 flex items-center gap-3">
                            <div className="flex items-center gap-2">
                                <Badge variant={isActive ? "default" : "secondary"}>
                                    {isActive ? "Activo" : "Desactivado"}
                                </Badge>
                                <Switch
                                    id={`type-active-${index}`}
                                    aria-label={`Activar o desactivar ${typeObj.data.label || typeObj.key}`}
                                    checked={isActive}
                                    onCheckedChange={(checked) => handleDataChange(index, "is_active", checked)}
                                />
                            </div>
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                aria-label={`Eliminar tipo ${typeObj.data.label || typeObj.key}`}
                                disabled={!canDelete}
                                title={
                                    canDelete
                                        ? "Eliminar tipo de turno"
                                        : `No se puede borrar: tiene ${workLogsCount} turno(s) registrado(s)`
                                }
                                className="text-destructive hover:text-destructive hover:bg-destructive/10 disabled:opacity-40"
                                onClick={() => handleRequestDelete(index, typeObj)}
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>

                        <CardHeader className="pb-3 pr-44">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <Label htmlFor={`type-key-${index}`} className="text-xs text-muted-foreground">
                                        Clave interna (inmutable tras guardar)
                                    </Label>
                                    <Input
                                        id={`type-key-${index}`}
                                        value={typeObj.key}
                                        disabled={!typeObj.isNew}
                                        onChange={(e) =>
                                            handleKeyChange(
                                                index,
                                                e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""),
                                            )
                                        }
                                        className="font-mono text-sm h-8"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label htmlFor={`type-label-${index}`} className="text-xs text-muted-foreground">
                                        Nombre / Etiqueta visible
                                    </Label>
                                    <Input
                                        id={`type-label-${index}`}
                                        value={typeObj.data.label || ""}
                                        onChange={(e) => handleDataChange(index, "label", e.target.value)}
                                        className="font-medium h-8"
                                    />
                                </div>
                            </div>
                            {!typeObj.isNew && workLogsCount > 0 && (
                                <p className="text-xs text-muted-foreground pt-1">
                                    Tiene {workLogsCount} turno(s) registrado(s): solo se puede desactivar, no borrar.
                                </p>
                            )}
                        </CardHeader>

                        <CardContent className="space-y-4 pt-0">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-100 dark:bg-slate-800 p-3 rounded-md">
                                <div className="space-y-2">
                                    <Label className="text-sm font-semibold">Modo de Cálculo / Unidad</Label>
                                    <Select
                                        value={typeObj.data.unit || "hours"}
                                        onValueChange={(val) => handleDataChange(index, "unit", val)}
                                    >
                                        <SelectTrigger className="h-9 bg-white dark:bg-slate-950">
                                            <SelectValue placeholder="Seleccionar modo" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="hours">Por Horas (Requiere Hora Inicio/Fin)</SelectItem>
                                            <SelectItem value="days">Por Días (Requiere Rango de Fechas)</SelectItem>
                                            <SelectItem value="fixed">Precio Fijo (Solo Fecha, sin horas)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="flex flex-col justify-end">
                                    <p className="text-[11px] text-muted-foreground pb-1">
                                        {typeObj.data.unit === "fixed"
                                            ? "El trabajador solo elige el día. Se cobra la tarifa base directamente."
                                            : typeObj.data.unit === "days"
                                              ? "Ideal para cursillos o viajes de varios días."
                                              : "Ideal para clases particulares o turnos sueltos."}
                                    </p>
                                </div>
                            </div>

                            {/* Opciones Extra (pluses) */}
                            <div className="space-y-3">
                                <Label className="flex items-center text-sm font-semibold border-b pb-1">
                                    Opciones Extra (Pluses)
                                </Label>
                                <div className="space-y-2">
                                    <div className="flex flex-wrap gap-2 mb-2">
                                        {(typeObj.data.options || []).map((opt) => (
                                            <span
                                                key={opt}
                                                className="inline-flex items-center gap-1 px-2 py-1 bg-secondary text-secondary-foreground text-xs rounded-full"
                                            >
                                                {opt}
                                                <button
                                                    type="button"
                                                    onClick={() => handleRemoveOption(index, opt)}
                                                    className="hover:text-foreground/50"
                                                    aria-label={`Quitar opcion ${opt}`}
                                                >
                                                    &times;
                                                </button>
                                            </span>
                                        ))}
                                    </div>
                                    <div className="flex gap-2">
                                        <Input
                                            id={`input-opts-${index}`}
                                            placeholder="Ej: Nocturnidad"
                                            className="h-8 text-sm"
                                            onKeyDown={(e) => {
                                                if (e.key === "Enter") {
                                                    e.preventDefault();
                                                    handleAddOption(index, e.currentTarget.value);
                                                    e.currentTarget.value = "";
                                                }
                                            }}
                                        />
                                        <Button
                                            type="button"
                                            size="sm"
                                            variant="secondary"
                                            className="h-8"
                                            onClick={() => {
                                                const input = document.getElementById(
                                                    `input-opts-${index}`,
                                                ) as HTMLInputElement | null;
                                                if (!input) return;
                                                handleAddOption(index, input.value);
                                                input.value = "";
                                            }}
                                        >
                                            <Plus className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                );
            })}

            <div className="flex gap-4">
                <Button type="button" onClick={handleAddType} variant="outline" className="w-full border-dashed">
                    <Plus className="mr-2 h-4 w-4" /> Añadir Tipo de Turno
                </Button>
                <Button type="button" onClick={handleSaveClick} className="min-w-[180px]">
                    <Save className="mr-2 h-4 w-4" /> Guardar Tipos de Turno
                </Button>
            </div>

            <Dialog open={pendingDelete !== null} onOpenChange={(open) => !open && setPendingDelete(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5 text-amber-500" />
                            Eliminar tipo de turno
                        </DialogTitle>
                        <DialogDescription>
                            Vas a eliminar permanentemente el tipo de turno <strong>{pendingDelete?.label}</strong>.
                            {pendingDelete && pendingDelete.memberRatesCount > 0
                                ? ` Tiene tarifas asociadas en ${pendingDelete.memberRatesCount} miembro(s) que tambien se eliminaran de forma definitiva.`
                                : " Si tiene tarifas asociadas en algun miembro, se eliminaran tambien junto con el."}
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => setPendingDelete(null)}>
                            Cancelar
                        </Button>
                        <Button type="button" variant="destructive" onClick={handleConfirmDelete}>
                            Eliminar y limpiar tarifas
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
