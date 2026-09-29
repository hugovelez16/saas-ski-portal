"use client";

import React, { useState } from "react";
import {
    AreaChart,
    Area,
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export interface TimeSeriesPoint {
    date: string;
    label: string;
    hours: number;
    amount: number;
}

export interface TypeDistributionPoint {
    typeKey: string;
    name: string;
    hours: number;
    count: number;
    value: number;
}

export interface WeekdayDistributionPoint {
    day: string;
    shortDay: string;
    hours: number;
    count: number;
}

interface DashboardChartsProps {
    timeSeriesData: TimeSeriesPoint[];
    typeDistribution: TypeDistributionPoint[];
    weekdayDistribution: WeekdayDistributionPoint[];
    isLoading?: boolean;
}

const PIE_COLORS = [
    "#3b82f6", // Blue
    "#8b5cf6", // Purple
    "#10b981", // Emerald
    "#f59e0b", // Amber
    "#06b6d4", // Cyan
    "#ec4899", // Pink
    "#64748b"  // Slate
];

export function DashboardCharts({
    timeSeriesData,
    typeDistribution,
    weekdayDistribution,
    isLoading
}: DashboardChartsProps) {
    const [trendMetric, setTrendMetric] = useState<"hours" | "amount">("hours");

    // Adaptive condition: If 2 or more types with activity, show type distribution; otherwise show weekly load
    const activeTypesCount = typeDistribution.filter(t => t.hours > 0 || t.count > 0).length;
    const showTypeDistribution = activeTypesCount >= 2;

    return (
        <div className="grid gap-6 grid-cols-1 lg:grid-cols-7">
            {/* Grafico 1: Evolucion Temporal (4 columnas) */}
            <Card className="lg:col-span-4 border-slate-200 dark:border-slate-800 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <div>
                        <CardTitle className="text-base font-semibold text-slate-900 dark:text-slate-100">
                            Evolución de Actividad
                        </CardTitle>
                        <CardDescription className="text-xs text-muted-foreground">
                            Tendencia en el período seleccionado
                        </CardDescription>
                    </div>

                    {/* Selector de metrica */}
                    <div className="flex items-center bg-slate-100 dark:bg-slate-800 p-0.5 rounded-lg border border-slate-200 dark:border-slate-700">
                        <Button
                            variant={trendMetric === "hours" ? "default" : "ghost"}
                            size="sm"
                            onClick={() => setTrendMetric("hours")}
                            className={`h-7 px-2.5 text-xs font-medium ${
                                trendMetric === "hours"
                                    ? "bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100 shadow-xs"
                                    : "text-slate-600 dark:text-slate-400"
                            }`}
                        >
                            Horas
                        </Button>
                        <Button
                            variant={trendMetric === "amount" ? "default" : "ghost"}
                            size="sm"
                            onClick={() => setTrendMetric("amount")}
                            className={`h-7 px-2.5 text-xs font-medium ${
                                trendMetric === "amount"
                                    ? "bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100 shadow-xs"
                                    : "text-slate-600 dark:text-slate-400"
                            }`}
                        >
                            Coste (€)
                        </Button>
                    </div>
                </CardHeader>

                <CardContent className="pt-4 pl-0 pr-4">
                    <div className="h-[280px] w-full">
                        {timeSeriesData.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-xs text-muted-foreground italic">
                                No hay datos de actividad para graficar en este período.
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={timeSeriesData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id="colorMetric" x1="0" y1="0" x2="0" y2="1">
                                            <stop
                                                offset="5%"
                                                stopColor={trendMetric === "hours" ? "#3b82f6" : "#10b981"}
                                                stopOpacity={0.3}
                                            />
                                            <stop
                                                offset="95%"
                                                stopColor={trendMetric === "hours" ? "#3b82f6" : "#10b981"}
                                                stopOpacity={0}
                                            />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                    <XAxis
                                        dataKey="label"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 11, fill: "#64748b" }}
                                        minTickGap={25}
                                    />
                                    <YAxis
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 11, fill: "#64748b" }}
                                        tickFormatter={(v) => (trendMetric === "hours" ? `${v}h` : `${v}€`)}
                                    />
                                    <Tooltip
                                        formatter={(val: number) => [
                                            trendMetric === "hours" ? `${Number(val).toFixed(1)} horas` : `${Number(val).toFixed(2)} €`,
                                            trendMetric === "hours" ? "Horas" : "Importe"
                                        ]}
                                        labelFormatter={(l) => `Fecha: ${l}`}
                                        contentStyle={{
                                            borderRadius: "8px",
                                            border: "1px solid #e2e8f0",
                                            backgroundColor: "#ffffff",
                                            fontSize: "12px",
                                            boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                                        }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey={trendMetric === "hours" ? "hours" : "amount"}
                                        stroke={trendMetric === "hours" ? "#2563eb" : "#059669"}
                                        strokeWidth={2.5}
                                        fillOpacity={1}
                                        fill="url(#colorMetric)"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Grafico 2 Adaptativo: Distribucion por tipo o Carga semanal (3 columnas) */}
            <Card className="lg:col-span-3 border-slate-200 dark:border-slate-800 shadow-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-base font-semibold text-slate-900 dark:text-slate-100">
                        {showTypeDistribution ? "Distribución por Tipo de Turno" : "Carga por Día de la Semana"}
                    </CardTitle>
                    <CardDescription className="text-xs text-muted-foreground">
                        {showTypeDistribution
                            ? "Proporción de horas según tipo de clase/servicio"
                            : "Distribución acumulada de Lunes a Domingo"}
                    </CardDescription>
                </CardHeader>

                <CardContent className="pt-4">
                    <div className="h-[280px] w-full">
                        {showTypeDistribution ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={typeDistribution.filter(t => t.hours > 0)}
                                        dataKey="hours"
                                        nameKey="name"
                                        cx="50%"
                                        cy="45%"
                                        innerRadius={55}
                                        outerRadius={85}
                                        paddingAngle={4}
                                    >
                                        {typeDistribution.map((entry, index) => (
                                            <Cell key={`cell-${entry.typeKey}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        formatter={(val: number, name: string) => [`${Number(val).toFixed(1)} h`, name]}
                                        contentStyle={{
                                            borderRadius: "8px",
                                            border: "1px solid #e2e8f0",
                                            backgroundColor: "#ffffff",
                                            fontSize: "12px",
                                            boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                                        }}
                                    />
                                    <Legend
                                        verticalAlign="bottom"
                                        height={36}
                                        iconType="circle"
                                        formatter={(value) => <span className="text-xs text-slate-700 dark:text-slate-300">{value}</span>}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={weekdayDistribution} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                    <XAxis
                                        dataKey="shortDay"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 11, fill: "#64748b" }}
                                    />
                                    <YAxis
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 11, fill: "#64748b" }}
                                        tickFormatter={(v) => `${v}h`}
                                    />
                                    <Tooltip
                                        formatter={(val: number) => [`${Number(val).toFixed(1)} horas`, "Horas acumuladas"]}
                                        labelFormatter={(day) => `Día: ${day}`}
                                        contentStyle={{
                                            borderRadius: "8px",
                                            border: "1px solid #e2e8f0",
                                            backgroundColor: "#ffffff",
                                            fontSize: "12px",
                                            boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                                        }}
                                    />
                                    <Bar
                                        dataKey="hours"
                                        fill="#3b82f6"
                                        radius={[4, 4, 0, 0]}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
