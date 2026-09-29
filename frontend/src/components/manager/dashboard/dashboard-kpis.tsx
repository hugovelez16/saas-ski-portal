"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Clock, FileText, Users, Coins, Wallet } from "lucide-react";
import { DateRangeFilter } from "@/components/manager/date-range-filter";
import { DateRange } from "react-day-picker";

export type DashboardPeriod = "today" | "week" | "month" | "last_month" | "season" | "custom";

export interface KpiSummaryData {
    totalHours: number;
    totalGross: number;
    totalNet: number;
    totalLogs: number;
    activeMembersCount: number;
    daysCount: number;
    isSinglePrice: boolean;
}

interface DashboardKpisProps {
    period: DashboardPeriod;
    onPeriodChange: (p: DashboardPeriod) => void;
    customDateRange?: DateRange;
    onCustomDateRangeChange?: (range: DateRange | undefined) => void;
    kpis: KpiSummaryData;
    isLoading?: boolean;
}

export function DashboardKpis({
    period,
    onPeriodChange,
    customDateRange,
    onCustomDateRangeChange,
    kpis,
    isLoading
}: DashboardKpisProps) {
    const periodButtons: { key: DashboardPeriod; label: string }[] = [
        { key: "today", label: "Hoy" },
        { key: "week", label: "Esta Semana" },
        { key: "month", label: "Este Mes" },
        { key: "last_month", label: "Mes Anterior" },
        { key: "season", label: "Temporada" },
        { key: "custom", label: "Personalizado" },
    ];

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat("es-ES", {
            style: "currency",
            currency: "EUR",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(val);
    };

    // Unify financial KPI if gross and net are identical or single price
    const isFinancialUnified = kpis.isSinglePrice || Math.abs(kpis.totalGross - kpis.totalNet) < 0.01 || kpis.totalGross === 0;

    return (
        <div className="space-y-4">
            {/* Period Selector Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white dark:bg-slate-900 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
                    {periodButtons.map(btn => (
                        <Button
                            key={btn.key}
                            variant={period === btn.key ? "default" : "ghost"}
                            size="sm"
                            onClick={() => onPeriodChange(btn.key)}
                            className={`text-xs h-8 font-medium whitespace-nowrap ${
                                period === btn.key
                                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 shadow-xs"
                                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400"
                            }`}
                        >
                            {btn.label}
                        </Button>
                    ))}
                </div>

                {period === "custom" && onCustomDateRangeChange && (
                    <div className="flex items-center gap-2">
                        <DateRangeFilter
                            date={customDateRange}
                            setDate={onCustomDateRangeChange}
                        />
                    </div>
                )}
            </div>

            {/* KPI Metric Cards */}
            <div className={`grid gap-4 sm:grid-cols-2 ${isFinancialUnified ? "lg:grid-cols-4" : "lg:grid-cols-5"}`}>
                {/* Total Horas */}
                <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                            Horas Totales
                        </CardTitle>
                        <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                            {kpis.totalHours.toFixed(1)} h
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            {kpis.daysCount} días de actividad
                        </p>
                    </CardContent>
                </Card>

                {/* Partes / Turnos */}
                <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                            Partes Registrados
                        </CardTitle>
                        <FileText className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                            {kpis.totalLogs}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Turnos en el período
                        </p>
                    </CardContent>
                </Card>

                {/* Monitores Activos */}
                <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                            Monitores Activos
                        </CardTitle>
                        <Users className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                            {kpis.activeMembersCount}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Con turnos asignados
                        </p>
                    </CardContent>
                </Card>

                {/* Financial KPI Cards */}
                {isFinancialUnified ? (
                    <Card className="border-emerald-200/70 dark:border-emerald-900/60 shadow-sm hover:shadow transition-shadow bg-emerald-50/20 dark:bg-emerald-950/10">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-xs font-semibold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider">
                                Total Liquidación
                            </CardTitle>
                            <Coins className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                                {formatCurrency(kpis.totalGross || kpis.totalNet)}
                            </div>
                            <p className="text-xs text-emerald-700/80 dark:text-emerald-400/80 mt-1">
                                Importe total del período
                            </p>
                        </CardContent>
                    </Card>
                ) : (
                    <>
                        <Card className="border-emerald-200/70 dark:border-emerald-900/60 shadow-sm hover:shadow transition-shadow">
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                    Coste Empresa (Bruto)
                                </CardTitle>
                                <Coins className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                                    {formatCurrency(kpis.totalGross)}
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Coste total estimado
                                </p>
                            </CardContent>
                        </Card>

                        <Card className="border-indigo-200/70 dark:border-indigo-900/60 shadow-sm hover:shadow transition-shadow">
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                    Liquidación Equipo (Neto)
                                </CardTitle>
                                <Wallet className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                                    {formatCurrency(kpis.totalNet)}
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Total neto percibido
                                </p>
                            </CardContent>
                        </Card>
                    </>
                )}
            </div>
        </div>
    );
}
