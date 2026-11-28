"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Button } from "@/components/ui/button";
import { MousePointer2, Timer, Layers } from "lucide-react";

interface WorkerUXBuilderProps {
    initialValue: any;
    onSave: (val: any) => void;
}

export function WorkerUXBuilder({ initialValue, onSave }: WorkerUXBuilderProps) {
    const [ux, setUx] = useState({
        input_mode: initialValue?.worker_experience?.input_mode,
    });

    useEffect(() => {
        setUx({
            input_mode: initialValue?.worker_experience?.input_mode,
        });
    }, [JSON.stringify(initialValue?.worker_experience || {})]);

    const handleSave = () => {
        onSave({
            ...initialValue,
            worker_experience: ux,
        });
    };

    return (
        <div className="space-y-6">
            {/* Input Mode */}
            <div className="max-w-md space-y-3">
                    <Label className="text-sm font-bold">Modo de Entrada de Datos</Label>
                    <p className="text-xs text-muted-foreground mb-3">
                        Define cómo el trabajador introduce sus jornadas.
                    </p>
                    <RadioGroup
                        value={ux.input_mode}
                        onValueChange={(val) => setUx({ ...ux, input_mode: val })}
                        className="grid grid-cols-1 gap-2"
                    >
                        <div className="flex items-center space-x-3 p-3 rounded-lg border border-slate-200">
                            <RadioGroupItem value="manual_single" id="manual_single" />
                            <div className="flex-1">
                                <Label htmlFor="manual_single" className="flex items-center gap-2 font-semibold cursor-pointer">
                                    <MousePointer2 className="h-4 w-4 text-indigo-500" />
                                    Manual (Uno a uno)
                                </Label>
                                <p className="text-[10px] text-muted-foreground">Formulario tradicional campo a campo.</p>
                            </div>
                        </div>
                        <div className="flex items-center space-x-3 p-3 rounded-lg border border-slate-200 opacity-50 cursor-not-allowed">
                            <RadioGroupItem value="timer" id="timer" disabled />
                            <div className="flex-1">
                                <Label htmlFor="timer" className="flex items-center gap-2 font-semibold">
                                    <Timer className="h-4 w-4 text-slate-400" />
                                    Cronómetro (Próximamente)
                                </Label>
                                <p className="text-[10px] text-muted-foreground">Botón de Inicio/Fin de jornada.</p>
                            </div>
                        </div>
                        <div className="flex items-center space-x-3 p-3 rounded-lg border border-slate-200 opacity-50 cursor-not-allowed">
                            <RadioGroupItem value="bulk" id="bulk" disabled />
                            <div className="flex-1">
                                <Label htmlFor="bulk" className="flex items-center gap-2 font-semibold">
                                    <Layers className="h-4 w-4 text-slate-400" />
                                    Masivo (Próximamente)
                                </Label>
                                <p className="text-[10px] text-muted-foreground">Rellenar toda la semana de una vez.</p>
                            </div>
                        </div>
                    </RadioGroup>
                </div>

            <div className="flex justify-end">
                <Button onClick={handleSave} size="sm" className="bg-indigo-600 hover:bg-indigo-700">
                    Guardar Preferencias de Trabajador
                </Button>
            </div>
        </div>
    );
}
