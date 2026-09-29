"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { PlusCircle, Download } from "lucide-react";
import { ManagerAddWorkLogDialog } from "@/components/work-log/manager-add-log-dialog";

interface DashboardHeaderActionsProps {
    companyId: string;
    companyName: string;
    worklogDefinitions?: Record<string, any>;
    users: any[];
    onShiftCreated?: () => void;
    onExportCsv?: () => void;
    canExport?: boolean;
}

export function DashboardHeaderActions({
    companyId,
    companyName,
    worklogDefinitions,
    users,
    onShiftCreated,
    onExportCsv,
    canExport = false
}: DashboardHeaderActionsProps) {
    const [addShiftOpen, setAddShiftOpen] = useState(false);

    return (
        <div className="flex items-center gap-2 sm:gap-3">
            {/* Accion Secundaria: Exportar datos del período si hay datos */}
            {onExportCsv && (
                <Button
                    variant="outline"
                    size="sm"
                    className="h-9 text-xs sm:text-sm font-medium border-slate-200 hover:bg-slate-50 dark:border-slate-800"
                    onClick={onExportCsv}
                    disabled={!canExport}
                    title="Exportar registros del período en formato CSV"
                >
                    <Download className="mr-1.5 h-4 w-4 text-slate-500" />
                    Exportar CSV
                </Button>
            )}

            {/* Accion Principal: Modal de Añadir Registro */}
            <ManagerAddWorkLogDialog
                companyId={companyId}
                companyName={companyName}
                users={users}
                worklogDefinitions={worklogDefinitions}
                open={addShiftOpen}
                onOpenChange={setAddShiftOpen}
                onSuccess={() => {
                    setAddShiftOpen(false);
                    onShiftCreated?.();
                }}
            >
                <Button
                    className="bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200 shadow-sm text-xs sm:text-sm h-9 font-medium"
                >
                    <PlusCircle className="mr-1.5 h-4 w-4" />
                    Añadir Registro
                </Button>
            </ManagerAddWorkLogDialog>
        </div>
    );
}

