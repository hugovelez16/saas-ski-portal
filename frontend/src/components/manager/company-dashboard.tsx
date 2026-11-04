"use client";

import React, { useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
    startOfDay,
    endOfDay,
    startOfWeek,
    endOfWeek,
    startOfMonth,
    endOfMonth,
    subMonths,
    startOfYear,
    endOfYear,
    format,
    parseISO,
    eachDayOfInterval,
    eachWeekOfInterval
} from "date-fns";
import { es } from "date-fns/locale";
import { DateRange } from "react-day-picker";
import { mkConfig, generateCsv, download } from "export-to-csv";
import { getAllWorkLogs } from "@/lib/api/work-logs";
import { getCompany, getCompaniesDetailed, getCompanyDashboardSummary } from "@/lib/api/companies";

// Modular Dashboard Components
import { DashboardHeaderActions } from "./dashboard/dashboard-header-actions";
import { DashboardTodayCard } from "./dashboard/dashboard-today-card";
import { DashboardKpis, DashboardPeriod, KpiSummaryData } from "./dashboard/dashboard-kpis";
import {
    DashboardCharts,
    TimeSeriesPoint,
    TypeDistributionPoint,
    WeekdayDistributionPoint
} from "./dashboard/dashboard-charts";
import { DashboardTeamTable } from "./dashboard/dashboard-team-table";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

interface CompanyDashboardProps {
    companyId: string;
    companyName: string;
}

