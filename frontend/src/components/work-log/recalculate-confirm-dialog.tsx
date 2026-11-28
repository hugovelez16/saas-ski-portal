"use client";

import React from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import type { WorkLogRecalculatePreview } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

export interface RecalculateConfirmDialogProps {
    open: boolean;
    preview: WorkLogRecalculatePreview | null;
    mode: "recalculate" | "type_change";
    isSubmitting?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}

/**
 * Aviso comparativo antes de guardar cuando cambia el tipo del turno o se recalcula
 * con las tarifas vigentes (R-TUR-20, R-TUR-21).
 */
export function RecalculateConfirmDialog({
    open,
    preview,
    mode,
    isSubmitting = false,
    onConfirm,
    onCancel,
}: RecalculateConfirmDialogProps) {
    if (!preview) return null;

    const isGroup = preview.applyToGroup && preview.groupCount > 1;
    const title = mode === "recalculate" ? "Recalcular con tarifa vigente" : "Confirmar cambio de tipo";
    const description =
        mode === "recalculate"
            ? "Se recalculará el turno usando la tarifa, definición e impuestos vigentes."
            : "Al cambiar el tipo de turno se recalculará el importe con la tarifa vigente.";

    return (
        <Dialog open={open} onOpenChange={(isOpen) => !isOpen && !isSubmitting && onCancel()}>
            <DialogContent className="sm:max-w-[460px]">
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>{description}</DialogDescription>
                </DialogHeader>

                <div className="space-y-3 py-2 text-sm">
                    <div className="grid grid-cols-2 gap-3 rounded-md border bg-slate-50 p-3 dark:bg-slate-900/50">
                        <div>
                            <p className="text-xs font-medium text-muted-foreground">Importe actual</p>
                            <p className="text-base font-semibold">{formatCurrency(preview.currentNetAmount)} neto</p>
                            <p className="text-xs text-muted-foreground">
                                {formatCurrency(preview.currentGrossAmount)} bruto
                            </p>
                        </div>
                        <div>
                            <p className="text-xs font-medium text-muted-foreground">Nuevo importe</p>
                            <p className="text-base font-semibold text-indigo-600 dark:text-indigo-400">
                                {formatCurrency(preview.newNetAmount)} neto
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {formatCurrency(preview.newGrossAmount)} bruto
                            </p>
                        </div>
                    </div>

                    {isGroup &&
                        preview.currentGroupNetAmount != null &&
                        preview.newGroupNetAmount != null && (
                            <div className="grid grid-cols-2 gap-3 rounded-md border p-3">
                                <div>
                                    <p className="text-xs font-medium text-muted-foreground">
                                        Grupo actual ({preview.groupCount} turnos)
                                    </p>
                                    <p className="font-semibold">{formatCurrency(preview.currentGroupNetAmount)} neto</p>
                                    {preview.currentGroupGrossAmount != null && (
                                        <p className="text-xs text-muted-foreground">
                                            {formatCurrency(preview.currentGroupGrossAmount)} bruto
                                        </p>
                                    )}
                                </div>
                                <div>
                                    <p className="text-xs font-medium text-muted-foreground">
                                        Nuevo total del grupo
                                    </p>
                                    <p className="font-semibold text-indigo-600 dark:text-indigo-400">
                                        {formatCurrency(preview.newGroupNetAmount)} neto
                                    </p>
                                    {preview.newGroupGrossAmount != null && (
                                        <p className="text-xs text-muted-foreground">
                                            {formatCurrency(preview.newGroupGrossAmount)} bruto
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}
                </div>

                <DialogFooter className="gap-2 sm:gap-2">
                    <Button variant="ghost" disabled={isSubmitting} onClick={onCancel}>
                        Cancelar
                    </Button>
                    <Button disabled={isSubmitting} onClick={onConfirm}>
                        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Confirmar y guardar
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
