"use client";

import { useAuth } from "@/context/AuthContext";
import { SUSPENDED_COMPANY_MESSAGE } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { getCompanies, getMyCompanies } from "@/lib/api/companies";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Building2, User, ShieldCheck, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface ScopeSelectionDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function ScopeSelectionDialog({ open, onOpenChange }: ScopeSelectionDialogProps) {
    const { user, switchScope } = useAuth();
    const isPlatformAdmin = Boolean(user?.isPlatformAdmin || user?.role === 'admin');

    const { data: allCompanies = [], isLoading } = useQuery({
        queryFn: async () => {
            if (isPlatformAdmin) {
                return getCompanies();
            }
            return getMyCompanies();
        },
        queryKey: ['scopeCompanies', isPlatformAdmin],
        enabled: open && !!user
    });

    // Worker y manager no pueden operar en empresas suspendidas; el PA si las ve.
    const companies = isPlatformAdmin
        ? allCompanies
        : allCompanies.filter((company: { isActive?: boolean }) => company.isActive !== false);

    const handleSelect = async (companyId: string | null, viewAs?: 'manager' | 'worker') => {
        await switchScope(companyId, viewAs);
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Cambiar Contexto de Trabajo</DialogTitle>
                    <DialogDescription>
                        {isPlatformAdmin
                            ? "Como Administrador, puedes gestionar cualquier empresa, verla en modo solo lectura como manager o worker, o volver al modo principal."
                            : "Selecciona la empresa con la que deseas operar ahora."}
                    </DialogDescription>
                </DialogHeader>

                {isPlatformAdmin && (
                    <div className={cn(
                        "mb-2 p-4 rounded-xl border-2 transition-all flex items-center justify-between",
                        !user?.activeCompanyId ? "border-indigo-600 bg-indigo-50" : "border-slate-100 bg-slate-50/50"
                    )}>
                        <div className="flex items-center space-x-3">
                            <div className="p-2 bg-indigo-100 rounded-lg">
                                <ShieldCheck className="w-5 h-5 text-indigo-600" />
                            </div>
                            <div>
                                <h3 className="font-bold text-slate-900 leading-tight">Administrador Principal</h3>
                                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Sin empresa asignada</p>
                            </div>
                        </div>
                        <Button
                            variant={!user?.activeCompanyId ? "default" : "outline"}
                            size="sm"
                            onClick={() => handleSelect(null)}
                            className="text-xs h-8"
                        >
                            {!user?.activeCompanyId ? "Activo" : "Restablecer"}
                        </Button>
                    </div>
                )}

                <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
                    {isLoading ? (
                        <div className="text-center py-4">Cargando empresas...</div>
                    ) : companies.length === 0 ? (
                        <div className="text-center py-4 text-muted-foreground">
                            {allCompanies.length > 0 ? SUSPENDED_COMPANY_MESSAGE : "No hay empresas disponibles."}
                        </div>
                    ) : (
                        companies.map((company: any) => {
                            const isCurrentCompany = user?.activeCompanyId === company.id;
                            const dbRole = (company.role || 'N/A').toLowerCase();
                            const isReadOnlyManager = isCurrentCompany && user?.viewAs === 'manager';
                            const isReadOnlyWorker = isCurrentCompany && user?.viewAs === 'worker';

                            return (
                                <div key={company.id} className={cn(
                                    "p-4 rounded-xl border-2 transition-all",
                                    isCurrentCompany ? "border-primary bg-primary/5" : "border-slate-100 bg-white"
                                )}>
                                    <div className="flex items-center space-x-3 mb-4">
                                        <div className="p-2 bg-slate-100 rounded-lg">
                                            <Building2 className="w-5 h-5 text-slate-600" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-slate-900">{company.name}</h3>
                                            {!isPlatformAdmin && <p className="text-xs text-slate-500 uppercase tracking-wider">Tu Rol: {dbRole}</p>}
                                            {isPlatformAdmin && <p className="text-xs text-indigo-600 font-bold uppercase tracking-wider">Acceso Administrativo</p>}
                                        </div>
                                        {isCurrentCompany && (
                                            <div className="ml-auto bg-primary text-primary-foreground px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                                                Activa
                                            </div>
                                        )}
                                    </div>

                                    {isPlatformAdmin ? (
                                        <div className="grid grid-cols-3 gap-2">
                                            <Button
                                                variant={isCurrentCompany && !user?.isReadOnlyView ? "default" : "outline"}
                                                size="sm"
                                                className="justify-start h-auto py-2"
                                                onClick={() => handleSelect(company.id)}
                                            >
                                                <div className="flex flex-col items-start">
                                                    <span className="text-xs font-semibold">Gestionar</span>
                                                </div>
                                                {isCurrentCompany && !user?.isReadOnlyView && (
                                                    <Check className="ml-auto h-3 w-3" />
                                                )}
                                            </Button>

                                            <Button
                                                variant={isReadOnlyManager ? "default" : "outline"}
                                                size="sm"
                                                className="justify-start h-auto py-2"
                                                onClick={() => handleSelect(company.id, 'manager')}
                                            >
                                                <ShieldCheck className="mr-2 h-4 w-4 opacity-70" />
                                                <div className="flex flex-col items-start">
                                                    <span className="text-xs font-semibold">Ver como manager</span>
                                                    <span className="text-[10px] opacity-70">Solo lectura</span>
                                                </div>
                                                {isReadOnlyManager && (
                                                    <Check className="ml-auto h-3 w-3" />
                                                )}
                                            </Button>

                                            <Button
                                                variant={isReadOnlyWorker ? "default" : "outline"}
                                                size="sm"
                                                className="justify-start h-auto py-2"
                                                onClick={() => handleSelect(company.id, 'worker')}
                                            >
                                                <User className="mr-2 h-4 w-4 opacity-70" />
                                                <div className="flex flex-col items-start">
                                                    <span className="text-xs font-semibold">Ver como worker</span>
                                                    <span className="text-[10px] opacity-70">Solo lectura</span>
                                                </div>
                                                {isReadOnlyWorker && (
                                                    <Check className="ml-auto h-3 w-3" />
                                                )}
                                            </Button>
                                        </div>
                                    ) : (
                                        <Button
                                            variant={isCurrentCompany ? "default" : "outline"}
                                            size="sm"
                                            className="w-full"
                                            onClick={() => handleSelect(company.id)}
                                        >
                                            Entrar
                                        </Button>
                                    )}
                                </div>
                            );
                        })
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
