"use client";
export const dynamic = "force-dynamic";

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCompaniesDetailed, updateMemberStatus, updateMemberRole, MemberRole, getCompanyRates, updateCompany } from "@/lib/api/companies";
import { usePermissions } from "@/hooks/use-permissions";
import { useParams, useRouter } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbSeparator, BreadcrumbPage } from "@/components/ui/breadcrumb";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Check, X, Shield, Loader2, Pencil } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { AddMemberDialog } from "@/components/admin/add-member-dialog";
import { CompanyConfigurationTab } from "@/components/admin/company-configuration-tab";
import { useAuth } from "@/context/AuthContext";
import { CompanyMember } from "@/lib/types";
import { DataTable } from "@/components/ui/data-table";
import { ColumnDef } from "@tanstack/react-table";
import { UserRatesEditDialog } from "@/components/admin/user-rates-edit-dialog";
import { formatPercentage } from "@/lib/utils";

export default function CompanyDetailsPage() {
    const { user } = useAuth();
    const { companyId } = useParams();
    const router = useRouter();
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const { data: companies = [], isLoading } = useQuery({
        queryFn: () => getCompaniesDetailed({ asAdmin: true }),
        queryKey: ["companiesDetailed"],
    });

    const company = companies.find(c => c.id === companyId);
    const { canManageMembers, canEditCompany } = usePermissions();

    const statusMutation = useMutation({
        mutationFn: ({ userId, status }: { userId: string, status: string }) =>
            updateMemberStatus(companyId as string, userId, status),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            toast({ title: "Estado membresía actualizado" });
        },    });

    const roleMutation = useMutation({
        mutationFn: ({ userId, role }: { userId: string, role: MemberRole }) =>
            updateMemberRole(companyId as string, userId, role),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            toast({ title: "Rol actualizado" });
        },    });


    if (isLoading) return <div className="p-8"><Loader2 className="animate-spin" /></div>;
    if (!company) return <div className="p-8">Empresa no encontrada</div>;

    const workers = company.members.filter(m => m.role === 'worker');
    const managers = company.members.filter(m => m.role === 'manager');

    const memberColumns: ColumnDef<CompanyMember>[] = [
        {
            accessorKey: "user",
            header: "Usuario",
            cell: ({ row }) => (
                <div className="flex flex-col">
                    <span className="font-medium">{row.original.user?.firstName} {row.original.user?.lastName}</span>
                    <span className="text-xs text-muted-foreground">{row.original.user?.email}</span>
                </div>
            )
        },
        {
            id: "active",
            header: "Activo",
            cell: ({ row }) => {
                const member = row.original;
                return (
                    <div 
                        className="flex items-center"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <Switch
                            checked={member.isActive}
                            onCheckedChange={(checked) => statusMutation.mutate({
                                userId: member.userId,
                                status: checked ? 'active' : 'rejected'
                            })}
                        />
                    </div>
                );
            }
        },
        {
            id: "actions",
            header: "Acciones",
            cell: ({ row }) => {
                const member = row.original;
                return (
                    <div className="flex items-center gap-2">
                        {canManageMembers && (member.role === 'worker' ? (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    roleMutation.mutate({ userId: member.userId, role: 'manager' });
                                }}
                                title="Promover a Manager"
                            >
                                <Shield className="h-4 w-4 mr-1 text-indigo-600" />
                                Promover
                            </Button>
                        ) : (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    roleMutation.mutate({ userId: member.userId, role: 'worker' });
                                }}
                                title="Degradar a Trabajador"
                            >
                                Degradar
                            </Button>
                        ))}
                    </div>
                );
            }
        }
    ];

    return (
        <div className="space-y-6">
            <Breadcrumb>
                <BreadcrumbList>
                    <BreadcrumbItem>
                        <BreadcrumbLink onClick={() => router.push('/admin/companies')} className="cursor-pointer text-indigo-600">Empresas</BreadcrumbLink>
                    </BreadcrumbItem>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                        <BreadcrumbPage>{company.name}</BreadcrumbPage>
                    </BreadcrumbItem>
                </BreadcrumbList>
            </Breadcrumb>

            <div className="flex justify-between items-start">
                <div>
                    <CompanyNameHeading companyId={companyId as string} name={company.name} canEdit={canEditCompany} />
                    <p className="text-muted-foreground">Panel avanzado de gestión para administradores.</p>
                </div>
                <div className="flex gap-2">
                    {canManageMembers && (
                        <AddMemberDialog companyId={companyId as string} companyName={company.name} existingMembers={company.members} />
                    )}
                </div>
            </div>

            <Tabs defaultValue="workers" className="w-full">
                <TabsList className="bg-slate-100 dark:bg-slate-900 p-1 rounded-lg">
                    <TabsTrigger value="workers">Trabajadores ({workers.length})</TabsTrigger>
                    <TabsTrigger value="managers">Managers ({managers.length})</TabsTrigger>
                    <TabsTrigger value="taxes">Tasas & IRPF</TabsTrigger>
                    <TabsTrigger value="settings">Configuración</TabsTrigger>
                </TabsList>

                {/* WORKERS TAB */}
                <TabsContent value="workers" className="pt-4">
                    <Card className="border-none shadow-none bg-transparent">
                        <CardHeader className="px-0">
                            <CardTitle>Trabajadores</CardTitle>
                            <CardDescription>Gestión de personal de campo y sus permisos.</CardDescription>
                        </CardHeader>
                        <CardContent className="px-0">
                            <DataTable 
                                columns={memberColumns} 
                                data={workers} 
                                searchKey="user" 
                                searchPlaceholder="Buscar trabajador..." 
                                onRowClick={(row) => {
                                    const path = user?.role === 'admin' ? `/admin/users/${row.userId}` : `/manager/users/${row.userId}`;
                                    router.push(path);
                                }}
                            />
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* MANAGERS TAB */}
                <TabsContent value="managers" className="pt-4">
                    <Card className="border-none shadow-none bg-transparent">
                        <CardHeader className="px-0">
                            <CardTitle>Managers</CardTitle>
                            <CardDescription>Usuarios con privilegios de gestión en esta empresa.</CardDescription>
                        </CardHeader>
                        <CardContent className="px-0">
                            <DataTable 
                                columns={memberColumns} 
                                data={managers} 
                                searchKey="user" 
                                searchPlaceholder="Buscar manager..." 
                                onRowClick={(row) => {
                                    const path = user?.role === 'admin' ? `/admin/users/${row.userId}` : `/manager/users/${row.userId}`;
                                    router.push(path);
                                }}
                            />
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* TAXES TAB */}
                <TabsContent value="taxes" className="pt-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Resumen de Tasas</CardTitle>
                            <CardDescription>Vista consolidada de los costes por miembro.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <TaxOverview company={company} isAdmin={user?.role === 'admin'} />
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* CONFIGURATION TAB */}
                <TabsContent value="settings" className="pt-4">
                    <CompanyConfigurationTab key={company.id} company={company} />
                </TabsContent>
            </Tabs>
        </div>
    );
}

