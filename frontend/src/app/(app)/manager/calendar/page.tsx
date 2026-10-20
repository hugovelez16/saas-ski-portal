"use client";
export const dynamic = "force-dynamic";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useEffect, useCallback } from "react";
import { type CalendarEvent, EventCalendar } from "@/components/event-calendar";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { WorkLogDetailsDialog } from "@/components/work-log/details-dialog";
import { ManagerAddWorkLogDialog } from "@/components/work-log/manager-add-log-dialog";
import { getAllWorkLogs, deleteWorkLog } from "@/lib/api/work-logs";
import { getCompaniesDetailed, getMyCompanies } from "@/lib/api/companies";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { mapMemberToLegacyRate } from "@/lib/utils/rates";
import { Calendar as CalendarIcon, Users, Building2, Loader2 } from "lucide-react";

export default function ManagerCalendarPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();
    const { user: currentUser } = useAuth();
    const { toast } = useToast();

    const [selectedLogs, setSelectedLogs] = useState<any[]>([]);
    const [isDetailsOpen, setIsDetailsOpen] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [logToEdit, setLogToEdit] = useState<any>(null);
    const [selectedDate, setSelectedDate] = useState<Date | null>(null);
    const [selectedUserIdFilter, setSelectedUserIdFilter] = useState<string>("all");

    // 1. Fetch My Managed Companies
    const { data: myCompanies = [], isLoading: loadingMyCompanies } = useQuery({
        queryFn: getMyCompanies,
        queryKey: ["myCompanies"],
    });

    const companyIdFromUrl = searchParams.get("companyId");
    const selectedCompanyId = companyIdFromUrl || (myCompanies.length > 0 ? myCompanies[0].id : null);

    // Fetch detailed companies to get members list and definitions
    const { data: companiesDetailed = [], isLoading: loadingDetailed } = useQuery({
        queryFn: getCompaniesDetailed,
        queryKey: ["companiesDetailed"],
    });

    const selectedCompany = useMemo(() => {
        return companiesDetailed.find((c: any) => c.id === selectedCompanyId);
    }, [companiesDetailed, selectedCompanyId]);

    // Rango visible del calendario (lo notifica EventCalendar); null hasta el primer render
    const [visibleRange, setVisibleRange] = useState<{ startDate: string; endDate: string } | null>(null);
    const handleRangeChange = useCallback(({ start, end }: { start: Date; end: Date }) => {
        setVisibleRange({ startDate: format(start, "yyyy-MM-dd"), endDate: format(end, "yyyy-MM-dd") });
    }, []);

    // Filas del rango visible de la empresa seleccionada
    const { data: workLogs = [], isLoading: loadingLogs, refetch: refetchWorkLogs } = useQuery({
        queryFn: () => getAllWorkLogs({
            companyId: selectedCompanyId || undefined,
            startDate: visibleRange?.startDate,
            endDate: visibleRange?.endDate,
        }),
        queryKey: ["workLogs", "manager-calendar", selectedCompanyId, visibleRange?.startDate, visibleRange?.endDate],
        enabled: !!selectedCompanyId && !!visibleRange,
    });

    // Extract members for filtering dropdown
    const companyMembers = useMemo(() => {
        if (!selectedCompany) return [];
        return selectedCompany.members.map((m: any) => ({
            ...m.user,
            relationRole: m.role,
            relationIsActive: m.isActive
        }));
    }, [selectedCompany]);

    // Format events for calendar
    const events = useMemo(() => {
        let list = [...workLogs];

        // Apply local filter by user
        if (selectedUserIdFilter && selectedUserIdFilter !== "all") {
            list = list.filter((log: any) => log.userId === selectedUserIdFilter);
        }

        return list.map((log: any) => {
            const member = selectedCompany?.members.find((m: any) => m.userId === log.userId);
            const userName = member ? `${member.user?.firstName} ${member.user?.lastName}` : "Desconocido";

            let allDay = true;
            let startTime = new Date(log.date || log.startDate);
            let endTime = new Date(log.date || log.endDate || log.startDate);

            startTime.setHours(9, 0, 0, 0);
            endTime.setHours(17, 0, 0, 0);

            if (log.startTime && log.endTime) {
                try {
                    const [startH, startM] = log.startTime.split(':').map(Number);
                    const [endH, endM] = log.endTime.split(':').map(Number);

                    if (!isNaN(startH) && !isNaN(startM) && !isNaN(endH) && !isNaN(endM)) {
                        const baseDate = new Date(log.date || log.startDate);
                        startTime = new Date(baseDate);
                        startTime.setHours(startH, startM, 0, 0);

                        endTime = new Date(baseDate);
                        endTime.setHours(endH, endM, 0, 0);

                        allDay = false;
                    }
                } catch (e) {
                    console.error("Error parsing times for log", log.id, e);
                }
            } else if (log.type === "tutorial" && log.startDate && log.endDate) {
                startTime = new Date(log.startDate);
                endTime = new Date(log.endDate);
            }

            let color = "sky";
            if (log.type === "Vacaciones") color = "emerald";
            else if (log.type === "Baja médica") color = "rose";
            else if (log.type === "Asuntos propios") color = "amber";
            else if (log.type === "tutorial") color = "purple";

            return {
                allDay,
                color: color as any,
                description: log.description || log.notes,
                end: endTime,
                id: log.id,
                start: startTime,
                title: `${userName}: ${log.description || log.type}`,
                extendedProps: log,
            };
        });
    }, [workLogs, selectedCompany, selectedUserIdFilter]);

    const handleEventClick = (event: CalendarEvent) => {
        const extendedEvent = event as CalendarEvent & { extendedProps: any };
        if (extendedEvent.extendedProps) {
            setSelectedLogs([extendedEvent.extendedProps]);
            setIsDetailsOpen(true);
        }
    };

    const handleDateClick = (date: Date) => {
        setSelectedDate(date);
        setIsCreateOpen(true);
    };

    // Reset user filter if company changes
    useEffect(() => {
        setSelectedUserIdFilter("all");
    }, [selectedCompanyId]);

    if (loadingMyCompanies || loadingDetailed) {
        return (
            <div className="flex flex-1 items-center justify-center text-muted-foreground p-8">
                <Loader2 className="mr-2 h-6 w-6 animate-spin text-indigo-600" />
                Cargando datos del calendario...
            </div>
        );
    }

    if (!selectedCompanyId) {
        return (
            <div className="flex flex-1 flex-col items-center justify-center p-8 text-center text-muted-foreground">
                <Building2 className="h-12 w-12 mb-4 opacity-20" />
                <p className="font-semibold text-lg">Sin empresa seleccionada</p>
                <p className="text-sm">Por favor, selecciona una empresa para acceder al calendario.</p>
            </div>
        );
    }

    return (
        <div className="flex flex-1 flex-col gap-4 p-4 md:gap-8 md:p-8 h-full bg-slate-50/30 dark:bg-slate-950/20">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
                        <CalendarIcon className="h-7 w-7 text-indigo-600" />
                        Calendario de Equipo
                    </h1>
                    <p className="text-muted-foreground text-sm">Visualización mensual de los partes y turnos de trabajo de tu equipo.</p>
                </div>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4">
                    {/* User Filter Dropdown */}
                    <div className="flex items-center gap-2 min-w-[200px]">
                        <Label htmlFor="user-filter" className="text-xs font-bold text-muted-foreground uppercase whitespace-nowrap">Miembro:</Label>
                        <Select value={selectedUserIdFilter} onValueChange={setSelectedUserIdFilter}>
                            <SelectTrigger id="user-filter" className="h-9 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
                                <SelectValue placeholder="Filtrar por miembro" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Todos los miembros</SelectItem>
                                {companyMembers.map((m: any) => (
                                    <SelectItem key={m.id} value={m.id}>
                                        {m.firstName} {m.lastName}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <Button onClick={() => { setSelectedDate(null); setIsCreateOpen(true); }} className="bg-indigo-600 hover:bg-indigo-700 shadow-md">
                        Añadir Registro
                    </Button>
                </div>
            </div>

            {/* Calendar Grid */}
            <div className="flex-1 min-h-[500px] h-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
                <EventCalendar
                    events={events}
                    initialView="month"
                    onEventClick={handleEventClick}
                    onDateClick={handleDateClick}
                    onRangeChange={handleRangeChange}
                    showAddButton={false}
                />
            </div>

            {/* Event Details Dialog */}
            <WorkLogDetailsDialog
                open={isDetailsOpen}
                onOpenChange={setIsDetailsOpen}
                log={selectedLogs[0]}
                userSettings={
                    selectedLogs[0] && selectedCompany?.members
                        ? (() => {
                            const m = selectedCompany.members.find((m: any) => m.userId === selectedLogs[0].userId);
                            return m ? mapMemberToLegacyRate(m) : null;
                          })()
                        : null
                }
                onEdit={(log) => {
                    setIsDetailsOpen(false);
                    setLogToEdit(log);
                    setIsCreateOpen(true);
                }}
                onDelete={async (log) => {
                    if (confirm("¿Estás seguro de que deseas eliminar este registro de trabajo?")) {
                        try {
                            await deleteWorkLog(log.id);
                            toast({ title: "Éxito", description: "Registro eliminado correctamente." });
                            setIsDetailsOpen(false);
                            refetchWorkLogs();
                            queryClient.invalidateQueries({ queryKey: ["work-logs-daily-manager"] });
                        } catch (error) {
                            console.error("Error deleting work log:", error);
                            toast({ title: "Error", description: "No se pudo eliminar el registro.", variant: "destructive" });
                        }
                    }
                }}
            />

            {/* Add/Edit Log Dialog */}
            <ManagerAddWorkLogDialog
                open={isCreateOpen}
                onOpenChange={(open) => {
                    setIsCreateOpen(open);
                    if (!open) {
                        setLogToEdit(null);
                        setSelectedDate(null);
                    }
                }}
                companyId={selectedCompanyId}
                companyName={selectedCompany?.name || "Empresa"}
                worklogDefinitions={selectedCompany?.worklogDefinitions}
                users={companyMembers}
                initialData={logToEdit || (selectedDate ? { startDate: format(selectedDate, 'yyyy-MM-dd'), date: format(selectedDate, 'yyyy-MM-dd') } : undefined)}
                onSuccess={() => {
                    refetchWorkLogs();
                    queryClient.invalidateQueries({ queryKey: ["work-logs-daily-manager"] });
                    setLogToEdit(null);
                    setSelectedDate(null);
                }}
            >
                <span className="hidden" />
            </ManagerAddWorkLogDialog>
        </div>
    );
}
