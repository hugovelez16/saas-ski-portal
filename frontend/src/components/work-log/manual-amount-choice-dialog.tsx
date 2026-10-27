"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

export interface ManualAmountChoiceDialogProps {
    open: boolean;
    /** Mensaje del backend (409 manual_amount_choice). */
    message: string;
    /** Solo manager y platform admin pueden recalcular por tarifa. */
    canRecalculate: boolean;
    onKeep: () => void;
    onRecalculate: () => void;
    onCancel: () => void;
}

/**
 * Pregunta cómo resolver la edicion de un turno con importe manual:
 * conservar el importe actual o recalcularlo con las tarifas vigentes.
 */
export function ManualAmountChoiceDialog({
    open,
    message,
    canRecalculate,
    onKeep,
    onRecalculate,
    onCancel,
}: ManualAmountChoiceDialogProps) {
    return (
        <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onCancel(); }}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Importe manual</DialogTitle>
                    <DialogDescription>{message}</DialogDescription>
                </DialogHeader>
                <DialogFooter>
                    <Button variant="ghost" onClick={onCancel}>
                        Cancelar
                    </Button>
                    {canRecalculate && (
                        <Button variant="outline" onClick={onRecalculate}>
                            Calcular por tarifa
                        </Button>
                    )}
                    <Button onClick={onKeep}>Conservar importe</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
