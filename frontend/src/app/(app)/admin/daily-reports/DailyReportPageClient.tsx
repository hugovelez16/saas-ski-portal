"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, addDays, subDays, isSameDay, parseISO, startOfDay } from "date-fns";
import { getUsers, getUserCompanies } from "@/lib/api/users";
import { getCompaniesDetailed, getDailyReport } from "@/lib/api/companies";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, ArrowUp, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRouter, useSearchParams } from "next/navigation";
import { WorkLogDetailsDialog } from "@/components/work-log/details-dialog";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ManagerAddWorkLogDialog } from "@/components/work-log/manager-add-log-dialog";
import { useQueryClient } from "@tanstack/react-query";
import type { DailyReportLog, DailyReportMember, DailyReportWorkType } from "@/lib/types";

export default function DailyReportPage() {
    const router = useRouter();
    const queryClient = useQueryClient();
    const [date, setDate] = useState<Date>(new Date());
    const [selectedLog, setSelectedLog] = useState<any>(null);
    const [createLogState, setCreateLogState] = useState<{ open: boolean, data?: Partial<any> }>({ open: false });
    const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

    // 1. Lista de empresas (selector y nombres)
    const { data: companies = [], isLoading: loadingCompanies } = useQuery({
        queryFn: getCompaniesDetailed,
        queryKey: ["companies-detailed-admin"],
    });

    // Empresa activa: la elegida o, por defecto, la primera de la lista
    const activeCompanyId = selectedCompanyId || companies[0]?.id || "";
    const activeCompany = companies.find((c) => c.id === activeCompanyId);
    const dateKey = format(date, 'yyyy-MM-dd');

    // 2. Parte diario de la empresa activa (miembros, tipos de turno y turnos del dia)
    const { data: dailyReport, isLoading: loadingReport } = useQuery({
        queryFn: () => getDailyReport(activeCompanyId, dateKey),
        queryKey: ["daily-report", activeCompanyId, dateKey],
        enabled: !!activeCompanyId,
    });

    const workLogs: DailyReportLog[] = dailyReport?.logs ?? [];
    const workTypes: Record<string, DailyReportWorkType> = dailyReport?.workTypes ?? {};

    // Activos primero por rol y estado; gestores y administradores al final
    const sortedMembers = useMemo(() => {
        const getPriority = (m: DailyReportMember) => {
            if (m.role === 'manager' || m.role === 'admin') return 3;
            if (!m.isActive) return 2;
            return 1;
        };

        return [...(dailyReport?.members ?? [])].sort((a, b) => {
            const pA = getPriority(a);
            const pB = getPriority(b);
            if (pA !== pB) return pA - pB;

            return (a.firstName || "").localeCompare(b.firstName || "");
        });
    }, [dailyReport]);

    const companyUsers = useMemo(() => {
        return (dailyReport?.members ?? []).map((m) => ({
            id: m.userId,
            firstName: m.firstName,
            lastName: m.lastName,
        }));
    }, [dailyReport]);

    const hours = Array.from({ length: 12 }, (_, i) => i + 8);

    const getLogsForUserAndDate = (userId: string) => {
        return workLogs.filter((log) => {
            if (log.userId !== userId) return false;
            if (log.companyId !== activeCompanyId) return false;

            const def = workTypes[log.type];
            const isCrossDay = Boolean(
                (log.startDate && log.endDate && log.startDate !== log.endDate) ||
                def?.unit === 'days'
            );

            if (isCrossDay && log.startDate && log.endDate) {
                const s = startOfDay(parseISO(log.startDate));
                const e = startOfDay(parseISO(log.endDate));
                const currentDay = startOfDay(date);
                return currentDay >= s && currentDay <= e;
            }

            return isSameDay(parseISO(log.startDate), date);
        });
    };

    if (loadingCompanies) return <div className="p-8">Loading...</div>;

    return (
        <div className="space-y-8">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold">Admin Daily Report</h1>
                    <p className="text-muted-foreground text-sm">Overview of activities by company.</p>
                </div>

                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => setDate(new Date())}>
                        Today
                    </Button>
                    <Button variant="outline" size="icon" onClick={() => setDate(subDays(date, 1))}>
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Popover>
                        <PopoverTrigger asChild>
                            <Button variant="outline" className={cn("w-[200px] justify-start text-left font-normal", !date && "text-muted-foreground")}>
                                <CalendarIcon className="mr-2 h-4 w-4" />
                                {date ? format(date, "PPP") : <span>Pick a date</span>}
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0">
                            <Calendar mode="single" selected={date} onSelect={(d) => d && setDate(d)} initialFocus />
                        </PopoverContent>
                    </Popover>
                    <Button variant="outline" size="icon" onClick={() => setDate(addDays(date, 1))}>
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Selector de empresa */}
            {companies.length > 0 ? (
                <div className="flex flex-wrap items-center gap-4">
                    <Select value={activeCompanyId} onValueChange={setSelectedCompanyId}>
                        <SelectTrigger className="w-[280px]">
                            <SelectValue placeholder="Selecciona una empresa" />
                        </SelectTrigger>
                        <SelectContent>
                            {companies.map((c) => (
                                <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Badge variant="outline">{sortedMembers.length} Users</Badge>
                    <Button size="sm" variant="secondary" onClick={() => setCreateLogState({ open: true, data: { companyId: activeCompanyId } })}>
                        Add Log
                    </Button>
                </div>
            ) : (
                <div className="text-center py-12 text-muted-foreground border rounded bg-slate-50">
                    No hay empresas disponibles.
                </div>
            )}

            {activeCompanyId && (
                <div className="space-y-4">
                    <h2 className="text-xl font-semibold">{activeCompany?.name}</h2>

                    {loadingReport ? (
                        <div className="p-8">Loading...</div>
                    ) : (
                        <div className="border rounded-lg overflow-x-auto bg-card shadow-sm">
                            <div className="min-w-[1000px]">
                                {/* Header Row */}
                                <div className="flex border-b bg-muted/40 h-10 divide-x">
                                    <div className="w-64 flex-shrink-0 p-2 font-medium text-sm flex items-center sticky left-0 bg-muted/40 z-10">User</div>
                                    {hours.map(h => (
                                        <div key={h} className="flex-1 min-w-[50px] text-center text-xs p-2 border-r last:border-r-0">
                                            {h}:00
                                        </div>
                                    ))}
                                </div>

                                {/* User Rows */}
                                {sortedMembers.map((member) => {
                                    const logs = getLogsForUserAndDate(member.userId);
                                    return (
                                        <div key={member.userId} className="flex border-b last:border-b-0 hover:bg-muted/5 divide-x group">
                                            <div className="w-64 flex-shrink-0 p-2 flex items-center gap-2 sticky left-0 bg-background z-10 group-hover:bg-muted/10 border-r">
                                                <div
                                                    className="cursor-pointer hover:underline truncate flex-1"
                                                    onClick={() => router.push(`/admin/users/${member.userId}`)}
                                                >
                                                    <span className="font-medium text-sm">{member.firstName} {member.lastName} ({logs.length})</span>
                                                    <div className="flex gap-1 mt-1">
                                                        {member.isActive ?
                                                            <div className="w-2 h-2 rounded-full bg-green-500" title="Active" /> :
                                                            <div className="w-2 h-2 rounded-full bg-red-400" title="Inactive" />
                                                        }
                                                        {(member.role !== 'user' && member.role) && <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">{member.role}</Badge>}
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex-1 relative h-12 flex">
                                                {/* Clickable Grid Background */}
                                                {hours.map(h => (
                                                    <div
                                                        key={h}
                                                        className="flex-1 border-r border-slate-100 last:border-r-0 hover:bg-blue-50/50 cursor-pointer transition-colors"
                                                        onClick={() => setCreateLogState({
                                                            open: true,
                                                            data: {
                                                                userId: member.userId,
                                                                companyId: activeCompanyId,
                                                                date: dateKey,
                                                                startTime: `${h.toString().padStart(2, '0')}:00`,
                                                                endTime: `${(h + 1).toString().padStart(2, '0')}:00`,
                                                                type: 'particular'
                                                            }
                                                        })}
                                                        title={`Add log for ${h}:00`}
                                                    />
                                                ))}

                                                {/* Logs Overlay */}
                                                <div className="absolute inset-0 pointer-events-none">
                                                    {logs.map((log) => {
                                                        let startDecimal = 8;
                                                        let endDecimal = 19;

                                                        if (log.startTime && log.endTime) {
                                                            const [sh, sm] = log.startTime.split(':').map(Number);
                                                            const [eh, em] = log.endTime.split(':').map(Number);
                                                            startDecimal = sh + sm / 60;
                                                            endDecimal = eh + em / 60;
                                                        } else if (log.type === 'tutorial') {
                                                            startDecimal = 9;
                                                            endDecimal = 16;
                                                        }

                                                        // Clamp to visible grid range without silently discarding early morning or night shifts
                                                        const clampedStart = Math.min(Math.max(startDecimal, 8), 20);
                                                        const clampedEnd = Math.min(Math.max(endDecimal, 8), 20);
                                                        const totalHours = 12; // 8:00 to 20:00

                                                        // Ensure visual representation for shifts at boundaries
                                                        const rawOffset = ((clampedStart - 8) / totalHours) * 100;
                                                        const rawDuration = ((clampedEnd - clampedStart) / totalHours) * 100;
                                                        const offset = Math.min(rawOffset, 96);
                                                        const duration = Math.min(Math.max(rawDuration, 4), 100 - offset);

                                                        return (
                                                            <div
                                                                key={log.id}
                                                                className={cn(
                                                                    "absolute top-1 bottom-1 rounded-sm text-xs flex items-center justify-start px-2 cursor-pointer hover:brightness-95 transition-all text-white font-bold overflow-hidden whitespace-nowrap pointer-events-auto z-20",
                                                                    log.type === 'tutorial' ? "bg-purple-500 opacity-80" : "bg-blue-600"
                                                                )}
                                                                style={{ left: `${offset}%`, width: `${duration}%` }}
                                                                onClick={(e) => {
                                                                    e.stopPropagation(); // Prevent grid click
                                                                    setSelectedLog(log);
                                                                }}
                                                                title={`${log.description || 'Work Log'} (${log.startTime} - ${log.endTime})`}
                                                            >
                                                                {log.description || log.type}
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}

            <WorkLogDetailsDialog
                log={selectedLog}
                open={!!selectedLog}
                onOpenChange={(open) => !open && setSelectedLog(null)}
                userSettings={null}
            />

            {/* Create Dialog */}
            <ManagerAddWorkLogDialog
                open={createLogState.open}
                onOpenChange={(open) => setCreateLogState(prev => ({ ...prev, open }))}
                initialData={createLogState.data}
                companyId={activeCompanyId}
                companyName={activeCompany?.name || "Company"}
                worklogDefinitions={workTypes}
                users={companyUsers}
                onSuccess={() => {
                    queryClient.invalidateQueries({ queryKey: ["daily-report"] });
                    setCreateLogState({ open: false });
                }}
            >
                <span className="hidden" />
            </ManagerAddWorkLogDialog>
        </div>
    );
}
