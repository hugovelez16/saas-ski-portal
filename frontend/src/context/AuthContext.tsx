"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { setAuthToken } from "@/lib/api";
import { UserProfile, Token } from "@/lib/types";
import { useRouter } from 'next/navigation';

interface AuthContextType {
    user: UserProfile | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<{ requires2FA: boolean }>;
    verify2FA: (code: string, trustDevice?: boolean) => Promise<void>;
    resend2FA: () => Promise<void>;
    logout: () => void;
    stopImpersonation: () => Promise<void>;
    switchScope: (companyId: string, role: string) => Promise<void>;
    checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    login: async () => { return { requires2FA: false } },
    verify2FA: async () => { },
    resend2FA: async () => { },
    logout: () => { },
    stopImpersonation: async () => { },
    switchScope: async () => { },
    checkAuth: async () => { },
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const fetchUser = async () => {
        try {
            const response = await api.get<UserProfile>('/users/me');
            setUser(response.data);
            return response.data;
        } catch (error: any) {
            // Suppress 401 errors from console to avoid Next.js error overlay
            if (error.response?.status !== 401) {
                console.error("Failed to fetch user:", error);
            } else {
                const path = typeof window !== 'undefined' ? window.location.pathname : '';
                const publicPaths = ['/login', '/forgot-password', '/reset-password'];
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

    const login = async (email: string, password: string) => {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        // Add Device Token if exists
        const deviceToken = localStorage.getItem('device_token');
        if (deviceToken) {
            formData.append('device_token', deviceToken);
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
            localStorage.setItem('device_token', tokenData.deviceToken);
        }


        const userData = await fetchUser();

        if (userData?.role === 'admin') {
            router.push('/admin/companies');
        } else if (userData?.isManager) {
            router.push('/manager/daily-reports');
        } else {
            router.push('/dashboard');
        }
        return { requires2FA: false };
    };

    const verify2FA = async (code: string, trustDevice: boolean = false) => {
        const response = await api.post('/verify-2fa', { code, trustDevice });
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

    const resend2FA = async () => {
        await api.post('/resend-2fa');
    };

    const logout = async () => {
        try {
            await api.post('/logout');
        } catch (error) {
            console.error("Logout failed on server:", error);
        } finally {
            setAuthToken(null);
            setUser(null);
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

    const switchScope = async (companyId: string, role: string) => {
        try {
            await api.post('/auth/switch-scope', { companyId: companyId, companyRole: role });
            await fetchUser();
            // Force a full page reload to clear all caches and ensure everything (Sidebar, etc) reflects the new context
            if (!companyId) {
                window.location.href = '/admin/companies';
            } else if (role === 'manager') {
                window.location.href = `/manager/dashboard?companyId=${companyId}`;
            } else {
                window.location.href = `/dashboard?companyId=${companyId}`;
            }
        } catch (error) {
            console.error("Failed to switch scope:", error);
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, verify2FA, resend2FA, logout, stopImpersonation, switchScope, checkAuth }}>
            {children}
        </AuthContext.Provider>
    );
};
