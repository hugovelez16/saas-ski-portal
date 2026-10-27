import type { WorkLog } from "@/lib/types";

type WorkLogWarningsSource = { warnings?: WorkLog['warnings'] } | null | undefined;

/**
 * Shows a single "Aviso" toast with the distinct warning messages of a saved work log.
 * The backend only warns and never rejects, so this is informational only.
 * Errors while notifying are logged and never propagated to the caller.
 */
export function notifyWorkLogWarnings(
    toast: (o: { title: string; description?: string }) => void,
    log: WorkLogWarningsSource
): void {
    try {
        const avisos = log?.warnings;
        if (!avisos || avisos.length === 0) return;

        const mensajes = Array.from(new Set(avisos.map((w) => w.message)));
        toast({ title: "Aviso", description: mensajes.join(" ") });
    } catch (error) {
        console.warn("No se pudieron mostrar los avisos del turno.", error);
    }
}
