"use client";

import * as React from "react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Trash2, Plus, Save } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
interface WorklogDefinitionBuilderProps {
    initialValue: Record<string, any>;
    onSave: (value: Record<string, any>) => void;
}

export function WorklogDefinitionBuilder({ initialValue, onSave }: WorklogDefinitionBuilderProps) {
    const [types, setTypes] = useState<{ key: string, data: any }[]>(() => {
        return Object.entries(initialValue || {}).map(([key, data]) => ({ key, data }));
    });

    const initialValueString = JSON.stringify(initialValue || {});
    React.useEffect(() => {
        setTypes(Object.entries(initialValue || {}).map(([key, data]) => ({ key, data })));
    }, [initialValueString]);

    const handleSaveClick = () => {
        const newObj: Record<string, any> = {};
        types.forEach(t => {
            if (t.key.trim() !== "") {
                // Se descarta cualquier is_range heredado: el contrato solo usa unit.
                const { is_range: _legacyIsRange, ...rest } = t.data;
                newObj[t.key] = { ...rest, unit: rest.unit || "hours" };
            }
        });
        onSave(newObj);
    };

    const handleAddType = () => {
        setTypes(prev => [...prev, {
            key: `nuevo_turno_${prev.length + 1}`,
            data: { label: "Nuevo Turno", unit: "hours", fields: [], options: [] }
        }]);
    };

    const handleRemoveType = (index: number) => {
        setTypes(prev => prev.filter((_, i) => i !== index));
    };

    const handleKeyChange = (index: number, newKey: string) => {
        setTypes(prev => prev.map((t, i) => i === index ? { ...t, key: newKey } : t));
    };

    const handleDataChange = (index: number, field: string, value: any) => {
        setTypes(prev => prev.map((t, i) => i === index ? { ...t, data: { ...t.data, [field]: value } } : t));
    };

    const handleAddArrayItem = (index: number, arrayName: 'fields' | 'options', val: string) => {
        if (!val.trim()) return;
        setTypes(prev => {
            const currentItem = prev[index];
            const currentArray = currentItem.data[arrayName] || [];
            if (!currentArray.includes(val.trim())) {
                return prev.map((t, i) => i === index ? {
                    ...t,
                    data: { ...t.data, [arrayName]: [...currentArray, val.trim()] }
                } : t);
            }
            return prev;
        });
    };

    const handleRemoveArrayItem = (index: number, arrayName: 'fields' | 'options', itemToRemove: string) => {
        setTypes(prev => prev.map((t, i) => i === index ? {
            ...t,
            data: {
                ...t.data,
                [arrayName]: (t.data[arrayName] || []).filter((item: string) => item !== itemToRemove)
            }
        } : t));
    };

    return (
        <div className="space-y-4">
            {types.length === 0 && (
                <div className="text-center p-8 border border-dashed rounded-lg bg-slate-50 dark:bg-slate-900/20">
                    <p className="text-muted-foreground mb-4">No hay turnos definidos. Los trabajadores no podrán crear partes.</p>
                </div>
            )}

            {types.map((typeObj, index) => (
                <Card key={index} className="relative border-l-4 border-l-primary">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-2 top-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => handleRemoveType(index)}
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>

                    <CardHeader className="pb-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <Label className="text-xs text-muted-foreground">ID Interno (Sin espacios)</Label>
                                <Input
                                    value={typeObj.key}
                                    onChange={(e) => handleKeyChange(index, e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                                    className="font-mono text-sm h-8"
                                />
                            </div>
                            <div className="space-y-1">
                                <Label className="text-xs text-muted-foreground">Nombre / Etiqueta Visible</Label>
                                <Input
                                    value={typeObj.data.label || ''}
                                    onChange={(e) => handleDataChange(index, 'label', e.target.value)}
                                    className="font-medium h-8"
                                />
                            </div>
                        </div>
                    </CardHeader>

                    <CardContent className="space-y-6 pt-0">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-100 dark:bg-slate-800 p-3 rounded-md">
                            <div className="space-y-2">
                                <Label className="text-sm font-semibold">Modo de Cálculo / Unidad</Label>
                                <Select 
                                    value={typeObj.data.unit || "hours"}
                                    onValueChange={(val) => handleDataChange(index, 'unit', val)}
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
                                    {typeObj.data.unit === 'fixed' 
                                        ? 'El trabajador solo elige el día. Se cobra la tarifa base directamente.' 
                                        : typeObj.data.unit === 'days'
                                            ? 'Ideal para cursillos o viajes de varios días.'
                                            : 'Ideal para clases particulares o turnos sueltos.'}
                                </p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Fields Selection */}
                            <div className="space-y-3">
                                <Label className="flex items-center text-sm font-semibold border-b pb-1">
                                    Campos a solicitar
                                </Label>
                                <div className="space-y-2">
                                    <div className="flex flex-wrap gap-2 mb-2">
                                        {(typeObj.data.fields || []).map((field: string) => (
                                            <span key={field} className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary text-xs rounded-full">
                                                {field}
                                                <button onClick={() => handleRemoveArrayItem(index, 'fields', field)} className="text-primary hover:text-foreground">
                                                    &times;
                                                </button>
                                            </span>
                                        ))}
                                    </div>
                                    <div className="flex gap-2">
                                        <Input
                                            id={`input-fields-${index}`}
                                            placeholder="Ej: Punto de recogida"
                                            className="h-8 text-sm"
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') {
                                                    e.preventDefault();
                                                    handleAddArrayItem(index, 'fields', e.currentTarget.value);
                                                    e.currentTarget.value = '';
                                                }
                                            }}
                                        />
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            className="h-8"
                                            onClick={(e) => {
                                                const input = document.getElementById(`input-fields-${index}`) as HTMLInputElement;
                                                handleAddArrayItem(index, 'fields', input.value);
                                                input.value = '';
                                            }}
                                        >
                                            <Plus className="h-4 w-4" />
                                        </Button>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground">Escribe el campo y pulsa Enter.</p>
                                </div>
                            </div>
 
                             {/* Options Selection */}
                             <div className="space-y-3">
                                 <Label className="flex items-center text-sm font-semibold border-b pb-1">
                                     Opciones Extra
                                 </Label>
                                 <div className="space-y-2">
                                     <div className="flex flex-wrap gap-2 mb-2">
                                         {(typeObj.data.options || []).map((opt: string) => (
                                             <span key={opt} className="inline-flex items-center gap-1 px-2 py-1 bg-secondary text-secondary-foreground text-xs rounded-full">
                                                 {opt}
                                                 <button onClick={() => handleRemoveArrayItem(index, 'options', opt)} className="hover:text-foreground/50">
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
                                                if (e.key === 'Enter') {
                                                    e.preventDefault();
                                                    handleAddArrayItem(index, 'options', e.currentTarget.value);
                                                    e.currentTarget.value = '';
                                                }
                                            }}
                                        />
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            className="h-8"
                                            onClick={(e) => {
                                                const input = document.getElementById(`input-opts-${index}`) as HTMLInputElement;
                                                handleAddArrayItem(index, 'options', input.value);
                                                input.value = '';
                                            }}
                                        >
                                            <Plus className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            ))}

            <div className="flex gap-4">
                <Button onClick={handleAddType} variant="outline" className="w-full border-dashed">
                    <Plus className="mr-2 h-4 w-4" /> Añadir Tipo de Turno
                </Button>
                <Button onClick={handleSaveClick} className="min-w-[150px]">
                    <Save className="mr-2 h-4 w-4" /> Guardar JSON
                </Button>
            </div>
        </div>
    );
}
