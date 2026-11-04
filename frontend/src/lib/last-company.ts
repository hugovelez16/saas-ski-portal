/**
 * Ultima empresa activa recordada en el navegador.
 *
 * Solo se guarda el id de empresa, sin email ni userId. El backend valida
 * siempre la membresia al emitir el token: si el valor no es una membresia
 * activa del usuario que entra, se ignora. Todo acceso a localStorage va en
 * try/catch porque puede lanzar (ventana privada, datos bloqueados) o no
 * existir (entornos sin storage); en ese caso se omite sin error.
 */

export const LAST_COMPANY_KEY = 'lastCompanyId';

export function getLastCompanyId(key: string): string | null {
    try {
        return localStorage.getItem(key) || null;
    } catch {
        return null;
    }
}

export function setLastCompanyId(key: string, companyId: string): void {
    try {
        localStorage.setItem(key, companyId);
    } catch {
        // Storage no disponible: no se recuerda la empresa, el flujo continua
    }
}
