"use client";

import React, { useState, useMemo } from "react";
import { DataTable } from "@/components/ui/data-table";
import { WorkLogDetailsDialog } from "@/components/work-log/details-dialog";
import { UserCreateWorkLogDialog } from "@/components/work-log/user-dialog";
import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { deleteWorkLog } from "@/lib/api/work-logs";
import { useToast } from "@/hooks/use-toast";
import { format, parseISO } from "date-fns";
import { Pencil, Trash2, Sparkles, Moon } from "lucide-react";
import type { WorkLog, Company } from "@/lib/types";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface WorkLogsTableProps {
    data: WorkLog[];
    companies: Company[];
    onUpdate: () => void;
    isLoading?: boolean;
    user?: { id: string; firstName?: string | null; lastName?: string | null; activeCompanyId?: string | null };
    showUserColumn?: boolean;
    readOnly?: boolean;
    fixedCompanyId?: string;
}

export function WorkLogsTable({
    data,
    companies,
    onUpdate,
    isLoading,
    user,
    showUserColumn = false,
    readOnly = false,
    fixedCompanyId,
}: WorkLogsTableProps) {
    const { toast } = useToast();
    const [selectedCompanyId, setSelectedCompanyId] = useState<string>(
        fixedCompanyId || (companies.length > 0 ? companies[0].id : "all")
    );
    const [viewLog, setViewLog] = useState<WorkLog | null>(null);
    const [editLog, setEditLog] = useState<WorkLog | null>(null);

    // Sync fixedCompanyId when it changes externally (e.g., shifts page)
    React.useEffect(() => {
        if (fixedCompanyId) {
            setSelectedCompanyId(fixedCompanyId);
        }
    }, [fixedCompanyId]);

    // Set first company when companies array is populated asynchronously
    React.useEffect(() => {
        if (!fixedCompanyId && selectedCompanyId === "all" && companies.length > 0) {
            setSelectedCompanyId(companies[0].id);
        }
    }, [companies, fixedCompanyId, selectedCompanyId]);

    // 1. Filter work logs by company
    const filteredData = useMemo(() => {
        if (selectedCompanyId === "all") return data;
        return data.filter(log => log.companyId === selectedCompanyId);
    }, [data, selectedCompanyId]);

    // 2. Extract labels and icons from all companies' dynamic fields
    const fieldDefinitions = useMemo(() => {
        const defs: Record<string, { label: string, icon?: any }> = {};
        companies.forEach(c => {
            if (c.worklogDefinitions) {
                Object.entries(c.worklogDefinitions).forEach(([key, val]: [string, any]) => {
                    defs[key] = { label: val.label || key };
                });
            }
        });
        if (defs["has_coordination"]) defs["has_coordination"].icon = Sparkles;
        if (defs["has_night"]) defs["has_night"].icon = Moon;
        return defs;
    }, [companies]);

    // 3. Extract dynamic JSONB keys present in the filtered logs
    const dynamicExtraKeys = useMemo(() => {
        const keys = new Set<string>();
        filteredData.forEach(log => {
            if (log.extraData) {
                const datos = log.extraData.datos;
                if (datos) {
                    Object.keys(datos).forEach(k => {
                        const val = datos[k];
                        if (val !== null && val !== undefined && (val as any) !== false && val !== "") {
                            keys.add(k);
                        }
                    });
                }
                const opciones = log.extraData.opciones;
                if (opciones) {
                    Object.keys(opciones).forEach(k => {
                        const val = opciones[k];
                        if (val !== null && val !== undefined && val !== false) {
                            keys.add(k);
                        }
                    });
                }
            }
        });
        return Array.from(keys);
    }, [filteredData]);

    // 4. Handle log deletion
    const handleDeleteClick = async (logId: string) => {
        if (!confirm("¿Eliminar este parte de trabajo?")) return;
        try {
            await deleteWorkLog(logId);
            toast({ title: "Parte eliminado" });
            onUpdate();
        } catch (error) {
            toast({ title: "Error al eliminar", variant: "destructive" });
        }
    };

    // 5. Build dynamic columns definition
    const logColumns = useMemo<ColumnDef<any>[]>(() => {
        const columns: ColumnDef<any>[] = [];

        // User Column
        if (showUserColumn) {
            columns.push({
                id: "user",
                header: "Usuario",
                cell: ({ row }) => (
                    <div className="flex flex-col">
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                            {row.original.userName || (row.original.user ? `${row.original.user.firstName} ${row.original.user.lastName}` : "-")}
                        </span>
                        {row.original.userEmail && (
                            <span className="text-xs text-muted-foreground truncate max-w-[150px]">{row.original.userEmail}</span>
                        )}
                    </div>
                )
            });
        }

        // Date Column
        columns.push({
            accessorKey: "date",
            header: "Fecha",
            cell: ({ row }) => {
                const log = row.original;
                const isMultiDay = log.type === 'tutorial' && log.startDate && log.endDate && log.startDate !== log.endDate;
                return (
                    <div className="flex flex-col">
                        <span className="font-medium whitespace-nowrap">
                            {isMultiDay
                                ? `${format(parseISO(log.startDate), "dd/MM/yyyy")} - ${format(parseISO(log.endDate), "dd/MM/yyyy")}`
                                : (log.startDate ? format(parseISO(log.startDate), "dd/MM/yyyy") : (log.date ? format(parseISO(log.date), "dd/MM/yyyy") : "-"))
                            }
                        </span>
                        {log.type === 'particular' && log.startTime && log.endTime && (
                            <span className="text-xs text-muted-foreground whitespace-nowrap">{log.startTime} - {log.endTime}</span>
                        )}
                    </div>
                );
            }
        });

        // Type Column
        columns.push({
            accessorKey: "type",
            header: "Tipo",
            cell: ({ row }) => (
                <Badge variant={row.original.type === 'tutorial' ? 'secondary' : 'outline'} className="capitalize">
                    {row.original.type}
                </Badge>
            )
        });

        // Description Column
        columns.push({
            accessorKey: "description",
            header: "Descripción",
            cell: ({ row }) => (
                <div className="max-w-[200px] truncate" title={row.original.description || ""}>
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                        {row.original.description || "-"}
                    </span>
                </div>
            )
        });

        // Company Column
        if (selectedCompanyId === "all" && !fixedCompanyId) {
            columns.push({
                accessorKey: "companyId",
                header: "Empresa",
                cell: ({ row }) => {
                    const company = companies.find(c => c.id === row.original.companyId);
                    return <span>{company?.name ?? "N/A"}</span>;
                }
            });
        }

        // Dynamic Columns (JSONB Extra Keys)
        dynamicExtraKeys.forEach(key => {
            const def = fieldDefinitions[key];
            const label = def?.label || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const Icon = def?.icon;

            columns.push({
                id: `extra-${key}`,
                header: label,
                cell: ({ row }) => {
                    const val = row.original.extraData?.datos?.[key] !== undefined
                        ? row.original.extraData?.datos?.[key]
                        : row.original.extraData?.opciones?.[key];
                    if (val === null || val === undefined || val === false || val === "") return <span />;

                    if (typeof val === 'boolean') {
                        return Icon ? <Icon className="h-4 w-4 text-indigo-500" /> : <Badge variant="secondary" className="text-[10px]">Sí</Badge>;
                    }
                    
                    if (typeof val === 'object') {
                        return <span className="text-sm">{JSON.stringify(val)}</span>;
                    }
                    
                    return <span className="text-sm">{String(val)}</span>;
                }
            });
        });

        // Amount Column
        columns.push({
            accessorKey: "amount",
            header: () => <div className="text-right">Importe</div>,
            cell: ({ row }) => (
                <div className="text-right font-bold text-slate-900 dark:text-slate-100">
                    €{Number(row.original.netAmount || row.original.grossAmount || row.original.amount || 0).toFixed(2)}
                </div>
            )
        });

        // Actions Column
        if (!readOnly) {
            columns.push({
                id: "actions",
                header: "",
                cell: ({ row }) => (
                    <div className="flex items-center gap-1 justify-end" onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-600" onClick={() => setEditLog(row.original)}>
                            <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600" onClick={() => handleDeleteClick(row.original.id)}>
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                )
            });
        }

        return columns;
    }, [companies, dynamicExtraKeys, fieldDefinitions, selectedCompanyId, fixedCompanyId, showUserColumn, readOnly]);

    const activeUser = user || (editLog?.userId ? { id: editLog.userId } : { id: "" });

    return (
        <div className="space-y-4">
            {/* Top Toolbar: Company Selector */}
            {!fixedCompanyId && companies.length > 1 && (
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-500 dark:text-slate-400">Filtrar por empresa:</span>
                    <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId}>
                        <SelectTrigger className="w-[200px] h-9">
                            <SelectValue placeholder="Seleccionar empresa" />
                        </SelectTrigger>
                        <SelectContent className="bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800">
                            {companies.map((c) => (
                                <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            )}

            {/* Standard Data Table */}
            <DataTable
                columns={logColumns}
                data={filteredData}
                searchKey="type"
                searchPlaceholder="Buscar por tipo..."
                isLoading={isLoading}
                onRowClick={(log) => setViewLog(log)}
            />

            {/* View Details Dialog */}
            <WorkLogDetailsDialog
                log={viewLog}
                open={!!viewLog}
                onOpenChange={() => setViewLog(null)}
                companies={companies}
            />

            {/* Edit Form Dialog */}
            {editLog && (
                <UserCreateWorkLogDialog
                    user={activeUser}
                    companies={companies}
                    logToEdit={editLog}
                    open={!!editLog}
                    onOpenChange={(open) => !open && setEditLog(null)}
                    onLogUpdate={() => {
                        setEditLog(null);
                        onUpdate();
                    }}
                />
            )}
        </div>
    );
}
