import { PLANS, type PlanId } from "@/lib/landing-pricing";

export const CONTACT_EMAIL = "hugo@vesotel.com";
export const WHATSAPP_NUMBER = "34685710117";
export const SELECT_PLAN_EVENT = "landing:select-plan";
export const CONTACT_SUBJECT = "Solicitud de demo de Vesotel Jornadas";
export const MONITOR_WAITLIST_SUBJECT = "Lista de espera para monitores";
export const MONITOR_WAITLIST_MESSAGE =
    "Hola, soy monitor y quiero apuntarme a la lista de espera de la versión gratuita de Vesotel Jornadas.\nMi nombre es: ";
export const MONITOR_CONTACT_MESSAGE =
    "Hola, soy monitor y me gustaría saber más sobre la versión gratuita de Vesotel Jornadas, sin compromiso.";

export type PlanChoice = PlanId | "no-se";
export const PLAN_CHOICES: readonly { value: PlanChoice; label: string }[] = [
    ...PLANS.map((plan) => ({ value: plan.id, label: plan.name })),
    { value: "no-se", label: "No lo sé" },
];

export interface ContactData {
    school: string;
    monitors: string;
    plan: PlanChoice;
    contactName: string;
    email: string;
}
export type ContactErrors = Partial<Record<keyof ContactData, string>>;
export const EMPTY_CONTACT: ContactData = {
    school: "",
    monitors: "",
    plan: "no-se",
    contactName: "",
    email: "",
};

const MONITORS_PATTERN = /^[1-9]\d*$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Valida los campos del formulario de contacto. El campo `plan` nunca genera error. */
export function validateContact(data: ContactData): ContactErrors {
    const errors: ContactErrors = {};
    const school = data.school.trim();
    const monitors = data.monitors.trim();
    const contactName = data.contactName.trim();
    const email = data.email.trim();

    if (!school) {
        errors.school = "Indica el nombre de la escuela.";
    }
    if (!MONITORS_PATTERN.test(monitors)) {
        errors.monitors = "Indica un número entero de monitores mayor que 0.";
    }
    if (!contactName) {
        errors.contactName = "Indica tu nombre.";
    }
    if (!email) {
        errors.email = "Indica tu correo.";
    } else if (!EMAIL_PATTERN.test(email)) {
        errors.email = "Introduce un correo válido.";
    }
    return errors;
}

function planLabel(plan: PlanChoice): string {
    return PLAN_CHOICES.find((choice) => choice.value === plan)?.label ?? "No lo sé";
}

/** Mensaje prellenado para WhatsApp y correo. Lineas unidas con salto de linea, sin salto final. */
export function buildContactMessage(data: ContactData): string {
    return [
        "Hola, quiero pedir una demo de Vesotel Jornadas.",
        `Escuela: ${data.school.trim()}`,
        `Monitores (aprox.): ${data.monitors.trim()}`,
        `Plan: ${planLabel(data.plan)}`,
        `Contacto: ${data.contactName.trim()}`,
        `Correo: ${data.email.trim()}`,
    ].join("\n");
}

export function buildWhatsAppUrl(message: string): string {
    return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;
}

/** Los clientes de correo esperan saltos CRLF en el cuerpo del mailto. */
export function buildMailtoUrl(subject: string, message: string): string {
    const body = message.replace(/\n/g, "\r\n");
    return `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

/** Solo se llama en el navegador, tras un clic. */
export function announcePlan(plan: PlanChoice): void {
    window.dispatchEvent(new CustomEvent(SELECT_PLAN_EVENT, { detail: plan }));
}
