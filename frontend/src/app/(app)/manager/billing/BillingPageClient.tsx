"use client";

import { useState, useMemo } from "react";
import { DateRange } from "react-day-picker";
import { startOfMonth, endOfMonth, format, addMonths, subMonths } from "date-fns";
import { DateRangeFilter } from "@/components/manager/date-range-filter";
import { BillingTable } from "@/components/manager/billing-table";
import { getBillingSummary } from "@/lib/api/work-logs";
import { getCompaniesDetailed } from "@/lib/api/companies";
import { useQuery } from "@tanstack/react-query";
import { BillingSummaryItem, DynamicBillingRow } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, Download, Coins, Wallet, FileText } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { mkConfig, generateCsv, download } from "export-to-csv";

export default function ManagerBillingPage() {
    const searchParams = useSearchParams();
    const selectedCompanyId = searchParams.get("companyId");

    // Default to current month
    const [date, setDate] = useState<DateRange | undefined>({
        from: startOfMonth(new Date()),
        to: endOfMonth(new Date()),
    });

    // 1. Fetch Billing Summary for selected company and date range
    const { data: billingItems = [], isLoading: isLoadingBilling } = useQuery({
        queryFn: () => getBillingSummary({
            companyId: selectedCompanyId!,
            startDate: date?.from ? format(date.from, 'yyyy-MM-dd') : undefined,
            endDate: date?.to ? format(date.to, 'yyyy-MM-dd') : undefined,
        }),
        queryKey: ["companyBillingSummary", selectedCompanyId, date?.from, date?.to],
        enabled: !!selectedCompanyId && !!date?.from && !!date?.to,
    });

    // 2. Fetch Company Details for Settings
    const { data: company } = useQuery({
        queryFn: async () => (await import("@/lib/api").then(m => m.default.get(`/companies/${selectedCompanyId}`))).data,
        queryKey: ["company", selectedCompanyId],
        enabled: !!selectedCompanyId,
    });

    const { data: companiesDetailed = [] } = useQuery({
        queryFn: getCompaniesDetailed,
        queryKey: ["companiesDetailed"],
    });

    const orderedMemberIds = useMemo(() => {
        const comp = companiesDetailed.find((c: any) => c.id === selectedCompanyId);
        if (!comp || !comp.members) return [];
        return comp.members.map((m: any) => m.userId);
    }, [companiesDetailed, selectedCompanyId]);

    const worklogDefs = useMemo(
        () => (company?.worklogDefinitions ?? {}) as Record<string, { unit: string; label: string }>,
        [company]
    );

    // 3. Aggregate billingData from flat database rows:
    const billingData: DynamicBillingRow[] = useMemo(() => {
        if (!billingItems.length) return [];

        const userMap = new Map<string, DynamicBillingRow>();

        billingItems.forEach((item: BillingSummaryItem) => {
            let row = userMap.get(item.userId);
            if (!row) {
                row = {
                    userId: item.userId,
                    userName: `${item.firstName || ''} ${item.lastName || ''}`.trim() || item.email,
                    userEmail: item.email,
                    byType: {},
                    totalNet: 0,
                    totalGross: 0,
                    logsCount: 0,
                };
                userMap.set(item.userId, row);
            }

            // If the item has a type, add it to byType
            if (item.type) {
                const def = worklogDefs[item.type];
                const unit = def?.unit ?? 'hours';
                const label = def?.label ?? item.type;

                // Quantity is totalHours if unit is hours, otherwise uniqueDays
                const quantity = unit === 'hours' ? item.totalHours : item.uniqueDays;

                row.byType[item.type] = {
                    typeKey: item.type,
                    label,
                    unit,
                    quantity,
                    netAmount: item.totalNet,
                    grossAmount: item.totalGross,
                };

                row.totalNet += item.totalNet;
                row.totalGross += item.totalGross;
                row.logsCount += item.logsCount;
            }
        });

        const list = Array.from(userMap.values());
        
        if (orderedMemberIds.length > 0) {
            const orderMap = new Map();
            orderedMemberIds.forEach((id, index) => orderMap.set(id, index));
            
            list.sort((a, b) => {
                const idxA = orderMap.get(a.userId);
                const idxB = orderMap.get(b.userId);
                if (idxA === undefined && idxB === undefined) return 0;
                if (idxA === undefined) return 1;
                if (idxB === undefined) return -1;
                return idxA - idxB;
            });
        }
        
        return list;
    }, [billingItems, worklogDefs, orderedMemberIds]);

    const summaryStats = useMemo(() => {
        let totalGross = 0;
        let totalNet = 0;
        let totalLogs = 0;

        billingData.forEach(row => {
            totalGross += row.totalGross;
            totalNet += row.totalNet;
            totalLogs += row.logsCount;
        });

        return { totalGross, totalNet, totalLogs };
    }, [billingData]);

    const handleExportCsv = () => {
        if (billingData.length === 0) return;
        const csvConfig = mkConfig({
            fieldSeparator: ',',
            decimalSeparator: '.',
            useKeysAsHeaders: true,
            filename: `Facturacion_Mensual_${date?.from ? format(date.from, 'MM-yyyy') : 'report'}`
        });

        const exportData = billingData.map(row => {
            const base: Record<string, any> = {
                Nombre: row.userName,
                Email: row.userEmail,
            };
            Object.entries(worklogDefs).forEach(([typeKey, def]) => {
                const summary = row.byType[typeKey];
                const unitLabel = def.unit === 'hours' ? 'h' : 'días';
                base[`${def.label} (${unitLabel})`] = summary
                    ? summary.quantity.toFixed(def.unit === 'hours' ? 2 : 0)
                    : '0';
            });
            base['Total Bruto (€)'] = (row.totalGross || row.totalNet).toFixed(2);
            base['Total Neto (€)'] = row.totalNet.toFixed(2);
            return base;
        });

        const csv = generateCsv(csvConfig)(exportData);
        download(csvConfig)(csv);
    };

    return (
        <div className="flex flex-col gap-6 p-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Resumen y Facturación</h1>
                    <p className="text-muted-foreground text-sm">Resumen mensual de actividad y cálculo de costes del equipo.</p>
                </div>
                <div className="flex flex-col sm:flex-row gap-4 items-center w-full md:w-auto">
                    <div className="flex items-center gap-2">
                        <div className="flex border rounded-md shadow-sm bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="rounded-r-none h-8 w-8 px-0"
                                onClick={() => {
                                    if (date?.from) {
                                        const newDate = subMonths(date.from, 1);
                                        setDate({ from: startOfMonth(newDate), to: endOfMonth(newDate) });
                                    }
                                }}
                            >
                                <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <div className="h-8 flex items-center px-4 border-x text-sm font-medium bg-muted/20">
                                {date?.from ? format(date.from, 'MMMM yyyy') : 'Select Month'}
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="rounded-l-none h-8 w-8 px-0"
                                onClick={() => {
                                    if (date?.from) {
                                        const newDate = addMonths(date.from, 1);
                                        setDate({ from: startOfMonth(newDate), to: endOfMonth(newDate) });
                                    }
                                }}
                            >
                                <ChevronRight className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                    
                    <DateRangeFilter date={date} setDate={setDate} />
                    
                    {billingData.length > 0 && (
                        <Button onClick={handleExportCsv} className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm flex items-center gap-2 h-9">
                            <Download className="h-4 w-4" />
                            Exportar CSV
                        </Button>
                    )}
                </div>
            </div>

            {!selectedCompanyId && (
                <Card className="bg-yellow-50 border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-900/50">
                    <CardContent className="pt-6 text-yellow-800 dark:text-yellow-200">
                        No company selected. Please select a company from the sidebar.
                    </CardContent>
                </Card>
            )}

            {selectedCompanyId && (
                <>
                    {/* KPI Cards Grid */}
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        <Card className="border-emerald-100 dark:border-emerald-950 shadow-sm hover:shadow-md transition-all duration-300">
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">Coste Bruto (Empresa)</CardTitle>
                                <Coins className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                                    {new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(summaryStats.totalGross)}
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">Coste real consolidado</p>
                            </CardContent>
                        </Card>

                        <Card className="border-indigo-100 dark:border-indigo-950 shadow-sm hover:shadow-md transition-all duration-300">
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">Coste Neto (Personal)</CardTitle>
                                <Wallet className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                                    {new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(summaryStats.totalNet)}
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">Suma líquida percibida</p>
                            </CardContent>
                        </Card>

                        <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-all duration-300">
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">Total Registros</CardTitle>
                                <FileText className="h-5 w-5 text-slate-600 dark:text-slate-400" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                                    {summaryStats.totalLogs}
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">Registros en el período</p>
                            </CardContent>
                        </Card>
                    </div>

                    <BillingTable
                        data={billingData}
                        worklogDefs={worklogDefs}
                        isLoading={isLoadingBilling}
                    />
                </>
            )}
        </div>
    );
}
