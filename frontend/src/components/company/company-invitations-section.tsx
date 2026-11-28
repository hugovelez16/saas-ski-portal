"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Mail, RefreshCw, XCircle, Send } from "lucide-react";
import {
    cancelInvitation,
    createInvitation,
    listInvitations,
    resendInvitation,
} from "@/lib/api/v2/invitations";
import { InvitationOut } from "@/lib/api/v2/types";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface CompanyInvitationsSectionProps {
    companyId: string;
    asAdmin?: boolean;
    canInvite?: boolean;
}

function formatExpiration(iso: string): string {
    const parsed = new Date(iso);
    if (Number.isNaN(parsed.getTime())) return "-";
    return format(parsed, "dd/MM/yyyy HH:mm");
}

function StatusBadge({ status }: { status: InvitationOut["status"] }) {
    if (status === "expired") {
        return (
            <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                Caducada
            </Badge>
        );
    }
    return (
        <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200">
            Pendiente
        </Badge>
    );
}

export function CompanyInvitationsSection({
    companyId,
    asAdmin = false,
    canInvite = true,
}: CompanyInvitationsSectionProps) {
    const [email, setEmail] = useState("");
    const [validationError, setValidationError] = useState<string | null>(null);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const queryKey = ["companyInvitations", companyId, asAdmin ? "admin" : "manager"];

    const { data: invitations = [], isLoading } = useQuery({
        queryKey,
        queryFn: () => listInvitations(companyId, { asAdmin }),
        enabled: Boolean(companyId),
    });

    const inviteMutation = useMutation({
        mutationFn: (targetEmail: string) => createInvitation(companyId, targetEmail, { asAdmin }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            setEmail("");
            setValidationError(null);
            toast({
                title: "Invitacion enviada",
                description: "Se ha enviado un enlace de un solo uso valido durante 7 dias.",
            });
        },
    });

    const resendMutation = useMutation({
        mutationFn: (invitationId: string) => resendInvitation(companyId, invitationId, { asAdmin }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast({
                title: "Invitacion reenviada",
                description: "Se ha generado un nuevo enlace valido durante 7 dias.",
            });
        },
    });

    const cancelMutation = useMutation({
        mutationFn: (invitationId: string) => cancelInvitation(companyId, invitationId, { asAdmin }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast({ title: "Invitacion cancelada" });
        },
    });

    const handleInvite = (e: React.FormEvent) => {
        e.preventDefault();
        const trimmed = email.trim();
        if (!trimmed || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
            setValidationError("Introduce un correo electronico valido.");
            return;
        }
        setValidationError(null);
        inviteMutation.mutate(trimmed);
    };

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center gap-2">
                    <Mail className="h-5 w-5 text-indigo-600" />
                    <div>
                        <CardTitle>Invitaciones por correo</CardTitle>
                        <CardDescription>
                            Invita a trabajadores por correo electronico con un enlace de un solo uso valido durante 7 dias.
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                {canInvite && (
                    <form onSubmit={handleInvite} className="space-y-2">
                        <div className="flex flex-col sm:flex-row gap-2">
                            <Input
                                type="email"
                                placeholder="monitor@escuela.es"
                                value={email}
                                onChange={(e) => {
                                    setEmail(e.target.value);
                                    if (validationError) setValidationError(null);
                                }}
                                aria-label="Correo del trabajador a invitar"
                                disabled={inviteMutation.isPending}
                            />
                            <Button type="submit" disabled={inviteMutation.isPending} className="gap-2 shrink-0">
                                <Send className="h-4 w-4" />
                                {inviteMutation.isPending ? "Enviando..." : "Enviar invitacion"}
                            </Button>
                        </div>
                        {validationError && (
                            <p className="text-xs text-red-600 font-medium">{validationError}</p>
                        )}
                    </form>
                )}

                <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                        Invitaciones pendientes ({invitations.length})
                    </h3>
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground">Cargando invitaciones...</p>
                    ) : invitations.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No hay invitaciones pendientes en esta empresa.</p>
                    ) : (
                        <div className="divide-y rounded-md border">
                            {invitations.map((inv) => {
                                const busy = resendMutation.isPending || cancelMutation.isPending;
                                return (
                                    <div
                                        key={inv.id}
                                        className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3"
                                    >
                                        <div className="space-y-1">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="font-medium text-sm">{inv.email}</span>
                                                <StatusBadge status={inv.status} />
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                                Caduca: {formatExpiration(inv.expires_at)}
                                                {inv.invited_by_name ? ` · Invitada por ${inv.invited_by_name}` : ""}
                                            </p>
                                        </div>
                                        {canInvite && (
                                            <div className="flex items-center gap-2">
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    size="sm"
                                                    className="gap-1.5"
                                                    disabled={busy}
                                                    onClick={() => resendMutation.mutate(inv.id)}
                                                >
                                                    <RefreshCw className="h-3.5 w-3.5" />
                                                    Reenviar
                                                </Button>
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    className="gap-1.5 text-red-600 hover:text-red-700 hover:bg-red-50"
                                                    disabled={busy}
                                                    onClick={() => cancelMutation.mutate(inv.id)}
                                                >
                                                    <XCircle className="h-3.5 w-3.5" />
                                                    Cancelar
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
