import { APP_VERSION } from "@/lib/config";
import { cn } from "@/lib/utils";

/**
 * Muestra la version desplegada de la aplicacion. Sin version fijada en el build
 * se muestra "dev" sin prefijo.
 */
export function AppVersion({ className }: { className?: string }) {
    const etiqueta = APP_VERSION === "dev" ? APP_VERSION : `v${APP_VERSION}`;

    return (
        <span data-testid="app-version" className={cn("text-xs text-muted-foreground", className)}>
            {etiqueta}
        </span>
    );
}
