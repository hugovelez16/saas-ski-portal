"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save } from "lucide-react";

import { CompanyModulesList } from "@/components/modules/CompanyModulesList";
import { ReadOnlyJsonButton } from "@/components/admin/readonly-json-dialog";
import { TaxConfigBuilder } from "@/components/admin/tax-config-builder";
import { WorklogDefinitionBuilder } from "@/components/admin/worklog-definition-builder";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { usePermissions } from "@/hooks/use-permissions";
import { useToast } from "@/hooks/use-toast";
import {
    getCompanyManagerSettings,
    getWorklogDefinitionsUsage,
    updateCompany,
    updateCompanyManagerSettings,
} from "@/lib/api/companies";
import type { PlatformSettings } from "@/lib/types";

interface CompanyConfigurationTabProps {
    company: any;
}

const PLAN_OPTIONS = [
    { value: "__none__", label: "Sin plan asignado" },
    { value: "basico", label: "Pista Verde (Basico)" },
    { value: "escuela", label: "Pista Azul (Escuela)" },
    { value: "grande", label: "Pista Roja (Grande)" },
    { value: "pista_negra", label: "Pista Negra" },
    { value: "custom", label: "Personalizado" },
];

function CompanySettingsBuilder({
    initialValue,
    onSave,
}: {
    initialValue: { default_is_gross?: boolean };
    onSave: (val: { default_is_gross: boolean }) => void;
}) {
    const [defaultIsGross, setDefaultIsGross] = React.useState(Boolean(initialValue?.default_is_gross));

    React.useEffect(() => {
        setDefaultIsGross(Boolean(initialValue?.default_is_gross));
    }, [initialValue?.default_is_gross]);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5 pr-4">
                    <Label htmlFor="default-is-gross" className="text-sm font-medium">
                        Tarifa bruta por defecto para miembros nuevos
                    </Label>
                    <p className="text-xs text-muted-foreground">
                        Valor inicial de bruto o neto que se aplica al incorporar nuevos miembros. No altera los miembros existentes.
                    </p>
                </div>
                <Switch
                    id="default-is-gross"
                    checked={defaultIsGross}
                    onCheckedChange={setDefaultIsGross}
                />
            </div>
            <div className="flex justify-end">
                <Button type="button" onClick={() => onSave({ default_is_gross: defaultIsGross })}>
                    <Save className="mr-2 h-4 w-4" />
                    Guardar Ajustes
                </Button>
            </div>
        </div>
    );
}

