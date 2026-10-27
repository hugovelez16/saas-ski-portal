"use client";
export const dynamic = "force-dynamic";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getUser, getUserCompanies } from "@/lib/api/users";
import { getWorkLogsPage, deleteWorkLog } from "@/lib/api/work-logs";
import { updateMemberRates, updateMemberRole, updateMemberStatus, MemberRole } from "@/lib/api/companies";
import { useParams, useRouter } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar, Building2, Wallet, Database, ArrowLeft, Loader2, Sparkles, Moon, Trash2, Pencil, Shield } from "lucide-react";
import { format } from "date-fns";
import { useState, useMemo, useEffect } from "react";
import { WorkLogsTable } from "@/components/work-log/work-logs-table";
import { useToast } from "@/hooks/use-toast";
import { JsonEditor } from "@/components/admin/json-editor";
import { UserEditDialog } from "@/components/admin/user-edit-dialog";
import { UserCreateWorkLogDialog } from "@/components/work-log/user-dialog";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { TaxOverridesFields, compactTaxOverrides } from "@/components/admin/tax-overrides-fields";

const LOGS_PAGE_SIZE = 50;


const numericSchema = z.preprocess(
    (val) => (val === "" || val === undefined || val === null ? 0 : val),
    z.coerce.number().min(0)
);

const memberConfigSchema = z.object({
    role: z.string(),
    isActive: z.boolean(),
    isGross: z.boolean(),
    rates: z.record(numericSchema),
    // Fracciones 0..1 o null (sin override); NaN = entrada invalida en pantalla
    taxOverrides: z.record(z.number().min(0).max(1).nullable())
});

type MemberConfigValues = z.infer<typeof memberConfigSchema>;

