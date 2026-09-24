"use client";
export const dynamic = "force-dynamic";


import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, addDays, subDays, isSameDay, parseISO, startOfDay } from "date-fns";
import { getUsers, getUserCompanies } from "@/lib/api/users";
import { getWorkLogs, deleteWorkLog } from "@/lib/api/work-logs"; // Assuming same API, simpler to fetch all and filter
import { getCompaniesDetailed, getMyCompanies } from "@/lib/api/companies";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRouter, useSearchParams } from "next/navigation";
import { WorkLogDetailsDialog } from "@/components/work-log/details-dialog";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ManagerAddWorkLogDialog } from "@/components/work-log/manager-add-log-dialog";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { CalendarConfigProvider, useCalendarConfig } from "@/components/event-calendar/use-calendar-config";

function TimeRangeSelector() {
  const { startHour, endHour, setStartHour, setEndHour } = useCalendarConfig();

  return (
    <div className="flex items-center gap-1 sm:gap-2">
      <div className="flex items-center gap-1 text-xs sm:text-sm">
        <span className="text-muted-foreground hidden lg:inline">Desde:</span>
        <select 
          className="h-8 rounded-md border border-input bg-transparent px-2 py-1 text-xs sm:text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          value={startHour} 
          onChange={(e) => setStartHour(Number(e.target.value))}
        >
          {Array.from({ length: 24 }).map((_, i) => (
            <option key={i} value={i} disabled={i >= endHour}>{i}:00</option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-1 text-xs sm:text-sm">
        <span className="text-muted-foreground hidden lg:inline">Hasta:</span>
        <select 
          className="h-8 rounded-md border border-input bg-transparent px-2 py-1 text-xs sm:text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          value={endHour} 
          onChange={(e) => setEndHour(Number(e.target.value))}
        >
          {Array.from({ length: 24 }).map((_, i) => {
            const hour = i + 1;
            return <option key={hour} value={hour} disabled={hour <= startHour}>{hour}:00</option>
          })}
        </select>
      </div>
    </div>
  );
}

function ManagerDailyReportInner() {
    const { user: currentUser } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    // Allow pre-selection via URL, similar to Dashboard
    const initialCompanyId = searchParams.get("companyId");

    const queryClient = useQueryClient();
    const { toast } = useToast();
    const [date, setDate] = useState<Date>(new Date());
    const [selectedLog, setSelectedLog] = useState<any>(null);
    const [selectedCompanyId, setSelectedCompanyId] = useState<string>(initialCompanyId || "");
    const [applyToGroup, setApplyToGroup] = useState(false);

    // Sync state with URL if it changes (e.g. sidebar navigation)
    useEffect(() => {
        if (initialCompanyId) {
            setSelectedCompanyId(initialCompanyId);
        }
    }, [initialCompanyId]);

    // 1. Fetch My Managed Companies
    const { data: myCompanies = [], isLoading: loadingCompanies } = useQuery({
        queryFn: getMyCompanies,
        queryKey: ["myCompanies"],
    });

    const managedCompanies = useMemo(() => {
        return myCompanies.filter((c: any) => {
            const role = (c.role || c.pivot?.role || '').toLowerCase();
            const isManager = ['manager', 'admin', 'owner'].includes(role);
            const settings = c.settings || {};
            // Support both new 'modules' and legacy 'features'
            const canViewReport = (settings.modules?.worker_daily_report ?? settings.features?.worker_daily_report ?? true) === true;
            return isManager || canViewReport;
        });
    }, [myCompanies]);

    // Auto-select first company if not selected
    if (!selectedCompanyId && managedCompanies.length > 0) {
        setSelectedCompanyId(managedCompanies[0].id);
    }

    // State for Create Dialog (Controlled)
    const [createLogState, setCreateLogState] = useState<{ open: boolean, data?: Partial<any> }>({ open: false });

    // 2. Fetch Users for the selected company
    // We can use getCompaniesDetailed to get members of the selected company
    const { data: companyDetails } = useQuery({
        queryFn: getCompaniesDetailed,
        queryKey: ["companiesDetailed"],
        enabled: !!selectedCompanyId
    });

    const companyUsers = useMemo(() => {
        if (!selectedCompanyId || !companyDetails) return [];
        const company = companyDetails.find((c: any) => c.id === selectedCompanyId);
        if (!company) return [];

        // Members structure: { user_id, role, status, user: { ... } }
        return company.members.map((m: any) => ({
            ...m.user,
            relationRole: m.role,
            relationIsActive: m.isActive
        }));
    }, [companyDetails, selectedCompanyId]);


    // 3. Fetch Logs (We might need to fetch all and filter by companyId and date)
    // Ideally existing API supports companyId filter.
    // If getWorkLogs supports { companyId: ... } it's best.
    const { data: workLogs = [], isLoading: logsLoading } = useQuery({
        queryFn: () => getWorkLogs({
            startDate: format(date, 'yyyy-MM-dd'),
            endDate: format(date, 'yyyy-MM-dd'),
            limit: 2000,
            companyId: selectedCompanyId
        }),
        queryKey: ["work-logs-daily-manager", date.toISOString().split('T')[0], selectedCompanyId],
        enabled: !!selectedCompanyId
    });


    const { startHour: configStartHour, endHour: configEndHour } = useCalendarConfig();
    const hours = Array.from({ length: configEndHour - configStartHour }, (_, i) => i + configStartHour);

    const getLogsForUserAndDate = (userId: string) => {
        return workLogs.filter((log: any) => {
            // Must match user AND company (already filtered by API hopefully, but double check)
            if (log.userId !== userId) return false;
            if (log.companyId && log.companyId !== selectedCompanyId) return false;

            const logDate = log.date ? parseISO(log.date) : (log.startDate ? parseISO(log.startDate) : null);
            if (!logDate) return false;

            if (log.type === 'tutorial' && log.startDate && log.endDate) {
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
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold">Parte Diario</h1>
                    <p className="text-muted-foreground text-sm">Overview of daily activities.</p>
                </div>

                <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4">
                    <div className="flex items-center gap-2">
                        {selectedCompanyId && (
                            <Button onClick={() => setCreateLogState({ open: true, data: { companyId: selectedCompanyId } })}>
                                Add Log
                            </Button>
                        )}

                        <Button variant="outline" size="sm" onClick={() => setDate(new Date())}>
                            Today
                        </Button>
                    </div>

                    <TimeRangeSelector />

                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="icon" onClick={() => setDate(subDays(date, 1))}>
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Popover>
                            <PopoverTrigger asChild>
                                <Button variant="outline" className={cn("w-auto sm:w-[200px] justify-start text-left font-normal", !date && "text-muted-foreground")}>
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
            </div>

            {/* Matrix View */}
            {selectedCompanyId ? (
                <div className="border rounded-lg overflow-x-auto overscroll-x-none bg-card shadow-sm">
                    <div className="min-w-[1000px]">
                        {/* Header Row */}
                        <div className="flex border-b bg-muted h-10 divide-x">
                            <div className="w-12 md:w-64 flex-shrink-0 p-2 font-medium text-sm flex items-center justify-center md:justify-start sticky left-0 bg-muted z-30 shadow-[1px_0_5px_rgba(0,0,0,0.05)]">
                                <span className="md:hidden">#</span>
                                <span className="hidden md:inline">User</span>
                            </div>
                            {/* Mobile Name Column Header */}
                            <div className="md:hidden min-w-[120px] p-2 text-xs font-medium border-r flex items-center bg-muted/20">Name</div>
                            {hours.map(h => (
                                <div key={h} className="flex-1 min-w-[50px] text-center text-xs p-2 border-r last:border-r-0">
                                    {h}:00
                                </div>
                            ))}
                        </div>

                        {/* User Rows */}
                        {companyUsers.map((user: any) => {
                            const logs = getLogsForUserAndDate(user.id);
                            return (
                                <div key={user.id} className="flex border-b last:border-b-0 hover:bg-muted/5 divide-x group">
                                    <div className="w-12 md:w-64 flex-shrink-0 p-2 flex items-center gap-2 sticky left-0 bg-background z-30 group-hover:bg-muted/10 border-r shadow-[1px_0_5px_rgba(0,0,0,0.05)]">


                                        {/* Mobile View: Initials */}
                                        <div
                                            className={cn("md:hidden w-full h-full flex items-center justify-center", currentUser?.isManager ? "cursor-pointer" : "cursor-default")}
                                            onClick={() => currentUser?.isManager && router.push(`/manager/users/${user.id}`)}
                                        >
                                            <div className={cn(
                                                "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border",
                                                user.relationIsActive ? "bg-green-100 text-green-700 border-green-200" : "bg-red-100 text-red-700 border-red-200"
                                            )}>
                                                {(user.firstName?.[0] || "")}{(user.lastName?.[0] || "")}
                                            </div>
                                        </div>

                                        {/* Desktop View: Full Details */}
                                        <div
                                            className={cn("hidden md:block hover:underline truncate flex-1", currentUser?.isManager ? "cursor-pointer" : "cursor-default")}
                                            onClick={() => currentUser?.isManager && router.push(`/manager/users/${user.id}`)}
                                        >
                                            <span className="font-medium text-sm">{user.firstName} {user.lastName}</span>
                                            <div className="flex gap-1 mt-1">
                                                {user.relationIsActive ?
                                                    <div className="w-2 h-2 rounded-full bg-green-500" title="Active" /> :
                                                    <div className="w-2 h-2 rounded-full bg-red-400" title="Inactive" />
                                                }
                                                {(user.relationRole !== 'user' && user.relationRole) && <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">{user.relationRole}</Badge>}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Mobile Name Column */}
                                    <div className="md:hidden min-w-[120px] p-2 text-xs border-r flex items-center truncate bg-slate-50/50 text-muted-foreground">
                                        {user.firstName} {user.lastName}
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
                                                        companyId: selectedCompanyId,
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
                                                let startDecimal = configStartHour;
                                                let endDecimal = configEndHour;

                                                if (log.startTime && log.endTime) {
                                                    const [sh, sm] = log.startTime.split(':').map(Number);
                                                    const [eh, em] = log.endTime.split(':').map(Number);
                                                    startDecimal = sh + sm / 60;
                                                    endDecimal = eh + em / 60;
                                                } else if (log.type === 'tutorial') {
                                                    startDecimal = 9;
                                                    endDecimal = 16;
                                                }

                                                // Bounds Check
                                                if (endDecimal < configStartHour || startDecimal > configEndHour) return null;

                                                const visibleStart = Math.max(startDecimal, configStartHour);
                                                const visibleEnd = Math.min(endDecimal, configEndHour);
                                                const totalHours = configEndHour - configStartHour;

                                                // Calculate %
                                                const offset = ((visibleStart - configStartHour) / totalHours) * 100;
                                                const duration = ((visibleEnd - visibleStart) / totalHours) * 100;

                                                return (
                                                    <div
                                                        key={log.id}
                                                        className={cn(
                                                            "absolute top-1 bottom-1 rounded-sm text-xs flex items-center justify-start px-2 cursor-pointer hover:brightness-95 transition-all text-white font-bold overflow-hidden text-ellipsis whitespace-nowrap pointer-events-auto z-20",
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
            ) : (
                <div className="text-center py-12 text-muted-foreground border rounded bg-slate-50">
                    Please select a company to view the report.
                </div>
            )}

            <WorkLogDetailsDialog
                log={selectedLog}
                open={!!selectedLog}
                onOpenChange={(open) => !open && setSelectedLog(null)}
                userSettings={null}
                onEdit={(log, group) => {
                    setApplyToGroup(group);
                    setSelectedLog(null);
                    // TODO: Implement Edit Dialog here if needed
                }}
                onDelete={async (log) => {
                    if (confirm("¿Estás seguro de que deseas eliminar este registro de trabajo?")) {
                        try {
                            await deleteWorkLog(log.id);
                            toast({ title: "Éxito", description: "Registro eliminado correctamente." });
                            setSelectedLog(null);
                            queryClient.invalidateQueries({ queryKey: ["work-logs-daily-manager"] });
                        } catch (error) {
                            console.error("Error deleting work log:", error);
                            toast({ title: "Error", description: "No se pudo eliminar el registro.", variant: "destructive" });
                        }
                    }
                }}
            />

            {/* Create Dialog */}
            {selectedCompanyId && (
                <ManagerAddWorkLogDialog
                    open={createLogState.open}
                    onOpenChange={(open) => setCreateLogState(prev => ({ ...prev, open }))}
                    initialData={createLogState.data}
                    companyId={selectedCompanyId || ""}
                    companyName={managedCompanies.find(c => c.id === selectedCompanyId)?.name || "Company"}
                    worklogDefinitions={managedCompanies.find(c => c.id === selectedCompanyId)?.worklogDefinitions}
                    users={companyUsers}
                    onSuccess={() => {
                        queryClient.invalidateQueries({ queryKey: ["work-logs-daily-manager"] });
                        setCreateLogState({ open: false });
                    }}
                >
                    <span className="hidden" />
                </ManagerAddWorkLogDialog>
            )}
        </div>
    );
}

export default function ManagerDailyReportPage() {
    return (
        <CalendarConfigProvider>
            <ManagerDailyReportInner />
        </CalendarConfigProvider>
    );
}
