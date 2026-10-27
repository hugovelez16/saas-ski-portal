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
import { PlusCircle, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useQuery } from "@tanstack/react-query";
import { getMyCompanies } from "@/lib/api/companies";
import type { WorkLog, WorkLogCreate } from "@/lib/types";
import { WorkLogForm } from "./work-log-form";
import { createWorkLog, updateWorkLog } from "@/lib/api/work-logs";
import { notifyWorkLogWarnings } from "@/lib/work-log-warnings";
import { getManualAmountChoice } from "@/lib/manual-amount-choice";
import { ManualAmountChoiceDialog } from "./manual-amount-choice-dialog";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";

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

    // Edicion con importe manual pendiente de decision (409 manual_amount_choice)
    const [manualChoice, setManualChoice] = useState<{ message: string; body: any } | null>(null);

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

    // Reenvia el mismo PUT resolviendo el importe manual: conservar (keep_manual_amount) o recalcular por tarifa
    const resolveManualChoice = async (mode: 'keep' | 'recalculate') => {
        const pending = manualChoice;
        if (!pending || !logToEdit) return;

        setManualChoice(null);
        setIsLoading(true);
        try {
            const savedLog = await updateWorkLog(logToEdit.id, pending.body, initialApplyToGroup, {
                keepManualAmount: mode === 'keep',
                recalculateWithCurrentRates: mode === 'recalculate',
            });
            toast({ title: "Success", description: "Work log updated successfully." });
            notifyWorkLogWarnings(toast, savedLog);
            setOpen(false);
            onLogUpdate?.();
        } catch (error: any) {
            showSaveError(error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = async () => {
        setIsLoading(true);

        if (!formData.companyId) {
            toast({ title: "Error", description: "Selecciona una empresa.", variant: "destructive" });
            setIsLoading(false);
            return;
        }

        // Removed hardcoded client validation to support dynamic worklog definitions

        if (logType === 'particular' && (!formData.date || !formData.startTime || !formData.endTime)) {
            toast({ title: "Error", description: "Fecha, hora de inicio y fin son obligatorias para el tipo 'Particular'.", variant: "destructive" });
            setIsLoading(false);
            return;
        }
        if (logType === 'tutorial' && (!formData.startDate || !formData.endDate)) {
            toast({ title: "Error", description: "Fecha de inicio y fin son obligatorias para el tipo 'Tutorial'.", variant: "destructive" });
            setIsLoading(false);
            return;
        }

        // En edicion el titular del turno es el dueno original: el backend rechaza cambiarlo (422)
        let logData: any = {
            ...formData,
            userId: logToEdit ? logToEdit.userId : user.id,
            type: logType,
        };

        // SaaS Logic: Ensure startDate/endDate are present for all types
        // In 'particular' (single day) mode, they should match 'date'
        if (logType === 'particular' || !logData.startDate) {
            logData.startDate = logData.date;
            logData.endDate = logData.date;
        }

        // Remove redundant frontend-only fields
        delete logData.date;

        // If editing, we remove calculated fields to force backend recalculation
        // EXCEPT if the company is in manual input mode (but UserCreateWorkLogDialog doesn't easily know this, 
        // we can check if formData.amount was explicitly changed or just inherited).
        // To be safe and fix the user's issue: during EDIT, we want the backend to RECALCULATE 
        // unless the user is specifically using a manual override flow.
        if (logToEdit) {
            delete logData.amount;
            delete logData.rateApplied;
            delete logData.grossAmount;
            delete logData.isGrossCalculation; // Let backend use current user settings
        }

        try {
            if (logToEdit) {
                const savedLog = await updateWorkLog(logToEdit.id, logData, initialApplyToGroup);
                toast({ title: "Success", description: "Work log updated successfully." });
                notifyWorkLogWarnings(toast, savedLog);
            } else {
                const savedLog = await createWorkLog(logData);
                toast({ title: "Success", description: "Work log created successfully." });
                notifyWorkLogWarnings(toast, savedLog);
            }

            setOpen(false);
            if (!logToEdit) {
                // Save the company ID for next time
                if (logData.companyId) setLastSelectedCompanyId(logData.companyId);
                resetForm();
            }
            onLogUpdate?.();

        } catch (error: any) {
            const manualChoiceError = logToEdit ? getManualAmountChoice(error) : null;
            if (manualChoiceError) {
                // Sin toast: el usuario decide como resolver el importe manual
                setManualChoice({ message: manualChoiceError.message, body: logData });
                return;
            }
            showSaveError(error);
        } finally {
            setIsLoading(false);
        }
    }

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

                <DialogFooter>
                    <DialogClose asChild>
                        <Button variant="ghost">Cancel</Button>
                    </DialogClose>
                    <Button type="submit" disabled={isLoading} onClick={handleSubmit}>
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {logToEdit ? "Update" : "Create"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
        <ManualAmountChoiceDialog
            open={manualChoice !== null}
            message={manualChoice?.message ?? ""}
            canRecalculate={canRecalculate}
            onKeep={() => resolveManualChoice('keep')}
            onRecalculate={() => resolveManualChoice('recalculate')}
            onCancel={() => setManualChoice(null)}
        />
        </>
    )
}
