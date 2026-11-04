"use client";

import * as React from "react";
import { Building2, LayoutDashboard } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { CompanyResponse } from "@/lib/types";
import { useAuth } from "@/context/AuthContext";
import {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectLabel,
    SelectTrigger,
    SelectValue,
    SelectSeparator,
} from "@/components/ui/select";

interface CompanySwitcherProps {
    companies: CompanyResponse[];
}

export function CompanySwitcher({ companies }: CompanySwitcherProps) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, switchScope } = useAuth();

    // La empresa activa viene del token (user.activeCompanyId), no de la URL.
    const currentCompanyId = user?.activeCompanyId ?? null;
    const isPlatformAdmin = Boolean(user?.isPlatformAdmin || user?.role === "admin");

    // Worker y manager no pueden operar en empresas suspendidas; el PA si las ve.
    const availableCompanies = React.useMemo(
        () => (isPlatformAdmin ? companies : companies.filter((c) => c.isActive !== false)),
        [companies, isPlatformAdmin]
    );

    const selectedCompany = React.useMemo(() =>
        availableCompanies.find((c) => c.id === currentCompanyId),
        [availableCompanies, currentCompanyId]
    );

    const onSelectCompany = (value: string) => {
        if (value === "overview") {
            const isManager = pathname.includes('/manager') || pathname.includes('/admin');
            router.push(isManager ? '/manager/dashboard' : '/dashboard');
            return;
        }

        const company = availableCompanies.find((c) => c.id === value);
        if (!company || company.id === currentCompanyId) return;

        // switchScope cambia la empresa activa en el backend y recarga la app.
        void switchScope(company.id);
    };

    if (availableCompanies.length === 0) {
        return null;
    }

    return (
        <Select
            value={selectedCompany?.id || (pathname === '/manager/dashboard' && !currentCompanyId ? "overview" : "")}
            onValueChange={onSelectCompany}
        >
            <SelectTrigger className="w-full h-auto py-2 bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700 focus:ring-0 focus:ring-offset-0">
                <div className="flex items-center w-full overflow-hidden">
                    <Building2 className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                    <div className="flex flex-col items-start truncate">
                        {selectedCompany ? (
                            <>
                                <span className="text-sm font-semibold truncate leading-none mb-1">
                                    {selectedCompany.name}
                                </span>
                                {selectedCompany.role && (
                                    <span className="text-[10px] uppercase tracking-wider opacity-60 leading-none">
                                        {selectedCompany.role}
                                    </span>
                                )}
                            </>
                        ) : (
                            <span className="text-sm">Overview</span>
                        )}
                    </div>
                </div>
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                <SelectGroup>
                    <SelectLabel className="text-slate-500">My Companies</SelectLabel>
                    {availableCompanies.map((company) => (
                        <SelectItem key={company.id} value={company.id} className="focus:bg-slate-800 focus:text-white cursor-pointer">
                            <div className="flex flex-col items-start py-0.5">
                                <span className="text-sm font-medium">{company.name}</span>
                                {company.role && (
                                    <span className="text-[10px] uppercase tracking-wider opacity-50">
                                        {company.role}
                                    </span>
                                )}
                            </div>
                        </SelectItem>
                    ))}
                </SelectGroup>
                <SelectSeparator className="bg-slate-800" />
                <SelectGroup>
                    <SelectItem value="overview" className="focus:bg-slate-800 focus:text-white cursor-pointer">
                        <div className="flex items-center">
                            <LayoutDashboard className="mr-2 h-4 w-4" />
                            <span>Overview</span>
                        </div>
                    </SelectItem>
                </SelectGroup>
            </SelectContent>
        </Select>
    );
}
