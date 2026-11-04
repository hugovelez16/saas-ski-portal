"use client";
export const dynamic = "force-dynamic";


import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getUsers, getUser, getUserCompanies } from "@/lib/api/users";
import { getWorkLogs, deleteWorkLog } from "@/lib/api/work-logs";
import { getMyCompanies, updateMemberRates, updateMemberStatus } from "@/lib/api/companies";
import { usePermissions } from "@/hooks/use-permissions";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Calendar, Building2, Clock, User as UserIcon, CheckCircle, XCircle, ArrowUp, ArrowDown, ArrowUpDown, ChevronLeft, ChevronRight, Sparkles, Moon, Pencil, Trash2, Wallet, Database, Loader2, Shield } from "lucide-react";
import { format, subMonths, addMonths, parseISO, differenceInCalendarDays } from "date-fns";
import { WorkLogsTable } from "@/components/work-log/work-logs-table";
import { FilterBar, FilterConfig } from "@/components/ui/filter-bar";
import { useState, useMemo, use, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { WorkLogDetailsDialog } from "@/components/work-log/details-dialog";
import { UserCreateWorkLogDialog } from "@/components/work-log/user-dialog";
import { useToast } from "@/hooks/use-toast";
import { User, WorkLog } from "@/lib/types";
import { OverviewV3 } from "@/components/dashboard/overview-v2";
import { AnalyticsV2 as AnalyticsV3 } from "@/components/dashboard/analytics-v2";
import { mapMemberToLegacyRate } from "@/lib/utils/rates";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { TaxOverridesFields, compactTaxOverrides } from "@/components/admin/tax-overrides-fields";

const numericSchema = z.preprocess(
    (val) => (val === "" || val === undefined || val === null ? 0 : val),
    z.coerce.number().min(0)
);

const memberConfigSchema = z.object({
    role: z.string(),
    isActive: z.boolean(),
    isGross: z.boolean(),
    rates: z.record(numericSchema),
    // Fracciones 0..1 o null (sin override); NaN = entrada invalida en pantalla
    taxOverrides: z.record(z.number().min(0).max(1).nullable())
});

type MemberConfigValues = z.infer<typeof memberConfigSchema>;

function CompanyMemberConfigCard({ user, company, onUpdate }: { user: any, company: any, onUpdate: () => void }) {
    const { toast } = useToast();
    const { canManageMembers } = usePermissions();
    const worklogDefinitionsStr = JSON.stringify(company.worklogDefinitions || {});
    const ratesConfigStr = JSON.stringify(company.ratesConfig || {});

    const worklogDefinitions = useMemo(() => {
        return company.worklogDefinitions || {};
    }, [worklogDefinitionsStr]);

    const form = useForm<MemberConfigValues>({
        resolver: zodResolver(memberConfigSchema),
        defaultValues: {
            role: company.role || "worker",
            isActive: company.isActiveMember ?? true,
            isGross: false,
            rates: {},
            taxOverrides: {}
        }
    });

    useEffect(() => {
        const definitions = JSON.parse(worklogDefinitionsStr);
        const rates = JSON.parse(ratesConfigStr);
        const shiftKeys = Object.keys(definitions);
        const initialRates: Record<string, number> = {};
        let isGross = false;
        let taxOverrides: Record<string, number | null> = {};

        let foundTaxes = false;
        for (const key of shiftKeys) {
            const shiftData = rates[key];
            if (shiftData && typeof shiftData === 'object') {
                initialRates[key] = shiftData.base_rate || 0;
                if (!foundTaxes) {
                    isGross = shiftData.is_gross !== undefined ? shiftData.is_gross : false;
                    if (shiftData.tax_overrides) {
                        taxOverrides = { ...shiftData.tax_overrides };
                        foundTaxes = true;
                    }
                }
            } else {
                initialRates[key] = 0;
            }
        }

        form.reset({
            role: company.role || "worker",
            isActive: company.isActiveMember ?? true,
            isGross,
            rates: initialRates,
            taxOverrides
        });
    }, [company.id, company.role, company.isActiveMember, worklogDefinitionsStr, ratesConfigStr, form]);

    const mutation = useMutation({
        mutationFn: async (data: { isActive?: boolean; ratesConfig: Record<string, any> }) => {
            if (canManageMembers && data.isActive !== undefined && data.isActive !== (company.isActiveMember ?? true)) {
                await updateMemberStatus(company.id, user.id, data.isActive ? "active" : "inactive");
            }
            return updateMemberRates(company.id, user.id, data.ratesConfig);
        },
        onSuccess: () => {
            toast({ title: "Configuración actualizada" });
            onUpdate();
        },    });

    function onSubmit(values: MemberConfigValues) {
        const newRatesConfig: Record<string, any> = {};
        const shiftKeys = Object.keys(worklogDefinitions);

        for (const key of shiftKeys) {
            newRatesConfig[key] = {
                base_rate: Number(values.rates[key]) || 0,
                is_gross: values.isGross,
                tax_overrides: compactTaxOverrides(values.taxOverrides)
            };
        }

        mutation.mutate({
            isActive: values.isActive,
            ratesConfig: newRatesConfig
        });
    }

    const onFormError = (errors: any) => {
        console.error("Form validation errors:", errors);
        toast({
            title: "Error de validación",
            description: "Por favor, revisa los campos del formulario.",
            variant: "destructive"
        });
    };

    return (
        <Card className="border-indigo-100 dark:border-indigo-900 shadow-sm overflow-hidden bg-white/50 dark:bg-slate-950/50 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between bg-indigo-50/30 dark:bg-indigo-950/10 border-b">
                <div className="flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-indigo-600" />
                    <div>
                        <CardTitle className="text-lg">{company.name}</CardTitle>
                        <CardDescription className="text-xs">ID: {company.id}</CardDescription>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <Badge variant={company.isActiveMember ? 'default' : 'secondary'}>
                        {company.isActiveMember ? 'Activo' : 'Inactivo'}
                    </Badge>
                    <Badge variant="outline" className="capitalize">{company.role}</Badge>
                </div>
            </CardHeader>
            <CardContent className="pt-6">
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit, onFormError)} className="space-y-8">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="md:col-span-1 space-y-4">
                                <h3 className="text-sm font-semibold flex items-center gap-2 text-indigo-600">
                                    <Shield className="h-4 w-4" />
                                    Membresía
                                </h3>
                                <div className="space-y-1">
                                    <label className="text-xs uppercase text-muted-foreground font-bold tracking-wider">Rol en Empresa</label>
                                    <div className="pt-1">
                                        <Badge variant="outline" className="text-xs font-medium">
                                            {company.role === 'admin' ? 'Administrador' : company.role === 'manager' ? 'Gestor' : 'Trabajador'}
                                        </Badge>
                                    </div>
                                </div>
                                {canManageMembers && (
                                    <FormField
                                        control={form.control}
                                        name="isActive"
                                        render={({ field }) => (
                                            <FormItem className="flex flex-row items-center justify-between rounded-md border bg-slate-50 dark:bg-slate-900 px-3 py-2">
                                                <div className="space-y-0.5">
                                                    <FormLabel className="text-sm">Usuario Activo</FormLabel>
                                                    <FormDescription className="text-[10px]">Permitir registros</FormDescription>
                                                </div>
                                                <FormControl>
                                                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                                                </FormControl>
                                            </FormItem>
                                        )}
                                    />
                                )}
                            </div>

                            <div className="md:col-span-2 space-y-4">
                                <h3 className="text-sm font-semibold flex items-center gap-2 text-indigo-600">
                                    <Wallet className="h-4 w-4" />
                                    Tarifas por Turno
                                </h3>
                                <div className="grid grid-cols-2 gap-4">
                                    {Object.entries(worklogDefinitions).map(([key, def]: [string, any]) => (
                                        <FormField
                                            key={key}
                                            control={form.control}
                                            name={`rates.${key}`}
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel className="text-xs uppercase text-muted-foreground font-bold tracking-wider">{def.label}</FormLabel>
                                                    <FormControl>
                                                        <div className="relative">
                                                            <span className="absolute left-3 top-2 text-muted-foreground text-xs">€</span>
                                                            <Input 
                                                                type="number" 
                                                                step="0.01" 
                                                                {...field} 
                                                                value={field.value ?? ""} 
                                                                onChange={field.onChange}
                                                                className="pl-7 h-9" 
                                                            />
                                                        </div>
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4 border-t pt-6">
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="text-sm font-semibold flex items-center gap-2 text-indigo-600">
                                    <Database className="h-4 w-4" />
                                    Impuestos y Deducciones (Per-User)
                                </h3>
                                <FormField
                                    control={form.control}
                                    name="isGross"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-row items-center gap-2 space-y-0">
                                            <FormLabel className="text-xs font-bold text-muted-foreground">{field.value ? "Tarifa bruta (se descuentan los impuestos)" : "Tarifa neta (sin deduccion)"}</FormLabel>
                                            <FormControl>
                                                <Switch checked={field.value} onCheckedChange={field.onChange} />
                                            </FormControl>
                                        </FormItem>
                                    )}
                                />
                            </div>

                            {form.watch("isGross") && (
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                    <FormField
                                        control={form.control}
                                        name="taxOverrides"
                                        render={({ field }) => (
                                            <FormItem className="sm:col-span-3">
                                                <TaxOverridesFields
                                                    companyTaxConfig={company.taxConfig || {}}
                                                    value={field.value || {}}
                                                    onChange={field.onChange}
                                                />
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end pt-2">
                            <Button type="submit" disabled={mutation.isPending} className="bg-indigo-600 hover:bg-indigo-700 shadow-md transition-all">
                                {mutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Pencil className="mr-2 h-4 w-4" />}
                                Actualizar Configuración en {company.name}
                            </Button>
                        </div>
                    </form>
                </Form>
            </CardContent>
        </Card>
    );
}

export default function ManagerUserDetailsPage({ params }: { params: Promise<{ userId: string }> }) {
    const { userId } = use(params);
    const router = useRouter();
    const { user: currentUser } = useAuth();
    const activeCompanyId = currentUser?.activeCompanyId ?? null;

    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [filters, setFilters] = useState<Record<string, any>>({});
    const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);
    const [selectedLog, setSelectedLog] = useState<WorkLog | null>(null);

    // Dashboard State
    const [dashboardTab, setDashboardTab] = useState("overview");
    const [selectedDate, setSelectedDate] = useState(new Date());
    const handlePrevMonth = () => setSelectedDate(prev => subMonths(prev, 1));
    const handleNextMonth = () => setSelectedDate(prev => addMonths(prev, 1));

    const handleLogUpdate = () => {
        queryClient.invalidateQueries({ queryKey: ["workLogs", userId] });
    };

    // Fetch user-specific data
    const { data: user, isLoading: isLoadingUser, isError: isErrorUser, error: errorUser } = useQuery({
        queryFn: () => getUser(userId),
        queryKey: ["user", userId],
        retry: 1
    });

    const { data: companies = [], isLoading: isLoadingCompanies } = useQuery({
        queryFn: () => getUserCompanies(userId),
        queryKey: ["userCompanies", userId],
        enabled: !!user
    });

    const { data: memberConfigs = [] } = useQuery({
        queryFn: () => getUserCompanies(userId),
        queryKey: ["userMemberConfigs", userId],
        enabled: !!user
    });

    const { data: workLogs = [], isLoading: isLoadingLogs, isError: isLogsError, error: logsError } = useQuery({
        queryFn: () => getWorkLogs({ userId: userId }), // Filter by this user
        queryKey: ["workLogs", userId],
        enabled: !!user
    });

    // Fetch Logged-in Manager's companies for visibility restriction
    const { data: myCompanies = [] } = useQuery({
        queryFn: getMyCompanies,
        queryKey: ["myCompanies"],
    });

    // Filtering Logic: Only show companies (and associated data) that the manager manages
    // Filtering Logic: Only show companies (and associated data) that the manager manages
    const visibleCompanies = useMemo(() => {
        // Strict filtering: If myCompanies is empty, show nothing.
        // This prevents "Global Admin" leakage in the Manager view.
        if (myCompanies.length === 0) return [];

        // 1. Filter by Manager's managed companies
        let filtered = companies.filter((c: any) => myCompanies.some((mc: any) => mc.id === c.id));

        // 2. Strict filtering: If there is an active company, ONLY show that company.
        if (activeCompanyId) {
            filtered = filtered.filter((c: any) => c.id === activeCompanyId);
        }

        return filtered;
    }, [companies, myCompanies, activeCompanyId]);

    // Derived lists based on visibleCompanies
    const visibleRates = useMemo(() => {
        return memberConfigs.filter((m: any) => visibleCompanies.some((c: any) => c.id === m.id));
    }, [memberConfigs, visibleCompanies]);

    const visibleWorkLogs = useMemo(() => {
        return workLogs.filter((log: any) =>
            Boolean(log.companyId) && visibleCompanies.some((c: any) => c.id === log.companyId)
        );
    }, [workLogs, visibleCompanies]);

    // Effective User Settings Logic (Top Level)
    const effectiveUserSettings = useMemo(() => {
        if (!selectedLog) return null;
        if (!memberConfigs || !companies) return null;

        const member = memberConfigs.find((m: any) => m.id === selectedLog.companyId);
        if (!member) return null;

        return mapMemberToLegacyRate(member);
    }, [selectedLog, memberConfigs, companies]);

    const filteredLogs = useMemo(() => {
        let result = [...visibleWorkLogs];
        if (filters.date) {
            const { from, to } = filters.date;
            result = result.filter((log: any) => {
                const date = new Date(log.date || log.startDate);
                return (!from || date >= from) && (!to || date <= to);
            });
        }

        // Sorting
        if (sortConfig) {
            result.sort((a, b) => {
                let aVal: any = "";
                let bVal: any = "";

                // Resolve values based on key
                switch (sortConfig.key) {
                    case 'date':
                        aVal = a.type === 'tutorial' ? a.startDate : a.date;
                        bVal = b.type === 'tutorial' ? b.startDate : b.date;
                        break;
                    case 'type':
                        aVal = a.type;
                        bVal = b.type;
                        break;
                    case 'company':
                        aVal = companies.find((c: any) => c.id === a.companyId)?.name || "";
                        bVal = companies.find((c: any) => c.id === b.companyId)?.name || "";
                        break;
                    case 'duration':
                        if (a.durationHours !== undefined || a.duration !== undefined || (a.startTime && a.endTime)) {
                            aVal = Number(a.durationHours ?? a.duration) || 0;
                        } else {
                            aVal = a.startDate && a.endDate
                                ? (new Date(a.endDate).getTime() - new Date(a.startDate).getTime())
                                : 0;
                        }

                        if (b.durationHours !== undefined || b.duration !== undefined || (b.startTime && b.endTime)) {
                            bVal = Number(b.durationHours ?? b.duration) || 0;
                        } else {
                            bVal = b.startDate && b.endDate
                                ? (new Date(b.endDate).getTime() - new Date(b.startDate).getTime())
                                : 0;
                        }
                        break;
                    case 'amount':
                        aVal = Number(a.amount) || 0;
                        bVal = Number(b.amount) || 0;
                        break;
                    case 'createdAt':
                        aVal = a.createdAt || "";
                        bVal = b.createdAt || "";
                        break;
                    default:
                        aVal = "";
                        bVal = "";
                }

                if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        } else {
            // Default: Newest first
            result.sort((a, b) => new Date(b.date || b.startDate).getTime() - new Date(a.date || a.startDate).getTime());
        }

        return result;
    }, [visibleWorkLogs, filters, sortConfig, companies]);


    // Stats Calculation
    const stats = useMemo(() => {
        const now = new Date();
        const currentMonth = now.getMonth();
        const currentYear = now.getFullYear();
        const currentMonthName = format(now, 'MMMM');

        const uniqueDays = new Set<string>();
        let totalParticularHours = 0;
        let totalTutorialDays = 0;

        workLogs.forEach((log: any) => {
            const logDateVal = log.date || log.startDate;
            if (!logDateVal) return;

            const logDate = new Date(logDateVal);
            // Check if log falls in current month (checking start date for simplicity)
            const isCurrentMonth = logDate.getMonth() === currentMonth && logDate.getFullYear() === currentYear;

            if (log.type === 'particular' || log.durationHours || log.duration || (log.startTime && log.endTime)) {
                totalParticularHours += (Number(log.durationHours || log.duration) || 0);
                if (isCurrentMonth) {
                    uniqueDays.add(format(logDate, 'yyyy-MM-dd'));
                }
            } else if (log.type === 'tutorial') {
                const start = new Date(log.startDate);
                const end = new Date(log.endDate);
                const days = differenceInCalendarDays(end, start) + 1;
                totalTutorialDays += days;

                if (isCurrentMonth) {
                    // Logic to add all days in range to the Set if they fall in current month
                    const monthStart = new Date(currentYear, currentMonth, 1);
                    const monthEnd = new Date(currentYear, currentMonth + 1, 0);

                    const overlapStart = start < monthStart ? monthStart : start;
                    const overlapEnd = end > monthEnd ? monthEnd : end;

                    if (overlapStart <= overlapEnd) {
                        const daysInMonth = differenceInCalendarDays(overlapEnd, overlapStart) + 1;
                        // Ideally we iterate and add distinct days, but for "Days Worked" count, 
                        // adding unique strings is best.
                        // Let's iterate the overlap range.
                        for (let i = 0; i < daysInMonth; i++) {
                            const day = new Date(overlapStart);
                            day.setDate(day.getDate() + i);
                            uniqueDays.add(format(day, 'yyyy-MM-dd'));
                        }
                    }
                }
            }
        });

        return {
            currentMonthName,
            daysWorkedCurrentMonth: uniqueDays.size,
            totalParticularHours,
            totalTutorialDays
        };
    }, [workLogs]);

    const handleSort = (key: string) => {
        setSortConfig(current => {
            if (current && current.key === key) {
                if (current.direction === 'asc') return { key, direction: 'desc' };
                return null;
            }
            return { key, direction: 'asc' };
        });
    };

    if (isLoadingUser) return <div className="p-8">Loading user details...</div>;
    if (isErrorUser) return (
        <div className="p-8 text-red-500">
            Error loading user details: {errorUser?.message || "Unknown Error"}
            <pre className="mt-2 text-xs bg-slate-100 p-2 rounded text-slate-800">
                {JSON.stringify(errorUser, null, 2)}
            </pre>
        </div>
    );
    if (!user) return <div className="p-8">User not found.</div>;

    const filterConfig: FilterConfig[] = [
        {
            id: "date",
            label: "Date Range",
            type: "date-range"
        },
        {
            id: "groupBy",
            label: "Group By",
            type: "select",
            options: [
                { label: "None", value: "none" },
                { label: "Month", value: "month" },
            ]
        }
    ];

    return (
        <div className="space-y-6">
            <Button variant="ghost" onClick={() => router.back()} className="pl-0 hover:bg-transparent">
                <ChevronLeft className="mr-2 h-4 w-4" />
                Back
            </Button>

            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-center gap-4">
                    <div className="h-16 w-16 bg-slate-200 rounded-full flex items-center justify-center text-slate-500">
                        <UserIcon size={32} />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">{user.firstName} {user.lastName}</h1>
                        <div className="flex items-center gap-2 text-muted-foreground">
                            <span>{user.email}</span>
                            <span>•</span>
                            <Badge variant={user.isActive ? "default" : "destructive"}>
                                {user.isActive ? "Active" : "Inactive"}
                            </Badge>
                            <Badge variant="outline" className="font-mono text-xs text-muted-foreground">{user.id}</Badge>
                        </div>
                        <div className="flex gap-2 mt-1">
                            {user.isActiveWorker && <Badge variant="secondary" className="text-xs border-green-200 bg-green-50 text-green-700">Worker</Badge>}
                            {user.isManager && <Badge variant="secondary" className="text-xs border-blue-200 bg-blue-50 text-blue-700">Manager</Badge>}
                            <span className="text-xs text-muted-foreground flex items-center ml-2">
                                <Calendar className="w-3 h-3 mr-1" /> Moved/Created: {user.createdAt ? format(new Date(user.createdAt), 'MMM d, yyyy') : 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Dashboard Tabs & Content */}
            <Tabs defaultValue="dashboard" className="w-full">
                <TabsList>
                    <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
                    <TabsTrigger value="work-logs">Work History</TabsTrigger>
                    <TabsTrigger value="rates">Rates</TabsTrigger>
                </TabsList>

                <TabsContent value="dashboard" className="mt-6 space-y-4">
                    <Tabs defaultValue="overview" value={dashboardTab} onValueChange={setDashboardTab} className="w-full">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-4">
                                <h2 className="text-2xl font-bold tracking-tight">
                                    {format(selectedDate, 'MMMM yyyy')}
                                </h2>
                                <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
                                    <button
                                        onClick={handlePrevMonth}
                                        className="p-1 hover:bg-white dark:hover:bg-slate-700 rounded-md transition-all shadow-sm"
                                        title="Previous Month"
                                    >
                                        <ChevronLeft className="h-4 w-4" />
                                    </button>
                                    <button
                                        onClick={handleNextMonth}
                                        className="p-1 hover:bg-white dark:hover:bg-slate-700 rounded-md transition-all shadow-sm"
                                        title="Next Month"
                                    >
                                        <ChevronRight className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>
                            <TabsList className="bg-slate-100 p-1 rounded-lg">
                                <TabsTrigger value="overview">Overview</TabsTrigger>
                                <TabsTrigger value="analytics">Analytics</TabsTrigger>
                            </TabsList>
                        </div>
                        <TabsContent value="overview" className="space-y-4">
                            <OverviewV3
                                workLogs={visibleWorkLogs}
                                companies={visibleCompanies}
                                onAddRecord={() => { }}
                                onNavigate={setDashboardTab}
                                selectedDate={selectedDate}
                                onViewLog={setSelectedLog}
                            />
                        </TabsContent>
                        <TabsContent value="analytics" className="space-y-4">
                            <AnalyticsV3 workLogs={visibleWorkLogs} selectedDate={selectedDate} />
                        </TabsContent>
                    </Tabs>
                </TabsContent>

                <TabsContent value="work-logs" className="space-y-4">
                    {isLogsError && (
                        <div className="bg-red-50 text-red-600 p-4 rounded-md border border-red-200">
                            Error loading work logs: {(logsError as any)?.message || "Unknown error"}
                        </div>
                    )}
                    <FilterBar config={filterConfig} onFilterChange={setFilters} />
                    <Card>
                        <CardHeader>
                            <CardTitle>Historial de Trabajo</CardTitle>
                            <CardDescription>Registros de actividad realizados por este usuario.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <WorkLogsTable
                                data={filteredLogs}
                                companies={visibleCompanies}
                                user={user}
                                onUpdate={() => queryClient.invalidateQueries({ queryKey: ["workLogs", userId] })}
                                isLoading={isLoadingLogs}
                            />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="rates" className="mt-6">
                    <div className="grid gap-8">
                        {visibleCompanies.map((company: any) => (
                            <CompanyMemberConfigCard 
                                key={company.id}
                                user={user} 
                                company={company} 
                                onUpdate={() => {
                                    queryClient.invalidateQueries({ queryKey: ["userCompanies", userId] });
                                    queryClient.invalidateQueries({ queryKey: ["userMemberConfigs", userId] });
                                }} 
                            />
                        ))}
                        {visibleCompanies.length === 0 && (
                            <div className="col-span-full text-center text-muted-foreground py-12 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
                                <Building2 className="h-12 w-12 mx-auto mb-4 opacity-20" />
                                <p className="font-medium text-lg">Sin tarifas configuradas</p>
                                <p className="text-sm">No hay tarifas específicas para las empresas visibles.</p>
                            </div>
                        )}
                    </div>
                </TabsContent>
            </Tabs>

            <WorkLogDetailsDialog
                log={selectedLog}
                open={!!selectedLog}
                onOpenChange={(open) => !open && setSelectedLog(null)}
                companies={visibleCompanies}
            />
        </div>
    );
}

// Simple FileText Icon component since lucide-react import might be tricky with just 'FileText' if not standard
function FileText({ className }: { className?: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <line x1="10" y1="9" x2="8" y2="9" />
        </svg>
    )
}
