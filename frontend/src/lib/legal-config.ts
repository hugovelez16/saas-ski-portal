import { CONTACT_EMAIL } from "@/lib/config";

/**
 * Datos del titular mostrados en las paginas legales (/aviso-legal,
 * /privacidad, /cookies, /terminos). Unico sitio donde se definen.
 *
 * Fuente: aviso legal y politica de privacidad de https://vesotel.com.
 * Solo se incluye el minimo exigido por el art. 10 LSSI; el resto se remite
 * a la web oficial del titular (LEGAL_OWNER.website).
 *
 * El correo de contacto sale de NEXT_PUBLIC_CONTACT_EMAIL (lib/config.ts);
 * si no esta definido se usa el correo publico del titular.
 */

export const LEGAL_OWNER = {
    legalName: "Vesotel Soporte y Telecomunicaciones, S.L.",
    taxId: "B21887302",
    address: "Calle López de Hoyos 38, 28006 Madrid",
    registryData: "Registro Mercantil de Madrid, hoja 868814",
    email: CONTACT_EMAIL ?? "hola@vesotel.com",
    /** Pagina legal de la web oficial del titular, para ampliar informacion. */
    website: "https://vesotel.com/aviso-legal",
} as const;

/** Nombre comercial del servicio, el mismo que usa la landing publica. */
export const SERVICE_NAME = "Vesotel Jornadas";

/** Categorias de proveedores (art. 13 RGPD permite indicar categorias de destinatarios). */
export const LEGAL_PROVIDERS = {
    hosting: "proveedor de alojamiento de servidores contratado por el titular",
    email: "proveedor de envío de correo electrónico contratado por el titular",
} as const;

/** Misma formula que el aviso legal de vesotel.com. */
export const LEGAL_JURISDICTION = "los juzgados y tribunales que correspondan conforme a la ley";

/** Fecha de ultima actualizacion mostrada en las cuatro paginas. */
export const LEGAL_LAST_UPDATED = "3 de noviembre de 2026";

export const LEGAL_LINKS = [
    { href: "/aviso-legal", label: "Aviso legal" },
    { href: "/privacidad", label: "Privacidad" },
    { href: "/cookies", label: "Cookies" },
    { href: "/terminos", label: "Términos" },
] as const;
