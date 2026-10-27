"use client";
export const dynamic = "force-dynamic";


import { useQuery } from "@tanstack/react-query";
import { getMyCompanies } from "@/lib/api/companies";
import { CompanyDashboard } from "@/components/manager/company-dashboard";
import { useMemo } from "react";
import { Building2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function ManagerDashboardPage() {
    const { user } = useAuth();
    const companyId = user?.activeCompanyId;

    // Fetch My Companies
    const { data: myCompanies = [], isLoading } = useQuery({
        queryFn: getMyCompanies,
        queryKey: ["myCompanies"],
    });

    // Filter Managed Companies
    const managedCompanies = useMemo(() => {
        return myCompanies.filter((c: any) => {
            const role = (c.role || '').toLowerCase();
            return role === 'manager' || role === 'admin' || role === 'owner';
        });
    }, [myCompanies]);

    if (isLoading) {
        return <div className="p-8 text-sm text-muted-foreground">Cargando empresas...</div>;
    }

    // Determine current view
    // La empresa activa (user.activeCompanyId) debe pertenecer a managedCompanies
    const selectedCompany = managedCompanies.find(c => c.id === companyId);

    // Sin empresa activa gestionable: estado de espera o vacio
    if (!selectedCompany) {
        if (managedCompanies.length === 0) {
            return <div className="p-8 text-sm text-muted-foreground">No tienes asignada la gestión de ninguna empresa activa.</div>;
        }
        return <div className="p-8 text-sm text-muted-foreground">Selecciona una empresa activa para ver el panel de gestión.</div>;
    }

    return (
        <div className="space-y-6">
            {/* Dashboard Content */}
            <CompanyDashboard
                companyId={selectedCompany.id}
                companyName={selectedCompany.name}
            />
        </div>
    );
}
