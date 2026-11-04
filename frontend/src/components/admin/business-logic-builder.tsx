"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Button } from "@/components/ui/button";

interface BusinessLogicBuilderProps {
    initialValue: any;
    onSave: (val: any) => void;
}

export function BusinessLogicBuilder({ initialValue, onSave }: BusinessLogicBuilderProps) {
    const [logic, setLogic] = useState({
        price_type: initialValue?.business_logic?.price_type,
    });

    useEffect(() => {
        setLogic({
            price_type: initialValue?.business_logic?.price_type,
        });
    }, [JSON.stringify(initialValue?.business_logic || {})]);

    const handleSave = () => {
        onSave({
            ...initialValue,
            business_logic: logic,
        });
    };

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Price Type */}
                <div className="space-y-3">
                    <Label className="text-sm font-bold">Tipo de Base de Precios</Label>
                    <p className="text-xs text-muted-foreground mb-3">
                        Determina si los precios introducidos se consideran Netos (antes de impuestos) o Brutos.
                    </p>
                    <RadioGroup
                        value={logic.price_type}
                        onValueChange={(val) => setLogic({ ...logic, price_type: val })}
                        className="grid grid-cols-2 gap-4"
                    >
                        <div>
                            <RadioGroupItem value="net" id="net" className="peer sr-only" />
                            <Label
                                htmlFor="net"
                                className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-indigo-600 [&:has([data-state=checked])]:border-indigo-600"
                            >
                                <span className="text-sm font-semibold">Neto</span>
                                <span className="text-[10px] text-muted-foreground mt-1">Imuestos aparte</span>
                            </Label>
                        </div>
                        <div>
                            <RadioGroupItem value="gross" id="gross" className="peer sr-only" />
                            <Label
                                htmlFor="gross"
                                className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-indigo-600 [&:has([data-state=checked])]:border-indigo-600"
                            >
                                <span className="text-sm font-semibold">Bruto</span>
                                <span className="text-[10px] text-muted-foreground mt-1">Impuestos incluidos</span>
                            </Label>
                        </div>
                    </RadioGroup>
                </div>

            </div>

            <div className="flex justify-end">
                <Button onClick={handleSave} size="sm" className="bg-indigo-600 hover:bg-indigo-700">
                    Guardar Configuración Económica
                </Button>
            </div>
        </div>
    );
}
