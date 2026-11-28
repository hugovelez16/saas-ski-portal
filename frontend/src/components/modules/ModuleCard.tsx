"use client";

import { AppModule, ModuleSubscription } from "@/lib/types";
import { SubscriptionBadge } from "./SubscriptionBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, Edit2 } from "lucide-react";
import { useRouter } from "next/navigation";

interface Props {
    module: AppModule;
    subscriptions: ModuleSubscription[];
    onAddSubscription: (module: AppModule) => void;
    onCancelSubscription: (sub: ModuleSubscription) => void;
    onEditSubscription: (sub: ModuleSubscription) => void;
}

export function ModuleCard({ module, subscriptions, onAddSubscription, onCancelSubscription, onEditSubscription }: Props) {
    const router = useRouter();
    const registeredSubs = subscriptions.filter(s => s.status === "active" || s.status === "trial" || s.status === "expired" || s.status === "cancelled");

    const getAssigneeName = (sub: ModuleSubscription) => {
        return sub.company?.name ?? (sub.companyId ? `Empresa: ${sub.companyId.substring(0, 8)}...` : "Empresa sin ID");
    };

    const handleCardClick = (e: React.MouseEvent<HTMLDivElement>) => {
        const target = e.target as HTMLElement;
        if (target.closest("button") || target.closest("a") || target.closest("input")) {
            return;
        }
        router.push(`/admin/modules/${module.id}`);
    };

    return (
        <Card 
            onClick={handleCardClick}
            className={`relative overflow-hidden transition-all duration-300 hover:shadow-md hover:border-slate-300 cursor-pointer border-slate-200/80 ${!module.isActive ? "opacity-60 bg-slate-50/50" : "bg-white"}`}
        >
            {module.isActive && (
                <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-indigo-500 to-sky-400" />
            )}
            <CardHeader className="flex flex-row items-start justify-between gap-4 pb-3">
                <div className="flex items-start gap-3">
                    <div className={`rounded-lg p-2.5 ${module.isActive ? "bg-indigo-50 text-indigo-600" : "bg-slate-100 text-slate-500"}`}>
                        <Building2 className="h-5 w-5" />
                    </div>
                    <div>
                        <CardTitle className="text-base font-bold text-slate-800">{module.name}</CardTitle>
                        <code className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200/60 mt-1 inline-block">
                            {module.codeName}
                        </code>
                    </div>
                </div>
                <div className="flex gap-1.5">
                    {!module.isActive && <Badge variant="secondary" className="bg-slate-100 text-slate-600 text-[10px] font-semibold border border-slate-200">Inactivo</Badge>}
                </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
                {module.description && (
                    <CardDescription className="text-sm text-slate-500 leading-relaxed font-normal">
                        {module.description}
                    </CardDescription>
                )}

                {/* Lista de Suscripciones */}
                {registeredSubs.length > 0 && (
                    <div className="space-y-2.5 pt-2 border-t border-slate-100">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Suscripciones registradas</p>
                        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                            {registeredSubs.map(sub => (
                                <div key={sub.id} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/50 p-2.5 hover:bg-slate-50 transition-colors">
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
                                    <div className="flex items-center gap-1 shrink-0">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => onEditSubscription(sub)}
                                            className="h-7 w-7 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50/60 rounded-md"
                                            title="Editar suscripción"
                                        >
                                            <Edit2 className="h-3.5 w-3.5" />
                                        </Button>
                                        {sub.status !== "cancelled" && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => onCancelSubscription(sub)}
                                                className="h-7 text-[11px] font-semibold text-rose-500 hover:text-rose-600 hover:bg-rose-50/60 rounded-md"
                                            >
                                                Cancelar
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <Button
                    variant="outline"
                    size="sm"
                    className="w-full font-semibold border-indigo-100 hover:border-indigo-200 text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50/30 transition-all duration-200 mt-2"
                    disabled={!module.isActive}
                    onClick={() => onAddSubscription(module)}
                >
                    + Añadir Suscripción
                </Button>
            </CardContent>
        </Card>
    );
}
