import Link from "next/link";
import { LEGAL_LINKS } from "@/lib/legal-config";
import { cn } from "@/lib/utils";

/**
 * Enlaces a las paginas legales. Renderiza un <nav> (no un <footer>) para
 * poder colocarlo dentro de pies ya existentes sin anidar footers.
 */
export function LegalFooter({ className }: { className?: string }) {
    return (
        <nav aria-label="Información legal" className={cn("text-xs text-muted-foreground", className)}>
            <ul className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
                {LEGAL_LINKS.map((link) => (
                    <li key={link.href}>
                        <Link href={link.href} className="hover:underline underline-offset-4">
                            {link.label}
                        </Link>
                    </li>
                ))}
            </ul>
        </nav>
    );
}
