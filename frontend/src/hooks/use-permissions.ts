import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { getCompany } from "@/lib/api/companies";
import { CompanyResponse } from "@/lib/types";

export type PermissionRole = 'platform_admin' | 'manager' | 'worker' | null;

export interface Permissions {
    isPlatformAdmin: boolean;
    isReadOnlyView: boolean;
    role: PermissionRole;
    isManaged: boolean;
    canCreateWorkLog: boolean;
    canEditWorkLog: (log: { userId: string }) => boolean;
    canManageMembers: boolean;
    canInviteMembers: boolean;
    canToggleMemberStatus: (targetRole?: string | null) => boolean;
    canEditCompany: boolean;
    canEditRates: (targetUserId: string) => boolean;
}

/**
 * Permisos de UI derivados del usuario autenticado y de la empresa.
 * Si `company` no se pasa (undefined), consulta la empresa activa con `getCompany`.
 * Espeja las reglas del backend (`access_policy`); en vista de solo lectura
 * (PA "ver como" o suplantacion) todas las acciones `can*` devuelven false.
 */
export function usePermissions(company?: CompanyResponse | null): Permissions {
    const { user } = useAuth();
    const activeCompanyId = user?.activeCompanyId;

    const { data: fetchedCompany = null } = useQuery({
        queryKey: ['company', activeCompanyId],
        queryFn: () => getCompany(activeCompanyId as string),
        enabled: company === undefined && Boolean(activeCompanyId),
    });

    const activeCompany: CompanyResponse | null =
        company === undefined ? fetchedCompany : company;

    const isPlatformAdmin = Boolean(user?.role === 'admin' || user?.isPlatformAdmin);
    const isReadOnlyView = Boolean(user?.isReadOnlyView);
    const isManaged = Boolean(activeCompany?.isManaged);
    const userId = user?.id;

    const rawRole = user?.activeRole ?? activeCompany?.role ?? null;
    let role: PermissionRole = null;
    if (isPlatformAdmin && !user?.activeRole) {
        role = 'platform_admin';
    } else if (rawRole === 'manager' || rawRole === 'worker') {
        role = rawRole;
    }

    const canWrite = !isReadOnlyView;
    const isManagerLike = isPlatformAdmin || role === 'manager';
    const isAutonomousWorker = role === 'worker' && !isManaged;

    return {
        isPlatformAdmin,
        isReadOnlyView,
        role,
        isManaged,
        canCreateWorkLog: canWrite && (isManagerLike || isAutonomousWorker),
        canEditWorkLog: (log) =>
            canWrite && (isManagerLike || (isAutonomousWorker && log.userId === userId)),
        canManageMembers: canWrite && isPlatformAdmin,
        canInviteMembers: canWrite && isManagerLike,
        canToggleMemberStatus: (targetRole?: string | null) =>
            canWrite && (isPlatformAdmin || (role === 'manager' && targetRole === 'worker')),
        canEditCompany: canWrite && isPlatformAdmin,
        canEditRates: (targetUserId) =>
            canWrite && (isManagerLike || (isAutonomousWorker && targetUserId === userId)),
    };
}
