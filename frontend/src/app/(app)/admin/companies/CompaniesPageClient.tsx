"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCompaniesDetailed, updateCompany } from "@/lib/api/companies";
import { CompanyWithMembers } from "@/lib/types";
import { CompanyDialog } from "@/components/admin/company-dialog";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Building2, Users, Wallet, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { useState } from "react";

export default function AdminCompaniesPage() {
    const router = useRouter();
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [searchQuery, setSearchQuery] = useState("");

    const { data: companies = [], isLoading } = useQuery({
        queryFn: getCompaniesDetailed,
        queryKey: ["companiesDetailed"],
    });

    const updateCompanyMutation = useMutation({
        mutationFn: ({ companyId, data }: { companyId: string; data: any }) =>
            updateCompany(companyId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            toast({ title: "Configuracion de empresa actualizada" });
        },
        onError: () => {
            toast({ title: "Error al actualizar empresa", variant: "destructive" });
        }
    });

    const filteredCompanies = companies.filter(company =>
        company.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (isLoading) {
        return <div className="p-8 text-center">Cargando empresas...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-center gap-2">
                    <Building2 className="h-7 w-7 text-indigo-600" />
                    <h1 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-700">
                        Gestión de Empresas
                    </h1>
                </div>
                <div className="flex items-center gap-3 w-full md:w-auto">
                    <div className="relative w-full md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Buscar empresa..."
                            className="pl-9 bg-white border-slate-200"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <CompanyDialog />
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredCompanies.map((company) => {
                    const activeWorkers = (company.members || []).filter((m) => m.isActive && m.role !== 'manager').length;
                    const activeManagers = (company.members || []).filter((m) => m.isActive && m.role === 'manager').length;
                    const ss = (company.taxConfig?.social_security || 0) * 100;
                    const isManaged = Boolean(company.isManaged || company.settings?.is_managed);
                    const isActive = company.isActive !== false;

                    return (
                        <Card 
                            key={company.id} 
                            className="group hover:shadow-xl hover:ring-2 hover:ring-indigo-500/20 transition-all duration-300 cursor-pointer overflow-hidden border-slate-200"
                            onClick={() => router.push(`/admin/companies/${company.id}`)}
                        >
                            <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
                                <CardTitle className="flex items-center justify-between">
                                    <div className="space-y-1">
                                        <span className="text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition-colors block">
                                            {company.name}
                                        </span>
                                        <div className="flex items-center gap-1.5 pt-1">
                                            <Badge 
                                                variant={isActive ? "default" : "destructive"} 
                                                className={`text-[10px] font-medium px-2 py-0.5 ${isActive ? "bg-emerald-600 hover:bg-emerald-700 text-white" : ""}`}
                                            >
                                                {isActive ? "Activa" : "Suspendida"}
                                            </Badge>
                                            <Badge 
                                                variant={isManaged ? "secondary" : "outline"} 
                                                className={`text-[10px] font-medium px-2 py-0.5 ${isManaged ? "bg-indigo-100 text-indigo-700 border-indigo-200" : "text-slate-600"}`}
                                            >
                                                {isManaged ? "Gestionada" : "Autonoma"}
                                            </Badge>
                                        </div>
                                    </div>
                                    <div className="p-2 bg-white rounded-lg border border-slate-100 shadow-sm group-hover:bg-indigo-50 group-hover:border-indigo-100 transition-all">
                                        <Building2 className="h-5 w-5 text-indigo-500" />
                                    </div>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-6 space-y-4">
                                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
                                    <div className="space-y-1">
                                        <p className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">Miembros Activos</p>
                                        <div className="flex items-center gap-3">
                                            <div className="flex items-center gap-1.5" title="Trabajadores">
                                                <Users className="h-4 w-4 text-slate-400" />
                                                <span className="text-sm font-bold text-slate-700">{activeWorkers}</span>
                                            </div>
                                            {activeManagers > 0 && (
                                                <Badge 
                                                    variant="secondary" 
                                                    className="px-1.5 py-0 h-5 text-[10px] bg-indigo-100/50 text-indigo-700 border-indigo-200/50"
                                                >
                                                    {activeManagers} Gestores
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                    <div className="h-8 w-[1px] bg-slate-200" />
                                    <div className="text-right">
                                        <p className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">SS (%)</p>
                                        <div className="flex items-center justify-end gap-1 text-indigo-600">
                                            <Wallet className="h-4 w-4" />
                                            <span className="text-sm font-bold">{ss}%</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="pt-2 border-t border-slate-100 flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
                                    <div className="flex items-center space-x-2">
                                        <Switch
                                            checked={isManaged}
                                            disabled={updateCompanyMutation.isPending}
                                            onCheckedChange={(checked) => {
                                                updateCompanyMutation.mutate({
                                                    companyId: company.id,
                                                    data: { isManaged: checked }
                                                });
                                            }}
                                        />
                                        <span className="text-xs text-slate-600 font-medium">Modo Gestionada</span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <Switch
                                            checked={isActive}
                                            disabled={updateCompanyMutation.isPending}
                                            onCheckedChange={(checked) => {
                                                updateCompanyMutation.mutate({
                                                    companyId: company.id,
                                                    data: { isActive: checked }
                                                });
                                            }}
                                        />
                                        <span className={`text-xs font-medium ${isActive ? "text-emerald-700" : "text-red-600"}`}>
                                            {isActive ? "Activa" : "Suspendida"}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium pt-1">
                                    <span>Ver configuración completa</span>
                                    <div className="h-1 w-1 rounded-full bg-slate-300" />
                                    <span>{company.fiscalId || "Sin CIF/NIF"}</span>
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {filteredCompanies.length === 0 && (
                <div className="py-20 text-center space-y-3 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
                    <Search className="h-10 w-10 text-slate-300 mx-auto" />
                    <div className="space-y-1">
                        <p className="text-slate-600 font-medium">No se encontraron empresas</p>
                        <p className="text-slate-400 text-sm">Prueba con otro término de búsqueda o crea una nueva empresa.</p>
                    </div>
                </div>
            )}
        </div>
    );
}
