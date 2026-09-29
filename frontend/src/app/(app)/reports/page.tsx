"use client";
export const dynamic = "force-dynamic";


import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, startOfMonth, endOfMonth, setMonth, setYear } from "date-fns";
import { es } from "date-fns/locale";
import { mkConfig, generateCsv, download } from "export-to-csv";
import { Loader2, AlertCircle, FileText, Download, CalendarIcon, FileSpreadsheet, Building2, User as UserIcon, Copy } from "lucide-react";
import { DateRange } from "react-day-picker";
import { useRouter } from "next/navigation";
import { useToast } from "@/hooks/use-toast";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { getMyCompanies, getCompanyMembers, getCompaniesDetailed } from "@/lib/api/companies";
import { getUsers } from "@/lib/api/users";
import { WorkLog, Company } from "@/lib/types";

export default function ReportsPage() {
    const { user } = useAuth();
    const router = useRouter();
    const { toast } = useToast();

    const isAdmin = user?.role === 'admin';

    // -- Queries -- 
    const { data: companies = [] } = useQuery({
        queryFn: isAdmin ? getCompaniesDetailed : getMyCompanies,
        queryKey: isAdmin ? ['allCompanies'] : ['myCompanies'],
        enabled: !!user
    });

    // -- Accessible Companies (Modules Filter) --
    const accessibleCompanies = useMemo(() => {
        if (isAdmin) return companies;
        return companies.filter(c => {
            const modules = c.settings?.modules || {};
            const reportsConfig = modules.reports;

            // 1. Basic check
            if (!reportsConfig) return false;

            // 2. Boolean mode
            if (typeof reportsConfig === 'boolean') return reportsConfig;

            // 3. Object mode (Advanced SaaS settings)
            if (typeof reportsConfig === 'object') {
                if (reportsConfig.enabled === false) return false;
                
                if (reportsConfig.access_level === 'managers') {
                    const role = String(c.role || '').toLowerCase();
                    return ['manager', 'admin', 'owner'].includes(role);
                }
                return true; // All members allowed if not specified
            }
            return false;
        });
    }, [companies, isAdmin]);

    const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

    // Effect to select default company
    useEffect(() => {
        if (accessibleCompanies.length > 0 && !selectedCompanyId) {
            // Priority: Active Context > User Default > First Available
            const targetId = user?.activeCompanyId || user?.defaultCompanyId;
            
            if (targetId) {
                const exists = accessibleCompanies.find(c => c.id === targetId);
                if (exists) {
                    setSelectedCompanyId(targetId);
                    return;
                }
            }
            setSelectedCompanyId(accessibleCompanies[0].id);
        }
    }, [accessibleCompanies, selectedCompanyId, user?.activeCompanyId, user?.defaultCompanyId]);

    // Fetch members/users
    // If Admin and NO company selected -> Get ALL Users
    // If Company selected -> Get Company Members
    const { data: rawUsers = [] } = useQuery({
        queryFn: async () => {
            if (isAdmin && selectedCompanyId === "all") {
                return getUsers();
            } else if (selectedCompanyId && selectedCompanyId !== "all") {
                return getCompanyMembers(selectedCompanyId);
            }
            return [];
        },
        queryKey: ['reportUsers', selectedCompanyId, isAdmin],
        enabled: !!selectedCompanyId
    });

    // Normalize users list for the selector
    const userOptions = useMemo(() => {
        if (isAdmin && selectedCompanyId === "all") {
            // rawUsers is User[]
            const users = rawUsers as any[]; // Temporary cast as we know the shape but specific import might be missing User type details in this context if not fully aligned. 
            // Actually let's trust the shape:
            return users.map((u: any) => ({ id: u.id, name: `${u.firstName} ${u.lastName}`, role: u.role, email: u.email }));
        } else {
            // rawUsers is CompanyMemberResponse[]
            const members = rawUsers as any[];
            return members.map((m: any) => ({ id: m.userId, name: m.user ? `${m.user.firstName} ${m.user.lastName}` : 'Unknown', role: m.role }));
        }
    }, [rawUsers, isAdmin, selectedCompanyId]);


    // -- State --
    const [reportType, setReportType] = useState<"individual" | "company">("individual");
    const [selectedUserId, setSelectedUserId] = useState<string>("me"); // "me" or userId

    const [mode, setMode] = useState<"month" | "season" | "custom">("month");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<string | null>(null);

    // Month Mode State
    const currentYear = new Date().getFullYear();
    const [selectedMonth, setSelectedMonth] = useState<string>(new Date().getMonth().toString());
    const [selectedYear, setSelectedYear] = useState<string>(currentYear.toString());

    // Season Mode State
    const getInitialSeason = () => {
        const now = new Date();
        const month = now.getMonth();
        const year = now.getFullYear();
        if (month >= 6) return `${year}/${year + 1}`;
        return `${year - 1}/${year}`;
    };
    const [selectedSeason, setSelectedSeason] = useState<string>(getInitialSeason());

    // Custom Mode State
    const [dateRange, setDateRange] = useState<DateRange | undefined>({
        from: new Date(),
        to: new Date()
    });

    const isAdminOrManager = useMemo(() => {
        if (!user) return false;
        if (user.role === 'admin') return true;
        if (selectedCompanyId) {
            const company = companies.find(c => c.id === selectedCompanyId);
            const role = String(company?.role || '').toLowerCase();
            return ['manager', 'admin', 'owner'].includes(role);
        }
        return false;
    }, [user, companies, selectedCompanyId]);

    // Force individual mode for non-managers
    useEffect(() => {
        if (!isAdminOrManager) {
            setReportType('individual');
            setSelectedUserId('me');
        }
    }, [isAdminOrManager]);

    // Text Summary State
    const [textDialogOpen, setTextDialogOpen] = useState(false);
    const [generatedText, setGeneratedText] = useState("");

    // Fallback UI if no accessible companies
    if (user && accessibleCompanies.length === 0) {
        return (
            <div className="container mx-auto py-8 max-w-3xl px-4 text-center">
                <h1 className="text-3xl font-bold mb-8">Informes</h1>
                <Card className="p-12">
                    <div className="flex flex-col items-center gap-4">
                        <AlertCircle className="h-12 w-12 text-muted-foreground" />
                        <CardTitle>Módulo de informes no habilitado</CardTitle>
                        <CardDescription>
                            No tienes acceso al módulo de informes en ninguna de tus empresas actuales. 
                            Contacta con tu administrador para solicitar acceso.
                        </CardDescription>
                        <Button variant="outline" onClick={() => router.push('/dashboard')}>
                            Volver al Dashboard
                        </Button>
                    </div>
                </Card>
            </div>
        );
    }



    const generateSeasons = () => {
        const seasons = [];
        for (let i = -4; i <= 1; i++) {
            const start = currentYear + i;
            seasons.push(`${start}/${start + 1}`);
        }
        return seasons;
    };

    const getSeasonRange = (seasonStr: string) => {
        const [startYearStr, endYearStr] = seasonStr.split('/');
        const startYear = parseInt(startYearStr);
        const endYear = parseInt(endYearStr);
        const start = new Date(startYear, 10, 1); // Nov 1
        const end = new Date(endYear, 4, 31); // May 31
        return { start, end };
    };

    const getDateRangeAndTitle = () => {
        let start: Date;
        let end: Date;
        let title = "";
        let filename = "";

        // Determine context prefix
        let prefix = "Report";
        if (reportType === "company") {
            const cName = companies.find(c => c.id === selectedCompanyId)?.name || 'Company';
            prefix = `CompanyReport_${cName.replace(/\s+/g, '')}`;
        } else if (selectedUserId !== "me") {
            const u = userOptions.find(m => m.id === selectedUserId);
            if (u) prefix = `Report_${u.name.replace(/\s+/g, '')}`;
        }

        if (mode === "month") {
            start = startOfMonth(setMonth(setYear(new Date(), parseInt(selectedYear)), parseInt(selectedMonth)));
            end = endOfMonth(start);
            title = `Reporte ${format(start, 'MMMM yyyy', { locale: es })}`;
            filename = `${prefix}_${format(start, 'MMMM_yyyy')}`;
        } else if (mode === "season") {
            const range = getSeasonRange(selectedSeason);
            start = range.start;
            end = range.end;
            title = `Reporte Temporada ${selectedSeason}`;
            filename = `${prefix}_Season_${selectedSeason.replace('/', '-')}`;
        } else {
            if (!dateRange?.from || !dateRange?.to) {
                return null;
            }
            start = dateRange.from;
            end = dateRange.to;
            title = "Reporte Personalizado";
            filename = `${prefix}_Custom_${format(start, 'yyyyMMdd')}_${format(end, 'yyyyMMdd')}`;
        }
        return { start, end, title, filename };
    };

    const fetchLogs = async (start: Date, end: Date) => {
        const params: any = {
            start_date: format(start, 'yyyy-MM-dd'),
            end_date: format(end, 'yyyy-MM-dd'),
            limit: 1000 // Ensure we get enough
        };

        if (reportType === 'company') {
            if (selectedCompanyId !== 'all') {
                params.company_id = selectedCompanyId;
            } else {
                // If company is 'all', do we want stats for ALL companies? 
                // Currently backend treats no params as "me". Admin needs explicit logic or backend support to "get all logs of system".
                // If user_id is null and company_id is null, backend defaults to "me" even for admin? 
                // Let's check backend logic... (Lines 242-243 in main.py: if not company_id and not user_id: target_user_id = current_user.id)
                // So purely "Global" logs might be tricky without specific param.
                // However, user mostly asked for "generate report of any company". 
                // If they select "All Companies", maybe it's "All My Managed Companies" or effectively "Global System".
                // We'll leave company_id empty if 'all', and if backend defaults to 'me', that's a limitation for now unless we iterate companies.
                // Actually, for Admin, if I pass user_id it works.
            }
        } else {
            // Individual
            if (selectedUserId !== 'me') {
                params.user_id = selectedUserId;
            }
            if (selectedCompanyId) {
                params.company_id = selectedCompanyId;
            }
        }

        const response = await api.get<WorkLog[]>('/work-logs', { params });
        return response.data;
    };



    const handleNativePDF = async () => {
        setError(null);
        const range = getDateRangeAndTitle();
        if (!range) {
            setError("Rango de fechas inválido.");
            return;
        }

        setLoading('native');

        try {
            const { pdf } = await import("@react-pdf/renderer");

            // Fetch Data
            const logs = await fetchLogs(range.start, range.end);
            if (!logs || logs.length === 0) {
                setError("No hay registros dentro del rango seleccionado.");
                setLoading(null);
                return;
            }

            let blob: Blob;

            if (reportType === 'company') {
                const { CompanyPDFReport } = await import("@/components/reports/CompanyPDFReport");

                const statsMap = new Map<string, { 
                    name: string; 
                    hours: number; 
                    amount: number; 
                    grossAmount: number;
                    netAmount: number;
                    days: number; 
                    dates: Set<string>;
                }>();

                const company = companies.find(c => c.id === selectedCompanyId) || { 
                    id: '0', 
                    name: 'Company', 
                    settings: {},
                    taxConfig: { social_security: 0, irpf_base: 0 },
                    worklogDefinitions: {}
                } as any;

                logs.forEach(log => {
                    const u = userOptions.find(o => o.id === log.userId);
                    const name = u ? u.name : `User ${log.userId}`;

                    if (!statsMap.has(log.userId)) {
                        statsMap.set(log.userId, { 
                            name, 
                            hours: 0, 
                            amount: 0, 
                            grossAmount: 0,
                            netAmount: 0,
                            days: 0, 
                            dates: new Set() 
                        });
                    }
                    const s = statsMap.get(log.userId)!;

                    const effectiveGross = Number(log.grossAmount ?? log.netAmount ?? log.amount ?? 0);
                    const effectiveNet = Number(log.netAmount ?? log.grossAmount ?? log.amount ?? 0);
                    s.grossAmount += effectiveGross;
                    s.netAmount += effectiveNet;
                    s.amount += effectiveNet;

                    const d = log.date || (log.startDate ? format(new Date(log.startDate), 'yyyy-MM-dd') : null);
                    if (d) s.dates.add(d);

                    let days = 1;
                    if (log.startDate && log.endDate && log.startDate !== log.endDate) {
                        try {
                            days = Math.round(Math.abs((new Date(log.endDate).getTime() - new Date(log.startDate).getTime()) / 86400000)) + 1;
                        } catch (e) {}
                    }
                    const isMultiDay = days > 1;

                    const durationVal = Number(log.durationHours ?? log.duration ?? (isMultiDay ? days : 1));
                    s.hours += durationVal;
                });

                const employeeStats = Array.from(statsMap.entries()).map(([uid, stat]) => ({
                    userId: uid,
                    name: stat.name,
                    totalHours: stat.hours,
                    totalAmount: stat.amount,
                    totalGross: stat.grossAmount,
                    totalNet: stat.netAmount,
                    totalDays: stat.dates.size
                }));

                blob = await pdf(
                    <CompanyPDFReport
                        company={company}
                        employeeStats={employeeStats}
                        title={range.title}
                        startDate={range.start}
                        endDate={range.end}
                    />
                ).toBlob();

            } else {
                // Individual Report
                const { PDFReport } = await import("@/components/reports/PDFReport");

                logs.sort((a, b) => {
                    const dateA = a.date || a.startDate || a.createdAt;
                    const dateB = b.date || b.startDate || b.createdAt;
                    return new Date(dateA as string).getTime() - new Date(dateB as string).getTime();
                });

                blob = await pdf(
                    <PDFReport
                        workLogs={logs}
                        companies={companies}
                        title={range.title}
                        dateRange={{ from: range.start, to: range.end }}
                    />
                ).toBlob();
            }

            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${range.filename}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

        } catch (e) {
            console.error(e);
            setError("Error al generar el PDF.");
        } finally {
            setLoading(null);
        }
    }

    const handleGenerateText = async () => {
        setError(null);
        const range = getDateRangeAndTitle();
        if (!range) { setError("Rango de fechas inválido."); return; }
        setLoading('text');

        try {
            const logs = await fetchLogs(range.start, range.end);
            if (!logs || logs.length === 0) {
                setError(`No hay registros. (Empresa: ${selectedCompanyId || 'N/A'}, Usuario: ${selectedUserId}, Fechas: ${format(range.start, 'yyyy-MM-dd')} al ${format(range.end, 'yyyy-MM-dd')})`);
                setLoading(null);
                return;
            }

            // Generar el texto utilizando el sistema modular
            const company = companies.find(c => c.id === selectedCompanyId);
            
            const { generateTextReport } = await import("@/lib/reports/textGenerators");
            
            const fullText = generateTextReport(logs, {
                company,
                companyId: selectedCompanyId,
                userId: selectedUserId,
                startDate: range.start,
                endDate: range.end
            });

            setGeneratedText(fullText);
            setTextDialogOpen(true);

        } catch (e) {
            console.error(e);
            setError("Error al generar el texto.");
        } finally {
            setLoading(null);
        }
    };

    const handleCopyText = async () => {
        try {
            await navigator.clipboard.writeText(generatedText);
            toast({ title: "Copiado", description: "Resumen copiado al portapapeles." });
            setTextDialogOpen(false);
        } catch (e) {
            toast({ variant: "destructive", title: "Error", description: "No se pudo copiar automáticamente. Intenta seleccionarlo manualmente." });
        }
    };

    // ... CSV Handler (simplified) ...
    const handleGenerateCSV = async () => {
        setError(null);
        const range = getDateRangeAndTitle();
        if (!range) { setError("Rango de fechas inválido."); return; }
        setLoading('csv');

        try {
            const logs = await fetchLogs(range.start, range.end);
            if (!logs || logs.length === 0) {
                setError("No hay registros.");
                setLoading(null);
                return;
            }
            const csvConfig = mkConfig({ useKeysAsHeaders: true, filename: range.filename });
            const data = logs.map(log => {
                const companyName = companies.find(c => c.id === log.companyId)?.name || log.companyId || 'N/A';
                return {
                    Date: log.date || log.startDate || '',
                    Type: log.type,
                    Company: companyName,
                    User: userOptions.find(u => u.id === log.userId)?.name || log.userId,
                    Amount: Number(log.netAmount ?? log.grossAmount ?? log.amount ?? 0)
                };
            });
            const csv = generateCsv(csvConfig)(data);
            download(csvConfig)(csv);
        } catch (e) { setLoading(null); }
        setLoading(null);
    };


    return (
        <div className="container mx-auto py-8 max-w-3xl px-4">
            <h1 className="text-3xl font-bold mb-8">Informes y Exportación</h1>

            <Card className="mb-8">
                <CardHeader>
                    <CardTitle>Configuración de Reporte</CardTitle>
                    <CardDescription>Define el alcance y filtros del reporte</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Filters Section */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Company Selector - For everyone */}
                        {companies.length > 0 && (
                            <div className="space-y-2">
                                <Label>Empresa</Label>
                                <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId} disabled={!!user?.activeCompanyId}>
                                    <SelectTrigger><SelectValue placeholder="Seleccionar empresa" /></SelectTrigger>
                                    <SelectContent>
                                        {accessibleCompanies.map(c => (
                                            <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        {/* Report Type - Admin/Manager Only */}
                        {isAdminOrManager && companies.length > 0 && (
                            <div className="space-y-2">
                                <Label>Tipo de Informe</Label>
                                <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-900 p-1 rounded-md">
                                    <Button
                                        variant={reportType === 'individual' ? 'default' : 'ghost'}
                                        size="sm"
                                        onClick={() => setReportType('individual')}
                                        className="flex-1"
                                    >
                                        <UserIcon size={14} className="mr-2" /> Individual
                                    </Button>
                                    <Button
                                        variant={reportType === 'company' ? 'default' : 'ghost'}
                                        size="sm"
                                        onClick={() => setReportType('company')}
                                        className="flex-1"
                                    >
                                        <Building2 size={14} className="mr-2" /> Empresa
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* User Selector (Only if Individual + Admin/Manager) */}
                    {reportType === 'individual' && isAdminOrManager && (
                        <div className="space-y-2">
                            <Label>Empleado</Label>
                            <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="me">Mí mismo (Mis registros)</SelectItem>
                                    {userOptions.map(m => (
                                        <SelectItem key={m.id} value={m.id}>
                                            {m.name} ({m.role || 'Usuario'})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FileText className="h-6 w-6" />
                        Generar Documento
                    </CardTitle>
                    <CardDescription>
                        Selecciona el periodo deseado.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <RadioGroup defaultValue="month" value={mode} onValueChange={(v) => { setMode(v as any); setError(null); }} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Existing Radio Group Items (Month, Season, Custom) - Keeping same structure */}
                        <div>
                            <RadioGroupItem value="month" id="month" className="peer sr-only" />
                            <Label htmlFor="month" className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer text-center h-full">
                                <span className="mb-2 text-lg font-semibold">Mes</span>
                                <span className="text-sm text-muted-foreground">Mensual</span>
                            </Label>
                        </div>
                        <div>
                            <RadioGroupItem value="season" id="season" className="peer sr-only" />
                            <Label htmlFor="season" className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer text-center h-full">
                                <span className="mb-2 text-lg font-semibold">Temporada</span>
                                <span className="text-sm text-muted-foreground">Nov - May</span>
                            </Label>
                        </div>
                        <div>
                            <RadioGroupItem value="custom" id="custom" className="peer sr-only" />
                            <Label htmlFor="custom" className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer text-center h-full">
                                <span className="mb-2 text-lg font-semibold">Custom</span>
                                <span className="text-sm text-muted-foreground">Rango</span>
                            </Label>
                        </div>
                    </RadioGroup>

                    <div className="p-4 border rounded-lg bg-slate-50 dark:bg-slate-900/50 min-h-[120px] flex items-center justify-center">
                        {mode === "month" && (
                            <div className="flex flex-col gap-6 w-full max-w-sm mx-auto">
                                <div className="space-y-2">
                                    <Label className="text-center block">Año</Label>
                                    <Select value={selectedYear} onValueChange={setSelectedYear}>
                                        <SelectTrigger className="w-full text-center font-medium"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {Array.from({ length: 5 }).map((_, i) => (
                                                <SelectItem key={i} value={(currentYear - 2 + i).toString()}>
                                                    {currentYear - 2 + i}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-center block">Mes</Label>
                                    <div className="grid grid-cols-3 gap-2">
                                        {Array.from({ length: 12 }).map((_, i) => {
                                            const isSelected = i.toString() === selectedMonth;
                                            return (
                                                <Button
                                                    key={i}
                                                    variant={isSelected ? "default" : "outline"}
                                                    onClick={() => setSelectedMonth(i.toString())}
                                                    className={cn("h-9 text-xs capitalize", isSelected ? "" : "hover:bg-accent")}
                                                >
                                                    {format(new Date(2000, i, 1), 'MMM', { locale: es })}
                                                </Button>
                                            )
                                        })}
                                    </div>
                                </div>
                            </div>
                        )}

                        {mode === "season" && (
                            <div className="space-y-2 w-full">
                                <Label>Seleccionar Temporada</Label>
                                <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {generateSeasons().map((s) => (
                                            <SelectItem key={s} value={s}>Temporada {s}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        {mode === "custom" && (
                            <div className="space-y-2 w-full flex flex-col items-center">
                                <Label className="mb-2">Rango de Fechas</Label>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <Button id="date" variant={"outline"} className={cn("w-[300px] justify-start text-left font-normal", !dateRange && "text-muted-foreground")}>
                                            <CalendarIcon className="mr-2 h-4 w-4" />
                                            {dateRange?.from ? (
                                                dateRange.to ? <>{format(dateRange.from, "LLL dd, y", { locale: es })} - {format(dateRange.to, "LLL dd, y", { locale: es })}</> : format(dateRange.from, "LLL dd, y", { locale: es })
                                            ) : <span>Selecciona fechas</span>}
                                        </Button>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="center">
                                        <Calendar initialFocus mode="range" defaultMonth={dateRange?.from} selected={dateRange} onSelect={setDateRange} numberOfMonths={2} locale={es} />
                                    </PopoverContent>
                                </Popover>
                            </div>
                        )}
                    </div>

                    {error && (
                        <div className="flex items-center gap-2 p-3 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-md border border-red-100 dark:border-red-900/50">
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}
                </CardContent>
                <CardFooter className="flex-col gap-3">
                    {/* Visual Button - Disabled for Company Mode */}


                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                        <Button onClick={handleNativePDF} disabled={loading === 'native'} variant="outline" className="w-full h-auto py-3 whitespace-normal">
                            {loading === 'native' ? <Loader2 className="mr-2 h-4 w-4 animate-spin shrink-0" /> : <Download className="mr-2 h-4 w-4 shrink-0" />}
                            <span className="truncate">Descargar PDF ({reportType === 'company' ? 'Empresa' : 'Individual'})</span>
                        </Button>

                        <Button onClick={handleGenerateText} disabled={loading === 'text'} variant="outline" className="w-full h-auto py-3 whitespace-normal">
                            {loading === 'text' ? <Loader2 className="mr-2 h-4 w-4 animate-spin shrink-0" /> : <Copy className="mr-2 h-4 w-4 shrink-0" />}
                            <span className="truncate">Copiar Resumen</span>
                        </Button>

                        {/* CSV - Simplified basic export */}
                        <Button onClick={handleGenerateCSV} disabled={loading === 'csv'} variant="outline" className="w-full h-auto py-3 whitespace-normal sm:col-span-2">
                            {loading === 'csv' ? <Loader2 className="mr-2 h-4 w-4 animate-spin shrink-0" /> : <FileSpreadsheet className="mr-2 h-4 w-4 shrink-0" />}
                            Descargar CSV
                        </Button>
                    </div>
                </CardFooter>
            </Card>

            {/* Text Preview Dialog */}
            <Dialog open={textDialogOpen} onOpenChange={setTextDialogOpen}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Resumen Generado</DialogTitle>
                        <DialogDescription>
                            Revisa el resumen antes de copiarlo.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <Textarea
                            value={generatedText}
                            readOnly
                            className="h-[300px] font-mono text-xs resize-none"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="secondary" onClick={() => setTextDialogOpen(false)}>Cerrar</Button>
                        <Button onClick={handleCopyText}>
                            <Copy className="mr-2 h-4 w-4" /> Copiar
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
