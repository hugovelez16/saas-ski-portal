"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import { Banknote, Clock, ArrowUpRight, ArrowDownRight, CalendarDays, Sparkles, Moon, Layers } from "lucide-react";
import { WorkLog, Company } from "@/lib/types";
import { useMemo } from "react";
import { format, startOfMonth, endOfMonth, eachDayOfInterval, subMonths, eachMonthOfInterval, parseISO, differenceInCalendarDays } from "date-fns";
import { es } from "date-fns/locale";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/data-table";
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { Badge } from "@/components/ui/badge";

const COLOR_PALETTE = [
    "#3b82f6", // Blue
    "#10b981", // Emerald
    "#8b5cf6", // Violet
    "#f59e0b", // Amber
    "#06b6d4", // Cyan
    "#ec4899", // Pink
    "#6366f1", // Indigo
    "#14b8a6", // Teal
];

interface OverviewV3Props {
    workLogs: WorkLog[];
    companies: Company[];
    activeCompanyId?: string | null;
    onAddRecord: () => void;
    onNavigate: (tab: string) => void;
    selectedDate: Date;
    onViewLog?: (log: WorkLog) => void;
}

export function OverviewV3({ workLogs, companies, activeCompanyId, onAddRecord, onNavigate, selectedDate, onViewLog }: OverviewV3Props) {
    const activeCompany = useMemo(() => {
        return companies.find(c => c.id === activeCompanyId) || companies[0] || null;
    }, [companies, activeCompanyId]);

    const getDefinition = (type: string, companyId?: string) => {
        const comp = companies.find(c => c.id === companyId) || activeCompany;
        const def = comp?.worklogDefinitions?.[type];
        if (def) {
            return {
                label: def.label || type,
                unit: def.unit || "hours",
                isRange: def.is_range === true || def.unit === "days",
            };
        }
        return {
            label: type.charAt(0).toUpperCase() + type.slice(1),
            unit: "hours",
            isRange: false,
        };
    };

    const stats = useMemo(() => {
        const currentMonth = selectedDate.getMonth();
        const currentYear = selectedDate.getFullYear();

        const prevDate = subMonths(selectedDate, 1);
        const lastMonth = prevDate.getMonth();
        const lastMonthYear = prevDate.getFullYear();

        const currentMonthLogs = workLogs.filter(log => {
            const dateStr = log.startDate || log.date || log.createdAt;
            if (!dateStr) return false;
            const d = parseISO(dateStr);
            return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
        });

        const lastMonthLogs = workLogs.filter(log => {
            const dateStr = log.startDate || log.date || log.createdAt;
            if (!dateStr) return false;
            const d = parseISO(dateStr);
            return d.getMonth() === lastMonth && d.getFullYear() === lastMonthYear;
        });

        const income = currentMonthLogs.reduce((acc, log) => acc + (Number(log.netAmount ?? log.grossAmount ?? log.amount) || 0), 0);
        const lastIncome = lastMonthLogs.reduce((acc, log) => acc + (Number(log.netAmount ?? log.grossAmount ?? log.amount) || 0), 0);
        const percentChange = lastIncome > 0 ? ((income - lastIncome) / lastIncome) * 100 : income > 0 ? 100 : 0;

        // Dynamic aggregation by shift type
        const typeAggregation = new Map<string, {
            type: string;
            label: string;
            unit: string;
            quantity: number;
            count: number;
            amount: number;
        }>();

        // Calculate unique days worked
        const activeDaysSet = new Set<string>();

        currentMonthLogs.forEach(log => {
            const def = getDefinition(log.type, log.companyId);
            const amount = Number(log.netAmount ?? log.grossAmount ?? log.amount) || 0;

            let logQuantity = 0;
            if (def.unit === "days" || def.isRange) {
                if (log.startDate && log.endDate && log.startDate !== log.endDate) {
                    try {
                        const start = parseISO(log.startDate);
                        const end = parseISO(log.endDate);
                        logQuantity = Math.max(1, differenceInCalendarDays(end, start) + 1);
                        const interval = eachDayOfInterval({ start, end });
                        interval.forEach(day => activeDaysSet.add(format(day, "yyyy-MM-dd")));
                    } catch {
                        logQuantity = 1;
                        if (log.startDate) activeDaysSet.add(format(parseISO(log.startDate), "yyyy-MM-dd"));
                    }
                } else {
                    logQuantity = 1;
                    const dateStr = log.startDate || log.date;
                    if (dateStr) activeDaysSet.add(format(parseISO(dateStr), "yyyy-MM-dd"));
                }
            } else if (def.unit === "fixed") {
                logQuantity = 1;
                const dateStr = log.startDate || log.date;
                if (dateStr) activeDaysSet.add(format(parseISO(dateStr), "yyyy-MM-dd"));
            } else {
                // Hours unit
                logQuantity = Number(log.durationHours || log.duration || 0);
                const dateStr = log.startDate || log.date;
                if (dateStr) activeDaysSet.add(format(parseISO(dateStr), "yyyy-MM-dd"));
            }

            const existing = typeAggregation.get(log.type) || {
                type: log.type,
                label: def.label,
                unit: def.unit,
                quantity: 0,
                count: 0,
                amount: 0,
            };

            existing.quantity += logQuantity;
            existing.count += 1;
            existing.amount += amount;
            typeAggregation.set(log.type, existing);
        });

        const start = startOfMonth(selectedDate);
        const end = endOfMonth(selectedDate);
        const totalDaysInMonth = eachDayOfInterval({ start, end }).length;
        const activeDaysCount = activeDaysSet.size;
        const freeDaysCount = Math.max(0, totalDaysInMonth - activeDaysCount);

        const typeBreakdown = Array.from(typeAggregation.values()).map((item, idx) => ({
            ...item,
            color: COLOR_PALETTE[idx % COLOR_PALETTE.length],
        }));

        const totalHoursWorked = typeBreakdown
            .filter(t => t.unit === "hours")
            .reduce((acc, curr) => acc + curr.quantity, 0);

        const totalDaysWorkedFromDays = typeBreakdown
            .filter(t => t.unit === "days")
            .reduce((acc, curr) => acc + curr.quantity, 0);

        return {
            income,
            lastIncome,
            percentChange,
            typeBreakdown,
            activeDaysCount,
            freeDaysCount,
            totalDaysInMonth,
            totalHoursWorked,
            totalDaysWorkedFromDays,
            currentMonthLogsCount: currentMonthLogs.length,
        };
    }, [workLogs, selectedDate, companies, activeCompany]);

    // Income Trend: Last 6 Months
    const chartData = useMemo(() => {
        const end = selectedDate;
        const start = subMonths(end, 5);
        const months = eachMonthOfInterval({ start, end });

        return months.map(month => {
            const monthStart = startOfMonth(month);
            const monthEnd = endOfMonth(month);

            const monthIncome = workLogs
                .filter(log => {
                    const dateStr = log.startDate || log.date || log.createdAt;
                    if (!dateStr) return false;
                    const d = parseISO(dateStr);
                    return d >= monthStart && d <= monthEnd;
                })
                .reduce((acc, log) => acc + (Number(log.netAmount ?? log.grossAmount ?? log.amount) || 0), 0);

            return {
                name: format(month, "MMM", { locale: es }),
                fullDate: format(month, "MMMM yyyy", { locale: es }),
                total: monthIncome,
            };
        });
    }, [workLogs, selectedDate]);

    const recentLogs = useMemo(() => {
        return [...workLogs].sort((a, b) => {
            const dateA = parseISO(a.startDate || a.date || a.createdAt);
            const dateB = parseISO(b.startDate || b.date || b.createdAt);
            return dateB.getTime() - dateA.getTime();
        }).slice(0, 5);
    }, [workLogs]);

    const dynamicFields = useMemo(() => {
        const keys = new Set<string>();
        recentLogs.forEach(log => {
            if (log.extraData?.datos) {
                Object.keys(log.extraData.datos).forEach(k => {
                    const val = log.extraData.datos?.[k];
                    if (val !== null && val !== undefined && (val as any) !== false && val !== "") {
                        keys.add(k);
                    }
                });
            }
            if (log.extraData?.opciones) {
                Object.keys(log.extraData.opciones).forEach(k => {
                    const val = log.extraData.opciones?.[k];
                    if (val !== null && val !== undefined && val !== false) {
                        keys.add(k);
                    }
                });
            }
        });
        return Array.from(keys);
    }, [recentLogs]);

    return (
        <div className="space-y-6">
            {/* Top Stats Row (4 Columns) */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {/* 1. Monthly Revenue */}
                <Card className="bg-gradient-to-br from-white to-slate-50 border-l-4 border-l-slate-900 shadow-sm flex flex-col justify-between">
                    <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Ingresos Mensuales</CardTitle>
                            <Banknote className="h-4 w-4 text-slate-700" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-slate-900 mb-1">{formatCurrency(stats.income)}</div>
                        <p className="text-xs text-muted-foreground flex items-center">
                            {stats.percentChange >= 0 ? (
                                <ArrowUpRight className="h-4 w-4 text-emerald-600 mr-1" />
                            ) : (
                                <ArrowDownRight className="h-4 w-4 text-rose-600 mr-1" />
                            )}
                            <span className={stats.percentChange >= 0 ? "text-emerald-600 font-medium" : "text-rose-600 font-medium"}>
                                {Math.abs(stats.percentChange).toFixed(1)}%
                            </span>
                            <span className="ml-1">respecto al mes anterior</span>
                        </p>
                    </CardContent>
                </Card>

                {/* 2. Days Worked */}
                <Card className="shadow-sm flex flex-col justify-between">
                    <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Dias de Actividad</CardTitle>
                            <CalendarDays className="h-4 w-4 text-blue-500" />
                        </div>
                        <CardDescription className="text-xs">
                            {format(selectedDate, "MMMM yyyy", { locale: es })}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="w-full px-4">
                        <div className="text-3xl font-bold mb-3 text-center">
                            {stats.activeDaysCount}
                            <span className="text-lg font-normal text-muted-foreground">/{stats.totalDaysInMonth} dias</span>
                        </div>
                        <div className="w-full space-y-2">
                            <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                                <div
                                    style={{ width: `${(stats.activeDaysCount / stats.totalDaysInMonth) * 100}%` }}
                                    className="h-full bg-blue-600 transition-all duration-500"
                                    title={`Dias activos: ${stats.activeDaysCount}`}
                                />
                                <div
                                    style={{ width: `${(stats.freeDaysCount / stats.totalDaysInMonth) * 100}%` }}
                                    className="h-full bg-slate-200 transition-all duration-500"
                                    title={`Dias libres: ${stats.freeDaysCount}`}
                                />
                            </div>
                            <div className="flex items-center justify-between text-[11px] text-muted-foreground px-0.5">
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2 h-2 rounded-full bg-blue-600" />
                                    <span>Activos ({stats.activeDaysCount})</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2 h-2 rounded-full bg-slate-300" />
                                    <span>Libres ({stats.freeDaysCount})</span>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* 3. Dynamic Activity Breakdown */}
                <Card className="shadow-sm flex flex-col justify-between">
                    <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Actividad por Tipo</CardTitle>
                            <Layers className="h-4 w-4 text-violet-500" />
                        </div>
                    </CardHeader>
                    <CardContent className="flex flex-col justify-center">
                        {stats.typeBreakdown.length === 0 ? (
                            <div className="text-center py-4 text-xs text-muted-foreground">
                                Sin registros este mes
                            </div>
                        ) : (
                            <div className="space-y-2.5">
                                <div className="flex flex-wrap gap-2 justify-center">
                                    {stats.typeBreakdown.map((item) => (
                                        <div
                                            key={item.type}
                                            className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-50 border text-xs"
                                        >
                                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                                            <span className="font-medium text-slate-700">{item.label}:</span>
                                            <span className="font-bold text-slate-900">
                                                {item.unit === "hours" ? `${item.quantity.toFixed(1)}h` : item.unit === "days" ? `${item.quantity}d` : `${item.quantity} serv.`}
                                            </span>
                                        </div>
                                    ))}
                                </div>

                                <div className="text-center pt-1 border-t text-[11px] text-muted-foreground">
                                    Total de partes registrados: <span className="font-semibold text-slate-700">{stats.currentMonthLogsCount}</span>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* 4. Revenue Trend Chart */}
                <Card className="shadow-sm border-none bg-white">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Tendencia de Ingresos</CardTitle>
                        <CardDescription className="text-xs">Ultimos 6 Meses</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[100px] pt-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData}>
                                <defs>
                                    <linearGradient id="colorOverviewRevenue" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#1e293b" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#1e293b" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis dataKey="name" hide />
                                <Tooltip
                                    contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)", fontSize: "12px" }}
                                    itemStyle={{ padding: 0, fontWeight: "bold", color: "#1e293b" }}
                                    formatter={(value: number) => [formatCurrency(value), "Ingresos"]}
                                    labelFormatter={(label, payload) => {
                                        if (payload && payload.length > 0) {
                                            return payload[0].payload.fullDate;
                                        }
                                        return label;
                                    }}
                                    labelStyle={{ color: "#64748b", marginBottom: "0.25rem", fontSize: "10px" }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="total"
                                    stroke="#1e293b"
                                    strokeWidth={2}
                                    fillOpacity={1}
                                    fill="url(#colorOverviewRevenue)"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* Main Content: Recent Activity */}
            <div className="grid grid-cols-1">
                <Card className="shadow-sm flex flex-col h-full overflow-hidden">
                    <CardHeader>
                        <CardTitle>Actividad Reciente</CardTitle>
                        <CardDescription>Ultimos registros de trabajo</CardDescription>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <div className="overflow-x-auto">
                            <Table className="min-w-full">
                                <TableHeader>
                                    <TableRow className="bg-slate-900 hover:bg-slate-900 border-none">
                                        <TableHead className="text-slate-50 rounded-tl-md whitespace-nowrap">Fecha</TableHead>
                                        <TableHead className="text-slate-50 min-w-[100px]">Tipo</TableHead>
                                        <TableHead className="text-slate-50 min-w-[120px]">Descripcion</TableHead>
                                        <TableHead className="text-slate-50 min-w-[100px]">Duracion / Unidad</TableHead>
                                        {dynamicFields.map(field => {
                                            const label = field.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
                                            return (
                                                <TableHead key={field} className="text-slate-50 hidden lg:table-cell">{label}</TableHead>
                                            );
                                        })}
                                        <TableHead className="text-slate-50 hidden md:table-cell">Extras</TableHead>
                                        <TableHead className="text-slate-50 rounded-tr-md">Importe</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {recentLogs.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={6 + dynamicFields.length} className="text-center py-4 text-muted-foreground">
                                                Sin actividad reciente.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        recentLogs.map((log: any) => {
                                            const def = getDefinition(log.type, log.companyId);
                                            const isRange = def.isRange || (log.startDate && log.endDate && log.startDate !== log.endDate);

                                            return (
                                                <TableRow
                                                    key={log.id}
                                                    onClick={() => onViewLog?.(log)}
                                                    className="cursor-pointer transition-colors hover:bg-slate-200 dark:hover:bg-slate-700 even:bg-slate-100 dark:even:bg-slate-800"
                                                >
                                                    <TableCell className="py-2">
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-medium whitespace-nowrap">
                                                                {isRange && log.startDate && log.endDate
                                                                    ? `${format(parseISO(log.startDate), "dd/MM/yyyy")} - ${format(parseISO(log.endDate), "dd/MM/yyyy")}`
                                                                    : log.startDate
                                                                        ? format(parseISO(log.startDate), "dd/MM/yyyy")
                                                                        : "-"}
                                                            </span>
                                                            {log.startTime && log.endTime && (
                                                                <span className="text-xs text-muted-foreground whitespace-nowrap">
                                                                    {log.startTime} - {log.endTime}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="py-2">
                                                        <Badge variant="outline" className="font-normal capitalize">
                                                            {def.label}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell className="py-2">
                                                        <div className="max-w-[150px] md:max-w-[200px] truncate" title={log.description || ""}>
                                                            <span className="truncate block">{log.description || "-"}</span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="py-2 text-xs font-medium">
                                                        {(() => {
                                                            if (def.unit === "days" || isRange) {
                                                                const days = log.startDate && log.endDate
                                                                    ? Math.max(1, differenceInCalendarDays(parseISO(log.endDate), parseISO(log.startDate)) + 1)
                                                                    : 1;
                                                                return `${days} ${days === 1 ? "dia" : "dias"}`;
                                                            }
                                                            if (def.unit === "fixed") {
                                                                return "1 servicio";
                                                            }
                                                            const hours = Number(log.durationHours || log.duration || 0);
                                                            return hours > 0 ? `${hours}h` : "-";
                                                        })()}
                                                    </TableCell>
                                                    {dynamicFields.map(field => {
                                                        const val = log.extraData?.datos?.[field] !== undefined
                                                            ? log.extraData?.datos?.[field]
                                                            : log.extraData?.opciones?.[field];

                                                        if (val === null || val === undefined || val === false || val === "") {
                                                            return <TableCell key={field} className="py-2 hidden lg:table-cell">-</TableCell>;
                                                        }

                                                        const displayVal = typeof val === "boolean" ? "Si" : String(val);
                                                        return (
                                                            <TableCell key={field} className="py-2 hidden lg:table-cell truncate max-w-[100px]" title={displayVal}>
                                                                {displayVal}
                                                            </TableCell>
                                                        );
                                                    })}
                                                    <TableCell className="py-2 hidden md:table-cell">
                                                        <div className="flex gap-1">
                                                            {log.hasCoordination && (
                                                                <div className="p-1 bg-blue-100 text-blue-700 rounded" title="Suplemento de coordinacion">
                                                                    <Sparkles className="h-3 w-3" />
                                                                </div>
                                                            )}
                                                            {log.hasNight && (
                                                                <div className="p-1 bg-indigo-100 text-indigo-700 rounded" title="Suplemento nocturno">
                                                                    <Moon className="h-3 w-3" />
                                                                </div>
                                                            )}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="py-2 font-medium">
                                                        {(log.netAmount || log.grossAmount || log.amount)
                                                            ? formatCurrency(Number(log.netAmount || log.grossAmount || log.amount))
                                                            : "-"}
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
