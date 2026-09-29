"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, addDays, subDays, isSameDay, parseISO, startOfDay } from "date-fns";
import { getUsers, getUserCompanies } from "@/lib/api/users";
import { getWorkLogs } from "@/lib/api/work-logs";
import { getCompaniesDetailed } from "@/lib/api/companies";
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

export default function DailyReportPage() {
    const router = useRouter();
    const queryClient = useQueryClient();
    const [date, setDate] = useState<Date>(new Date());
    const [selectedLog, setSelectedLog] = useState<any>(null);
    const [createLogState, setCreateLogState] = useState<{ open: boolean, data?: Partial<any> }>({ open: false });

    // 1. Fetch All Companies (Admin View)
    const { data: companies = [], isLoading: loadingCompanies } = useQuery({
        queryFn: getCompaniesDetailed,
        queryKey: ["companies-detailed-admin"],
    });

    // 2. Fetch Logs (Filtered by Date, ALL companies)
    // We increased the limit to ensure we get logs for all companies
    const { data: workLogs = [], isLoading: loadingLogs } = useQuery({
        queryFn: () => getWorkLogs({
            startDate: format(date, 'yyyy-MM-dd'),
            endDate: format(date, 'yyyy-MM-dd'),
            limit: 2000
        }),
        queryKey: ["work-logs-daily-admin", format(date, 'yyyy-MM-dd')],
    });

    // Helper to sort users per company
    const getSortedUsers = (company: any) => {
        if (!company || !company.members) return [];

        let users = company.members.map((m: any) => ({
            ...m.user,
            relationRole: m.role,
            relationStatus: m.status
        }));

        users.sort((a: any, b: any) => {
            const getPriority = (u: any) => {
                if (u.relationRole === 'manager' || u.relationRole === 'admin') return 3;
                if (u.relationStatus !== 'active') return 2;
                return 1;
            };

            const pA = getPriority(a);
            const pB = getPriority(b);
            if (pA !== pB) return pA - pB;

            return (a.firstName || "").localeCompare(b.firstName || "");
        });
        return users;
    };

    const hours = Array.from({ length: 12 }, (_, i) => i + 8);

    const getLogsForUserAndDate = (userId: string, companyId: string) => {
        return workLogs.filter((log: any) => {
            if (log.userId !== userId) return false;

            const logCompanyId = log.companyId;
            if (logCompanyId && logCompanyId !== companyId) return false;

            const logDate = log.date ? parseISO(log.date) : (log.startDate ? parseISO(log.startDate) : null);
            if (!logDate) return false;

            const company = companies.find((c: any) => c.id === companyId);
            const def = company?.worklogDefinitions?.[log.type];
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

            return isSameDay(logDate, date);
        });
    };

    if (loadingCompanies) return <div className="p-8">Loading...</div>;

    return (
        <div className="space-y-8">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold">Admin Daily Report</h1>
                    <p className="text-muted-foreground text-sm">Overview of activities across all companies.</p>
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

            {/* List of Companies */}
            {companies.map((company: any) => {
                const sortedUsers = getSortedUsers(company);
                // Can filter out empty companies if desired: if (sortedUsers.length === 0) return null;

                return (
                    <div key={company.id} className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <h2 className="text-xl font-semibold">{company.name}</h2>
                                <Badge variant="outline">{sortedUsers.length} Users</Badge>
                            </div>
                            <Button size="sm" variant="secondary" onClick={() => setCreateLogState({ open: true, data: { companyId: company.id } })}>
                                Add Log
                            </Button>
                        </div>

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
                                {sortedUsers.map((user: any) => {
                                    const logs = getLogsForUserAndDate(user.id, company.id);
                                    return (
                                        <div key={user.id} className="flex border-b last:border-b-0 hover:bg-muted/5 divide-x group">
                                            <div className="w-64 flex-shrink-0 p-2 flex items-center gap-2 sticky left-0 bg-background z-10 group-hover:bg-muted/10 border-r">
                                                <div
                                                    className="cursor-pointer hover:underline truncate flex-1"
                                                    onClick={() => router.push(`/admin/users/${user.id}`)}
                                                >
                                                    <span className="font-medium text-sm">{user.firstName} {user.lastName} ({logs.length})</span>
                                                    <div className="flex gap-1 mt-1">
                                                        {user.relationStatus === 'active' ?
                                                            <div className="w-2 h-2 rounded-full bg-green-500" title="Active" /> :
                                                            <div className="w-2 h-2 rounded-full bg-red-400" title="Inactive" />
                                                        }
                                                        {(user.relationRole !== 'user' && user.relationRole) && <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">{user.relationRole}</Badge>}
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
                                                                userId: user.id,
                                                                companyId: company.id,
                                                                date: format(date, 'yyyy-MM-dd'),
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
                                                    {logs.map((log: any) => {
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
                    </div>
                );
            })}

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
                companyId={createLogState.data?.companyId || ""}
                companyName={companies.find(c => c.id === createLogState.data?.companyId)?.name || "Company"}
                users={
                    companies.find((c: any) => c.id === createLogState.data?.companyId)?.members.map((m: any) => m.user) || []
                }
                onSuccess={() => {
                    queryClient.invalidateQueries({ queryKey: ["work-logs-daily-admin"] });
                    setCreateLogState({ open: false });
                }}
            >
                <span className="hidden" />
            </ManagerAddWorkLogDialog>
        </div>
    );
}
