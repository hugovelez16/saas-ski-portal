import api from "@/lib/api";
import { User, Token, Session } from "@/lib/types";

export interface CreateUserRequest {
    email: string;
    password?: string;
    firstName: string;
    lastName: string;
    role?: string;
    companyId?: string | null;
    sendEmail?: boolean;
}

export const getUsers = async (): Promise<User[]> => {
    const response = await api.get("/users");
    return response.data;
};

// Sessions Management
export const getUserSessions = async (userId: string): Promise<Session[]> => {
    const response = await api.get(`/users/${userId}/sessions`);
    return response.data;
};

export const revokeUserSession = async (userId: string, sessionId: string) => {
    const response = await api.delete(`/users/${userId}/sessions/${sessionId}`);
    return response.data;
};

export const getUser = async (userId: string): Promise<User> => {
    const response = await api.get(`/users/${userId}`);
    return response.data;
};

export const getUserCompanies = async (userId: string): Promise<any[]> => {
    const response = await api.get(`/users/${userId}/companies`);
    return response.data;
};

export const createUser = async (data: CreateUserRequest): Promise<User> => {
    const response = await api.post("/users", data);
    return response.data;
};

export const updateUserStatus = async (userId: string, isActive: boolean): Promise<any> => {
    const response = await api.put(`/users/${userId}/status?isActive=${isActive}`);
    return response.data;
};

export const updateUser = async (userId: string, data: Partial<User> & { password?: string }): Promise<User> => {
    const response = await api.put(`/users/${userId}`, data);
    return response.data;
};

export const updateMe = async (data: Partial<User>): Promise<User> => {
    const response = await api.put(`/users/me`, data);
    return response.data;
};

export const changePassword = async (data: any): Promise<void> => {
    await api.post('/users/me/change-password', data);
};

export const resetPasswordEmail = async (userId: string) => {
    const response = await api.post(`/users/${userId}/reset-password-email`);
    return response.data;
};

// Two-Factor Authentication (TOTP)
export interface TwoFactorSetup {
    secret: string;
    qrCodeUri: string;
}

export const setup2fa = async (): Promise<TwoFactorSetup> => {
    const response = await api.post<TwoFactorSetup>("/2fa/setup");
    return response.data;
};

export const activate2fa = async (code: string): Promise<{ message: string }> => {
    const response = await api.post("/2fa/activate", { code });
    return response.data;
};

export const disable2fa = async (code: string): Promise<{ message: string }> => {
    const response = await api.post("/2fa/disable", { code });
    return response.data;
};

// Platform admin: reset 2FA for a user who lost their authenticator app
export const resetUser2fa = async (userId: string): Promise<{ message: string }> => {
    const response = await api.post(`/users/${userId}/reset-2fa`);
    return response.data;
};

// Master Admin: Impersonation
export const impersonateUser = async (userId: string): Promise<Token> => {
    const response = await api.post<Token>(`/admin/impersonate/${userId}`);
    return response.data;
};

// Password Recovery
export const forgotPassword = async (email: string): Promise<{ message: string }> => {
    const response = await api.post("/auth/forgot-password", { email });
    return response.data;
};

export const resetPassword = async (data: any): Promise<{ message: string }> => {
    const response = await api.post("/auth/reset-password", data);
    return response.data;
};



