import { CompanyMember, DynamicRateConfig, DynamicRateEntry, UserCompanyRate } from "../types";

/**
 * Helper to get the most relevant rate entry from a member's config.
 * Priority: "tutorial" > "particular" > First entry found.
 */
export function getPrimaryRateEntry(ratesConfig: DynamicRateConfig | null | undefined): { key: string, entry: DynamicRateEntry } | null {
    if (!ratesConfig || Object.keys(ratesConfig).length === 0) return null;

    if (ratesConfig.tutorial) return { key: "tutorial", entry: ratesConfig.tutorial };
    if (ratesConfig.particular) return { key: "particular", entry: ratesConfig.particular };

    const firstKey = Object.keys(ratesConfig)[0];
    return { key: firstKey, entry: ratesConfig[firstKey] };
}

/**
 * Maps a CompanyMember (new SaaS JSONB) to the legacy UserCompanyRate (flat) structure.
 * Useful for interoperability during migration.
 *
 * Accepts partial objects (e.g. a company view that only carries `ratesConfig`).
 * `userId` and `companyId` are "" when not available; do not match on them in that case.
 */
export function mapMemberToLegacyRate(
    member: Pick<CompanyMember, "ratesConfig"> & Partial<Pick<CompanyMember, "userId" | "companyId" | "user">>
): UserCompanyRate {
    const primary = getPrimaryRateEntry(member.ratesConfig);
    const entry = primary?.entry;

    return {
        userId: member.userId ?? "",
        companyId: member.companyId ?? "",
        user: member.user,
        hourlyRate: member.ratesConfig?.tutorial?.base_rate || 0,
        dailyRate: member.ratesConfig?.particular?.base_rate || 0,
        nightRate: member.ratesConfig?.night?.base_rate || 0,
        coordinationRate: member.ratesConfig?.coordination?.base_rate || 0,
        isGross: entry?.is_gross !== undefined ? entry.is_gross : false,
        deductionSs: entry?.tax_overrides?.ss ?? undefined,
        deductionIrpf: entry?.tax_overrides?.irpf ?? 0,
        deductionExtra: entry?.tax_overrides?.extra ?? 0,
    };
}
