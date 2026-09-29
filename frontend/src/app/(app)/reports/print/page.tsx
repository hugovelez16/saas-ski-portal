"use client";
export const dynamic = "force-dynamic";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { parse } from "date-fns";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { getMyCompanies, getCompaniesDetailed } from "@/lib/api/companies";
import { WorkLog } from "@/lib/types";
import { PrintableReport } from "@/components/reports/PrintableReport";
import { Loader2 } from "lucide-react";

export default function PrintReportPage() {
    const searchParams = useSearchParams();
    const { user, loading: authLoading } = useAuth();

    const startStr = searchParams.get('start');
    const endStr = searchParams.get('end');
    const title = searchParams.get('title') || "Informe de Trabajo";
    const companyId = searchParams.get('companyId') || searchParams.get('company_id') || "";
    const userId = searchParams.get('userId') || searchParams.get('user_id') || "";

    const isAdmin = user?.role === 'admin' || user?.isPlatformAdmin;

    const { data: companies = [], isLoading: companiesLoading } = useQuery({
        queryFn: isAdmin ? getCompaniesDetailed : getMyCompanies,
        queryKey: isAdmin ? ['allCompanies'] : ['myCompanies'],
        enabled: !!user
    });

    const { data: workLogs = [], isLoading: logsLoading } = useQuery({
        queryKey: ['reportLogs', startStr, endStr, companyId, userId],
        queryFn: async () => {
            if (!startStr || !endStr) return [];
            const params: Record<string, any> = {
                start_date: startStr,
                end_date: endStr,
                limit: 1000
            };
            if (companyId && companyId !== 'all') {
                params.company_id = companyId;
            }
            if (userId && userId !== 'me') {
                params.user_id = userId;
            }
            const response = await api.get<WorkLog[]>('/work-logs', { params });
            return response.data;
        },
        enabled: !!user && !!startStr && !!endStr
    });

    if (authLoading || companiesLoading || logsLoading) {
        return (
            <div className="h-screen w-full flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
        );
    }

    if (!user) return null;

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

            <PrintableReport
                workLogs={workLogs}
                companies={companies}
                title={title}
                dateRange={{ from: startDate, to: endDate }}
            />
        </div>
    );
}
