"use client";
export const dynamic = "force-dynamic";


import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getCompaniesDetailed } from "@/lib/api/companies";
import { useAuth } from "@/context/AuthContext";
import api, { describeLoadError } from "@/lib/api";
import { useState, useMemo } from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/data-table";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Loader2, ArrowUp, ArrowDown, ArrowUpDown, User as UserIcon, Calendar, Sparkles, Moon } from "lucide-react";
import { FilterBar, FilterConfig } from "@/components/ui/filter-bar";
import { WorkLogsTable } from "@/components/work-log/work-logs-table";
import { Badge } from "@/components/ui/badge";
import { WorkLog } from "@/lib/types";

export default function ManagerShiftsPage() {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [filters, setFilters] = useState<Record<string, any>>({});

    // Fetch companies
    const { data: companies = [], isLoading: loadingCompanies } = useQuery({
        queryFn: getCompaniesDetailed,
        queryKey: ["companiesDetailed"],
    });

    const selectedCompanyId = user?.activeCompanyId || null;

    const { data: workLogs = [], isLoading: loadingLogs, error: logsError } = useQuery({
        queryFn: async () => {
            if (!selectedCompanyId) return [];
            const res = await api.get<WorkLog[]>(`/work-logs?company_id=${selectedCompanyId}`);
            return res.data;
        },
        queryKey: ["companyWorkLogs", selectedCompanyId],
        enabled: !!selectedCompanyId
    });

    const selectedCompany = useMemo(() => companies.find(c => c.id === selectedCompanyId), [companies, selectedCompanyId]);

    const memberOptions = useMemo(() => {
        if (!selectedCompany) return [];
        return selectedCompany.members
            .filter(m => m.user)
            .map(m => ({
                label: `${m.user!.firstName} ${m.user!.lastName}`,
                value: m.userId
            }));
    }, [selectedCompany]);

    const typeOptions = useMemo(() => {
        if (!selectedCompany?.worklogDefinitions) {
            return [
                { label: "Particular", value: "particular" },
                { label: "Tutorial", value: "tutorial" }
            ];
        }
        return Object.keys(selectedCompany.worklogDefinitions).map(key => ({
            label: key.charAt(0).toUpperCase() + key.slice(1),
            value: key
        }));
    }, [selectedCompany]);

    const logsWithMeta = useMemo(() => {
        return workLogs.map(log => {
            const member = selectedCompany?.members.find(m => m.userId === log.userId);
            return {
                ...log,
                userName: member ? `${member.user?.firstName} ${member.user?.lastName}` : 'Desconocido',
                userEmail: member?.user?.email
            };
        }).filter(log => {
            if (filters.userId && filters.userId.length > 0 && !filters.userId.includes(log.userId)) return false;
            if (filters.type && filters.type.length > 0 && !filters.type.includes(log.type)) return false;
            if (filters.date) {
                const { from, to } = filters.date;
                const d = new Date(log.startDate);
                if (from && d < from) return false;
                if (to && d > to) return false;
            }
            return true;
        });
    }, [workLogs, selectedCompany, filters]);



    if (loadingCompanies) {
        return <div className="p-8 flex items-center justify-center text-muted-foreground"><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Cargando empresas...</div>;
    }

    const filterConfig: FilterConfig[] = [
        { id: "date", label: "Rango de fechas", type: "date-range" },
        { id: "userId", label: "Usuario", type: "select", options: memberOptions },
        { id: "type", label: "Tipo", type: "select", options: typeOptions },
    ];

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Turnos y Partes</h1>
                <p className="text-muted-foreground">Visualiza y gestiona los partes de trabajo de tus empresas.</p>
            </div>

            <div className="space-y-4">
                <FilterBar config={filterConfig} onFilterChange={setFilters} />

                <WorkLogsTable
                    data={logsWithMeta}
                    companies={companies}
                    fixedCompanyId={selectedCompanyId || undefined}
                    showUserColumn={true}
                    readOnly={false}
                    onUpdate={() => {
                        queryClient.invalidateQueries({ queryKey: ["companyWorkLogs", selectedCompanyId] });
                    }}
                    isLoading={loadingLogs}
                    error={logsError ? describeLoadError(logsError, "No se pudieron cargar los turnos.") : null}
                />

                <div className="text-xs text-muted-foreground text-right">
                    Mostrando {logsWithMeta.length} registros
                </div>
            </div>
        </div>
    );
}
