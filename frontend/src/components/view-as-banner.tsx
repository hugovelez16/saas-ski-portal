"use client";

import { Eye } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

/**
 * Aviso del modo "ver como" del PA: solo lectura con los permisos del rol visto.
 * "Salir del modo" vuelve a la vista completa de la empresa activa.
 */
export function ViewAsBanner() {
    const { user, switchScope } = useAuth();

    if (!user?.isReadOnlyView) return null;

    return (
        <div
            role="status"
            className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-300 bg-amber-100 px-4 py-2 text-sm text-amber-900"
        >
            <span className="flex items-center gap-2 font-medium">
                <Eye className="h-4 w-4 shrink-0" />
                Viendo como {user.viewAs ?? "usuario"} (solo lectura)
            </span>
            <Button
                size="sm"
                variant="outline"
                className="border-amber-400 bg-white text-amber-900 hover:bg-amber-50"
                onClick={() => switchScope(user.activeCompanyId ?? null)}
            >
                Salir del modo
            </Button>
        </div>
    );
}
