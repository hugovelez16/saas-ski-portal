"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { setAuthToken } from "@/lib/api";
import { UserProfile } from "@/lib/types";
import { getLastCompanyId, setLastCompanyId, LAST_COMPANY_KEY } from "@/lib/last-company";
import { useRouter } from 'next/navigation';
import posthog from 'posthog-js';

interface AuthContextType {
    user: UserProfile | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<{ requires2FA: boolean }>;
    devLogin: () => Promise<{ requires2FA: boolean }>;
    verify2FA: (code: string, companyId?: string) => Promise<void>;
    logout: () => void;
    stopImpersonation: () => Promise<void>;
    switchScope: (companyId: string | null, viewAs?: 'manager' | 'worker') => Promise<void>;
    checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    login: async () => { return { requires2FA: false } },
    devLogin: async () => { return { requires2FA: false } },
    verify2FA: async () => { },
    logout: () => { },
    stopImpersonation: async () => { },
    switchScope: async () => { },
    checkAuth: async () => { },
});

export const useAuth = () => useContext(AuthContext);

const analyticsEnabled = () => Boolean(process.env.NEXT_PUBLIC_POSTHOG_KEY) && posthog.__loaded;

function identifyUser(u: UserProfile) {
  if (!analyticsEnabled() || !u?.id) return;
  posthog.identify(String(u.id), {
    role: u.role,
    company_id: u.activeCompanyId ?? null,
  });
}

function resetAnalytics() {
  if (!analyticsEnabled()) return;
  posthog.reset();
}

function isPlatformAdminUser(u: UserProfile | null | undefined): boolean {
  return Boolean(u?.isPlatformAdmin || u?.role === 'admin');
}

// Pantalla de inicio tras iniciar sesion, segun el rol.
export function homePathFor(u: UserProfile | null | undefined): string {
    if (isPlatformAdminUser(u)) return '/admin/companies';
    if (u?.isManager) return '/manager/daily-reports';
    return '/dashboard';
}

