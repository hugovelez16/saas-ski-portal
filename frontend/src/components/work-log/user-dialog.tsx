"use client";

import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogClose
} from "@/components/ui/dialog";
import { PlusCircle, Loader2, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useQuery } from "@tanstack/react-query";
import { getMyCompanies } from "@/lib/api/companies";
import type { WorkLog, WorkLogCreate, WorkLogRecalculatePreview } from "@/lib/types";
import { WorkLogForm } from "./work-log-form";
import { createWorkLog, previewWorkLogRecalculation, updateWorkLog } from "@/lib/api/work-logs";
import { notifyWorkLogWarnings } from "@/lib/work-log-warnings";
import { RecalculateConfirmDialog } from "./recalculate-confirm-dialog";
import { useAuth } from "@/context/AuthContext";

/**
 * Convierte `detail` de una respuesta de error de FastAPI (string, lista de `{ msg }` o objeto)
 * en un texto para el usuario. Devuelve null si no hay nada que mostrar.
 */
function extractDetailMessage(detail: unknown): string | null {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((d: any) => (typeof d === 'string' ? d : d?.msg ?? JSON.stringify(d)))
            .join(", ");
    }
    if (detail && typeof detail === 'object') {
        const message = (detail as { message?: unknown }).message;
        return typeof message === 'string' ? message : JSON.stringify(detail);
    }
    return null;
}

interface UserCreateWorkLogDialogProps {
    user: { id: string; firstName?: string | null; lastName?: string | null; activeCompanyId?: string | null };
    onLogUpdate?: () => void;
    children?: React.ReactNode;
    logToEdit?: WorkLog | null;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    initialDate?: Date | null;
    companies?: any[];
    applyToGroup?: boolean;
}

