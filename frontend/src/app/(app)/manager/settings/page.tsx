"use client";

import { useAuth } from "@/context/AuthContext";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { CompanyConfigurationTab } from "@/components/admin/company-configuration-tab";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export default function ManagerSettingsPage() {
    const { user, loading: authLoading } = useAuth();
    const searchParams = useSearchParams();
    const selectedCompanyId = searchParams.get("companyId") || user?.activeCompanyId || user?.defaultCompanyId;

    const { data: company, isLoading: isLoadingCompany } = useQuery({
        queryKey: ["company", selectedCompanyId],
        queryFn: async () => (await api.get(`/companies/${selectedCompanyId}`)).data,
        enabled: !!selectedCompanyId,
    });

    if (authLoading || (isLoadingCompany && selectedCompanyId)) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (!selectedCompanyId) {
        return (
            <div className="p-6">
                <Card className="bg-yellow-50 border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-900/50">
                    <CardContent className="pt-6 text-yellow-800 dark:text-yellow-200">
                        No se ha seleccionado ninguna empresa. Por favor, selecciona una empresa activa para ver su configuracion.
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (!company) {
        return (
            <div className="p-6">
                <Card>
                    <CardContent className="pt-6 text-muted-foreground">
                        No se encontro la informacion de la empresa seleccionada.
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Configuración de Escuela</h1>
                <p className="text-muted-foreground text-sm">
                    Gestiona los turnos, tarifas, reglas de negocio y opciones del panel para tu escuela.
                </p>
            </div>

            <CompanyConfigurationTab company={company} />
        </div>
    );
}
