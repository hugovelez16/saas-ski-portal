"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { WorkLog } from "@/lib/types";
import { Users, Clock, ArrowRight, Activity, CalendarCheck2 } from "lucide-react";

interface DashboardTodayCardProps {
    companyId: string;
    todayLogs: WorkLog[];
    members: any[];
    worklogDefinitions?: Record<string, any>;
    isLoading?: boolean;
    onAddShiftClick?: () => void;
}

export function DashboardTodayCard({
    companyId,
    todayLogs,
    members,
    worklogDefinitions,
    isLoading,
    onAddShiftClick
}: DashboardTodayCardProps) {
    const todayFormatted = format(new Date(), "EEEE, d 'de' MMMM 'de' yyyy", { locale: es });

    // Map logs with member details
    const enrichedLogs = useMemo(() => {
        return todayLogs.map(log => {
            const member = members.find(m => m.userId === log.userId || m.user?.id === log.userId);
            const user = member?.user || {};
            const fullName = `${user.firstName || ''} ${user.lastName || ''}`.trim() || 'Monitor';
            const initials = `${(user.firstName?.[0] || 'M')}${(user.lastName?.[0] || '')}`.toUpperCase();
            return {
                ...log,
                fullName,
                initials,
                userEmail: user.email,
                role: member?.role || 'worker'
            };
        }).sort((a, b) => {
            const timeA = a.startTime || '00:00';
            const timeB = b.startTime || '00:00';
            return timeA.localeCompare(timeB);
        });
    }, [todayLogs, members]);

    // Unique active members working today
    const activeInstructorsToday = useMemo(() => {
        const set = new Set<string>();
        todayLogs.forEach(l => set.add(l.userId));
        return set.size;
    }, [todayLogs]);

    // Total scheduled hours today
    const totalHoursToday = useMemo(() => {
        return todayLogs.reduce((acc, log) => {
            if (log.duration) return acc + Number(log.duration);
            if (log.startTime && log.endTime) {
                const [sh, sm] = log.startTime.split(':').map(Number);
                const [eh, em] = log.endTime.split(':').map(Number);
                const diff = (eh * 60 + em - (sh * 60 + sm)) / 60;
                return acc + (diff > 0 ? diff : 0);
            }
            return acc;
        }, 0);
    }, [todayLogs]);

    // Grouping by type
    const typesSummary = useMemo(() => {
        const counts: Record<string, number> = {};
        todayLogs.forEach(log => {
            const typeKey = log.type || 'particular';
            counts[typeKey] = (counts[typeKey] || 0) + 1;
        });
        return Object.entries(counts).map(([typeKey, count]) => {
            const def = worklogDefinitions?.[typeKey];
            return {
                typeKey,
                label: def?.label || (typeKey.charAt(0).toUpperCase() + typeKey.slice(1)),
                count
            };
        });
    }, [todayLogs, worklogDefinitions]);

    return (
        <Card className="border-slate-200 dark:border-slate-800 shadow-sm bg-gradient-to-br from-white to-slate-50 dark:from-slate-950 dark:to-slate-900/60">
            <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800/80">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                        <div className="h-8 w-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                            <Activity className="h-4 w-4" />
                        </div>
                        <div>
                            <CardTitle className="text-base font-semibold text-slate-900 dark:text-slate-100">
                                Operativa en Tiempo Real (Hoy)
                            </CardTitle>
                            <CardDescription className="text-xs capitalize text-muted-foreground">
                                {todayFormatted}
                            </CardDescription>
                        </div>
                    </div>

                    <Button asChild variant="outline" size="sm" className="h-8 text-xs font-medium self-start sm:self-auto">
                        <Link href={`/manager/daily-reports?companyId=${companyId}`}>
                            Planning Diario
                            <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                        </Link>
                    </Button>
                </div>
            </CardHeader>

            <CardContent className="pt-4">
                {/* Metric Strip */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    <div className="p-3 rounded-lg bg-slate-100/60 dark:bg-slate-900/60 border border-slate-200/50 dark:border-slate-800/50">
                        <div className="flex items-center justify-between text-muted-foreground mb-1">
                            <span className="text-xs font-medium">Monitores Hoy</span>
                            <Users className="h-3.5 w-3.5 text-indigo-500" />
                        </div>
                        <div className="text-xl font-bold text-slate-900 dark:text-slate-100">
                            {activeInstructorsToday}
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-0.5">En pista / activos</p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-100/60 dark:bg-slate-900/60 border border-slate-200/50 dark:border-slate-800/50">
                        <div className="flex items-center justify-between text-muted-foreground mb-1">
                            <span className="text-xs font-medium">Horas Programadas</span>
                            <Clock className="h-3.5 w-3.5 text-blue-500" />
                        </div>
                        <div className="text-xl font-bold text-slate-900 dark:text-slate-100">
                            {totalHoursToday.toFixed(1)} h
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-0.5">Jornada total hoy</p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-100/60 dark:bg-slate-900/60 border border-slate-200/50 dark:border-slate-800/50">
                        <div className="flex items-center justify-between text-muted-foreground mb-1">
                            <span className="text-xs font-medium">Turnos / Servicios</span>
                            <CalendarCheck2 className="h-3.5 w-3.5 text-emerald-500" />
                        </div>
                        <div className="text-xl font-bold text-slate-900 dark:text-slate-100">
                            {todayLogs.length}
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-0.5">Registros del día</p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-100/60 dark:bg-slate-900/60 border border-slate-200/50 dark:border-slate-800/50">
                        <div className="text-xs font-medium text-muted-foreground mb-1">Desglose Turnos</div>
                        <div className="flex flex-wrap gap-1 mt-0.5">
                            {typesSummary.length > 0 ? (
                                typesSummary.map(item => (
                                    <Badge key={item.typeKey} variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
                                        {item.count} {item.label}
                                    </Badge>
                                ))
                            ) : (
                                <span className="text-xs text-muted-foreground italic">Sin actividad</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Timeline / Live Shift Preview */}
                {enrichedLogs.length === 0 ? (
                    <div className="text-center py-6 px-4 rounded-lg border border-dashed border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20">
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            No hay turnos programados para la jornada de hoy.
                        </p>
                        <p className="text-xs text-muted-foreground mt-1 mb-3">
                            Puedes registrar los partes de hoy o acceder al planning interactivo.
                        </p>
                        {onAddShiftClick && (
                            <Button size="sm" variant="outline" onClick={onAddShiftClick} className="text-xs h-8">
                                Añadir Registro
                            </Button>
                        )}
                    </div>
                ) : (
                    <div className="space-y-2">
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-1">
                            Turnos programados ({enrichedLogs.length})
                        </div>
                        <div className="max-h-[220px] overflow-y-auto space-y-2 pr-1">
                            {enrichedLogs.map(log => {
                                const typeLabel = worklogDefinitions?.[log.type]?.label || log.type;
                                const timeStr = log.startTime && log.endTime
                                    ? `${log.startTime} - ${log.endTime}`
                                    : (log.duration ? `${log.duration} horas` : 'Jornada completa');

                                return (
                                    <div
                                        key={log.id}
                                        className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/80 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors text-xs"
                                    >
                                        <div className="flex items-center gap-2.5 min-w-0">
                                            <Avatar className="h-7 w-7 border border-slate-200 dark:border-slate-700">
                                                <AvatarFallback className="text-[11px] font-medium bg-slate-100 dark:bg-slate-800">
                                                    {log.initials}
                                                </AvatarFallback>
                                            </Avatar>
                                            <div className="min-w-0">
                                                <p className="font-medium text-slate-900 dark:text-slate-100 truncate">
                                                    {log.fullName}
                                                </p>
                                                <p className="text-[11px] text-muted-foreground truncate">
                                                    {log.description || log.extraData?.client || 'Sin notas adicionales'}
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-2 flex-shrink-0">
                                            <Badge variant="outline" className="capitalize text-[10px] px-1.5 h-5">
                                                {typeLabel}
                                            </Badge>
                                            <div className="font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-[11px]">
                                                {timeStr}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
