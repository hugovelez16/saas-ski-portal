/**
 * Adaptador TEMPORAL v2 (snake_case) -> tipos actuales (camelCase) [Q-2].
 * Se elimina cuando las pantallas migren a los tipos de `./types`.
 *
 * Solo se convierten las claves del nivel superior (y las de `user` y `members`):
 * el contenido de `settings`, `rates_config`, `tax_config` y `worklog_definitions`
 * ya es snake_case en v1 y se entrega tal cual. Las claves ausentes siguen ausentes
 * (la vista reducida no debe ganar `isActive`, `createdAt`, etc.).
 */
import type { Company, CompanyMember, CompanyUpdatePayload, CompanyWithMembers, UserProfile } from "@/lib/types";
import type { CompanyCreateV2, CompanyFull, CompanyFullWithMembers, CompanyReduced, CompanyUpdateV2, CompanyMemberV2, MemberOut } from "./types";

const snakeToCamel = (key: string): string => key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
const camelToSnake = (key: string): string => key.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);

const mapKeys = (obj: Record<string, any>, fn: (key: string) => string): Record<string, any> => {
    const out: Record<string, any> = {};
    for (const [key, value] of Object.entries(obj)) {
        out[fn(key)] = value;
    }
    return out;
};

export const fromV2Member = (member: CompanyMemberV2 | MemberOut): CompanyMember => {
    const { user, ...rest } = member as MemberOut;
    const out = mapKeys(rest, snakeToCamel);
    if (user) {
        out.user = mapKeys(user, snakeToCamel) as unknown as UserProfile;
    } else if ("user" in member) {
        out.user = undefined;
    }
    return out as unknown as CompanyMember;
};

export const fromV2Company = (company: CompanyFull | CompanyFullWithMembers | CompanyReduced): Company => {
    const { members, ...rest } = company as CompanyFullWithMembers;
    return mapKeys(rest, snakeToCamel) as unknown as Company;
};

/** Empresa con sus miembros (`include=members`); `members` es `[]` si el backend no lo envia. */
export const fromV2CompanyWithMembers = (company: CompanyFullWithMembers): CompanyWithMembers => ({
    ...(fromV2Company(company) as Company),
    members: (company.members ?? []).map(fromV2Member),
});

/** Cuerpo camelCase de las pantallas -> cuerpo v2 (solo nivel superior). */
export const toV2CompanyBody = <T extends CompanyUpdateV2 | CompanyCreateV2>(
    payload: CompanyUpdatePayload | Record<string, any>
): T => mapKeys(payload, camelToSnake) as T;
