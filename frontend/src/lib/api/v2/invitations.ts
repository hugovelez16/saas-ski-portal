import api from "@/lib/api";
import { InvitationAcceptOut, InvitationOut, InvitationPreviewOut, InvitationStatus } from "@/lib/api/v2/types";

function invitationsBase(companyId: string, asAdmin?: boolean): string {
    return asAdmin ? `/v2/admin/companies/${companyId}/invitations` : `/v2/companies/${companyId}/invitations`;
}

/** GET /v2/companies/{companyId}/invitations (o /v2/admin/... para PA). */
export const listInvitations = async (
    companyId: string,
    params?: { status?: InvitationStatus | "all"; asAdmin?: boolean },
    config?: { meta?: { silent?: boolean } }
): Promise<InvitationOut[]> => {
    const query = params?.status ? { status: params.status } : undefined;
    const response = await api.get<InvitationOut[]>(invitationsBase(companyId, params?.asAdmin), {
        params: query,
        ...config,
    });
    return response.data;
};

/** POST /v2/companies/{companyId}/invitations. */
export const createInvitation = async (
    companyId: string,
    email: string,
    options?: { asAdmin?: boolean }
): Promise<InvitationOut> => {
    const response = await api.post<InvitationOut>(invitationsBase(companyId, options?.asAdmin), { email });
    return response.data;
};

/** POST /v2/companies/{companyId}/invitations/{invitationId}/resend. */
export const resendInvitation = async (
    companyId: string,
    invitationId: string,
    options?: { asAdmin?: boolean }
): Promise<InvitationOut> => {
    const response = await api.post<InvitationOut>(
        `${invitationsBase(companyId, options?.asAdmin)}/${invitationId}/resend`
    );
    return response.data;
};

/** DELETE /v2/companies/{companyId}/invitations/{invitationId}. */
export const cancelInvitation = async (
    companyId: string,
    invitationId: string,
    options?: { asAdmin?: boolean }
): Promise<InvitationOut> => {
    const response = await api.delete<InvitationOut>(
        `${invitationsBase(companyId, options?.asAdmin)}/${invitationId}`
    );
    return response.data;
};

/** GET /v2/invitations/preview?token=... */
export const previewInvitation = async (token: string): Promise<InvitationPreviewOut> => {
    const response = await api.get<InvitationPreviewOut>("/v2/invitations/preview", {
        params: { token },
        meta: { silent: true },
    });
    return response.data;
};

/** POST /v2/invitations/accept. */
export const acceptInvitation = async (token: string): Promise<InvitationAcceptOut> => {
    const response = await api.post<InvitationAcceptOut>(
        "/v2/invitations/accept",
        { token },
        { meta: { silent: true } }
    );
    return response.data;
};