export function UserCreateWorkLogDialog({
    user,
    onLogUpdate,
    children,
    logToEdit,

    open: controlledOpen,
    onOpenChange,
    companies: providedCompanies,
    initialDate,
    applyToGroup: initialApplyToGroup = false
}: UserCreateWorkLogDialogProps) {
    const [internalOpen, setInternalOpen] = useState(false);
    const isControlled = controlledOpen !== undefined;
    const open = isControlled ? controlledOpen : internalOpen;
    const setOpen = isControlled ? onOpenChange! : setInternalOpen;

    const [isLoading, setIsLoading] = useState(false);
    const [logType, setLogType] = useState<string>('particular');
    const [formData, setFormData] = useState<Partial<WorkLogCreate>>({
        extraData: { datos: {}, opciones: {} },
    });

    const [lastSelectedCompanyId, setLastSelectedCompanyId] = useState<string | null>(null);

    const { toast } = useToast();
    const { user: authUser } = useAuth();

    // Fetch companies
    // Fetch companies if not provided
    const { data: fetchedCompanies = [] } = useQuery({
        queryFn: getMyCompanies,
        queryKey: ["myCompanies"],
        enabled: !providedCompanies,
    });

    const companies = providedCompanies || fetchedCompanies;

    // Rol del usuario que opera en la empresa del turno. No se usa `companies` (en la ficha de
    // usuario contiene los roles del titular). Sin dato, no se ofrece recalcular.
    const { data: myCompanies = [] } = useQuery({
        queryFn: getMyCompanies,
        queryKey: ["myCompanies"],
        enabled: Boolean(logToEdit),
    });
    const turnCompanyRole = myCompanies.find((c) => c.id === logToEdit?.companyId)?.role;
    const canRecalculate = Boolean(
        authUser?.isPlatformAdmin || authUser?.role === 'admin' || turnCompanyRole === 'manager'
    );

    // Confirmacion previa con comparativa de importes al cambiar de tipo o recalcular (R-TUR-20, R-TUR-21)
    const [pendingConfirm, setPendingConfirm] = useState<{
        mode: 'recalculate' | 'type_change';
        preview: WorkLogRecalculatePreview;
        body: any;
        recalculateWithCurrentRates: boolean;
    } | null>(null);
    const [isPreviewLoading, setIsPreviewLoading] = useState(false);

    // Reset form
    const resetForm = () => {
        setFormData({ 
            extraData: { datos: {}, opciones: {} } 
        });
        setLogType('particular');
    };

    // Set default company
    useEffect(() => {
        if (open && companies.length > 0 && !formData.companyId && !logToEdit) {
            // Priority: Active Context > Last Selected > User Default > Personal > First Available
            let targetId = user?.activeCompanyId || lastSelectedCompanyId;

            if (!targetId) {
                const personal = companies.find((c: any) => c.name === "Personal");
                targetId = personal ? personal.id : companies[0].id;
            }

            setFormData(prev => ({ ...prev, companyId: targetId || undefined }));
        }
    }, [open, companies, formData.companyId, logToEdit, lastSelectedCompanyId, user?.activeCompanyId]);

    // Initialize Form Data when entering Edit Mode
    useEffect(() => {
        if (open) {
            if (logToEdit) {
                setLogType(logToEdit.type as 'particular' | 'tutorial');
                setFormData({
                    companyId: logToEdit.companyId,
                    date: logToEdit.date,
                    startTime: logToEdit.startTime,
                    endTime: logToEdit.endTime,
                    startDate: logToEdit.startDate,
                    endDate: logToEdit.endDate,
                    description: logToEdit.description,
                    extraData: logToEdit.extraData || { datos: {}, opciones: {} },
                });
            } else {
                // If opening in Create mode (and uncontrolled), reset.
                // If controlled (from parent), parent might handle reset, but we ensure consistency.
                if (!isControlled) {
                    resetForm();
                }

                if (initialDate) {
                    // Keep format YYYY-MM-DD
                    const isoDate = initialDate.toISOString().split('T')[0];
                    setFormData(prev => ({ ...prev, date: isoDate, startDate: isoDate, endDate: isoDate }));
                }
            }
        }
    }, [open, logToEdit, isControlled, initialDate]);

    const showSaveError = (error: any) => {
        console.error("Error saving work log:", error);
        let msg = "No se pudo guardar el turno.";
        const detailMsg = extractDetailMessage(error.response?.data?.detail);

        if (detailMsg) {
            msg = detailMsg;
        } else if (error.message) {
            msg = error.message;
        }

        // Check if it's a rate/pricing related validation error and make it friendly
        const lowercaseMsg = msg.toLowerCase();
        if (lowercaseMsg.includes("precio") || lowercaseMsg.includes("rate") || lowercaseMsg.includes("tarifa")) {
            msg = "No se puede guardar: El usuario no tiene tarifas configuradas para este tipo de turno. Por favor, configura sus tarifas primero.";
        }

        toast({ title: "Error", description: String(msg), variant: "destructive" });
    };

    const buildValidatedPayload = (): any | null => {
        if (!formData.companyId) {
            toast({ title: "Error", description: "Selecciona una empresa.", variant: "destructive" });
            return null;
        }

        const selectedCompany = companies.find((c: any) => c.id === formData.companyId);
        const currentDef = selectedCompany?.worklogDefinitions?.[logType] || null;
        const isRange = currentDef ? currentDef.unit === 'days' : logType === 'tutorial';
        const isFixed = currentDef?.unit === 'fixed';

        if (isRange) {
            if (!formData.startDate || !formData.endDate) {
                toast({ title: "Error", description: "Fecha de inicio y fin son obligatorias.", variant: "destructive" });
                return null;
            }
        } else {
            if (!formData.date) {
                toast({ title: "Error", description: "La fecha es obligatoria.", variant: "destructive" });
                return null;
            }
            if (!isFixed && (!formData.startTime || !formData.endTime)) {
                toast({ title: "Error", description: "Fecha, hora de inicio y fin son obligatorias.", variant: "destructive" });
                return null;
            }
        }

        // En edicion el titular del turno es el dueno original: el backend rechaza cambiarlo (422)
        const logData: any = {
            ...formData,
            userId: logToEdit ? logToEdit.userId : user.id,
            type: logType,
        };

        if (!isRange) {
            logData.startDate = logData.date;
            logData.endDate = logData.date;
        }

        if (logData.startTime === "") logData.startTime = null;
        if (logData.endTime === "") logData.endTime = null;

        delete logData.date;

        if (logToEdit) {
            delete logData.amount;
            delete logData.rateApplied;
            delete logData.grossAmount;
            delete logData.netAmount;
            delete logData.isGrossCalculation;
        }

        return logData;
    };

    const persistUpdate = async (body: any, recalculateWithCurrentRates: boolean) => {
        if (!logToEdit) return;
        setIsLoading(true);
        try {
            const savedLog = await updateWorkLog(logToEdit.id, body, initialApplyToGroup, {
                recalculateWithCurrentRates,
            });
            toast({ title: "Éxito", description: "Turno actualizado correctamente." });
            notifyWorkLogWarnings(toast, savedLog);
            setPendingConfirm(null);
            setOpen(false);
            onLogUpdate?.();
        } catch (error: any) {
            showSaveError(error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleRequestRecalculate = async () => {
        if (!logToEdit) return;
        const logData = buildValidatedPayload();
        if (!logData) return;

        setIsPreviewLoading(true);
        try {
            const preview = await previewWorkLogRecalculation(logToEdit.id, logData, initialApplyToGroup, {
                recalculateWithCurrentRates: true,
            });
            setPendingConfirm({
                mode: 'recalculate',
                preview,
                body: logData,
                recalculateWithCurrentRates: true,
            });
        } catch (error: any) {
            showSaveError(error);
        } finally {
            setIsPreviewLoading(false);
        }
    };

    const handleSubmit = async () => {
        const logData = buildValidatedPayload();
        if (!logData) return;

        if (logToEdit) {
            if (logType !== logToEdit.type) {
                setIsPreviewLoading(true);
                try {
                    const preview = await previewWorkLogRecalculation(logToEdit.id, logData, initialApplyToGroup, {
                        recalculateWithCurrentRates: false,
                    });
                    setPendingConfirm({
                        mode: 'type_change',
                        preview,
                        body: logData,
                        recalculateWithCurrentRates: false,
                    });
                } catch (error: any) {
                    showSaveError(error);
                } finally {
                    setIsPreviewLoading(false);
                }
                return;
            }
            await persistUpdate(logData, false);
            return;
        }

        setIsLoading(true);
        try {
            const savedLog = await createWorkLog(logData);
            toast({ title: "Éxito", description: "Turno creado correctamente." });
            notifyWorkLogWarnings(toast, savedLog);
            setOpen(false);
            if (logData.companyId) setLastSelectedCompanyId(logData.companyId);
            resetForm();
            onLogUpdate?.();
        } catch (error: any) {
            showSaveError(error);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <>
        <Dialog open={open} onOpenChange={(isOpen) => {
            setOpen(isOpen);
            if (!isOpen && !logToEdit) resetForm();
        }}>
            <DialogTrigger asChild>
                {children ?? (
                    <Button>
                        <PlusCircle className="mr-2 h-4 w-4" />
                        Add Work Log
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{logToEdit ? "Edit Work Log" : "Add Work Log"}</DialogTitle>
                    <DialogDescription>
                        {logToEdit
                            ? "Modify the details of this work log."
                            : user.firstName
                                ? `Add a new work log for ${user.firstName} ${user.lastName || ''}.`
                                : "Add a new work log to your history."}
                    </DialogDescription>
                    {/* Shared Form */}
                    <WorkLogForm
                        formData={formData}
                        setFormData={setFormData}
                        logType={logType}
                        setLogType={setLogType}
                        companies={companies || []}
                    />
                </DialogHeader>

                <DialogFooter className="gap-2 sm:gap-2">
                    {logToEdit && canRecalculate && (
                        <Button
                            type="button"
                            variant="outline"
                            className="sm:mr-auto"
                            disabled={isLoading || isPreviewLoading}
                            onClick={handleRequestRecalculate}
                        >
                            {isPreviewLoading ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <RefreshCw className="mr-2 h-4 w-4" />
                            )}
                            Recalcular con tarifa vigente
                        </Button>
                    )}
                    <DialogClose asChild>
                        <Button variant="ghost">Cancelar</Button>
                    </DialogClose>
                    <Button type="submit" disabled={isLoading || isPreviewLoading} onClick={handleSubmit}>
                        {(isLoading || isPreviewLoading) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {logToEdit ? "Actualizar" : "Crear"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
        <RecalculateConfirmDialog
            open={pendingConfirm !== null}
            preview={pendingConfirm?.preview ?? null}
            mode={pendingConfirm?.mode ?? 'recalculate'}
            isSubmitting={isLoading}
            onConfirm={() =>
                pendingConfirm && persistUpdate(pendingConfirm.body, pendingConfirm.recalculateWithCurrentRates)
            }
            onCancel={() => setPendingConfirm(null)}
        />
        </>
    )
}