function PlatformSettingsBuilder({
    initialValue,
    onSave,
}: {
    initialValue?: Partial<PlatformSettings> | null;
    onSave: (val: PlatformSettings) => void;
}) {
    const [plan, setPlan] = React.useState<string>(initialValue?.plan || "__none__");
    const [maxMonitors, setMaxMonitors] = React.useState<string>(
        initialValue?.limits?.max_monitors !== null && initialValue?.limits?.max_monitors !== undefined
            ? String(initialValue.limits.max_monitors)
            : "",
    );
    const [maxManagers, setMaxManagers] = React.useState<string>(
        initialValue?.limits?.max_managers !== null && initialValue?.limits?.max_managers !== undefined
            ? String(initialValue.limits.max_managers)
            : "",
    );

    const serialized = JSON.stringify(initialValue || {});
    React.useEffect(() => {
        setPlan(initialValue?.plan || "__none__");
        setMaxMonitors(
            initialValue?.limits?.max_monitors !== null && initialValue?.limits?.max_monitors !== undefined
                ? String(initialValue.limits.max_monitors)
                : "",
        );
        setMaxManagers(
            initialValue?.limits?.max_managers !== null && initialValue?.limits?.max_managers !== undefined
                ? String(initialValue.limits.max_managers)
                : "",
        );
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [serialized]);

    const parseLimit = (raw: string): number | null => {
        const clean = raw.trim();
        if (clean === "") return null;
        const n = Number(clean);
        if (!Number.isInteger(n) || n < 0) return null;
        return n;
    };

    const handleSave = () => {
        onSave({
            plan: plan === "__none__" ? null : plan,
            limits: {
                max_monitors: parseLimit(maxMonitors),
                max_managers: parseLimit(maxManagers),
            },
            modules: initialValue?.modules ? { ...initialValue.modules } : {},
        });
    };

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                    <Label htmlFor="platform-plan" className="text-xs text-muted-foreground">
                        Plan comercial
                    </Label>
                    <Select value={plan} onValueChange={setPlan}>
                        <SelectTrigger id="platform-plan">
                            <SelectValue placeholder="Selecciona un plan" />
                        </SelectTrigger>
                        <SelectContent>
                            {PLAN_OPTIONS.map((option) => (
                                <SelectItem key={option.value} value={option.value}>
                                    {option.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1.5">
                    <Label htmlFor="platform-max-monitors" className="text-xs text-muted-foreground">
                        Limite de monitores
                    </Label>
                    <Input
                        id="platform-max-monitors"
                        type="number"
                        min={0}
                        placeholder="Sin limite"
                        value={maxMonitors}
                        onChange={(e) => setMaxMonitors(e.target.value)}
                    />
                </div>
                <div className="space-y-1.5">
                    <Label htmlFor="platform-max-managers" className="text-xs text-muted-foreground">
                        Limite de responsables
                    </Label>
                    <Input
                        id="platform-max-managers"
                        type="number"
                        min={0}
                        placeholder="Sin limite"
                        value={maxManagers}
                        onChange={(e) => setMaxManagers(e.target.value)}
                    />
                </div>
            </div>
            <div className="flex justify-end">
                <Button type="button" onClick={handleSave}>
                    <Save className="mr-2 h-4 w-4" />
                    Guardar Ajustes de Plataforma
                </Button>
            </div>
        </div>
    );
}

/**
 * Configuracion de la empresa:
 * - Manager y PA editan `settings`, `worklog_definitions` y `tax_config` (R-EMP-08, R-EMP-45).
 * - Solo el PA edita `platform_settings` y consulta el JSON en solo lectura (R-EMP-42, R-EMP-49).
 */
export function CompanyConfigurationTab({ company }: CompanyConfigurationTabProps) {
    const { isPlatformAdmin, role } = usePermissions(company);
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const canEditCompanySettings = isPlatformAdmin || role === "manager";

    const { data: managerSettings } = useQuery({
        queryKey: ["companyManagerSettings", company.id],
        queryFn: () => getCompanyManagerSettings(company.id),
        enabled: !isPlatformAdmin && role === "manager",
    });

    const { data: worklogUsage = {} } = useQuery({
        queryKey: ["worklogUsage", company.id, isPlatformAdmin],
        queryFn: () => getWorklogDefinitionsUsage(company.id, { asAdmin: isPlatformAdmin }),
        enabled: canEditCompanySettings,
    });

    const mutation = useMutation({
        mutationFn: async (data: {
            settings?: { default_is_gross: boolean };
            worklogDefinitions?: Record<string, any>;
            taxConfig?: Record<string, number>;
            platformSettings?: PlatformSettings;
        }): Promise<void> => {
            if (isPlatformAdmin) {
                await updateCompany(company.id, data);
                return;
            }
            await updateCompanyManagerSettings(company.id, {
                ...(data.settings !== undefined ? { settings: data.settings } : {}),
                ...(data.worklogDefinitions !== undefined ? { worklog_definitions: data.worklogDefinitions } : {}),
                ...(data.taxConfig !== undefined ? { tax_config: data.taxConfig } : {}),
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            queryClient.invalidateQueries({ queryKey: ["company", company.id] });
            queryClient.invalidateQueries({ queryKey: ["companyManagerSettings", company.id] });
            queryClient.invalidateQueries({ queryKey: ["worklogUsage", company.id] });
            toast({ title: "Configuración guardada correctamente" });
        },
    });

    const effectiveSettings = isPlatformAdmin
        ? company.settings || {}
        : managerSettings?.settings || { default_is_gross: false };
    const effectiveWorklogDefs = isPlatformAdmin
        ? company.worklogDefinitions || {}
        : managerSettings?.worklog_definitions ?? company.worklogDefinitions ?? {};
    const effectiveTaxConfig = isPlatformAdmin
        ? company.taxConfig || {}
        : managerSettings?.tax_config ?? company.taxConfig ?? {};

    return (
        <div className="space-y-8">
            {/* 1. Modulos activos */}
            <Card className="border-indigo-100 shadow-sm">
                <CardHeader className="bg-indigo-50/30 flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="text-xl">Módulos Activos</CardTitle>
                        <CardDescription>Módulos y funcionalidades activos para esta empresa.</CardDescription>
                    </div>
                    {isPlatformAdmin && (
                        <Button variant="outline" size="sm" asChild>
                            <a href="/admin/modules">Gestionar Módulos</a>
                        </Button>
                    )}
                </CardHeader>
                <CardContent className="pt-6">
                    <CompanyModulesList companyId={company.id} />
                </CardContent>
            </Card>

            {canEditCompanySettings && (
                <>
                    {/* 2. Ajustes de Empresa */}
                    <Card className="border-slate-200 shadow-sm">
                        <CardHeader className="bg-slate-50/50 flex flex-row items-start justify-between gap-4">
                            <div>
                                <CardTitle className="text-xl">Ajustes de Empresa</CardTitle>
                                <CardDescription>
                                    Opciones operativas de la escuela editables por el equipo gestor.
                                </CardDescription>
                            </div>
                            {isPlatformAdmin && (
                                <ReadOnlyJsonButton title="settings.json" value={effectiveSettings} />
                            )}
                        </CardHeader>
                        <CardContent className="pt-6">
                            <CompanySettingsBuilder
                                initialValue={effectiveSettings}
                                onSave={(val) => mutation.mutate({ settings: val })}
                            />
                        </CardContent>
                    </Card>

                    {/* 3. Definiciones de Turnos e Impuestos */}
                    <Card className="border-slate-200 shadow-sm">
                        <CardHeader className="bg-slate-50/50">
                            <CardTitle className="text-xl">Tipos de Turno e Impuestos</CardTitle>
                            <CardDescription>
                                Configura los tipos de jornada, sus opciones y las retenciones globales de la empresa.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-10 pt-6">
                            <div className="space-y-4">
                                <div className="flex items-center justify-between gap-4">
                                    <h3 className="text-lg font-bold">Partes de Trabajo</h3>
                                    {isPlatformAdmin && (
                                        <ReadOnlyJsonButton
                                            title="worklog_definitions.json"
                                            value={effectiveWorklogDefs}
                                        />
                                    )}
                                </div>
                                <WorklogDefinitionBuilder
                                    initialValue={effectiveWorklogDefs}
                                    usage={worklogUsage}
                                    onSave={(val) => mutation.mutate({ worklogDefinitions: val })}
                                />
                            </div>
                            <hr />
                            <div className="space-y-4">
                                <div className="flex items-center justify-between gap-4">
                                    <h3 className="text-lg font-bold">Tasas de Impuestos (Default)</h3>
                                    {isPlatformAdmin && (
                                        <ReadOnlyJsonButton title="tax_config.json" value={effectiveTaxConfig} />
                                    )}
                                </div>
                                <TaxConfigBuilder
                                    initialValue={effectiveTaxConfig}
                                    onSave={(val) => mutation.mutate({ taxConfig: val })}
                                />
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}

            {/* 4. Ajustes de Plataforma (solo PA) */}
            {isPlatformAdmin && (
                <Card className="border-slate-200 shadow-sm">
                    <CardHeader className="bg-slate-50/50 flex flex-row items-start justify-between gap-4">
                        <div>
                            <CardTitle className="text-xl">Ajustes de Plataforma</CardTitle>
                            <CardDescription>
                                Plan comercial, limites y configuracion de plataforma (solo administrador de plataforma).
                            </CardDescription>
                        </div>
                        <ReadOnlyJsonButton title="platform_settings.json" value={company.platformSettings || {}} />
                    </CardHeader>
                    <CardContent className="pt-6">
                        <PlatformSettingsBuilder
                            initialValue={company.platformSettings}
                            onSave={(val) => mutation.mutate({ platformSettings: val })}
                        />
                    </CardContent>
                </Card>
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
