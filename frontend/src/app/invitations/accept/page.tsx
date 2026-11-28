"use client";

import { Suspense, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, AlertCircle, Loader2, Building2, LogIn, LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { acceptInvitation, previewInvitation } from "@/lib/api/v2/invitations";
import { formatErrorDetail } from "@/lib/api";
import { InvitationPreviewOut } from "@/lib/api/v2/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { LegalFooter } from "@/components/legal-footer";

function AcceptInvitationContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const token = searchParams.get("token")?.trim() || "";
    const { user, loading: authLoading, switchScope, logout } = useAuth();

    const [preview, setPreview] = useState<InvitationPreviewOut | null>(null);
    const [previewError, setPreviewError] = useState<string | null>(null);
    const [loadingPreview, setLoadingPreview] = useState<boolean>(true);
    const [accepting, setAccepting] = useState<boolean>(false);
    const [acceptError, setAcceptError] = useState<string | null>(null);
    const [acceptedCompany, setAcceptedCompany] = useState<string | null>(null);
    const [acceptedCompanyId, setAcceptedCompanyId] = useState<string | null>(null);

    useEffect(() => {
        let active = true;
        if (!token) {
            setLoadingPreview(false);
            setPreviewError("Enlace de invitacion incompleto o no valido.");
            return;
        }
        setLoadingPreview(true);
        setPreviewError(null);
        previewInvitation(token)
            .then((data) => {
                if (active) setPreview(data);
            })
            .catch((err: unknown) => {
                if (!active) return;
                const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
                setPreviewError(formatErrorDetail(detail) || "La invitacion no es valida o ha caducado.");
            })
            .finally(() => {
                if (active) setLoadingPreview(false);
            });
        return () => {
            active = false;
        };
    }, [token]);

    const handleAccept = async () => {
        if (!token) return;
        setAccepting(true);
        setAcceptError(null);
        try {
            const res = await acceptInvitation(token);
            setAcceptedCompany(res.company_name);
            setAcceptedCompanyId(res.company_id);
        } catch (err: unknown) {
            const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
            setAcceptError(formatErrorDetail(detail) || "No se pudo aceptar la invitacion.");
        } finally {
            setAccepting(false);
        }
    };

    const loginRedirectHref = `/login?next=${encodeURIComponent(`/invitations/accept?token=${token}`)}`;

    if (loadingPreview || authLoading) {
        return (
            <div className="flex flex-col items-center justify-center py-8 gap-3 text-sm text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                <span>Comprobando invitacion...</span>
            </div>
        );
    }

    if (previewError || !preview) {
        return (
            <div className="text-center py-4 space-y-4">
                <div className="flex justify-center">
                    <div className="p-3 bg-red-100 rounded-full text-red-600">
                        <AlertCircle className="h-8 w-8" />
                    </div>
                </div>
                <p className="text-sm text-red-600 font-medium">{previewError || "Invitacion no disponible."}</p>
                <Button asChild variant="outline" className="w-full">
                    <Link href="/login">Ir a iniciar sesion</Link>
                </Button>
            </div>
        );
    }

    if (acceptedCompany && acceptedCompanyId) {
        return (
            <div className="text-center py-4 space-y-4">
                <div className="flex justify-center">
                    <div className="p-3 bg-emerald-100 rounded-full text-emerald-600">
                        <CheckCircle2 className="h-10 w-10" />
                    </div>
                </div>
                <h3 className="text-lg font-semibold text-slate-900">Invitacion aceptada</h3>
                <p className="text-sm text-muted-foreground">
                    Ya formas parte de <strong>{acceptedCompany}</strong>.
                </p>
                <Button
                    type="button"
                    className="w-full"
                    onClick={() => switchScope(acceptedCompanyId)}
                >
                    Entrar en {acceptedCompany}
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-5">
            <div className="rounded-lg border bg-slate-50 p-4 text-center space-y-1">
                <div className="flex justify-center mb-2">
                    <Building2 className="h-6 w-6 text-indigo-600" />
                </div>
                <p className="text-sm text-muted-foreground">Has recibido una invitacion para unirte a</p>
                <p className="text-lg font-bold text-slate-900">{preview.company_name}</p>
            </div>

            {!user ? (
                <div className="space-y-4">
                    <p className="text-sm text-slate-600 text-center">
                        Inicia sesion con el correo al que se envio la invitacion para poder aceptarla.
                    </p>
                    <p className="text-xs text-muted-foreground text-center">
                        Si aun no tienes cuenta en Vesotel, el registro publico estara disponible proximamente; mientras tanto solicita el alta a tu responsable o administrador.
                    </p>
                    <Button
                        type="button"
                        className="w-full gap-2"
                        onClick={() => router.push(loginRedirectHref)}
                    >
                        <LogIn className="h-4 w-4" />
                        Iniciar sesion para aceptar
                    </Button>
                </div>
            ) : (
                <div className="space-y-4">
                    <p className="text-sm text-center text-slate-600">
                        Sesion iniciada como <strong>{user.email}</strong>.
                    </p>
                    {acceptError && (
                        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 text-center space-y-2">
                            <p className="font-medium">{acceptError}</p>
                            {acceptError === "Esta invitacion es para otro correo" && (
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="gap-1.5"
                                    onClick={() => logout()}
                                >
                                    <LogOut className="h-3.5 w-3.5" />
                                    Cerrar sesion y cambiar de cuenta
                                </Button>
                            )}
                        </div>
                    )}
                    <Button
                        type="button"
                        className="w-full"
                        disabled={accepting}
                        onClick={handleAccept}
                    >
                        {accepting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {accepting ? "Aceptando..." : "Aceptar invitacion"}
                    </Button>
                </div>
            )}
        </div>
    );
}

export default function AcceptInvitationPage() {
    return (
        <div
            className="flex min-h-screen items-center justify-center px-4 bg-cover bg-center bg-no-repeat"
            style={{ backgroundImage: "url('/login-bg.png')" }}
        >
            <Card className="w-full max-w-md bg-white/95 backdrop-blur-sm shadow-xl border-slate-200">
                <CardHeader className="text-center">
                    <div className="flex justify-center mb-4">
                        <Image
                            src="/logo.webp"
                            alt="Vesotel Logo"
                            width={80}
                            height={80}
                            priority
                            className="object-contain"
                            style={{ width: "auto", height: "auto" }}
                        />
                    </div>
                    <CardTitle className="text-2xl font-bold">Invitacion a empresa</CardTitle>
                    <CardDescription>
                        Revisa los datos de la invitacion antes de confirmar tu incorporacion.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Suspense
                        fallback={
                            <div className="flex justify-center py-6">
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                            </div>
                        }
                    >
                        <AcceptInvitationContent />
                    </Suspense>
                </CardContent>
                <CardFooter className="flex flex-col items-center gap-2 text-xs text-muted-foreground">
                    <span>Vesotel Work Management 2026</span>
                    <LegalFooter />
                </CardFooter>
            </Card>
        </div>
    );
}
