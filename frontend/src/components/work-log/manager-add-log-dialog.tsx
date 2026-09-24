"use client";

import React, { useState, useMemo, useEffect } from 'react';
import api from "@/lib/api";
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
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PlusCircle, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { WorkLog, WorkLogCreate, WorkLogBulkCreate } from "@/lib/types";
import { WorkLogForm } from "./work-log-form";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";

interface ManagerAddWorkLogDialogProps {
    companyId: string;
    companyName: string;
    users: any[];
    worklogDefinitions?: Record<string, any>;
    onSuccess?: () => void;
    children?: React.ReactNode;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    initialData?: Partial<WorkLog>;
}

export function ManagerAddWorkLogDialog({
    companyId,
    companyName,
    users,
    worklogDefinitions,
    onSuccess,
    children,
    open: externalOpen,
    onOpenChange: setExternalOpen,
    initialData
}: ManagerAddWorkLogDialogProps) {
    const [internalOpen, setInternalOpen] = useState(false);

    // Use external state if provided, otherwise internal
    const isControlled = externalOpen !== undefined;
    const open = isControlled ? externalOpen : internalOpen;
    const setOpen = isControlled ? setExternalOpen! : setInternalOpen;

    const [isLoading, setIsLoading] = useState(false);
    const [logType, setLogType] = useState<string>('particular');
    const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
    const [searchQuery, setSearchQuery] = useState('');

    // Form data - pre-fill companyId
    const [formData, setFormData] = useState<Partial<WorkLogCreate>>({
        companyId: companyId,
        hasCoordination: false,
        hasNight: false,
        arrivesPrior: false,
    });
    const { user } = useAuth(); // Need auth context for some user lookups or safety

    const { toast } = useToast();

    // Reset or Initialize when opening
    useEffect(() => {
        if (open) {
            setSearchQuery('');
            setFormData(prev => ({
                ...prev,
                companyId: companyId,
                hasCoordination: false,
                hasNight: false,
                arrivesPrior: false,
                // Merge initial data if present (filter out nulls if necessary)
                ...(initialData ? {
                    ...initialData,
                    startTime: initialData.startTime || undefined,
                    endTime: initialData.endTime || undefined,
                    date: initialData.date || undefined,
                } : {})
            }));

            if (initialData?.userId) {
                setSelectedUserIds([initialData.userId]);
            } else {
                setSelectedUserIds([]);
            }

            if (initialData?.type) {
                setLogType(initialData.type);
            }
        } else {
            // Only reset if closing (and we want to clear)
            // But usually we reset ON open to fresh state or defaults.
            // Let's reset on CLOSE to be clean.
            if (!isControlled) { // If controlled, parent might handle reset, but safe to do here.
                setFormData({ companyId: companyId, hasCoordination: false, hasNight: false, arrivesPrior: false });
                setSelectedUserIds([]);
                setLogType('particular');
                setSearchQuery('');
            }
        }
    }, [open, companyId, initialData, isControlled]);

    // Mock company object for WorkLogForm (passing worklogDefinitions)
    const companies = useMemo(() => [{
        id: companyId,
        name: companyName,
        settings: {},
        worklogDefinitions: worklogDefinitions || {}
    }], [companyId, companyName, worklogDefinitions]);

    const handleSubmit = async () => {
        if (selectedUserIds.length === 0) {
            toast({ title: "Error", description: "Por favor, selecciona al menos un usuario.", variant: "destructive" });
            return;
        }

        setIsLoading(true);

        const currentDef = (worklogDefinitions || {})[logType] || null;
        const isRange = currentDef?.is_range === true;
        const isFixed = currentDef?.unit === "fixed";

        if (isRange) {
            if (!formData.startDate || !formData.endDate) {
                toast({ title: "Error", description: "Fecha de inicio y fin son obligatorias.", variant: "destructive" });
                setIsLoading(false);
                return;
            }
        } else {
            if (!formData.date) {
                toast({ title: "Error", description: "La fecha es obligatoria.", variant: "destructive" });
                setIsLoading(false);
                return;
            }
            if (!isFixed && (!formData.startTime || !formData.endTime)) {
                toast({ title: "Error", description: "Las horas de inicio y fin son obligatorias.", variant: "destructive" });
                setIsLoading(false);
                return;
            }
        }

        const sharedData: any = {
            ...formData,
            companyId: companyId,
            type: logType,
        };

        // SaaS Logic: Ensure startDate/endDate are present for all types
        // In non-range mode, they should match 'date'
        if (!isRange) {
            sharedData.startDate = sharedData.date;
            sharedData.endDate = sharedData.date;
        }

        // Clean empty times to avoid Pydantic 422 errors
        if (sharedData.startTime === "") sharedData.startTime = null;
        if (sharedData.endTime === "") sharedData.endTime = null;

        // Remove redundant frontend-only fields
        delete sharedData.date;

        // Clean calculated fields during edits to force backend recalculation
        if (initialData?.id) {
            delete sharedData.amount;
            delete sharedData.rateApplied;
            delete sharedData.grossAmount;
            delete sharedData.isGrossCalculation;
            delete sharedData.netAmount;
        }

        try {
            if (initialData?.id) {
                await api.put(`/work-logs/${initialData.id}`, { ...sharedData, userId: selectedUserIds[0] });
                toast({ title: "Éxito", description: "Registro actualizado correctamente." });
            } else if (selectedUserIds.length === 1) {
                await api.post("/work-logs", { ...sharedData, userId: selectedUserIds[0] });
                toast({ title: "Éxito", description: "Registro añadido correctamente." });
            } else {
                const bulkData: WorkLogBulkCreate = {
                    ...sharedData,
                    userIds: selectedUserIds,
                } as any;
                await api.post("/work-logs/bulk", bulkData);
                toast({ title: "Éxito", description: `${selectedUserIds.length} registros añadidos correctamente.` });
            }

            setOpen(false);
            onSuccess?.();

        } catch (error: any) {
            console.error("Error saving work log:", error);
            let msg = "No se pudo guardar el registro.";
            
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

            toast({ title: "Error al guardar", description: msg, variant: "destructive" });
        } finally {
            setIsLoading(false);
        }
    }


    const toggleUser = (userId: string) => {
        setSelectedUserIds(prev =>
            prev.includes(userId)
                ? prev.filter(id => id !== userId)
                : [...prev, userId]
        );
    };

    const filteredUsers = useMemo(() => {
        if (!searchQuery.trim()) return users;
        const query = searchQuery.toLowerCase();
        return users.filter(u =>
            (u.firstName || '').toLowerCase().includes(query) ||
            (u.lastName || '').toLowerCase().includes(query) ||
            (u.email || '').toLowerCase().includes(query)
        );
    }, [users, searchQuery]);

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {children ?? (
                    <Button>
                        <PlusCircle className="mr-2 h-4 w-4" />
                        Añadir Registro
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto bg-white dark:bg-slate-950" onOpenAutoFocus={(e) => e.preventDefault()}>
                <DialogHeader>
                    <DialogTitle>Añadir Registro - {companyName}</DialogTitle>
                    <DialogDescription>
                        Crea un nuevo registro para un miembro del equipo.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                        <Label>Usuarios seleccionados ({selectedUserIds.length})</Label>
                        <div className="flex flex-wrap gap-2 border p-2 rounded-md min-h-[40px] bg-slate-50 dark:bg-slate-900">
                            {selectedUserIds.length > 0 ? (
                                selectedUserIds.map((userId) => {
                                    const u = users.find(u => u.id === userId);
                                    const name = u ? `${u.firstName} ${u.lastName}` : `Usuario ${userId}`;
                                    return (
                                        <Badge key={userId} variant="secondary" className="flex items-center gap-1 py-1">
                                            {name}
                                            <X
                                                className="h-3 w-3 cursor-pointer hover:text-destructive"
                                                onClick={() => toggleUser(userId)}
                                            />
                                        </Badge>
                                    );
                                })
                            ) : (
                                <span className="text-muted-foreground text-sm italic">Ningún usuario seleccionado</span>
                            )}
                        </div>

                        <Label className="mt-2">Seleccionar miembros</Label>
                        <Input
                            placeholder="Buscar usuario por nombre o email..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="h-8 text-xs my-1"
                        />
                        <div className="h-[120px] w-full border rounded-md p-2 overflow-y-auto bg-white dark:bg-slate-950">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {filteredUsers.map((u: any) => (
                                    <div key={u.id} className="flex items-center space-x-2 p-1 hover:bg-slate-100 dark:hover:bg-slate-900 rounded transition-colors">
                                        <Checkbox
                                            id={`user-${u.id}`}
                                            checked={selectedUserIds.includes(u.id)}
                                            onCheckedChange={() => toggleUser(u.id)}
                                        />
                                        <Label
                                            htmlFor={`user-${u.id}`}
                                            className="text-xs cursor-pointer flex-1 truncate"
                                            title={`${u.firstName} ${u.lastName}`}
                                        >
                                            {u.firstName} {u.lastName}
                                        </Label>
                                    </div>
                                ))}
                                {filteredUsers.length === 0 && (
                                    <span className="col-span-full text-center text-xs text-muted-foreground py-4 italic">
                                        No se encontraron usuarios
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Shared Form */}
                    <WorkLogForm
                        formData={formData}
                        setFormData={setFormData}
                        logType={logType}
                        setLogType={setLogType as any}
                        companies={companies}
                        hideCompanySelector={true}
                    />
                </div>

                <DialogFooter>
                    <DialogClose asChild>
                        <Button variant="ghost">Cancelar</Button>
                    </DialogClose>
                    <Button type="submit" disabled={isLoading} onClick={handleSubmit}>
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Guardar
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
