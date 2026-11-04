"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getModule, updateModule } from "@/lib/api/modules";
import { getSubscriptions, createSubscription, updateSubscription } from "@/lib/api/modules";
import { getCompanies } from "@/lib/api/companies";
import { getUsers } from "@/lib/api/users";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { ArrowLeft, Package, Sparkles, Edit2, X, ShieldAlert, PlusCircle } from "lucide-react";
import { SubscriptionBadge } from "@/components/modules/SubscriptionBadge";
import { ModuleSubscription } from "@/lib/types";

export default function ModuleDetailPage({ params }: { params: Promise<{ moduleId: string }> }) {
    const { moduleId } = use(params);
    const router = useRouter();
    const queryClient = useQueryClient();

    // ─── Form States ────────────────────────────────────────────────────────
    const [moduleForm, setModuleForm] = useState({
        name: "",
        description: "",
        targetScope: "both" as "company" | "user" | "both",
        priceMonthly: "" as string | number,
        isActive: true,
    });

    const [showSubForm, setShowSubForm] = useState(false);
    const [editingSub, setEditingSub] = useState<ModuleSubscription | null>(null);

    const [subForm, setSubForm] = useState({
        scope: "company" as "company" | "user",
        targetId: "",
        status: "active",
        expiresAt: "",
        notes: "",
    });

    // Helper para fechas seguras
    const parseDate = (dStr: string) => {
        if (!dStr) return null;
        const d = new Date(dStr);
        return isNaN(d.getTime()) ? null : d.toISOString();
    };

    // ─── Queries ────────────────────────────────────────────────────────────
    const { data: module, isLoading: loadingModule } = useQuery({
        queryKey: ["modules", moduleId],
        queryFn: () => getModule(moduleId),
    });

    const { data: subscriptions = [] } = useQuery({
        queryKey: ["subscriptions", { moduleId }],
        queryFn: () => getSubscriptions({ moduleId }),
    });

    const { data: companies = [] } = useQuery({
        queryKey: ["companies"],
        queryFn: getCompanies,
    });

    const { data: users = [] } = useQuery({
        queryKey: ["users"],
        queryFn: getUsers,
    });

    // Sincronizar formulario de módulo
    useEffect(() => {
        if (module) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setModuleForm({
                name: module.name,
                description: module.description || "",
                targetScope: module.targetScope,
                priceMonthly: module.priceMonthly != null ? module.priceMonthly : "",
                isActive: module.isActive,
            });
        }
    }, [module]);

    // ─── Mutations ──────────────────────────────────────────────────────────
    const updateModuleMutation = useMutation({
        mutationFn: (data: Parameters<typeof updateModule>[1]) => updateModule(moduleId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["modules"] });
            toast.success("Módulo actualizado correctamente.");
        },
        onError: () => toast.error("Error al actualizar el módulo."),
    });

    const addSubMutation = useMutation({
        mutationFn: createSubscription,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["subscriptions", { moduleId }] });
            setShowSubForm(false);
            setSubForm({ scope: "company", targetId: "", status: "active", expiresAt: "", notes: "" });
            toast.success("Suscripción registrada correctamente.");
        },
        onError: () => toast.error("Error al registrar la suscripción."),
    });

    const editSubMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: Parameters<typeof updateSubscription>[1] }) => updateSubscription(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["subscriptions", { moduleId }] });
            setEditingSub(null);
            setShowSubForm(false);
            setSubForm({ scope: "company", targetId: "", status: "active", expiresAt: "", notes: "" });
            toast.success("Suscripción actualizada correctamente.");
        },
        onError: () => toast.error("Error al actualizar la suscripción."),
    });

    const cancelSubMutation = useMutation({
        mutationFn: (id: string) => updateSubscription(id, { status: "cancelled" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["subscriptions", { moduleId }] });
            toast.success("Suscripción cancelada.");
        },
        onError: () => toast.error("Error al cancelar la suscripción."),
    });

    // ─── Handlers ───────────────────────────────────────────────────────────
    const handleSaveModule = () => {
        updateModuleMutation.mutate({
            name: moduleForm.name,
            description: moduleForm.description,
            targetScope: moduleForm.targetScope,
            priceMonthly: moduleForm.priceMonthly !== "" ? Number(moduleForm.priceMonthly) : null,
            isActive: moduleForm.isActive,
        });
    };

    const handleSaveSubscription = () => {
        if (!subForm.targetId && !editingSub) {
            toast.error("Por favor, selecciona una entidad para la suscripción.");
            return;
        }

        if (editingSub) {
            editSubMutation.mutate({
                id: editingSub.id,
                data: {
                    status: subForm.status,
                    expiresAt: parseDate(subForm.expiresAt),
                    notes: subForm.notes,
                },
            });
        } else {
            addSubMutation.mutate({
                moduleId,
                scope: subForm.scope,
                companyId: subForm.scope === "company" ? subForm.targetId : undefined,
                userId: subForm.scope === "user" ? subForm.targetId : undefined,
                status: subForm.status,
                expiresAt: parseDate(subForm.expiresAt) || undefined,
                notes: subForm.notes || undefined,
            });
        }
    };

    const handleOpenEditSub = (sub: ModuleSubscription) => {
        setEditingSub(sub);
        setSubForm({
            scope: sub.scope,
            targetId: sub.scope === "company" ? (sub.companyId || "") : (sub.userId || ""),
            status: sub.status,
            expiresAt: sub.expiresAt ? sub.expiresAt.substring(0, 10) : "",
            notes: sub.notes || "",
        });
        setShowSubForm(true);
    };

    const getAssigneeName = (sub: ModuleSubscription) => {
        if (sub.scope === "company") {
            return sub.company?.name ?? (sub.companyId ? `Empresa: ${sub.companyId.substring(0, 8)}...` : "Empresa sin ID");
        } else {
            const u = sub.user;
            if (!u) {
                return sub.userId ? `Usuario: ${sub.userId.substring(0, 8)}...` : "Usuario sin ID";
            }
            const fullName = `${u.firstName || ""} ${u.lastName || ""}`.trim();
            return fullName ? `${fullName} (${u.email})` : u.email;
        }
    };

    if (loadingModule) {
        return <div className="p-8 text-center text-slate-500 font-medium">Cargando detalles del módulo...</div>;
    }

    if (!module) {
        return (
            <div className="p-8 text-center max-w-md mx-auto space-y-4">
                <div className="rounded-full bg-rose-50 p-4 text-rose-500 w-14 h-14 flex items-center justify-center mx-auto">
                    <ShieldAlert className="h-6 w-6" />
                </div>
                <h1 className="text-xl font-bold text-slate-800">Módulo no encontrado</h1>
                <p className="text-sm text-slate-500">El identificador provisto no corresponde a ningún módulo activo en el catálogo.</p>
                <Button onClick={() => router.push("/admin/modules")}>Volver a la lista</Button>
            </div>
        );
    }



    return (
        <div className="space-y-6 w-full py-2">
            {/* Header */}
            <div className="flex items-center gap-4 border-b border-slate-100 pb-5">
                <Button
                    variant="outline"
                    size="icon"
                    onClick={() => router.push("/admin/modules")}
                    className="h-9 w-9 text-slate-500 hover:text-slate-800 rounded-lg shrink-0"
                >
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
                        <Package className="h-5 w-5" />
                    </div>
                    <div>
                        <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-800">
                            {moduleForm.name || "Cargando..."}
                        </h1>
                        <p className="text-xs text-slate-400 font-mono font-semibold">{module.codeName}</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Columna Izquierda: Formulario del Módulo */}
                <div className="lg:col-span-5 space-y-6">
                    <Card className="relative overflow-hidden border-slate-200/80 bg-white">
                        <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-indigo-500 to-sky-400" />
                        <CardHeader className="pb-4">
                            <CardTitle className="text-base font-bold text-slate-800 flex items-center gap-2">
                                <Sparkles className="h-4 w-4 text-indigo-500" /> Datos del Módulo
                            </CardTitle>
                            <CardDescription className="text-xs">Actualiza los datos visuales y de alcance del catálogo</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-1">
                                <Label className="text-xs font-bold text-slate-600">Código interno</Label>
                                <Input
                                    value={module.codeName}
                                    disabled
                                    className="bg-slate-100/80 text-slate-500 font-mono font-semibold text-xs border-slate-200"
                                />
                                <p className="text-[10px] text-slate-400">Identificador permanente de sistema.</p>
                            </div>
                            <div className="space-y-1">
                                <Label className="text-xs font-bold text-slate-600">Nombre visible</Label>
                                <Input
                                    value={moduleForm.name}
                                    onChange={e => setModuleForm(p => ({ ...p, name: e.target.value }))}
                                    className="bg-slate-50/50 focus-visible:ring-indigo-500"
                                />
                            </div>
                            <div className="space-y-1">
                                <Label className="text-xs font-bold text-slate-600">Descripción</Label>
                                <Textarea
                                    value={moduleForm.description}
                                    onChange={e => setModuleForm(p => ({ ...p, description: e.target.value }))}
                                    className="min-h-[100px] bg-slate-50/50 focus-visible:ring-indigo-500 text-sm leading-relaxed"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <Label className="text-xs font-bold text-slate-600">Alcance</Label>
                                    <Select
                                        value={moduleForm.targetScope}
                                        onValueChange={(v: "company" | "user" | "both") => setModuleForm(p => ({ ...p, targetScope: v }))}
                                    >
                                        <SelectTrigger className="bg-slate-50/50">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="both">Empresa y Usuario</SelectItem>
                                            <SelectItem value="company">Solo Empresa</SelectItem>
                                            <SelectItem value="user">Solo Usuario</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs font-bold text-slate-600">Precio mensual (€)</Label>
                                    <Input
                                        type="number"
                                        value={moduleForm.priceMonthly}
                                        onChange={e => setModuleForm(p => ({ ...p, priceMonthly: e.target.value }))}
                                        placeholder="0.00"
                                        className="bg-slate-50/50 focus-visible:ring-indigo-500"
                                    />
                                </div>
                            </div>
                            <div className="flex items-center justify-between border-t border-slate-100 pt-4 mt-2">
                                <div className="space-y-0.5">
                                    <Label className="text-xs font-bold text-slate-700">Módulo Activo</Label>
                                    <p className="text-[10px] text-slate-400">Si está inactivo, no se podrán crear nuevas suscripciones.</p>
                                </div>
                                <Switch
                                    checked={moduleForm.isActive}
                                    onCheckedChange={v => setModuleForm(p => ({ ...p, isActive: v }))}
                                />
                            </div>
                        </CardContent>
                        <CardFooter className="bg-slate-50/50 border-t border-slate-100 py-3.5 flex justify-end">
                            <Button
                                onClick={handleSaveModule}
                                disabled={!moduleForm.name || updateModuleMutation.isPending}
                                className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs py-1.5 px-4"
                            >
                                {updateModuleMutation.isPending ? "Guardando..." : "Guardar Cambios"}
                            </Button>
                        </CardFooter>
                    </Card>
                </div>

                {/* Columna Derecha: Gestión de Suscripciones */}
                <div className="lg:col-span-7 space-y-6">
                    <Card className="border-slate-200/80 bg-white">
                        <CardHeader className="flex flex-row justify-between items-center pb-4 border-b border-slate-100">
                            <div>
                                <CardTitle className="text-base font-bold text-slate-800">Suscripciones Asignadas</CardTitle>
                                <CardDescription className="text-xs">Control de accesos y licencias activas para este módulo</CardDescription>
                            </div>
                            <Button
                                size="sm"
                                disabled={!module.isActive || showSubForm}
                                onClick={() => {
                                    const defaultScope = moduleForm.targetScope === "both" ? "company" : moduleForm.targetScope;
                                    setEditingSub(null);
                                    setSubForm({ scope: defaultScope, targetId: "", status: "active", expiresAt: "", notes: "" });
                                    setShowSubForm(true);
                                }}
                                className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs"
                            >
                                <PlusCircle className="mr-1.5 h-3.5 w-3.5" />
                                Añadir Suscripción
                            </Button>
                        </CardHeader>
                        <CardContent className="space-y-6 pt-5">
                            {/* Formulario Inline Colapsable */}
                            {showSubForm && (
                                <div className="border border-slate-100 rounded-xl p-4 bg-slate-50/50 space-y-4 transition-all duration-300">
                                    <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                            {editingSub ? "Editar Suscripción" : "Nueva Suscripción"}
                                        </h3>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => setShowSubForm(false)}
                                            className="h-6 w-6 text-slate-400 hover:text-slate-600 rounded-md"
                                        >
                                            <X className="h-4.5 w-4.5" />
                                        </Button>
                                    </div>
                                    <div className="space-y-3">
                                        {/* Scope Select - Solo si el alcance general es 'both' y es creación */}
                                        {moduleForm.targetScope === "both" && !editingSub && (
                                            <div className="space-y-1">
                                                <Label className="text-xs font-bold text-slate-600">Tipo de suscripción</Label>
                                                <Select
                                                    value={subForm.scope}
                                                    onValueChange={(v: "company" | "user") => setSubForm(p => ({ ...p, scope: v, targetId: "" }))}
                                                >
                                                    <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="company">Empresa</SelectItem>
                                                        <SelectItem value="user">Usuario</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                        )}

                                        {/* Target Entity Selector - Solo en creación, en edición se muestra lectura */}
                                        {!editingSub ? (
                                            <div className="space-y-1">
                                                <Label className="text-xs font-bold text-slate-600">
                                                    {subForm.scope === "company" ? "Seleccionar Empresa" : "Seleccionar Usuario"}
                                                </Label>
                                                {subForm.scope === "company" ? (
                                                    <Select
                                                        value={subForm.targetId}
                                                        onValueChange={v => setSubForm(p => ({ ...p, targetId: v }))}
                                                    >
                                                        <SelectTrigger className="bg-white focus:ring-indigo-500">
                                                            <SelectValue placeholder="Selecciona una empresa..." />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {companies.map(c => (
                                                                <SelectItem key={c.id} value={c.id}>
                                                                    {c.name}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                ) : (
                                                    <Select
                                                        value={subForm.targetId}
                                                        onValueChange={v => setSubForm(p => ({ ...p, targetId: v }))}
                                                    >
                                                        <SelectTrigger className="bg-white focus:ring-indigo-500">
                                                            <SelectValue placeholder="Selecciona un usuario..." />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {users.map(u => (
                                                                <SelectItem key={u.id} value={u.id}>
                                                                    {u.firstName || u.lastName ? `${u.firstName || ""} ${u.lastName || ""}`.trim() : u.email} ({u.email})
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                )}
                                            </div>
                                        ) : (
                                            <div>
                                                <Label className="text-xs font-bold text-slate-500">Asignada a</Label>
                                                <div className="text-xs font-semibold border border-slate-200/60 rounded-lg px-3 py-2 bg-slate-100 text-slate-600 mt-1">
                                                    {getAssigneeName(editingSub)}
                                                </div>
                                            </div>
                                        )}

                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-1">
                                                <Label className="text-xs font-bold text-slate-600">Estado</Label>
                                                <Select
                                                    value={subForm.status}
                                                    onValueChange={v => setSubForm(p => ({ ...p, status: v }))}
                                                >
                                                    <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="active">Activo</SelectItem>
                                                        <SelectItem value="trial">Trial</SelectItem>
                                                        {editingSub && <SelectItem value="expired">Expirado</SelectItem>}
                                                        {editingSub && <SelectItem value="cancelled">Cancelado</SelectItem>}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            <div className="space-y-1">
                                                <Label className="text-xs font-bold text-slate-600">Fecha expiración (opcional)</Label>
                                                <Input
                                                    type="date"
                                                    value={subForm.expiresAt}
                                                    onChange={e => setSubForm(p => ({ ...p, expiresAt: e.target.value }))}
                                                    className="bg-white focus-visible:ring-indigo-500"
                                                />
                                            </div>
                                        </div>

                                        <div className="space-y-1">
                                            <Label className="text-xs font-bold text-slate-600">Notas (opcional)</Label>
                                            <Input
                                                placeholder="Notas de soporte, Stripe ID, etc..."
                                                value={subForm.notes}
                                                onChange={e => setSubForm(p => ({ ...p, notes: e.target.value }))}
                                                className="bg-white focus-visible:ring-indigo-500"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => setShowSubForm(false)}
                                            className="text-xs"
                                        >
                                            Cancelar
                                        </Button>
                                        <Button
                                            size="sm"
                                            onClick={handleSaveSubscription}
                                            disabled={addSubMutation.isPending || editSubMutation.isPending}
                                            className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs"
                                        >
                                            {addSubMutation.isPending || editSubMutation.isPending ? "Guardando..." : "Guardar Suscripción"}
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {/* Listado de Suscripciones */}
                            <div className="space-y-2.5">
                                {subscriptions.length > 0 ? (
                                    subscriptions.map(sub => (
                                        <div key={sub.id} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/40 p-3 hover:bg-slate-50 transition-colors">
                                            <div className="flex flex-col gap-1 min-w-0 flex-1 mr-2">
                                                <div className="flex items-center gap-2">
                                                    <SubscriptionBadge status={sub.status} />
                                                    <span className="text-xs font-semibold text-slate-700 truncate" title={getAssigneeName(sub)}>
                                                        {getAssigneeName(sub)}
                                                    </span>
                                                </div>
                                                <span className="text-[10px] text-slate-500 font-medium">
                                                    {sub.expiresAt
                                                        ? `Expira: ${new Date(sub.expiresAt).toLocaleDateString("es-ES")}`
                                                        : "Permanente"}
                                                    {sub.notes && ` • ${sub.notes}`}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-1.5 shrink-0">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    disabled={showSubForm}
                                                    onClick={() => handleOpenEditSub(sub)}
                                                    className="h-7 w-7 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50/60 rounded-md"
                                                    title="Editar suscripción"
                                                >
                                                    <Edit2 className="h-3.5 w-3.5" />
                                                </Button>
                                                {sub.status !== "cancelled" && (
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => {
                                                            const name = getAssigneeName(sub);
                                                            if (window.confirm(`¿Estás seguro de que deseas cancelar la suscripción de "${name}"?`)) {
                                                                cancelSubMutation.mutate(sub.id);
                                                            }
                                                        }}
                                                        className="h-7 text-[11px] font-semibold text-rose-500 hover:text-rose-600 hover:bg-rose-50/60 rounded-md"
                                                    >
                                                        Cancelar
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center py-8 text-slate-400 text-sm">
                                        No hay suscripciones registradas para este módulo.
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
