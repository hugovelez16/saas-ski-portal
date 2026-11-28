"use client";
export const dynamic = "force-dynamic";

import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { parse } from "date-fns";
import { useAuth } from "@/context/AuthContext";
import { getCompany, getCompaniesDetailed } from "@/lib/api/companies";
import { getAllWorkLogReport } from "@/lib/api/work-logs";
import { useModules } from "@/hooks/useModules";
import { PrintableReport } from "@/components/reports/PrintableReport";
import { AlertCircle, Loader2 } from "lucide-react";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function PrintReportPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();

    const startStr = searchParams.get('start');
    const endStr = searchParams.get('end');
    const title = searchParams.get('title') || "Informe de Trabajo";
    const isAdmin = Boolean(user?.role === 'admin' || user?.isPlatformAdmin);
    // El informe se genera sobre la empresa activa; un PA sin empresa activa puede indicar companyId en URL.
    const companyId = user?.activeCompanyId || (isAdmin ? (searchParams.get('companyId') || searchParams.get('company_id') || "") : "");
    const userId = searchParams.get('userId') || searchParams.get('user_id') || "";

    const { hasModule, isLoading: modulesLoading } = useModules(companyId || undefined);
    const canAccessReports = isAdmin || hasModule("reports");

    const { data: companies = [], isLoading: companiesLoading } = useQuery({
        queryFn: async () => {
            if (isAdmin) return getCompaniesDetailed({ asAdmin: true });
            if (!companyId || companyId === 'all') return [];
            return [await getCompany(companyId)];
        },
        queryKey: isAdmin ? ['allCompanies'] : ['company', companyId],
        enabled: !!user && canAccessReports
    });

    // Mismo alcance para el resumen y las filas de detalle
    const scope = {
        companyId: companyId && companyId !== 'all' ? companyId : undefined,
        userId: userId && userId !== 'me' ? userId : undefined
    };

    const { data: reportData, isLoading: reportLoading, isError: reportError } = useQuery({
        queryKey: ['reportData', startStr, endStr, companyId, userId],
        queryFn: async () => {
            if (!startStr || !endStr) return null;
            return getAllWorkLogReport({ ...scope, startDate: startStr, endDate: endStr });
        },
        enabled: !!user && !!startStr && !!endStr && canAccessReports
    });

    if (authLoading || modulesLoading || (canAccessReports && (companiesLoading || reportLoading))) {
        return (
            <div className="h-screen w-full flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
        );
    }

    if (!user) return null;

    if (!canAccessReports) {
        return (
            <div className="container mx-auto py-8 max-w-3xl px-4 text-center">
                <h1 className="text-3xl font-bold mb-8">Informes</h1>
                <Card className="p-12">
                    <div className="flex flex-col items-center gap-4">
                        <AlertCircle className="h-12 w-12 text-muted-foreground" />
                        <CardTitle>Módulo de informes no habilitado</CardTitle>
                        <CardDescription>
                            No tienes acceso al módulo de informes en tu empresa activa.
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

    if (reportError) {
        return (
            <div className="container mx-auto py-8 max-w-3xl px-4 text-center">
                <Card className="p-12">
                    <div className="flex flex-col items-center gap-4">
                        <AlertCircle className="h-12 w-12 text-red-500" />
                        <CardTitle>No se pudo cargar el informe</CardTitle>
                        <CardDescription>
                            No tienes permisos o hubo un problema al obtener los datos del informe.
                        </CardDescription>
                        <Button variant="outline" onClick={() => router.push('/reports')}>
                            Volver a Informes
                        </Button>
                    </div>
                </Card>
            </div>
        );
    }

    const workLogs = reportData?.items ?? [];
    const summary = reportData?.summary;

    const startDate = startStr ? parse(startStr, 'yyyy-MM-dd', new Date()) : new Date();
    const endDate = endStr ? parse(endStr, 'yyyy-MM-dd', new Date()) : new Date();

    return (
        <div className="min-h-screen bg-slate-100 print:bg-white p-4 print:p-0">
            {/* Print Controls (Hidden when printing) */}
            <div className="max-w-[210mm] mx-auto mb-4 flex justify-between items-center print:hidden">
                <button
                    onClick={() => window.history.back()}
                    className="text-sm text-slate-500 hover:text-slate-900"
                >
                    &larr; Volver
                </button>
                <button
                    onClick={() => window.print()}
                    className="bg-slate-900 text-white px-4 py-2 rounded-md shadow hover:bg-slate-800 text-sm font-medium"
                >
                    Imprimir / Guardar como PDF
                </button>
            </div>

            {summary && (
                <PrintableReport
                    workLogs={workLogs}
                    summary={summary}
                    worklogDefinitions={companies.find(c => c.id === companyId)?.worklogDefinitions}
                    title={title}
                    dateRange={{ from: startDate, to: endDate }}
                />
            )}
        </div>
    );
}
