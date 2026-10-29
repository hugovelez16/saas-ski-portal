"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { homePathFor, useAuth } from "@/context/AuthContext";

/**
 * La landing es para visitantes. Si ya hay sesion (por ejemplo, un marcador al dominio),
 * lleva directamente a la pantalla de inicio del rol y tapa la landing mientras tanto.
 */
export function SessionRedirect() {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && user) router.replace(homePathFor(user));
    }, [loading, user, router]);

    if (loading || !user) return null;
    return <div className="fixed inset-0 z-[100] bg-white" aria-hidden="true" />;
}
