export const MANUAL_AMOUNT_CHOICE_CODE = "manual_amount_choice";

/**
 * Detecta el 409 que devuelve el backend cuando un turno con importe manual cambia
 * hora, fechas, tipo u opciones de extras sin indicar como resolverlo.
 * Devuelve el mensaje del backend, o null si el error es cualquier otra cosa.
 */
export function getManualAmountChoice(error: unknown): { message: string } | null {
    if (!error || typeof error !== "object") return null;

    const response = (error as { response?: { status?: unknown; data?: unknown } }).response;
    if (!response || response.status !== 409) return null;

    const detail = (response.data as { detail?: unknown } | undefined)?.detail;
    if (!detail || typeof detail !== "object") return null;

    const { code, message } = detail as { code?: unknown; message?: unknown };
    if (code !== MANUAL_AMOUNT_CHOICE_CODE) return null;

    return { message: typeof message === "string" ? message : "" };
}
