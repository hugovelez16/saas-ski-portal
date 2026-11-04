import axios from 'axios';

// Ensure this matches your backend URL.
// In Docker, client-side requests go to localhost:8000 externally.
// Use same origin with /api prefix, which Next.js will proxy
// This avoids CORS and IP issues entirely
const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

/**
 * Global Axios instance configured with base URL and default headers.
 * Used for all API requests to the backend.
 */
const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Sets the authentication token for all future API requests (Fallback/Compatibility).
 * In Cookie mode, this is mostly ignored as cookies are handled by the browser.
 * 
 * @param token - The JWT access token or null to clear it.
 */
export const setAuthToken = (token: string | null) => {
  if (token && token !== 'cookie') {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

declare module 'axios' {
  interface AxiosRequestConfig {
    /** `silent: true` evita el toast automatico del interceptor de errores. */
    meta?: { silent?: boolean };
  }
}

export interface ErrorNotification {
  variant: 'destructive';
  title: string;
  description: string;
}

type ErrorNotifier = (notification: ErrorNotification) => void;

let errorNotifier: ErrorNotifier | null = null;

/**
 * Registra la funcion que muestra los errores de la API al usuario
 * (`providers.tsx` la conecta con `useToast`). `null` la desregistra.
 */
export const setErrorNotifier = (fn: ErrorNotifier | null) => {
  errorNotifier = fn;
};

const FALLBACK_DESCRIPTION = 'Ha ocurrido un error inesperado. Intentalo de nuevo.';

/**
 * Convierte el `detail` de FastAPI en texto legible. Acepta una cadena o la
 * lista de errores de validacion 422 (`[{ msg, loc }]`); lo demas da cadena vacia.
 */
export function formatErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (!Array.isArray(detail)) return '';

  return detail
    .map((item) => {
      if (!item || typeof item !== 'object') return '';
      const { msg, loc } = item as { msg?: unknown; loc?: unknown };
      if (typeof msg !== 'string' || !msg) return '';
      const field = Array.isArray(loc)
        ? loc.filter((part) => part !== 'body' && part !== 'query').join('.')
        : '';
      return field ? `${field}: ${msg}` : msg;
    })
    .filter(Boolean)
    .join('; ');
}

export const SUSPENDED_COMPANY_DETAIL = 'Empresa inactiva o suspendida';
export const SUSPENDED_COMPANY_MESSAGE = 'Tu empresa esta suspendida. Contacta con el administrador';

/** True si el error es el 403 que el backend devuelve para una empresa suspendida. */
export function isSuspendedCompanyError(error: unknown): boolean {
  const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })?.response;
  return response?.status === 403 && response.data?.detail === SUSPENDED_COMPANY_DETAIL;
}

/**
 * Texto de error para mostrar en pantalla cuando una carga falla (en vez de
 * pintar una lista vacia): mensaje de empresa suspendida, `detail` del backend o `fallback`.
 */
export function describeLoadError(error: unknown, fallback: string): string {
  if (isSuspendedCompanyError(error)) return SUSPENDED_COMPANY_MESSAGE;
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return formatErrorDetail(detail) || fallback;
}

function titleForStatus(status: number): string | null {
  switch (status) {
    case 403:
      return 'Sin permiso';
    case 404:
      return 'No encontrado';
    case 409:
      return 'Conflicto';
    case 422:
      return 'Datos no validos';
    default:
      return status >= 500 ? 'Error del servidor' : null;
  }
}

// El 401 no notifica: AuthContext cierra la sesion. Los errores sin respuesta
// (red) y los de otros estados los gestiona el llamador.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status: number | undefined = error?.response?.status;
    const silent = Boolean(error?.config?.meta?.silent);

    if (status && !silent && errorNotifier) {
      const title = titleForStatus(status);
      if (title) {
        errorNotifier({
          variant: 'destructive',
          title,
          description: formatErrorDetail(error.response.data?.detail) || FALLBACK_DESCRIPTION,
        });
      }
    }

    return Promise.reject(error);
  },
);

// Initialization from storage removed - now relying on HttpOnly cookies
export default api;