function CompanyMemberConfigCard({ user, company, onUpdate }: { user: any, company: any, onUpdate: () => void }) {
    const { toast } = useToast();
    const worklogDefinitions = company.worklogDefinitions || {};
    const ratesConfig = company.ratesConfig || {};

    const form = useForm<MemberConfigValues>({
        resolver: zodResolver(memberConfigSchema),
        defaultValues: {
            role: company.role || "worker",
            isActive: company.isActiveMember ?? true,
            isGross: false,
            rates: {},
            taxOverrides: {}
        }
    });

    useEffect(() => {
        const shiftKeys = Object.keys(worklogDefinitions);
        const initialRates: Record<string, number> = {};
        let isGross = false;
        let taxOverrides: Record<string, number | null> = {};

        let foundTaxes = false;
        for (const key of shiftKeys) {
            const shiftData = ratesConfig[key];
            if (shiftData && typeof shiftData === 'object') {
                initialRates[key] = shiftData.base_rate || 0;
                if (!foundTaxes) {
                    isGross = shiftData.is_gross !== undefined ? shiftData.is_gross : false;
                    if (shiftData.tax_overrides) {
                        taxOverrides = { ...shiftData.tax_overrides };
                        foundTaxes = true;
                    }
                }
            } else {
                initialRates[key] = 0;
            }
        }

        form.reset({
            role: company.role || "worker",
            isActive: company.isActiveMember ?? true,
            isGross,
            rates: initialRates,
            taxOverrides
        });
    }, [company, worklogDefinitions, ratesConfig, form]);

    const mutation = useMutation({
        mutationFn: async (data: { role?: string; isActive?: boolean; ratesConfig: Record<string, any> }) => {
            if (data.role && data.role !== company.role) {
                await updateMemberRole(company.id, user.id, data.role as MemberRole);
            }
            if (data.isActive !== undefined && data.isActive !== (company.isActiveMember ?? true)) {
                await updateMemberStatus(company.id, user.id, data.isActive ? "active" : "inactive");
            }
            return updateMemberRates(company.id, user.id, data.ratesConfig);
        },
        onSuccess: () => {
            toast({ title: "Configuración actualizada" });
            onUpdate();
        },    });

    function onSubmit(values: MemberConfigValues) {
        console.log("Submitting configuration:", values);
        const newRatesConfig: Record<string, any> = {};
        const shiftKeys = Object.keys(worklogDefinitions);

        for (const key of shiftKeys) {
            newRatesConfig[key] = {
                base_rate: Number(values.rates[key]) || 0,
                is_gross: values.isGross,
                tax_overrides: compactTaxOverrides(values.taxOverrides)
            };
        }

        mutation.mutate({
            role: values.role,
            isActive: values.isActive,
            ratesConfig: newRatesConfig
        });
    }

    const onFormError = (errors: any) => {
        console.error("Form validation errors:", errors);
        toast({
            title: "Error de validación",
            description: "Por favor, revisa los campos del formulario.",
            variant: "destructive"
        });
    };

    return (
        <Card className="border-indigo-100 dark:border-indigo-900 shadow-sm overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between bg-indigo-50/30 dark:bg-indigo-950/10 border-b">
                <div className="flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-indigo-600" />
                    <div>
                        <CardTitle className="text-lg">{company.name}</CardTitle>
                        <CardDescription className="text-xs">ID: {company.id}</CardDescription>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <Badge variant={company.isActiveMember ? 'default' : 'secondary'}>
                        {company.isActiveMember ? 'Activo' : 'Inactivo'}
                    </Badge>
                    <Badge variant="outline" className="capitalize">{company.role}</Badge>
                </div>
            </CardHeader>
            <CardContent className="pt-6">
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit, onFormError)} className="space-y-8">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="md:col-span-1 space-y-4">
                                <h3 className="text-sm font-semibold flex items-center gap-2 text-indigo-600">
                                    <Shield className="h-4 w-4" />
                                    Membresía
                                </h3>
                                <FormField
                                    control={form.control}
                                    name="role"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-xs uppercase text-muted-foreground font-bold tracking-wider">Rol en Empresa</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger className="h-9">
                                                        <SelectValue placeholder="Seleccionar rol" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="worker">Trabajador</SelectItem>
                                                    <SelectItem value="manager">Gestor / Supervisor</SelectItem>
                                                    <SelectItem value="admin">Administrador Empresa</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="isActive"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-row items-center justify-between rounded-md border bg-slate-50 dark:bg-slate-900 px-3 py-2">
                                            <div className="space-y-0.5">
                                                <FormLabel className="text-sm">Usuario Activo</FormLabel>
                                                <FormDescription className="text-[10px]">Permitir registros</FormDescription>
                                            </div>
                                            <FormControl>
                                                <Switch checked={field.value} onCheckedChange={field.onChange} />
                                            </FormControl>
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <div className="md:col-span-2 space-y-4">
                                <h3 className="text-sm font-semibold flex items-center gap-2 text-indigo-600">
                                    <Wallet className="h-4 w-4" />
                                    Tarifas por Turno
                                </h3>
                                <div className="grid grid-cols-2 gap-4">
                                    {Object.entries(worklogDefinitions).map(([key, def]: [string, any]) => (
                                        <FormField
                                            key={key}
                                            control={form.control}
                                            name={`rates.${key}`}
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel className="text-xs uppercase text-muted-foreground font-bold tracking-wider">{def.label}</FormLabel>
                                                    <FormControl>
                                                        <div className="relative">
                                                            <span className="absolute left-3 top-2 text-muted-foreground text-xs">€</span>
                                                            <Input 
                                                                type="number" 
                                                                step="0.01" 
                                                                {...field} 
                                                                value={field.value ?? ""} 
                                                                onChange={field.onChange}
                                                                className="pl-7 h-9" 
                                                            />
                                                        </div>
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4 border-t pt-6">
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="text-sm font-semibold flex items-center gap-2 text-indigo-600">
                                    <Database className="h-4 w-4" />
                                    Impuestos y Deducciones (Per-User)
                                </h3>
                                <FormField
                                    control={form.control}
                                    name="isGross"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-row items-center gap-2 space-y-0">
                                            <FormLabel className="text-xs font-bold text-muted-foreground">{field.value ? "Tarifa bruta (se descuentan los impuestos)" : "Tarifa neta (sin deduccion)"}</FormLabel>
                                            <FormControl>
                                                <Switch checked={field.value} onCheckedChange={field.onChange} />
                                            </FormControl>
                                        </FormItem>
                                    )}
                                />
                            </div>

                            {form.watch("isGross") && (
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                    <FormField
                                        control={form.control}
                                        name="taxOverrides"
                                        render={({ field }) => (
                                            <FormItem className="sm:col-span-3">
                                                <TaxOverridesFields
                                                    companyTaxConfig={company.taxConfig || {}}
                                                    value={field.value || {}}
                                                    onChange={field.onChange}
                                                />
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end pt-2">
                            <Button type="submit" disabled={mutation.isPending} className="bg-indigo-600 hover:bg-indigo-700 shadow-md transition-all">
                                {mutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Pencil className="mr-2 h-4 w-4" />}
                                Actualizar Configuración en {company.name}
                            </Button>
                        </div>
                    </form>
                </Form>
            </CardContent>
        </Card>
    );
}

export default function UserDetailPage() {
    const params = useParams();
    const router = useRouter();
    const queryClient = useQueryClient();
    const { toast } = useToast();
    const userId = params.userId as string;



    const { data: user, isLoading: loadingUser } = useQuery({
        queryFn: () => getUser(userId),
        queryKey: ["user", userId],
    });

    const { data: companies = [], isLoading: loadingCompanies } = useQuery({
        queryFn: () => getUserCompanies(userId),
        queryKey: ["user-companies", userId],
        enabled: !!userId,
    });

    // Historial paginado en servidor: empresa seleccionada (por defecto la primera) y pagina
    const [logCompanyId, setLogCompanyId] = useState<string | undefined>(undefined);
    const [logPage, setLogPage] = useState(1);
    const effectiveLogCompanyId = logCompanyId ?? companies[0]?.id;

    const { data: logsPage, isLoading: loadingLogs } = useQuery({
        queryFn: () => getWorkLogsPage({
            userId: userId,
            companyId: effectiveLogCompanyId,
            limit: LOGS_PAGE_SIZE,
            skip: (logPage - 1) * LOGS_PAGE_SIZE,
        }),
        queryKey: ["work-logs", userId, effectiveLogCompanyId ?? null, logPage],
        enabled: !!userId && !loadingCompanies,
    });

    const workLogs = logsPage?.items ?? [];
    const totalLogs = logsPage?.total ?? 0;
    const totalLogPages = Math.max(1, Math.ceil(totalLogs / LOGS_PAGE_SIZE));

    const updateMemberMutation = useMutation({
        mutationFn: ({ companyId, data }: { companyId: string, data: any }) =>
            updateMemberRates(companyId, userId, data.ratesConfig),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["user-companies", userId] });
            toast({ title: "Configuración de miembro actualizada" });
        },    });



    if (loadingUser) return <div className="p-8 text-center"><Loader2 className="animate-spin" /> Cargando...</div>;
    if (!user) return <div className="p-8 text-center text-red-600">Usuario no encontrado</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}>
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div className="flex-1">
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900">{user.firstName} {user.lastName}</h1>
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <p>{user.email}</p>
                        <span>•</span>
                        <Badge variant={user.isActive ? "default" : "destructive"}>{user.isActive ? "Activo" : "Inactivo"}</Badge>
                        <Badge variant="outline">{user.role}</Badge>
                    </div>
                </div>
                <div className="flex gap-2">
                    <UserCreateWorkLogDialog user={user} companies={companies} onLogUpdate={() => queryClient.invalidateQueries({ queryKey: ["work-logs", userId] })}>
                        <Button>Añadir Parte</Button>
                    </UserCreateWorkLogDialog>
                    <UserEditDialog user={user} />
                </div>
            </div>

            <Tabs defaultValue="worklogs" className="w-full">
                <TabsList className="bg-slate-100 dark:bg-slate-900 p-1 rounded-lg">
                    <TabsTrigger value="worklogs">Historial de Partes</TabsTrigger>
                    <TabsTrigger value="companies">Empresas & Configuración</TabsTrigger>
                </TabsList>

                <TabsContent value="worklogs" className="pt-4">
                    <Card className="border-none shadow-none bg-transparent">
                        <CardHeader className="px-0">
                            <CardTitle>
                                Partes Realizados <span className="text-sm font-normal text-muted-foreground">({totalLogs} registros)</span>
                            </CardTitle>
                            <CardDescription>Visualización completa de la actividad registrada.</CardDescription>
                        </CardHeader>
                        <CardContent className="px-0">
                            <WorkLogsTable
                                data={workLogs}
                                companies={companies}
                                user={user}
                                companyId={effectiveLogCompanyId}
                                onCompanyChange={(id) => { setLogCompanyId(id); setLogPage(1); }}
                                onUpdate={() => queryClient.invalidateQueries({ queryKey: ["work-logs", userId] })}
                                isLoading={loadingLogs}
                            />
                            {totalLogs > LOGS_PAGE_SIZE && (
                                <div className="flex items-center justify-end gap-3 pt-4 text-sm">
                                    <span className="text-muted-foreground">Página {logPage} de {totalLogPages}</span>
                                    <Button variant="outline" size="sm" disabled={logPage <= 1 || loadingLogs} onClick={() => setLogPage(p => p - 1)}>
                                        Anterior
                                    </Button>
                                    <Button variant="outline" size="sm" disabled={logPage >= totalLogPages || loadingLogs} onClick={() => setLogPage(p => p + 1)}>
                                        Siguiente
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="companies" className="pt-4">
                    <div className="grid gap-8">
                        {companies.map((company) => (
                            <CompanyMemberConfigCard 
                                key={company.id}
                                user={user} 
                                company={company} 
                                onUpdate={() => queryClient.invalidateQueries({ queryKey: ["user-companies", userId] })} 
                            />
                        ))}
                    </div>
                </TabsContent>

            </Tabs>
        </div>
    );
}
