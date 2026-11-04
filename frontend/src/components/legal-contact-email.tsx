import { CONTACT_EMAIL } from "@/lib/config";
import { LEGAL_OWNER } from "@/lib/legal-config";

/** Correo de contacto de las paginas legales: enlace mailto si esta configurado, marcador pendiente si no. */
export function LegalContactEmail() {
    if (!CONTACT_EMAIL) return <>{LEGAL_OWNER.email}</>;
    return <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>;
}
