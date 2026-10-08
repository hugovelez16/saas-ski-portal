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
import { getWorkLogs } from "@/lib/api/work-logs";
import { getCompany, getCompaniesDetailed, getCompanyDashboardSummary } from "@/lib/api/companies";
import { WorkLog } from "@/lib/types";

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

    // 4. Fetch Work Logs for the period
    const { data: periodLogs = [], isLoading: loadingLogs } = useQuery({
        queryKey: ["workLogs", companyId, startDateStr, endDateStr],
        queryFn: () => getWorkLogs({
            companyId,
            startDate: startDateStr,
            endDate: endDateStr,
            limit: 10000
        }),
        enabled: !!companyId
    });

    // 5. Fetch Today's Logs for Real-time Operations Card
    const todayStr = format(new Date(), "yyyy-MM-dd");
    const { data: todayLogs = [] } = useQuery({
        queryKey: ["workLogsToday", companyId, todayStr],
        queryFn: () => getWorkLogs({
            companyId,
            startDate: todayStr,
            endDate: todayStr,
            limit: 1000
        }),
        enabled: !!companyId
    });

    // 6. Calculate KPIs adaptively
    const kpis = useMemo<KpiSummaryData>(() => {
        let totalHours = 0;
        let totalGross = 0;
        let totalNet = 0;
        const distinctDays = new Set<string>();
        const activeUsers = new Set<string>();

        periodLogs.forEach((log: WorkLog) => {
            activeUsers.add(log.userId);

            if (log.duration) {
                totalHours += Number(log.duration);
            } else if (log.startTime && log.endTime) {
                const [sh, sm] = log.startTime.split(':').map(Number);
                const [eh, em] = log.endTime.split(':').map(Number);
                const diff = (eh * 60 + em - (sh * 60 + sm)) / 60;
                if (diff > 0) totalHours += diff;
            }

            if (log.startDate) {
                distinctDays.add(log.startDate.split('T')[0]);
            }

            totalGross += Number(log.grossAmount || 0);
            totalNet += Number(log.netAmount || log.grossAmount || log.amount || 0);
        });

        const isSinglePrice = company?.settings?.business_logic?.price_type === 'net' ||
            company?.settings?.billing?.price_type === 'net' ||
            Math.abs(totalGross - totalNet) < 0.01;

        return {
            totalHours,
            totalGross,
            totalNet,
            totalLogs: periodLogs.length,
            activeMembersCount: activeUsers.size,
            daysCount: distinctDays.size,
            isSinglePrice
        };
    }, [periodLogs, company]);

    // 7. Calculate Charts Data
    const timeSeriesData = useMemo<TimeSeriesPoint[]>(() => {
        if (!periodLogs.length) return [];

        const dayMap: Record<string, { hours: number; amount: number }> = {};

        periodLogs.forEach(log => {
            if (!log.startDate) return;
            const dateKey = log.startDate.split('T')[0];
            if (!dayMap[dateKey]) {
                dayMap[dateKey] = { hours: 0, amount: 0 };
            }

            let dur = 0;
            if (log.duration) {
                dur = Number(log.duration);
            } else if (log.startTime && log.endTime) {
                const [sh, sm] = log.startTime.split(':').map(Number);
                const [eh, em] = log.endTime.split(':').map(Number);
                const diff = (eh * 60 + em - (sh * 60 + sm)) / 60;
                if (diff > 0) dur = diff;
            }

            dayMap[dateKey].hours += dur;
            dayMap[dateKey].amount += Number(log.grossAmount || log.netAmount || log.amount || 0);
        });

        return Object.keys(dayMap).sort().map(dKey => {
            let label = dKey;
            try {
                label = format(parseISO(dKey), "d MMM", { locale: es });
            } catch (e) {
                label = dKey;
            }

            return {
                date: dKey,
                label,
                hours: dayMap[dKey].hours,
                amount: dayMap[dKey].amount
            };
        });
    }, [periodLogs]);

    const typeDistribution = useMemo<TypeDistributionPoint[]>(() => {
        const typeMap: Record<string, { hours: number; count: number; value: number }> = {};

        periodLogs.forEach(log => {
            const tKey = log.type || 'particular';
            if (!typeMap[tKey]) {
                typeMap[tKey] = { hours: 0, count: 0, value: 0 };
            }

            let dur = 0;
            if (log.duration) {
                dur = Number(log.duration);
            } else if (log.startTime && log.endTime) {
                const [sh, sm] = log.startTime.split(':').map(Number);
                const [eh, em] = log.endTime.split(':').map(Number);
                const diff = (eh * 60 + em - (sh * 60 + sm)) / 60;
                if (diff > 0) dur = diff;
            }

            typeMap[tKey].hours += dur;
            typeMap[tKey].count += 1;
            typeMap[tKey].value += Number(log.grossAmount || log.netAmount || log.amount || 0);
        });

        return Object.entries(typeMap).map(([tKey, stats]) => {
            const def = worklogDefs[tKey];
            const name = def?.label || (tKey.charAt(0).toUpperCase() + tKey.slice(1));
            return {
                typeKey: tKey,
                name,
                hours: stats.hours,
                count: stats.count,
                value: stats.value
            };
        });
    }, [periodLogs, worklogDefs]);

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

        periodLogs.forEach(log => {
            if (!log.startDate) return;
            try {
                const d = parseISO(log.startDate);
                // getDay(): 0 is Sunday, 1 is Monday ... 6 is Saturday
                const dayIndex = (d.getDay() + 6) % 7; // Convert to 0=Mon, 6=Sun
                let dur = 0;
                if (log.duration) {
                    dur = Number(log.duration);
                } else if (log.startTime && log.endTime) {
                    const [sh, sm] = log.startTime.split(':').map(Number);
                    const [eh, em] = log.endTime.split(':').map(Number);
                    const diff = (eh * 60 + em - (sh * 60 + sm)) / 60;
                    if (diff > 0) dur = diff;
                }
                days[dayIndex].hours += dur;
                days[dayIndex].count += 1;
            } catch (e) {
                // Ignore invalid date
            }
        });

        return days;
    }, [periodLogs]);

    // 8. Handle CSV Export
    const handleExportCsv = () => {
        if (!periodLogs.length) return;

        const csvConfig = mkConfig({
            fieldSeparator: ",",
            decimalSeparator: ".",
            useKeysAsHeaders: true,
            filename: `resumen_actividad_${companyName.toLowerCase().replace(/\s+/g, '_')}_${startDateStr}_${endDateStr}`
        });

        const exportData = periodLogs.map(log => {
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
    };

    const isLoading = loadingCompany || loadingDetailed || loadingLogs;

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
                    canExport={periodLogs.length > 0}
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
                workLogs={periodLogs}
                isLoading={isLoading}
            />
        </div>
    );
}