const COMPANY_NAME_MAX_LENGTH = 120;

function CompanyNameHeading({ companyId, name, canEdit }: { companyId: string, name: string, canEdit: boolean }) {
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [isEditing, setIsEditing] = React.useState(false);
    const [draftName, setDraftName] = React.useState("");
    const [validationError, setValidationError] = React.useState<string | null>(null);

    const nameMutation = useMutation({
        mutationFn: (newName: string) => updateCompany(companyId, { name: newName }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            setIsEditing(false);
            setValidationError(null);
            toast({ title: "Nombre de la empresa actualizado" });
        },
        // El error HTTP lo muestra el interceptor de lib/api.ts.
    });

    if (!canEdit) {
        return <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{name}</h1>;
    }

    const startEditing = () => {
        setDraftName(name);
        setValidationError(null);
        setIsEditing(true);
    };

    const cancelEditing = () => {
        setIsEditing(false);
        setValidationError(null);
    };

    const saveName = () => {
        const trimmed = draftName.trim();
        if (trimmed.length === 0) {
            setValidationError("El nombre no puede estar vacío.");
            return;
        }
        if (trimmed.length > COMPANY_NAME_MAX_LENGTH) {
            setValidationError(`El nombre no puede superar los ${COMPANY_NAME_MAX_LENGTH} caracteres.`);
            return;
        }
        if (trimmed === name) {
            setValidationError("El nombre no ha cambiado.");
            return;
        }
        setValidationError(null);
        nameMutation.mutate(trimmed);
    };

    if (!isEditing) {
        return (
            <div className="flex items-center gap-2">
                <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{name}</h1>
                <Button variant="ghost" size="icon" onClick={startEditing} aria-label="Editar nombre de la empresa" title="Editar nombre">
                    <Pencil className="h-4 w-4" />
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-1">
            <div className="flex items-center gap-2">
                <Input
                    value={draftName}
                    onChange={(e) => {
                        setDraftName(e.target.value);
                        setValidationError(null);
                    }}
                    aria-label="Nombre de la empresa"
                    aria-invalid={validationError !== null}
                    className="max-w-md text-2xl font-bold h-auto py-1"
                    disabled={nameMutation.isPending}
                    autoFocus
                />
                <Button size="icon" onClick={saveName} disabled={nameMutation.isPending} aria-label="Guardar nombre" title="Guardar">
                    {nameMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                </Button>
                <Button variant="outline" size="icon" onClick={cancelEditing} disabled={nameMutation.isPending} aria-label="Cancelar edición de nombre" title="Cancelar">
                    <X className="h-4 w-4" />
                </Button>
            </div>
            {validationError && <p className="text-sm text-destructive">{validationError}</p>}
        </div>
    );
}

function TaxOverview({ company, isAdmin }: { company: any, isAdmin?: boolean }) {
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [editingMember, setEditingMember] = React.useState<CompanyMember | any>(null);

    const { data: members = [], isLoading } = useQuery({
        queryKey: ["companyRates", company.id],
        queryFn: () => getCompanyRates(company.id),
    });

    const columns = React.useMemo<ColumnDef<CompanyMember>[]>(() => [
        {
            accessorKey: "user",
            header: "Miembro",
            cell: ({ row }) => (
                <div className="flex flex-col">
                    <span className="font-medium text-slate-900 dark:text-slate-100">{row.original.user?.firstName} {row.original.user?.lastName}</span>
                    <span className="text-[10px] text-muted-foreground uppercase font-mono">{row.original.user?.email}</span>
                </div>
            )
        },
        {
            id: "rates",
            header: "Tarifas (€)",
            cell: ({ row }) => {
                const m = row.original;
                const definitions = company.worklogDefinitions || {};
                const activeRates = Object.entries(definitions).map(([key, def]: [string, any]) => {
                    const rate = m.ratesConfig?.[key]?.base_rate;
                    if (!rate || rate <= 0) return null;
                    return { key, label: def.label, value: rate };
                }).filter(Boolean);

                return (
                    <div className="flex flex-wrap gap-2 text-[11px]">
                        {activeRates.length > 0 ? (
                            activeRates.map((r: any) => (
                                <span 
                                    key={r.key} 
                                    className="flex items-center bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700"
                                    title={r.label}
                                >
                                    <span className="opacity-50 mr-1">{r.label}:</span>
                                    <b className="text-indigo-600 dark:text-indigo-400">{r.value}€</b>
                                </span>
                            ))
                        ) : (
                            <span className="text-muted-foreground italic">Sin tarifas</span>
                        )}
                    </div>
                );
            }
        },
        {
            id: "taxes",
            header: "Configuración Fiscal",
            cell: ({ row }) => {
                const m = row.original;
                // Get primary tax config (first one found with overrides or just the first one)
                const configKeys = Object.keys(m.ratesConfig || {});
                const primaryKey = configKeys.find(k => m.ratesConfig?.[k]?.tax_overrides) || configKeys[0];
                const primary = primaryKey ? m.ratesConfig?.[primaryKey] : null;
                
                if (!primary) return <span className="text-muted-foreground text-[10px]">Sin configurar</span>;

                const isGross = primary.is_gross !== false;
                const overrides = primary.tax_overrides || {};
                const companyTaxes = company.taxConfig || {};
                // Efectivos: empresa + overrides no nulos del miembro
                const effective: Record<string, number> = { ...companyTaxes };
                for (const [name, v] of Object.entries(overrides)) {
                    if (v !== null && v !== undefined) effective[name] = v;
                }
                const taxEntries = Object.entries(effective);

                return (
                    <div className="flex items-center gap-3">
                        <Badge variant={isGross ? "default" : "outline"} className={isGross ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" : "text-slate-500"}>
                            {isGross ? "Bruto" : "Neto"}
                        </Badge>
                        <div className="flex gap-2 text-[10px] font-mono">
                            {taxEntries.length === 0 && (
                                <span className="text-muted-foreground">Sin impuestos</span>
                            )}
                            {taxEntries.map(([name, rate]) => (
                                <span
                                    key={name}
                                    className={
                                        name in companyTaxes
                                            ? "bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded"
                                            : "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 px-1.5 py-0.5 rounded"
                                    }
                                    title={name}
                                >
                                    {name}: <b className="ml-0.5">{formatPercentage(rate)}</b>
                                </span>
                            ))}
                        </div>
                    </div>
                );
            }
        }
    ], [company]);

    if (isLoading) return <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="relative">
            <DataTable 
                columns={columns} 
                data={members} 
                onRowClick={isAdmin ? (row) => setEditingMember(row) : undefined}
            />
            {editingMember && (
                <UserRatesEditDialog
                    open={!!editingMember}
                    onOpenChange={(open) => !open && setEditingMember(null)}
                    userId={editingMember.userId}
                    company={company}
                    member={editingMember}
                    userName={`${editingMember.user?.firstName} ${editingMember.user?.lastName}`}
                />
            )}
        </div>
    );
}
