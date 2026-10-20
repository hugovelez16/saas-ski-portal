"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getModules, getSubscriptions, createModule, createSubscription, updateSubscription } from "@/lib/api/modules";
import { getCompanies } from "@/lib/api/companies";
import { getUsers } from "@/lib/api/users";
import { AxiosError } from "axios";
import { AppModule, ModuleSubscription } from "@/lib/types";
import { ModuleCard } from "@/components/modules/ModuleCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { PlusCircle, Package } from "lucide-react";

export default function AdminModulesPage() {
    const queryClient = useQueryClient();

    const parseDate = (dStr: string) => {
        if (!dStr) return null;
        const d = new Date(dStr);
        return isNaN(d.getTime()) ? null : d.toISOString();
    };
    const [showCreateModule, setShowCreateModule] = useState(false);
    const [showAddSubscription, setShowAddSubscription] = useState<AppModule | null>(null);
    const [showEditSubscription, setShowEditSubscription] = useState<ModuleSubscription | null>(null);

    // ─── Queries ────────────────────────────────────────────────────────────
    const { data: modules = [] } = useQuery({
        queryKey: ["modules", "all"],
        queryFn: () => getModules(true), // include_inactive = true for admin
    });

    const { data: subscriptions = [] } = useQuery({
        queryKey: ["subscriptions"],
        queryFn: () => getSubscriptions(),
    });

    const { data: companies = [] } = useQuery({
        queryKey: ["companies"],
        queryFn: getCompanies,
    });

    const { data: users = [] } = useQuery({
        queryKey: ["users"],
        queryFn: getUsers,
    });

    // ─── Mutations ──────────────────────────────────────────────────────────
    const createModuleMutation = useMutation({
        mutationFn: createModule,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["modules"] });
            setShowCreateModule(false);
            setNewModule({ codeName: "", name: "", description: "", targetScope: "both" });
            toast.success("Módulo creado correctamente.");
        },
        onError: (e: AxiosError<{ detail?: string }>) => toast.error(e?.response?.data?.detail ?? "Error al crear el módulo."),
    });

    const cancelSubMutation = useMutation({
        mutationFn: (sub: ModuleSubscription) => updateSubscription(sub.id, { status: "cancelled" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
            toast.success("Suscripción cancelada.");
        },
        onError: () => toast.error("Error al cancelar la suscripción."),
    });

    const addSubMutation = useMutation({
        mutationFn: createSubscription,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
            setShowAddSubscription(null);
            setNewSub({ scope: "company", targetId: "", status: "active", expiresAt: "", notes: "" });
            toast.success("Suscripción creada correctamente.");
        },
        onError: (e: AxiosError<{ detail?: string }>) => toast.error(e?.response?.data?.detail ?? "Error al crear la suscripción."),
    });

    const editSubMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: { status: string; expiresAt: string | null; notes: string } }) =>
            updateSubscription(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
            setShowEditSubscription(null);
            setEditSubForm({ status: "active", expiresAt: "", notes: "" });
            toast.success("Suscripción actualizada correctamente.");
        },
        onError: () => toast.error("Error al actualizar la suscripción."),
    });

    // ─── Form States ────────────────────────────────────────────
    const [newModule, setNewModule] = useState({ codeName: "", name: "", description: "", targetScope: "both" });
    const [newSub, setNewSub] = useState({ scope: "company", targetId: "", status: "active", expiresAt: "", notes: "" });
    const [editSubForm, setEditSubForm] = useState({ status: "active", expiresAt: "", notes: "" });

    const handleOpenEdit = (sub: ModuleSubscription) => {
        setShowEditSubscription(sub);
        setEditSubForm({
            status: sub.status,
            expiresAt: sub.expiresAt ? sub.expiresAt.substring(0, 10) : "",
            notes: sub.notes || "",
        });
    };

    const subsForModule = (moduleId: string) =>
        subscriptions.filter(s => s.moduleId === moduleId);

    return (
        <div className="space-y-6 w-full py-2">
            {/* Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
                <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-indigo-50 p-2.5 text-indigo-600">
                        <Package className="h-6 w-6" />
                    </div>
                    <div>
                        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-800">Gestión de Módulos</h1>
                        <p className="text-sm text-slate-500 font-medium">Catálogo de funcionalidades de la plataforma y control de suscripciones</p>
                    </div>
                </div>
                <Button onClick={() => setShowCreateModule(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">
                    <PlusCircle className="mr-2 h-4 w-4" />
                    Nuevo Módulo
                </Button>
            </div>

            {/* Module Grid */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {modules.map(module => (
                    <ModuleCard
                        key={module.id}
                        module={module}
                        subscriptions={subsForModule(module.id)}
                        onAddSubscription={(m) => {
                            const defaultScope = m.targetScope === "both" ? "company" : m.targetScope;
                            setNewSub({ scope: defaultScope, targetId: "", status: "active", expiresAt: "", notes: "" });
                            setShowAddSubscription(m);
                        }}
                        onCancelSubscription={(sub) => {
                            if (window.confirm(`¿Estás seguro de que deseas cancelar la suscripción del módulo para ${sub.scope === "company" ? (sub.company?.name ?? "esta empresa") : (sub.user?.email ?? "este usuario")}?`)) {
                                cancelSubMutation.mutate(sub);
                            }
                        }}
                        onEditSubscription={handleOpenEdit}
                    />
                ))}
            </div>

            {/* Create Module Dialog */}
            <Dialog open={showCreateModule} onOpenChange={(open) => {
                setShowCreateModule(open);
                if (!open) {
                    setNewModule({ codeName: "", name: "", description: "", targetScope: "both" });
                }
            }}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="text-lg font-bold text-slate-800">Nuevo Módulo</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Código interno</Label>
                            <Input
                                placeholder="export_pdf"
                                value={newModule.codeName}
                                onChange={e => setNewModule(p => ({ ...p, codeName: e.target.value }))}
                                className="bg-slate-50/50 focus-visible:ring-indigo-500"
                            />
                            <p className="text-[10px] text-slate-400 font-medium">Snake_case, sin espacios. Identificador único permanente.</p>
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Nombre visible</Label>
                            <Input
                                placeholder="Exportación a PDF"
                                value={newModule.name}
                                onChange={e => setNewModule(p => ({ ...p, name: e.target.value }))}
                                className="bg-slate-50/50 focus-visible:ring-indigo-500"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Descripción</Label>
                            <Textarea
                                value={newModule.description}
                                onChange={e => setNewModule(p => ({ ...p, description: e.target.value }))}
                                placeholder="Describe brevemente el propósito de este módulo..."
                                className="min-h-[80px] bg-slate-50/50 focus-visible:ring-indigo-500"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Alcance</Label>
                            <Select value={newModule.targetScope} onValueChange={v => setNewModule(p => ({ ...p, targetScope: v }))}>
                                <SelectTrigger className="bg-slate-50/50 focus:ring-indigo-500">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="both">Empresa y Usuario</SelectItem>
                                    <SelectItem value="company">Solo Empresa</SelectItem>
                                    <SelectItem value="user">Solo Usuario</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="outline" onClick={() => setShowCreateModule(false)}>Cancelar</Button>
                        <Button
                            onClick={() => createModuleMutation.mutate(newModule)}
                            disabled={!newModule.codeName || !newModule.name || createModuleMutation.isPending}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
                        >
                            Crear Módulo
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Add Subscription Dialog */}
            <Dialog open={!!showAddSubscription} onOpenChange={(open) => {
                if (!open) {
                    setShowAddSubscription(null);
                    setNewSub({ scope: "company", targetId: "", status: "active", expiresAt: "", notes: "" });
                }
            }}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="text-lg font-bold text-slate-800">Añadir Suscripción</DialogTitle>
                        <p className="text-xs text-indigo-600 font-semibold">{showAddSubscription?.name}</p>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        {showAddSubscription?.targetScope === "both" && (
                            <div className="space-y-1">
                                <Label className="text-xs font-bold text-slate-600">Tipo de suscripción</Label>
                                <Select value={newSub.scope} onValueChange={v => setNewSub(p => ({ ...p, scope: v, targetId: "" }))}>
                                    <SelectTrigger className="bg-slate-50/50"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="company">Empresa</SelectItem>
                                        <SelectItem value="user">Usuario</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">
                                {newSub.scope === "company" ? "Seleccionar Empresa" : "Seleccionar Usuario"}
                            </Label>
                            {newSub.scope === "company" ? (
                                <Select value={newSub.targetId} onValueChange={v => setNewSub(p => ({ ...p, targetId: v }))}>
                                    <SelectTrigger className="bg-slate-50/50 focus:ring-indigo-500">
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
                                <Select value={newSub.targetId} onValueChange={v => setNewSub(p => ({ ...p, targetId: v }))}>
                                    <SelectTrigger className="bg-slate-50/50 focus:ring-indigo-500">
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
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Estado inicial</Label>
                            <Select value={newSub.status} onValueChange={v => setNewSub(p => ({ ...p, status: v }))}>
                                <SelectTrigger className="bg-slate-50/50"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="active">Activo</SelectItem>
                                    <SelectItem value="trial">Trial</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Fecha de expiración (opcional)</Label>
                            <Input
                                type="date"
                                value={newSub.expiresAt}
                                onChange={e => setNewSub(p => ({ ...p, expiresAt: e.target.value }))}
                                className="bg-slate-50/50 focus-visible:ring-indigo-500"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Notas (opcional)</Label>
                            <Input
                                placeholder="Regalo, Pago Stripe #123..."
                                value={newSub.notes}
                                onChange={e => setNewSub(p => ({ ...p, notes: e.target.value }))}
                                className="bg-slate-50/50 focus-visible:ring-indigo-500"
                            />
                        </div>
                    </div>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="outline" onClick={() => setShowAddSubscription(null)}>Cancelar</Button>
                        <Button
                            onClick={() => {
                                if (!showAddSubscription || !newSub.targetId) return;
                                addSubMutation.mutate({
                                    moduleId: showAddSubscription.id,
                                    scope: newSub.scope,
                                    companyId: newSub.scope === "company" ? newSub.targetId : undefined,
                                    userId: newSub.scope === "user" ? newSub.targetId : undefined,
                                    status: newSub.status,
                                    expiresAt: parseDate(newSub.expiresAt) || undefined,
                                    notes: newSub.notes || undefined,
                                });
                            }}
                            disabled={!newSub.targetId || addSubMutation.isPending}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
                        >
                            Crear Suscripción
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Edit Subscription Dialog */}
            <Dialog open={!!showEditSubscription} onOpenChange={(open) => {
                if (!open) {
                    setShowEditSubscription(null);
                    setEditSubForm({ status: "active", expiresAt: "", notes: "" });
                }
            }}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="text-lg font-bold text-slate-800">Editar Suscripción</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div>
                            <Label className="text-xs font-bold text-slate-500">Asignada a</Label>
                            <div className="text-xs font-bold border border-slate-200/80 rounded-lg px-3.5 py-2.5 bg-slate-50 text-slate-700 mt-1">
                                {showEditSubscription?.scope === "company"
                                    ? `Empresa: ${showEditSubscription?.company?.name ?? showEditSubscription?.companyId}`
                                    : `Usuario: ${showEditSubscription?.user?.email ?? showEditSubscription?.userId}`}
                            </div>
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Estado</Label>
                            <Select value={editSubForm.status} onValueChange={v => setEditSubForm(p => ({ ...p, status: v }))}>
                                <SelectTrigger className="bg-slate-50/50"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="active">Activo</SelectItem>
                                    <SelectItem value="trial">Trial</SelectItem>
                                    <SelectItem value="expired">Expirado</SelectItem>
                                    <SelectItem value="cancelled">Cancelado</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Fecha de expiración (opcional)</Label>
                            <Input
                                type="date"
                                value={editSubForm.expiresAt}
                                onChange={e => setEditSubForm(p => ({ ...p, expiresAt: e.target.value }))}
                                className="bg-slate-50/50 focus-visible:ring-indigo-500"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs font-bold text-slate-600">Notas (opcional)</Label>
                            <Input
                                placeholder="Regalo, Pago Stripe #123..."
                                value={editSubForm.notes}
                                onChange={e => setEditSubForm(p => ({ ...p, notes: e.target.value }))}
                                className="bg-slate-50/50 focus-visible:ring-indigo-500"
                            />
                        </div>
                    </div>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="outline" onClick={() => setShowEditSubscription(null)}>Cancelar</Button>
                        <Button
                            onClick={() => {
                                if (!showEditSubscription) return;
                                editSubMutation.mutate({
                                    id: showEditSubscription.id,
                                    data: {
                                        status: editSubForm.status,
                                        expiresAt: parseDate(editSubForm.expiresAt),
                                        notes: editSubForm.notes,
                                    }
                                });
                            }}
                            disabled={editSubMutation.isPending}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
                        >
                            Guardar Cambios
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
