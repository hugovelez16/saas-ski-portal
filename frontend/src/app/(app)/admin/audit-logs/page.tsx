"use client";
export const dynamic = "force-dynamic";

import { Fragment, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ChevronDown, ChevronUp, ScrollText, Trash2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { getCompaniesDetailed } from "@/lib/api/companies";
import {
    AuditLogItem,
    AuditLogParams,
    AuditLogPurgePreview,
    AuditLogPurgeRequest,
    getAuditActions,
    getAuditLogs,
    getAuditPurgePreview,
    purgeAuditLogs,
} from "@/lib/api/audit-logs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const PAGE_SIZE = 50;
// Radix Select no admite value vacio; este valor centinela representa "todas".
const ALL = "__all__";

interface Filters {
    companyId: string;
    actorUserId: string;
    targetUserId: string;
    action: string;
    /** YYYY-MM-DD */
    fromDate: string;
    /** YYYY-MM-DD */
    toDate: string;
}

const EMPTY_FILTERS: Filters = {
    companyId: "",
    actorUserId: "",
    targetUserId: "",
    action: "",
    fromDate: "",
    toDate: "",
};

// El backend espera datetime. Se usan los limites del dia en hora local, convertidos a ISO UTC.
const startOfDayIso = (date: string) => new Date(`${date}T00:00:00`).toISOString();
const endOfDayIso = (date: string) => new Date(`${date}T23:59:59.999`).toISOString();

function buildParams(filters: Filters, offset: number): AuditLogParams {
    return {
        companyId: filters.companyId || undefined,
        actorUserId: filters.actorUserId.trim() || undefined,
        targetUserId: filters.targetUserId.trim() || undefined,
        action: filters.action || undefined,
        from: filters.fromDate ? startOfDayIso(filters.fromDate) : undefined,
        to: filters.toDate ? endOfDayIso(filters.toDate) : undefined,
        limit: PAGE_SIZE,
        offset,
    };
}

function formatDate(iso: string): string {
    return format(new Date(iso), "dd/MM/yyyy HH:mm:ss");
}

function JsonBlock({ label, value }: { label: string; value: Record<string, unknown> | null }) {
    return (
        <div className="space-y-1">
            <p className="text-xs font-medium text-slate-500">{label}</p>
            <pre className="overflow-x-auto rounded border bg-white p-2 text-xs">
                {value === null ? "-" : JSON.stringify(value, null, 2)}
            </pre>
        </div>
    );
}

export default function AuditLogsPage() {
    const router = useRouter();
    const queryClient = useQueryClient();
    const { toast } = useToast();
    const { user, loading } = useAuth();

    const isPlatformAdmin = Boolean(user?.role === "admin" || user?.isPlatformAdmin);

    const [draft, setDraft] = useState<Filters>(EMPTY_FILTERS);
    const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS);
    const [offset, setOffset] = useState(0);
    const [expandedId, setExpandedId] = useState<string | null>(null);

    const [purgeOpen, setPurgeOpen] = useState(false);
    const [purgeDate, setPurgeDate] = useState("");
    const [purgeReason, setPurgeReason] = useState("");
    const [purgePreview, setPurgePreview] = useState<AuditLogPurgePreview | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewError, setPreviewError] = useState<string | null>(null);
    const [purgeError, setPurgeError] = useState<string | null>(null);

    const todayDate = format(new Date(), "yyyy-MM-dd");

    const resetPurgeState = () => {
        setPurgeDate("");
        setPurgeReason("");
        setPurgePreview(null);
        setPreviewLoading(false);
        setPreviewError(null);
        setPurgeError(null);
    };

    const purgeMutation = useMutation({
        mutationFn: (data: AuditLogPurgeRequest) => purgeAuditLogs(data),
        onSuccess: (result) => {
            setOffset(0);
            setExpandedId(null);
            queryClient.invalidateQueries({ queryKey: ["audit-logs"] });
            toast({
                title: "Purga completada",
                description: `Se eliminaron ${result.deletedCount} registros de auditoría.`,
            });
            setPurgeOpen(false);
            resetPurgeState();
        },
        onError: () => {
            setPurgeError("No se pudo completar la purga de registros.");
        },
    });

    const { data: companies = [] } = useQuery({
        queryKey: ["companiesDetailed"],
        queryFn: () => getCompaniesDetailed({ asAdmin: true }),
        enabled: isPlatformAdmin,
    });

    const { data: actions = [] } = useQuery({
        queryKey: ["audit-actions"],
        queryFn: getAuditActions,
        enabled: isPlatformAdmin,
    });

    const { data: logsPage, isLoading, isError } = useQuery({
        queryKey: ["audit-logs", applied, offset],
        queryFn: () => getAuditLogs(buildParams(applied, offset)),
        enabled: isPlatformAdmin,
    });

    const companyNames = useMemo(
        () => new Map(companies.map((c) => [c.id, c.name])),
        [companies]
    );

    useEffect(() => {
        if (!loading && user && !isPlatformAdmin) {
            router.replace("/dashboard");
        }
    }, [loading, user, isPlatformAdmin, router]);

    if (!isPlatformAdmin) return null;

    const rangeInvalid = Boolean(draft.fromDate && draft.toDate && draft.fromDate > draft.toDate);
    const items: AuditLogItem[] = logsPage?.items ?? [];
    const total = logsPage?.total ?? 0;
    const hasPrev = offset > 0;
    const hasNext = offset + PAGE_SIZE < total;

    const applyFilters = () => {
        setApplied(draft);
        setOffset(0);
        setExpandedId(null);
    };

    const clearFilters = () => {
        setDraft(EMPTY_FILTERS);
        setApplied(EMPTY_FILTERS);
        setOffset(0);
        setExpandedId(null);
    };

    const goToPage = (newOffset: number) => {
        setOffset(Math.max(0, newOffset));
        setExpandedId(null);
    };

    const purgeDateFuture = Boolean(purgeDate && purgeDate > todayDate);

    const handleOpenPurge = () => {
        resetPurgeState();
        setPurgeOpen(true);
    };

    const handlePreviewPurge = async () => {
        if (!purgeDate || purgeDateFuture) return;
        setPreviewLoading(true);
        setPreviewError(null);
        setPurgeError(null);
        try {
            const preview = await getAuditPurgePreview(startOfDayIso(purgeDate));
            setPurgePreview(preview);
        } catch {
            setPurgePreview(null);
            setPreviewError("No se pudo consultar el recuento de registros.");
        } finally {
            setPreviewLoading(false);
        }
    };

    const handleConfirmPurge = () => {
        if (!purgeDate || purgeDateFuture || !purgePreview || purgePreview.count === 0) return;
        setPurgeError(null);
        purgeMutation.mutate({
            before: startOfDayIso(purgeDate),
            reason: purgeReason.trim() || undefined,
        });
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="flex items-center gap-2 text-2xl font-bold">
                        <ScrollText className="h-6 w-6" />
                        Auditoría
                    </h1>
                    <p className="text-sm text-muted-foreground">Registro de acciones sensibles de la plataforma.</p>
                </div>
                <Button variant="outline" onClick={handleOpenPurge}>
                    <Trash2 className="mr-2 h-4 w-4" />
                    Purgar registros
                </Button>
            </div>

            <Card>
                <CardContent className="grid grid-cols-1 gap-4 pt-6 md:grid-cols-2 xl:grid-cols-3">
                    <div className="space-y-1">
                        <Label>Empresa</Label>
                        <Select
                            value={draft.companyId || ALL}
                            onValueChange={(v) => setDraft({ ...draft, companyId: v === ALL ? "" : v })}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Todas" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={ALL}>Todas</SelectItem>
                                {companies.map((c) => (
                                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-1">
                        <Label>Acción</Label>
                        <Select
                            value={draft.action || ALL}
                            onValueChange={(v) => setDraft({ ...draft, action: v === ALL ? "" : v })}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Todas" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={ALL}>Todas</SelectItem>
                                {actions.map((a) => (
                                    <SelectItem key={a} value={a}>{a}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-1">
                        <Label htmlFor="audit-actor">Actor (UUID)</Label>
                        <Input
                            id="audit-actor"
                            value={draft.actorUserId}
                            onChange={(e) => setDraft({ ...draft, actorUserId: e.target.value })}
                            placeholder="UUID del usuario que ejecuta"
                        />
                    </div>

                    <div className="space-y-1">
                        <Label htmlFor="audit-target">Usuario objetivo (UUID)</Label>
                        <Input
                            id="audit-target"
                            value={draft.targetUserId}
                            onChange={(e) => setDraft({ ...draft, targetUserId: e.target.value })}
                            placeholder="UUID del usuario afectado"
                        />
                    </div>

                    <div className="space-y-1">
                        <Label htmlFor="audit-from">Desde</Label>
                        <Input
                            id="audit-from"
                            type="date"
                            value={draft.fromDate}
                            onChange={(e) => setDraft({ ...draft, fromDate: e.target.value })}
                        />
                    </div>

                    <div className="space-y-1">
                        <Label htmlFor="audit-to">Hasta</Label>
                        <Input
                            id="audit-to"
                            type="date"
                            value={draft.toDate}
                            onChange={(e) => setDraft({ ...draft, toDate: e.target.value })}
                        />
                    </div>

                    <div className="flex items-center gap-2 md:col-span-2 xl:col-span-3">
                        <Button onClick={applyFilters} disabled={rangeInvalid}>
                            Aplicar filtros
                        </Button>
                        <Button variant="outline" onClick={clearFilters}>
                            Limpiar
                        </Button>
                        {rangeInvalid && (
                            <span className="text-sm text-red-600">La fecha inicial no puede ser posterior a la final.</span>
                        )}
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardContent className="pt-6">
                    {isLoading && <p className="text-sm text-muted-foreground">Cargando registros...</p>}
                    {isError && <p className="text-sm text-red-600">No se pudieron cargar los registros de auditoría.</p>}

                    {!isLoading && !isError && (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm">
                                <thead className="border-b text-slate-500">
                                    <tr>
                                        <th className="px-3 py-2 font-medium">Fecha</th>
                                        <th className="px-3 py-2 font-medium">Acción</th>
                                        <th className="px-3 py-2 font-medium">Actor</th>
                                        <th className="px-3 py-2 font-medium">Empresa</th>
                                        <th className="px-3 py-2 font-medium">Usuario objetivo</th>
                                        <th className="px-3 py-2 font-medium">Motivo</th>
                                        <th className="px-3 py-2 font-medium">Detalle</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.length === 0 && (
                                        <tr>
                                            <td colSpan={7} className="px-3 py-6 text-center text-muted-foreground">
                                                No hay registros para los filtros seleccionados.
                                            </td>
                                        </tr>
                                    )}
                                    {items.map((log) => {
                                        const expanded = expandedId === log.id;
                                        return (
                                            <Fragment key={log.id}>
                                                <tr className="border-b">
                                                    <td className="whitespace-nowrap px-3 py-2">{formatDate(log.createdAt)}</td>
                                                    <td className="px-3 py-2">
                                                        <Badge variant="outline">{log.action}</Badge>
                                                    </td>
                                                    <td className="px-3 py-2">{log.actorEmail ?? log.actorUserId ?? "-"}</td>
                                                    <td className="px-3 py-2">
                                                        {log.companyId ? (companyNames.get(log.companyId) ?? log.companyId) : "-"}
                                                    </td>
                                                    <td className="px-3 py-2 font-mono text-xs">{log.targetUserId ?? "-"}</td>
                                                    <td className="px-3 py-2">{log.reason ?? "-"}</td>
                                                    <td className="px-3 py-2">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            aria-expanded={expanded}
                                                            onClick={() => setExpandedId(expanded ? null : log.id)}
                                                        >
                                                            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                                            {expanded ? "Ocultar" : "Ver"}
                                                        </Button>
                                                    </td>
                                                </tr>
                                                {expanded && (
                                                    <tr className="border-b bg-slate-50">
                                                        <td colSpan={7} className="px-3 py-3">
                                                            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                                                                <JsonBlock label="Valor anterior" value={log.oldValue} />
                                                                <JsonBlock label="Valor nuevo" value={log.newValue} />
                                                                <JsonBlock label="Datos extra" value={log.extraData} />
                                                            </div>
                                                        </td>
                                                    </tr>
                                                )}
                                            </Fragment>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {!isLoading && !isError && (
                        <div className="mt-4 flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">
                                {total === 0
                                    ? "0 registros"
                                    : `Mostrando ${offset + 1}-${Math.min(offset + items.length, total)} de ${total}`}
                            </span>
                            <div className="flex items-center gap-2">
                                <Button variant="outline" size="sm" disabled={!hasPrev} onClick={() => goToPage(offset - PAGE_SIZE)}>
                                    Anterior
                                </Button>
                                <Button variant="outline" size="sm" disabled={!hasNext} onClick={() => goToPage(offset + PAGE_SIZE)}>
                                    Siguiente
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            <Dialog
                open={purgeOpen}
                onOpenChange={(open) => {
                    setPurgeOpen(open);
                    if (!open) resetPurgeState();
                }}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Purgar registros de auditoría</DialogTitle>
                        <DialogDescription>
                            Elige una fecha límite para consultar cuántos registros anteriores existen y confirmar su eliminación. La propia purga quedará auditada y no se borrará.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-2">
                        <div className="space-y-1">
                            <Label htmlFor="audit-purge-before">Eliminar registros anteriores a</Label>
                            <div className="flex items-center gap-2">
                                <Input
                                    id="audit-purge-before"
                                    type="date"
                                    max={todayDate}
                                    value={purgeDate}
                                    onChange={(e) => {
                                        setPurgeDate(e.target.value);
                                        setPurgePreview(null);
                                        setPreviewError(null);
                                        setPurgeError(null);
                                    }}
                                />
                                <Button
                                    type="button"
                                    variant="secondary"
                                    onClick={handlePreviewPurge}
                                    disabled={!purgeDate || purgeDateFuture || previewLoading}
                                >
                                    {previewLoading ? "Consultando..." : "Consultar recuento"}
                                </Button>
                            </div>
                            {purgeDateFuture && (
                                <p className="text-sm text-red-600">La fecha límite no puede ser futura.</p>
                            )}
                            {previewError && (
                                <p className="text-sm text-red-600">{previewError}</p>
                            )}
                        </div>

                        {purgePreview !== null && (
                            <div className="space-y-3 rounded-md border bg-slate-50 p-3 text-sm">
                                <p>
                                    {purgePreview.count === 0
                                        ? `No hay registros anteriores al ${format(new Date(`${purgeDate}T00:00:00`), "dd/MM/yyyy")} para purgar.`
                                        : `Se eliminarán ${purgePreview.count} registros anteriores al ${format(new Date(`${purgeDate}T00:00:00`), "dd/MM/yyyy")}. Los apuntes de purga previos se conservan.`}
                                </p>
                                {purgePreview.count > 0 && (
                                    <div className="space-y-1">
                                        <Label htmlFor="audit-purge-reason">Motivo (opcional)</Label>
                                        <Input
                                            id="audit-purge-reason"
                                            maxLength={500}
                                            value={purgeReason}
                                            onChange={(e) => setPurgeReason(e.target.value)}
                                            placeholder="Motivo de la purga manual"
                                        />
                                    </div>
                                )}
                            </div>
                        )}

                        {purgeError && <p className="text-sm text-red-600">{purgeError}</p>}
                    </div>

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                                setPurgeOpen(false);
                                resetPurgeState();
                            }}
                        >
                            Cancelar
                        </Button>
                        <Button
                            type="button"
                            variant="destructive"
                            onClick={handleConfirmPurge}
                            disabled={purgePreview === null || purgePreview.count === 0 || purgeMutation.isPending}
                        >
                            {purgeMutation.isPending ? "Purgando..." : "Confirmar purga"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
