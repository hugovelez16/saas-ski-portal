"use client";

import React from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
    DialogClose,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { format, parseISO, differenceInCalendarDays } from "date-fns";
import { es } from "date-fns/locale";
import { WorkLog, UserSettings, Company } from "@/lib/types";
import { formatCurrency, cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { useQuery } from "@tanstack/react-query";
import { getMyCompanies } from "@/lib/api/companies";
import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/hooks/use-permissions";

interface WorkLogDetailsDialogProps {
    log: WorkLog | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    companies?: Company[] | null;
    userSettings?: UserSettings | null;
    onEdit?: (log: WorkLog, applyToGroup: boolean) => void;
    onDelete?: (log: WorkLog) => void;
}

export function WorkLogDetailsDialog({ log, open, onOpenChange, companies: initialCompanies, userSettings, onEdit, onDelete }: WorkLogDetailsDialogProps) {
    const { user } = useAuth();
    const [applyToGroup, setApplyToGroup] = React.useState(false);

    // Fetch companies if not provided (cached by React Query)
    const { data: myCompanies = [] } = useQuery({
        queryKey: ["myCompanies"],
        queryFn: getMyCompanies,
        enabled: open && !initialCompanies,
    });

    const companies = initialCompanies || myCompanies;

    // Empresa del turno: sus reglas (gestionada o autonoma) deciden si se puede editar o borrar
    const logCompany = log ? companies?.find(c => c.id === log.companyId) ?? null : null;
    const { canEditWorkLog, role, isManaged } = usePermissions(logCompany);
    const canEdit = !!log && !!logCompany && canEditWorkLog(log);
    const isManagedWorker = role === 'worker' && isManaged;

    if (!log) return null;

    // Resolve Definition
    const company = logCompany;
    const definition = company?.worklogDefinitions?.[log.type];
    const typeLabel = definition?.label || log.type;

    // Logic for Date/Time display
    const isRange = definition?.unit === 'days' || (log.type === 'tutorial' && log.endDate);
    const isFixed = definition?.unit === 'fixed';

    // Calculation Snapshot Breakdown
    const snapshot = log.calculationSnapshot;
    const displayLines = snapshot?.display_lines || [];

    // Fallback breakdown for legacy logs
    const hasSnapshot = !!snapshot && displayLines.length > 0;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <span>Detalles del Parte</span>
                        <Badge variant="secondary" className="capitalize">{typeLabel}</Badge>
                    </DialogTitle>
                    <DialogDescription>
                        Información completa y desglose de cálculo.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4 text-sm">
                    {/* Basic Info Section */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 dark:bg-slate-900/50 p-4 rounded-lg border">
                        <div>
                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Empresa</h4>
                            <p className="font-medium">{company?.name || 'Cargando...'}</p>
                        </div>
                        <div>
                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Fecha</h4>
                            {isRange ? (
                                <p className="font-medium">
                                    {log.startDate ? format(parseISO(log.startDate), 'dd/MM/yyyy') : '-'} - {log.endDate ? format(parseISO(log.endDate), 'dd/MM/yyyy') : '-'}
                                </p>
                            ) : (
                                <p className="font-medium">{log.startDate ? format(parseISO(log.startDate), 'dd/MM/yyyy') : '-'}</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Tiempo / Unidad</h4>
                            {isRange ? (
                                <p className="font-medium">
                                    {log.startDate && log.endDate ? differenceInCalendarDays(parseISO(log.endDate), parseISO(log.startDate)) + 1 : 0} días
                                </p>
                            ) : isFixed ? (
                                <p className="font-medium">Precio Fijo / Jornada</p>
                            ) : (
                                <p className="font-medium">{log.startTime} - {log.endTime} ({Number(log.duration ?? log.durationHours ?? 0).toFixed(2)}h)</p>
                            )}
                        </div>
                    </div>

                    {/* Dynamic Fields Section (extraData) */}
                    {definition?.fields && definition.fields.length > 0 && (
                        <div className="space-y-3">
                            <h4 className="font-bold border-b pb-1 flex items-center gap-2">
                                Datos del Servicio
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3">
                                {definition.fields.map((field: string) => (
                                    <div key={field}>
                                        <h5 className="text-xs font-medium text-muted-foreground capitalize">{field}</h5>
                                        <p>{log.extraData?.datos?.[field] || '-'}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {log.description && (
                        <div className="space-y-1">
                            <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Descripción</h5>
                            <p className="text-sm bg-slate-50 dark:bg-slate-900/30 p-3 rounded border italic">
                                {log.description}
                            </p>
                        </div>
                    )}

                    {/* Price Breakdown Section (The "Ticket") */}
                    <div className="border rounded-lg overflow-hidden shadow-sm">
                        <div className="bg-slate-900 text-white px-4 py-2 flex justify-between items-center">
                            <h4 className="font-semibold text-xs uppercase tracking-widest">Desglose de Pago</h4>
                            <span className="text-[10px] opacity-70">Snapshot v{snapshot?.version || 'Legacy'}</span>
                        </div>
                        <div className="p-4 space-y-2 bg-white dark:bg-slate-950">
                            {hasSnapshot ? (
                                <>
                                    {displayLines.map((line: any, index: number) => {
                                        const isSubtotal = line.type === 'subtotal';
                                        const isTotal = line.type === 'total';
                                        const isTax = line.type === 'tax';
                                        
                                        return (
                                            <React.Fragment key={index}>
                                                {isSubtotal && <div className="h-px bg-slate-200 my-2" />}
                                                {isTotal && <div className="h-[2px] bg-slate-200 my-2" />}
                                                <div className={`flex justify-between items-center ${isTotal ? 'text-lg font-bold text-green-600' : isSubtotal ? 'font-bold' : ''}`}>
                                                    <span className={cn(
                                                        "text-sm",
                                                        isTax && "text-red-500 text-xs italic pl-2",
                                                        isSubtotal && "text-slate-700"
                                                    )}>
                                                        {line.label}
                                                    </span>
                                                    <span className={cn(
                                                        "font-mono",
                                                        isTax && "text-red-500 text-xs",
                                                        isTotal && "text-green-600"
                                                    )}>
                                                        {formatCurrency(line.value)}
                                                    </span>
                                                </div>
                                            </React.Fragment>
                                        );
                                    })}
                                </>
                            ) : (
                                <div className="text-center py-4 text-muted-foreground italic text-xs">
                                    No hay snapshot de cálculo disponible para este registro histórico.
                                    <div className="mt-2 text-sm not-italic font-bold text-foreground flex justify-between">
                                        <span>Total Cobrado:</span>
                                        <span>{formatCurrency(log.netAmount || log.amount || 0)}</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* ID and Metadata */}
                    <div className="flex justify-between items-center text-[10px] text-muted-foreground pt-2 border-t border-dashed">
                        <span>Log ID: {log.id}</span>
                        {log.groupId && <span>Group ID: {log.groupId}</span>}
                    </div>

                    {/* Group Action Checkbox - Only for Managers/Admins */}
                    {canEdit && log.groupId && (user?.isPlatformAdmin || company?.role === 'manager' || company?.role === 'admin' || user?.activeRole === 'manager') && (
                        <div className="flex items-center space-x-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-100 dark:border-blue-800 transition-colors hover:bg-blue-100 dark:hover:bg-blue-900/30">
                            <Checkbox 
                                id="applyToGroup" 
                                checked={applyToGroup} 
                                onCheckedChange={(checked) => setApplyToGroup(!!checked)}
                            />
                            <Label htmlFor="applyToGroup" className="text-xs font-medium text-blue-900 dark:text-blue-300 cursor-pointer select-none">
                                Aplicar cambios de edición a todo el grupo de trabajadores
                            </Label>
                        </div>
                    )}
                </div>

                <DialogFooter className="flex-col sm:flex-row gap-2 sm:gap-0 border-t pt-4">
                    <div className="flex gap-2 w-full sm:w-auto mr-auto">
                        {onEdit && canEdit && (
                            <Button variant="secondary" onClick={() => {
                                onEdit(log, applyToGroup);
                            }}>
                                Editar
                            </Button>
                        )}
                        {onDelete && canEdit && (
                            <Button variant="destructive" onClick={() => onDelete(log)}>
                                Eliminar
                            </Button>
                        )}
                        {(onEdit || onDelete) && !canEdit && isManagedWorker && (
                            <p className="text-xs text-muted-foreground italic self-center">
                                En esta empresa los turnos los registra el equipo gestor
                            </p>
                        )}
                    </div>
                    <DialogClose asChild>
                        <Button variant="outline">Cerrar</Button>
                    </DialogClose>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
