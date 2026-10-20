"use client";

import { useMemo } from "react";
import { format, eachDayOfInterval, parseISO } from "date-fns";
import { WorkLog, WorkLogSummary } from "@/lib/types";
import { formatCurrency, cn } from "@/lib/utils";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/data-table";
import { Banknote, CalendarDays, Clock, User as UserIcon } from "lucide-react";
import {
    WorklogDefinitions,
    buildTypeBlocks,
    blockQuantity,
    blockQuantityText,
    netByMonth
} from "@/lib/reports/report-types";

interface PrintableReportProps {
    /** Filas de detalle del rango (solo para el listado mensual). */
    workLogs: WorkLog[];
    /** Totales, desgloses por tipo y por dia del rango (GET /work-logs/summary). */
    summary: WorkLogSummary;
    /** Definiciones de tipos de turno de la empresa (etiqueta y unidad). */
    worklogDefinitions?: WorklogDefinitions;
    title: string;
    subtitle?: string;
    dateRange: { from: Date; to: Date };
}

export function PrintableReport({ workLogs, summary, worklogDefinitions, title, dateRange }: PrintableReportProps) {

    // --- Totales y bloques por tipo (todo desde el resumen del backend) ---
    const blocks = useMemo(
        () => buildTypeBlocks(summary.byType, worklogDefinitions),
        [summary, worklogDefinitions]
    );

    const monthlyNet = useMemo(
        () => netByMonth(summary.byDay, date => format(parseISO(date), 'MMMM yyyy')),
        [summary]
    );

    const stats = useMemo(() => {
        let totalDays = 0;
        try {
            totalDays = eachDayOfInterval({ start: dateRange.from, end: dateRange.to }).length;
        } catch (e) {
            totalDays = 0;
        }

        return {
            income: summary.totals.totalNet,
            totalHours: summary.totals.totalHours,
            workDays: summary.totals.uniqueDays,
            totalDays
        };
    }, [summary, dateRange]);

    // --- Log Grouping (solo detalle) ---
    const groupedLogs = useMemo(() => {
        const groups = new Map<string, WorkLog[]>();

        // Sort first
        const sorted = [...workLogs].sort((a, b) => {
            const dateA = new Date(a.date || a.startDate || a.createdAt);
            const dateB = new Date(b.date || b.startDate || b.createdAt);
            return dateA.getTime() - dateB.getTime();
        });

        sorted.forEach(log => {
            const d = new Date(log.date || log.startDate || log.createdAt);
            const key = format(d, 'MMMM yyyy'); // e.g. "January 2024"
            if (!groups.has(key)) {
                groups.set(key, []);
            }
            groups.get(key)!.push(log);
        });

        return groups;
    }, [workLogs]);

    return (
        <div className="w-full max-w-[210mm] min-h-[297mm] mx-auto bg-white p-8 print:p-0 print:max-w-none text-slate-900 print:text-xs">
            {/* Print specific styles */}
            <style jsx global>{`
                @media print {
                    @page { margin: 10mm 15mm; size: auto; }
                    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                    .print-break-inside-avoid { break-inside: avoid; }
                }
            `}</style>

            {/* Header: Mimic App Header */}
            <div className="mb-8 border-b-2 border-slate-900 pb-4 flex justify-between items-center bg-slate-900 text-white p-4 -mx-8 -mt-8 print:mx-0 print:mt-0 print:rounded-none">
                <div className="flex gap-4 items-center">
                    {/* Logo: Mimic Sidebar */}
                    <div className="w-10 h-10 rounded bg-slate-800 flex items-center justify-center font-bold text-xl border border-slate-700">
                        <span className="text-white">V</span>
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white uppercase tracking-tight">Vesotel</h1>
                        <p className="text-slate-400 text-xs font-medium uppercase tracking-wider">Informe de Jornadas</p>
                    </div>
                </div>
                <div className="text-right text-xs">
                    <p className="font-bold text-white">{title}</p>
                    <p className="text-slate-400 font-mono mt-1">{format(new Date(), 'dd/MM/yyyy HH:mm')}</p>
                </div>
            </div>

            {/* Global Stats Section */}
            <div className="mb-8 print-break-inside-avoid">
                <h3 className="text-lg font-bold text-slate-900 mb-4 px-2 border-l-4 border-slate-900">Resumen Global</h3>

                {/* Key Metrics Row */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                    {/* Income */}
                    <div className="p-4 border border-slate-200 rounded bg-slate-50 print:bg-slate-50 print:border-slate-300 shadow-sm relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-2 opacity-10"><Banknote size={48} /></div>
                        <p className="text-xs text-slate-500 font-bold uppercase mb-1">Total Ingresos</p>
                        <p className="text-3xl font-bold text-slate-900">{formatCurrency(stats.income)}</p>
                    </div>
                    {/* Days */}
                    <div className="p-4 border border-slate-200 rounded bg-slate-50 print:bg-slate-50 print:border-slate-300 shadow-sm relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-2 opacity-10"><CalendarDays size={48} /></div>
                        <p className="text-xs text-slate-500 font-bold uppercase mb-1">Días Trabajados</p>
                        <div className="text-3xl font-bold text-slate-900">
                            {stats.workDays}
                            <span className="text-sm text-slate-400 font-normal">/{stats.totalDays}</span>
                        </div>
                    </div>
                    {/* Hours */}
                    <div className="p-4 border border-slate-200 rounded bg-slate-50 print:bg-slate-50 print:border-slate-300 shadow-sm relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-2 opacity-10"><Clock size={48} /></div>
                        <p className="text-xs text-slate-500 font-bold uppercase mb-1">Horas Totales</p>
                        <p className="text-3xl font-bold text-slate-900">{stats.totalHours.toFixed(0)}h</p>
                    </div>
                </div>

                {/* Bloque por tipo de turno: etiqueta y unidad de la definicion de la empresa */}
                {blocks.length > 0 && (
                    <div className="grid grid-cols-3 gap-4 mb-6">
                        {blocks.map(block => {
                            const quantity = blockQuantity(block);
                            const valueText = block.unit === "fixed"
                                ? `${quantity.value} ${quantity.suffix}`
                                : `${quantity.value.toFixed(1)} ${quantity.suffix}`;
                            return (
                                <div key={block.type} className="p-4 border border-slate-200 rounded bg-slate-50 print:bg-slate-50 print:border-slate-300 shadow-sm">
                                    <p className="text-xs text-slate-500 font-bold uppercase mb-1">{block.label}</p>
                                    <p className="text-2xl font-bold text-slate-900">{valueText}</p>
                                    <p className="text-xs text-slate-500 mt-1">
                                        {block.logsCount} turnos · {formatCurrency(block.net)}
                                    </p>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Monthly Details */}
            {Array.from(groupedLogs.entries()).map(([month, logs]) => (
                <div key={month} className="mt-8 print-break-inside-avoid">
                    <div className="flex items-center gap-4 mb-4">
                        <h3 className="text-lg font-bold uppercase text-slate-900">{month}</h3>
                        <div className="h-px bg-slate-300 flex-1"></div>
                    </div>

                    <div className="border rounded-md overflow-hidden bg-white shadow-sm">
                        <Table className="w-full">
                            <TableHeader>
                                <TableRow className="bg-slate-900 border-none print:bg-slate-900 text-white hover:bg-slate-900">
                                    <TableHead className="font-bold text-white h-9 text-xs">Fecha</TableHead>
                                    <TableHead className="font-bold text-white h-9 text-xs">Tipo</TableHead>
                                    <TableHead className="font-bold text-white h-9 text-xs">Cliente</TableHead>
                                    <TableHead className="font-bold text-white h-9 text-xs hidden md:table-cell print:table-cell">Flags</TableHead>
                                    <TableHead className="font-bold text-white h-9 text-xs text-right">Importe</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {logs.map((log, index) => (
                                    <TableRow key={log.id} className={cn("border-b border-slate-100 last:border-0", index % 2 === 0 ? "bg-white" : "bg-slate-50/50 print:bg-slate-50/50")}>
                                        <TableCell className="whitespace-nowrap py-2 text-xs font-medium text-slate-700">
                                            {log.type === 'tutorial' && log.startDate && log.endDate
                                                ? `${format(new Date(log.startDate), "dd/MM/yy")} - ${format(new Date(log.endDate), "dd/MM/yy")}`
                                                : log.date ? format(new Date(log.date), "dd/MM/yy") : "-"}
                                        </TableCell>
                                        <TableCell className="capitalize py-2 text-xs text-slate-600">{log.type}</TableCell>
                                        <TableCell className="py-2 text-xs flex items-center gap-1 text-slate-600">
                                            {(log.extraData?.client || log.description) && <UserIcon className="w-3 h-3 text-slate-400" />}
                                            {log.extraData?.client || log.description || '-'}
                                        </TableCell>
                                        <TableCell className="text-[10px] py-2 hidden md:table-cell print:table-cell">
                                            <div className="flex gap-1">
                                                {log.hasCoordination && <span className="px-1.5 py-px bg-blue-100 text-blue-800 rounded-sm font-semibold border border-blue-200">Coord</span>}
                                                {log.hasNight && <span className="px-1.5 py-px bg-indigo-100 text-indigo-800 rounded-sm font-semibold border border-indigo-200">Noct</span>}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right font-bold py-2 text-xs text-slate-800">
                                            {formatCurrency(Number(log.netAmount ?? log.grossAmount ?? log.amount ?? 0))}
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {/* Monthly Subtotal (suma de los totales diarios del resumen) */}
                                <TableRow className="bg-slate-100 font-bold border-t-2 border-slate-900">
                                    <TableCell colSpan={4} className="text-right py-2 text-xs uppercase">Total {month}</TableCell>
                                    <TableCell className="text-right py-2 text-xs">
                                        {formatCurrency(monthlyNet.get(month) ?? 0)}
                                    </TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </div>
                </div>
            ))}

            {/* Footer */}
            <div className="mt-8 border-t pt-4 text-center text-[10px] text-slate-400">
                <p>Reporte Oficial - Ski Vesotel</p>
            </div>
        </div>
    );
}