// Un PA no tiene empresa recordada: su contexto es neutro.
function rememberActiveCompany(u: UserProfile | null | undefined) {
  if (!u || isPlatformAdminUser(u) || !u.activeCompanyId) return;
  setLastCompanyId(LAST_COMPANY_KEY, u.activeCompanyId);
}

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const fetchUser = async (retryDev: boolean = true): Promise<UserProfile | null> => {
        try {
            // En la landing la comprobacion de sesion es silenciosa: un visitante no debe ver errores del backend.
            const onLanding = typeof window !== 'undefined' && window.location.pathname === '/';
            const response = await api.get<UserProfile>('/users/me', { meta: { silent: onLanding } });
            setUser(response.data);
            identifyUser(response.data);
            rememberActiveCompany(response.data);
            return response.data;
        } catch (error: any) {
            if (error.response?.status === 401 && retryDev && process.env.NEXT_PUBLIC_DEV_LOGIN_BYPASS === 'true') {
                try {
                    await api.post('/auth/dev-login');
                    return await fetchUser(false);
                } catch {
                    // Si falla el auto-login en dev, continuar con flujo habitual
                }
            }

            // Suppress 401 errors from console to avoid Next.js error overlay
            if (error.response?.status !== 401) {
                console.error("Failed to fetch user:", error);
            } else {
                const path = typeof window !== 'undefined' ? window.location.pathname : '';
                const publicPaths = ['/', '/login', '/forgot-password', '/reset-password'];
                if (!publicPaths.includes(path)) {
                    logout();
                } else {
                    setAuthToken(null);
                    setUser(null);
                }
            }
            return null;
        } finally {
            setLoading(false);
        }
    };

    const checkAuth = async () => {
        // In Cookie mode, we just try to fetch the user. 
        // If the browser has the HttpOnly cookie, this will succeed.
        await fetchUser();
    };

    useEffect(() => {
        checkAuth();
    }, []);

    const devLogin = async () => {
        try {
            const response = await api.post('/auth/dev-login');
            const tokenData = response.data;
            setAuthToken(tokenData.accessToken);
            const userData = await fetchUser();

            router.push(homePathFor(userData));
            return { requires2FA: false };
        } catch (error) {
            console.error("Error en bypass de inicio de sesión en desarrollo:", error);
            throw error;
        }
    };

    const login = async (email: string, password: string) => {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        // Add Device Token if exists
        let deviceToken: string | null = null;
        try {
            deviceToken = localStorage.getItem('device_token');
        } catch {
            deviceToken = null;
        }
        if (deviceToken) {
            formData.append('device_token', deviceToken);
        }

        // Sugerencia de empresa; el backend valida la membresia
        const lastCompanyId = getLastCompanyId(LAST_COMPANY_KEY);
        if (lastCompanyId) {
            formData.append('company_id', lastCompanyId);
        }

        const response = await api.post('/token', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        // Backend returns snake_case: access_token, requires_2fa, device_token
        const tokenData = response.data;

        if (tokenData.requires2fa || tokenData.requires2Fa || tokenData.requires_2fa) {
            // Provisional token is also in a cookie now
            return { requires2FA: true };
        }

        setAuthToken(tokenData.accessToken);
        // If device token returned (e.g. rotated), update it
        if (tokenData.deviceToken) {
            try {
                localStorage.setItem('device_token', tokenData.deviceToken);
            } catch {
                // Storage no disponible: el device token no se persiste
            }
        }


        const userData = await fetchUser();

        router.push(homePathFor(userData));
        return { requires2FA: false };
    };

    const verify2FA = async (code: string, companyId?: string) => {
        const body: { code: string; companyId?: string } = { code };
        if (companyId) {
            body.companyId = companyId;
        }
        const response = await api.post('/verify-2fa', body);
        // Backend returns snake_case
        const tokenData = response.data;
        // setAuthToken handles the 'cookie' signal
        setAuthToken(tokenData.accessToken);

        const userData = await fetchUser();

        if (userData?.role === 'admin') {
            router.push('/admin/companies');
        } else if (userData?.isManager) {
            router.push('/manager/daily-reports');
        } else {
            router.push('/dashboard');
        }
    };

    const logout = async () => {
        try {
            await api.post('/logout');
        } catch (error) {
            console.error("Logout failed on server:", error);
        } finally {
            setAuthToken(null);
            setUser(null);
            resetAnalytics();
            localStorage.removeItem('token');
            sessionStorage.removeItem('token');
            router.push('/login');
        }
    };

    const stopImpersonation = async () => {
        try {
            await api.post('/admin/stop-impersonation');
            // After restoring cookies on server, we need to refresh local user state
            await fetchUser();
            router.push('/admin/users'); // Go back to users management
        } catch (error) {
            console.error("Failed to stop impersonation:", error);
            logout(); // Fallback to logout on error
        }
    };

    const switchScope = async (companyId: string | null, viewAs?: 'manager' | 'worker') => {
        try {
            await api.post('/auth/switch-scope', { companyId, viewAs });
            // fetchUser guarda activeCompanyId en el navegador (no aplica a PA)
            const userData = await fetchUser();
            // Force a full page reload to clear all caches and ensure everything (Sidebar, etc) reflects the new context
            if (!companyId) {
                window.location.href = '/admin/companies';
            } else if (isPlatformAdminUser(userData) && !viewAs) {
                window.location.href = `/admin/companies/${companyId}`;
            } else if (userData?.activeRole === 'manager') {
                window.location.href = '/manager/dashboard';
            } else {
                window.location.href = '/dashboard';
            }
        } catch (error) {
            console.error("Failed to switch scope:", error);
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, devLogin, verify2FA, logout, stopImpersonation, switchScope, checkAuth }}>
            {children}
        </AuthContext.Provider>
    );
};
