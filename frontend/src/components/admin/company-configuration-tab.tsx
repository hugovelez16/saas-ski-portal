"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateCompany } from "@/lib/api/companies";
import { Loader2 } from "lucide-react";
import { WorklogDefinitionBuilder } from "@/components/admin/worklog-definition-builder";
import { TaxConfigBuilder } from "@/components/admin/tax-config-builder";
import { Button } from "@/components/ui/button";
import { CompanyModulesList } from "@/components/modules/CompanyModulesList";
import { BusinessLogicBuilder } from "@/components/admin/business-logic-builder";
import { WorkerUXBuilder } from "@/components/admin/worker-ux-builder";
import { usePermissions } from "@/hooks/use-permissions";

interface CompanyConfigurationTabProps {
    company: any;
}

// Solo el platform admin edita reglas, experiencia y definiciones tecnicas.
// El resto de roles ve la lista de modulos activos en modo lectura.
export function CompanyConfigurationTab({ company }: CompanyConfigurationTabProps) {
    const { isPlatformAdmin } = usePermissions(company);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: (data: any) => updateCompany(company.id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            toast({ title: "Configuración guardada correctamente" });
        },
    });

    return (
        <div className="space-y-8">
            {/* 1. Módulos y Funcionalidades */}
            <Card className="border-indigo-100 shadow-sm">
                <CardHeader className="bg-indigo-50/30 flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="text-xl">Módulos Activos</CardTitle>
                        <CardDescription>Módulos y funcionalidades activos para esta empresa.</CardDescription>
                    </div>
                    {isPlatformAdmin && (
                        <Button variant="outline" size="sm" asChild>
                            <a href="/admin/modules">Gestionar Módulos →</a>
                        </Button>
                    )}
                </CardHeader>
                <CardContent className="pt-6">
                    <CompanyModulesList companyId={company.id} />
                </CardContent>
            </Card>

            {isPlatformAdmin && (
                <>
                    {/* 2. Lógica de Negocio y Económica */}
                    <Card className="border-slate-200 shadow-sm">
                        <CardHeader className="bg-slate-50/50">
                            <CardTitle className="text-xl">Reglas de Negocio</CardTitle>
                            <CardDescription>Configura cómo se procesan los cálculos económicos y la facturación.</CardDescription>
                        </CardHeader>
                        <CardContent className="pt-6">
                            <BusinessLogicBuilder
                                initialValue={company.settings || {}}
                                onSave={(val) => mutation.mutate({ settings: val })}
                            />
                        </CardContent>
                    </Card>

                    {/* 3. Panel del Trabajador */}
                    <Card className="border-slate-200 shadow-sm">
                        <CardHeader className="bg-slate-50/50">
                            <CardTitle className="text-xl">Experiencia del Trabajador</CardTitle>
                            <CardDescription>Controla qué pueden hacer los empleados y cómo interactúan con la App.</CardDescription>
                        </CardHeader>
                        <CardContent className="pt-6">
                            <WorkerUXBuilder
                                initialValue={company.settings || {}}
                                onSave={(val) => mutation.mutate({ settings: val })}
                            />
                        </CardContent>
                    </Card>

                    {/* 4. Definiciones de Datos (Legacy/Existing) */}
                    <Card className="border-slate-200 shadow-sm">
                        <CardHeader className="bg-slate-50/50">
                            <CardTitle className="text-xl">Definiciones Técnicas</CardTitle>
                            <CardDescription>Configura los tipos de jornada y las tasas de impuestos globales.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-10 pt-6">
                            <div className="space-y-4">
                                <h3 className="text-lg font-bold">Partes de Trabajo</h3>
                                <WorklogDefinitionBuilder
                                    initialValue={company.worklogDefinitions || {}}
                                    onSave={(val) => mutation.mutate({ worklogDefinitions: val })}
                                />
                            </div>
                            <hr />
                            <div className="space-y-4">
                                <h3 className="text-lg font-bold">Tasas de Impuestos (Default)</h3>
                                <TaxConfigBuilder
                                    initialValue={company.taxConfig || {}}
                                    onSave={(val) => mutation.mutate({ taxConfig: val })}
                                />
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}

            {mutation.isPending && (
                <div className="fixed bottom-8 right-8 bg-white p-4 rounded-xl shadow-2xl border border-indigo-100 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-4">
                    <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                    <span className="font-medium">Guardando cambios...</span>
                </div>
            )}
        </div>
    );
}