export function CompanyDashboard({ companyId, companyName }: CompanyDashboardProps) {
    const queryClient = useQueryClient();
    const [period, setPeriod] = useState<DashboardPeriod>("month");
    const [customRange, setCustomRange] = useState<DateRange | undefined>({
        from: startOfMonth(new Date()),
        to: endOfMonth(new Date())
    });

    // 1. Compute Date Boundaries based on Period
    const dateInterval = useMemo<{ from: Date; to: Date }>(() => {
        const now = new Date();
        switch (period) {
            case "today":
                return { from: startOfDay(now), to: endOfDay(now) };
            case "week":
                return {
                    from: startOfWeek(now, { weekStartsOn: 1 }),
                    to: endOfWeek(now, { weekStartsOn: 1 })
                };
            case "month":
                return { from: startOfMonth(now), to: endOfMonth(now) };
            case "last_month": {
                const prev = subMonths(now, 1);
                return { from: startOfMonth(prev), to: endOfMonth(prev) };
            }
            case "season":
                return { from: startOfYear(now), to: endOfYear(now) };
            case "custom":
                return {
                    from: customRange?.from ? startOfDay(customRange.from) : startOfMonth(now),
                    to: customRange?.to ? endOfDay(customRange.to) : endOfMonth(now)
                };
            default:
                return { from: startOfMonth(now), to: endOfMonth(now) };
        }
    }, [period, customRange]);

    const startDateStr = format(dateInterval.from, "yyyy-MM-dd");
    const endDateStr = format(dateInterval.to, "yyyy-MM-dd");

    // 2. Fetch Company Details
    const { data: company, isLoading: loadingCompany } = useQuery({
        queryKey: ["company", companyId],
        queryFn: () => getCompany(companyId),
        enabled: !!companyId
    });

    // 3. Fetch Companies Detailed for Members and strict sorting
    const { data: companiesDetailed = [], isLoading: loadingDetailed } = useQuery({
        queryKey: ["companiesDetailed"],
        queryFn: getCompaniesDetailed
    });

    const currentCompanyDetailed = useMemo(() => {
        return companiesDetailed.find((c: any) => c.id === companyId);
    }, [companiesDetailed, companyId]);

    const members = useMemo(() => {
        return currentCompanyDetailed?.members || [];
    }, [currentCompanyDetailed]);

    const orderedMemberIds = useMemo(() => {
        if (!members.length) return [];
        return members.map((m: any) => m.userId || m.user?.id);
    }, [members]);

    const usersForDialog = useMemo(() => {
        return members.map((m: any) => m.user || { id: m.userId, firstName: "Monitor", lastName: "" });
    }, [members]);

    const worklogDefs = useMemo(() => {
        return company?.worklogDefinitions || {};
    }, [company]);

    // 4. Aggregates for the period (computed by the backend over the full range)
    const { data: summary, isLoading: loadingSummary } = useQuery({
        queryKey: ["companyDashboardSummary", companyId, startDateStr, endDateStr],
        queryFn: () => getCompanyDashboardSummary(companyId, { startDate: startDateStr, endDate: endDateStr }),
        enabled: !!companyId
    });

    // 5. Fetch Today's Logs for Real-time Operations Card (detail rows, one day)
    const todayStr = format(new Date(), "yyyy-MM-dd");
    const { data: todayLogs = [] } = useQuery({
        queryKey: ["workLogsToday", companyId, todayStr],
        queryFn: () => getAllWorkLogs({
            companyId,
            startDate: todayStr,
            endDate: todayStr
        }),
        enabled: !!companyId
    });

    // 6. KPIs from the period aggregates
    const kpis = useMemo<KpiSummaryData>(() => {
        const periodMetrics = summary?.periodMetrics;
        const totalGross = periodMetrics?.totalGross ?? 0;
        const totalNet = periodMetrics?.totalNet ?? 0;

        const isSinglePrice = company?.settings?.business_logic?.price_type === 'net';

        return {
            totalHours: periodMetrics?.totalHours ?? 0,
            totalGross,
            totalNet,
            totalLogs: periodMetrics?.totalLogs ?? 0,
            activeMembersCount: periodMetrics?.activeMembersCount ?? 0,
            daysCount: periodMetrics?.uniqueDays ?? 0,
            isSinglePrice
        };
    }, [summary, company]);

    // 7. Charts data from the period aggregates
    const timeSeriesData = useMemo<TimeSeriesPoint[]>(() => {
        return (summary?.dailyBreakdown ?? [])
            .filter(day => day.count > 0)
            .sort((a, b) => a.date.localeCompare(b.date))
            .map(day => {
                let label = day.date;
                try {
                    label = format(parseISO(day.date), "d MMM", { locale: es });
                } catch (e) {
                    label = day.date;
                }

                return {
                    date: day.date,
                    label,
                    hours: day.hours,
                    amount: day.gross
                };
            });
    }, [summary]);

    const typeDistribution = useMemo<TypeDistributionPoint[]>(() => {
        return (summary?.typeBreakdown ?? []).map(item => {
            const def = worklogDefs[item.type];
            const name = def?.label || item.label || (item.type.charAt(0).toUpperCase() + item.type.slice(1));
            return {
                typeKey: item.type,
                name,
                hours: item.hours,
                count: item.count,
                value: item.gross
            };
        });
    }, [summary, worklogDefs]);

    const weekdayDistribution = useMemo<WeekdayDistributionPoint[]>(() => {
        const days = [
            { day: "Lunes", shortDay: "Lun", hours: 0, count: 0 },
            { day: "Martes", shortDay: "Mar", hours: 0, count: 0 },
            { day: "Miércoles", shortDay: "Mié", hours: 0, count: 0 },
            { day: "Jueves", shortDay: "Jue", hours: 0, count: 0 },
            { day: "Viernes", shortDay: "Vie", hours: 0, count: 0 },
            { day: "Sábado", shortDay: "Sáb", hours: 0, count: 0 },
            { day: "Domingo", shortDay: "Dom", hours: 0, count: 0 },
        ];

        (summary?.dailyBreakdown ?? []).forEach(day => {
            try {
                const d = parseISO(day.date);
                // getDay(): 0 is Sunday, 1 is Monday ... 6 is Saturday
                const dayIndex = (d.getDay() + 6) % 7; // Convert to 0=Mon, 6=Sun
                days[dayIndex].hours += day.hours;
                days[dayIndex].count += day.count;
            } catch (e) {
                // Ignore invalid date
            }
        });

        return days;
    }, [summary]);

    // 8. Handle CSV Export (detail rows of the range, fetched on demand)
    const handleExportCsv = async () => {
        let exportRows: Awaited<ReturnType<typeof getAllWorkLogs>>;
        try {
            exportRows = await getAllWorkLogs({
                companyId,
                startDate: startDateStr,
                endDate: endDateStr
            });
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "No se pudo exportar el periodo");
            return;
        }
        if (!exportRows.length) return;

        const csvConfig = mkConfig({
            fieldSeparator: ",",
            decimalSeparator: ".",
            useKeysAsHeaders: true,
            filename: `resumen_actividad_${companyName.toLowerCase().replace(/\s+/g, '_')}_${startDateStr}_${endDateStr}`
        });

        const exportData = exportRows.map(log => {
            const member = members.find((m: any) => m.userId === log.userId || m.user?.id === log.userId);
            const userName = member ? `${member.user?.firstName || ''} ${member.user?.lastName || ''}`.trim() : log.userId;
            const typeLabel = worklogDefs[log.type]?.label || log.type;

            return {
                Fecha: log.startDate ? log.startDate.split('T')[0] : '',
                Monitor: userName,
                Tipo: typeLabel,
                Hora_Inicio: log.startTime || '',
                Hora_Fin: log.endTime || '',
                Horas: log.duration || '',
                Importe_Bruto: log.grossAmount || '',
                Importe_Neto: log.netAmount || '',
                Descripcion: log.description || ''
            };
        });

        const csv = generateCsv(csvConfig)(exportData);
        download(csvConfig)(csv);
    };

    const handleShiftCreated = () => {
        queryClient.invalidateQueries({ queryKey: ["workLogs"] });
        queryClient.invalidateQueries({ queryKey: ["workLogsToday"] });
        queryClient.invalidateQueries({ queryKey: ["companyDashboardSummary"] });
    };

    const isLoading = loadingCompany || loadingDetailed || loadingSummary;

    if (isLoading && !company) {
        return (
            <div className="p-12 flex flex-col items-center justify-center gap-3 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin text-slate-600" />
                <span className="text-sm">Cargando panel de gestión de {companyName}...</span>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header with Title and Quick Actions */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                        {companyName}
                    </h1>
                    <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                        Centro de control y gestión operativa
                    </p>
                </div>

                <DashboardHeaderActions
                    companyId={companyId}
                    companyName={companyName}
                    worklogDefinitions={worklogDefs}
                    users={usersForDialog}
                    onShiftCreated={handleShiftCreated}
                    onExportCsv={handleExportCsv}
                    canExport={(summary?.periodMetrics.totalLogs ?? 0) > 0}
                />
            </div>

            {/* Bloque A: Operativa en Tiempo Real (Hoy) */}
            <DashboardTodayCard
                companyId={companyId}
                todayLogs={todayLogs}
                members={members}
                worklogDefinitions={worklogDefs}
                isLoading={isLoading}
                onAddShiftClick={handleShiftCreated}
            />

            {/* Bloque B: KPIs y Selector de Período */}
            <DashboardKpis
                period={period}
                onPeriodChange={setPeriod}
                customDateRange={customRange}
                onCustomDateRangeChange={setCustomRange}
                kpis={kpis}
                isLoading={isLoading}
            />

            {/* Bloque C: Gráficos de Evolución y Distribución Adaptativa */}
            <DashboardCharts
                timeSeriesData={timeSeriesData}
                typeDistribution={typeDistribution}
                weekdayDistribution={weekdayDistribution}
                isLoading={isLoading}
            />

            {/* Bloque D: Resumen de Plantilla en Orden Estricto de Mánager */}
            <DashboardTeamTable
                companyId={companyId}
                members={members}
                orderedMemberIds={orderedMemberIds}
                workersSummary={summary?.workersSummary ?? []}
                isLoading={isLoading}
            />
        </div>
    );
}
