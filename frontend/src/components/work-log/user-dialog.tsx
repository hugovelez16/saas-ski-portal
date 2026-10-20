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
import api from "@/lib/api";

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

    // Fetch companies
    // Fetch companies if not provided
    const { data: fetchedCompanies = [] } = useQuery({
        queryFn: getMyCompanies,
        queryKey: ["myCompanies"],
        enabled: !providedCompanies,
    });

    const companies = providedCompanies || fetchedCompanies;

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

        let logData: any = {
            ...formData,
            userId: user.id,
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
                await updateWorkLog(logToEdit.id, logData, initialApplyToGroup);
                toast({ title: "Success", description: "Work log updated successfully." });
            } else {
                await createWorkLog(logData);
                toast({ title: "Success", description: "Work log created successfully." });
            }

            setOpen(false);
            if (!logToEdit) {
                // Save the company ID for next time
                if (logData.companyId) setLastSelectedCompanyId(logData.companyId);
                resetForm();
            }
            onLogUpdate?.();

        } catch (error: any) {
            console.error("Error saving work log:", error);
            let msg = "Could not save the log.";
            
            if (error.response?.data?.detail) {
                const detail = error.response.data.detail;
                if (typeof detail === 'string') {
                    msg = detail;
                } else if (Array.isArray(detail)) {
                    msg = detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
                } else if (typeof detail === 'object') {
                    msg = detail.message || JSON.stringify(detail);
                }
            } else if (error.message) {
                msg = error.message;
            }

            // Check if it's a rate/pricing related validation error and make it friendly
            const lowercaseMsg = msg.toLowerCase();
            if (lowercaseMsg.includes("precio") || lowercaseMsg.includes("rate") || lowercaseMsg.includes("tarifa")) {
                msg = "No se puede guardar: El usuario no tiene tarifas configuradas para este tipo de turno. Por favor, configura sus tarifas primero.";
            }

            toast({ title: "Error", description: String(msg), variant: "destructive" });
        } finally {
            setIsLoading(false);
        }
    }

    return (
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
    )
}
