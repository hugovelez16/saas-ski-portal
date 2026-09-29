"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { WorkLog, Company } from "@/lib/types";
import { useMemo } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/data-table";
import { XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, CartesianGrid } from "recharts";
import { format, subMonths, startOfMonth, endOfMonth, eachMonthOfInterval, eachDayOfInterval, eachWeekOfInterval, isSameDay, endOfWeek, startOfWeek, parseISO, differenceInCalendarDays } from "date-fns";
import { es } from "date-fns/locale";
import { formatCurrency } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface AnalyticsV2Props {
    workLogs: WorkLog[];
    selectedDate: Date;
    companies?: Company[];
    activeCompanyId?: string | null;
}

export function AnalyticsV2({ workLogs, selectedDate, companies = [], activeCompanyId }: AnalyticsV2Props) {
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

    // 1. Monthly Income Data
    const monthlyData = useMemo(() => {
        const end = selectedDate;
        const start = subMonths(end, 5);
        const months = eachMonthOfInterval({ start, end });

        return months.map(month => {
            const monthStart = startOfMonth(month);
            const monthEnd = endOfMonth(month);

            const income = workLogs
                .filter(log => {
                    const dateStr = log.startDate || log.date || log.createdAt;
                    if (!dateStr) return false;
                    const d = parseISO(dateStr);
                    return d >= monthStart && d <= monthEnd;
                })
                .reduce((acc, log) => acc + (Number(log.netAmount ?? log.grossAmount ?? log.amount) || 0), 0);

            return {
                name: format(month, "MMMM yyyy", { locale: es }),
                shortName: format(month, "MMM", { locale: es }),
                income,
            };
        }).reverse();
    }, [workLogs, selectedDate]);

    // 2. Weekly Income (Last 5 Months)
    const weeklyData = useMemo(() => {
        const now = selectedDate;
        const start = subMonths(now, 5);
        const intervalStart = startOfWeek(start, { weekStartsOn: 1 });
        const end = endOfWeek(now, { weekStartsOn: 1 });

        const weeks = eachWeekOfInterval({ start: intervalStart, end }, { weekStartsOn: 1 });

        return weeks.map((weekStart) => {
            const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });

            const income = workLogs
                .filter(log => {
                    const dateStr = log.startDate || log.date || log.createdAt;
                    if (!dateStr) return false;
                    const d = parseISO(dateStr);
                    return d >= weekStart && d <= weekEnd;
                })
                .reduce((acc, log) => acc + (Number(log.netAmount ?? log.grossAmount ?? log.amount) || 0), 0);

            return {
                name: format(weekStart, "d MMM", { locale: es }),
                fullName: `${format(weekStart, "d MMM", { locale: es })} - ${format(weekEnd, "d MMM", { locale: es })}`,
                income,
                month: format(weekStart, "MMM", { locale: es }),
            };
        });
    }, [workLogs, selectedDate]);

    // 3. Dynamic Daily Effort (Current Month)
    const dailyEffortData = useMemo(() => {
        const now = selectedDate;
        const start = startOfMonth(now);
        const end = endOfMonth(now);
        const days = eachDayOfInterval({ start, end });

        return days.map(day => {
            let totalHours = 0;
            let activeEventsCount = 0;

            workLogs.forEach(log => {
                const def = getDefinition(log.type, log.companyId);

                if (def.unit === "days" || def.isRange) {
                    if (log.startDate && log.endDate) {
                        try {
                            const rangeStart = parseISO(log.startDate);
                            const rangeEnd = parseISO(log.endDate);
                            rangeStart.setHours(0, 0, 0, 0);
                            rangeEnd.setHours(23, 59, 59, 999);
                            const dayCheck = new Date(day);
                            dayCheck.setHours(12, 0, 0, 0);
                            if (dayCheck >= rangeStart && dayCheck <= rangeEnd) {
                                activeEventsCount += 1;
                            }
                        } catch {
                            // Ignorar fechas invalidas
                        }
                    } else if (log.startDate) {
                        if (isSameDay(parseISO(log.startDate), day)) {
                            activeEventsCount += 1;
                        }
                    }
                } else if (def.unit === "fixed") {
                    const dateStr = log.startDate || log.date;
                    if (dateStr && isSameDay(parseISO(dateStr), day)) {
                        activeEventsCount += 1;
                    }
                } else {
                    // Hours unit
                    const dateStr = log.startDate || log.date;
                    if (dateStr && isSameDay(parseISO(dateStr), day)) {
                        totalHours += Number(log.durationHours || log.duration || 0);
                        activeEventsCount += 1;
                    }
                }
            });

            return {
                day: format(day, "dd"),
                fullDate: format(day, "d MMMM", { locale: es }),
                hours: totalHours,
                events: activeEventsCount,
            };
        });
    }, [workLogs, selectedDate, companies, activeCompany]);

    // 4. Monthly Summary by Shift Type
    const typeBreakdownData = useMemo(() => {
        const currentMonth = selectedDate.getMonth();
        const currentYear = selectedDate.getFullYear();

        const currentMonthLogs = workLogs.filter(log => {
            const dateStr = log.startDate || log.date || log.createdAt;
            if (!dateStr) return false;
            const d = parseISO(dateStr);
            return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
        });

        const map = new Map<string, {
            type: string;
            label: string;
            unit: string;
            quantity: number;
            count: number;
            totalAmount: number;
        }>();

        currentMonthLogs.forEach(log => {
            const def = getDefinition(log.type, log.companyId);
            const amount = Number(log.netAmount ?? log.grossAmount ?? log.amount) || 0;

            let qty = 0;
            if (def.unit === "days" || def.isRange) {
                if (log.startDate && log.endDate && log.startDate !== log.endDate) {
                    try {
                        qty = Math.max(1, differenceInCalendarDays(parseISO(log.endDate), parseISO(log.startDate)) + 1);
                    } catch {
                        qty = 1;
                    }
                } else {
                    qty = 1;
                }
            } else if (def.unit === "fixed") {
                qty = 1;
            } else {
                qty = Number(log.durationHours || log.duration || 0);
            }

            const item = map.get(log.type) || {
                type: log.type,
                label: def.label,
                unit: def.unit,
                quantity: 0,
                count: 0,
                totalAmount: 0,
            };

            item.quantity += qty;
            item.count += 1;
            item.totalAmount += amount;
            map.set(log.type, item);
        });

        return Array.from(map.values());
    }, [workLogs, selectedDate, companies, activeCompany]);

    return (
        <div className="space-y-6">
            {/* Combined View: Weekly Chart + Monthly Table */}
            <Card className="shadow-sm border-none bg-slate-50/50">
                <CardHeader>
                    <CardTitle>Evolucion de Ingresos</CardTitle>
                    <CardDescription>Progresion semanal (ultimos 5 meses) frente a totales mensuales</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col lg:flex-row gap-6">
                        {/* Weekly Chart */}
                        <div className="w-full lg:flex-1 h-[250px] min-w-0">
                            <h4 className="text-sm font-semibold mb-4 text-muted-foreground">Tendencia de Ingresos Semanales</h4>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={weeklyData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                                    <defs>
                                        <linearGradient id="colorIncomeLong" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                    <XAxis
                                        dataKey="name"
                                        stroke="#888888"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                        interval={3}
                                    />
                                    <YAxis
                                        stroke="#888888"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(v) => `€${v}`}
                                    />
                                    <Tooltip
                                        contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }}
                                        formatter={(value: number) => [formatCurrency(value), "Ingresos"]}
                                        labelFormatter={(label, payload) => {
                                            if (payload && payload.length > 0) return payload[0].payload.fullName;
                                            return label;
                                        }}
                                    />
                                    <Area type="monotone" dataKey="income" stroke="#10b981" strokeWidth={3} fill="url(#colorIncomeLong)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Separator */}
                        <div className="w-full h-px lg:w-px lg:h-auto bg-slate-200" />

                        {/* Monthly Table */}
                        <div className="lg:w-[300px]">
                            <h4 className="text-sm font-semibold mb-4 text-muted-foreground">Totales Mensuales</h4>
                            <div className="border rounded-md bg-white overflow-hidden">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-slate-50">
                                            <TableHead>Mes</TableHead>
                                            <TableHead className="text-right">Ingresos</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {monthlyData.map((data) => (
                                            <TableRow key={data.name}>
                                                <TableCell className="font-medium text-xs capitalize">{data.name}</TableCell>
                                                <TableCell className="text-right font-bold text-slate-700 text-xs">
                                                    {formatCurrency(data.income)}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Daily Hours / Activity Chart */}
            <Card className="shadow-sm border-none bg-slate-50/50">
                <CardHeader>
                    <CardTitle>Actividad Diaria del Mes</CardTitle>
                    <CardDescription>
                        Horas de trabajo computadas por dia en {format(selectedDate, "MMMM yyyy", { locale: es })}
                    </CardDescription>
                </CardHeader>
                <CardContent className="h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={dailyEffortData}>
                            <defs>
                                <linearGradient id="colorHoursDaily" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                            <XAxis
                                dataKey="day"
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(v) => `${v}h`}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#fff", border: "1px solid #e2e8f0", borderRadius: "8px", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }}
                                itemStyle={{ color: "#0f172a", fontWeight: "bold" }}
                                formatter={(value: number) => [`${value}h`, "Horas"]}
                                labelFormatter={(label) => `Dia ${label}`}
                            />
                            <Area
                                type="monotone"
                                dataKey="hours"
                                stroke="#3b82f6"
                                strokeWidth={3}
                                fillOpacity={1}
                                fill="url(#colorHoursDaily)"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            {/* Monthly Breakdown Table by Shift Type */}
            {typeBreakdownData.length > 0 && (
                <Card className="shadow-sm border-none bg-slate-50/50">
                    <CardHeader>
                        <CardTitle>Desglose por Tipo de Turno</CardTitle>
                        <CardDescription>Resumen de unidades registradas y facturacion del mes actual</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="border rounded-md bg-white overflow-hidden">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-slate-50">
                                        <TableHead>Tipo de Turno</TableHead>
                                        <TableHead>Unidad</TableHead>
                                        <TableHead className="text-right">Partes</TableHead>
                                        <TableHead className="text-right">Cantidad Total</TableHead>
                                        <TableHead className="text-right">Importe Generado</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {typeBreakdownData.map((item) => (
                                        <TableRow key={item.type}>
                                            <TableCell className="font-medium text-xs">
                                                <Badge variant="outline" className="font-normal capitalize">
                                                    {item.label}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-xs text-muted-foreground uppercase">{item.unit}</TableCell>
                                            <TableCell className="text-right font-medium text-xs">{item.count}</TableCell>
                                            <TableCell className="text-right font-bold text-slate-800 text-xs">
                                                {item.unit === "hours" ? `${item.quantity.toFixed(1)} h` : item.unit === "days" ? `${item.quantity} dias` : `${item.quantity} serv.`}
                                            </TableCell>
                                            <TableCell className="text-right font-bold text-emerald-700 text-xs">
                                                {formatCurrency(item.totalAmount)}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}