"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
    Table,
    TableHeader,
    TableBody,
    TableRow,
    TableHead,
    TableCell
} from "@/components/ui/data-table";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { DashboardWorkerSummary } from "@/lib/types";
import { Search, ChevronRight, UserCheck } from "lucide-react";

export interface TeamMemberStats {
    userId: string;
    fullName: string;
    email: string;
    role: string;
    initials: string;
    totalHours: number;
    uniqueDays: number;
    totalLogs: number;
    totalAmount: number;
    isActive?: boolean;
}

interface DashboardTeamTableProps {
    companyId: string;
    members: any[];
    orderedMemberIds?: string[];
    workersSummary: DashboardWorkerSummary[];
    isLoading?: boolean;
}

export function DashboardTeamTable({
    members,
    orderedMemberIds = [],
    workersSummary,
    isLoading
}: DashboardTeamTableProps) {
    const [searchQuery, setSearchQuery] = useState("");

    // Aggregate stats strictly adhering to manager member order
    const teamStats = useMemo<TeamMemberStats[]>(() => {
        // 1. Index backend aggregates by userId (no sums in the browser)
        const summaryByUser = new Map<string, DashboardWorkerSummary>();
        workersSummary.forEach(worker => summaryByUser.set(worker.userId, worker));

        // 2. Build rows following members list
        const rows: TeamMemberStats[] = members.map(m => {
            const userId = m.userId || m.user?.id;
            const user = m.user || {};
            const fullName = `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.email || 'Monitor';
            const initials = `${(user.firstName?.[0] || fullName[0] || 'M')}${(user.lastName?.[0] || '')}`.toUpperCase();
            const role = m.role || 'worker';

            const worker = summaryByUser.get(userId);

            return {
                userId,
                fullName,
                email: user.email || '',
                role,
                initials,
                totalHours: worker?.totalHours ?? 0,
                uniqueDays: worker?.uniqueDays ?? 0,
                totalLogs: worker?.logsCount ?? 0,
                totalAmount: worker?.totalNet ?? 0,
                isActive: worker?.isActive
            };
        });

        // 3. Strict ordering: NUNCA ranking ni Top Monitores
        if (orderedMemberIds && orderedMemberIds.length > 0) {
            const orderMap = new Map<string, number>();
            orderedMemberIds.forEach((id, idx) => orderMap.set(id, idx));

            rows.sort((a, b) => {
                const idxA = orderMap.get(a.userId);
                const idxB = orderMap.get(b.userId);
                if (idxA === undefined && idxB === undefined) return 0;
                if (idxA === undefined) return 1;
                if (idxB === undefined) return -1;
                return idxA - idxB;
            });
        }

        return rows;
    }, [members, orderedMemberIds, workersSummary]);

    const filteredRows = useMemo(() => {
        if (!searchQuery.trim()) return teamStats;
        const q = searchQuery.toLowerCase();
        return teamStats.filter(m =>
            m.fullName.toLowerCase().includes(q) ||
            m.email.toLowerCase().includes(q)
        );
    }, [teamStats, searchQuery]);

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat("es-ES", {
            style: "currency",
            currency: "EUR",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(val);
    };

    return (
        <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                    <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                        <UserCheck className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                        Resumen de Plantilla
                    </h3>
                    <p className="text-xs text-muted-foreground">
                        Mostrando trabajadores según el orden de gestión de la empresa ({filteredRows.length})
                    </p>
                </div>

                <div className="relative w-full sm:w-64">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Buscar monitor por nombre..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-8 h-9 text-xs"
                    />
                </div>
            </div>

            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
                <Table>
                    <TableHeader className="bg-slate-50/80 dark:bg-slate-800/50">
                        <TableRow>
                            <TableHead className="w-[40px] text-xs font-semibold">#</TableHead>
                            <TableHead className="text-xs font-semibold">Monitor / Usuario</TableHead>
                            <TableHead className="text-xs font-semibold">Rol</TableHead>
                            <TableHead className="text-right text-xs font-semibold">Horas</TableHead>
                            <TableHead className="text-right text-xs font-semibold">Días</TableHead>
                            <TableHead className="text-right text-xs font-semibold">Partes</TableHead>
                            <TableHead className="text-right text-xs font-semibold">Importe Acumulado</TableHead>
                            <TableHead className="w-[50px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredRows.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={8} className="h-24 text-center text-xs text-muted-foreground">
                                    No se encontraron monitores con los criterios especificados.
                                </TableCell>
                            </TableRow>
                        ) : (
                            filteredRows.map((row, index) => (
                                <TableRow
                                    key={row.userId}
                                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors text-xs"
                                >
                                    <TableCell className="font-mono text-muted-foreground text-[11px]">
                                        {index + 1}
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center gap-2.5">
                                            <Avatar className="h-7 w-7 border border-slate-200 dark:border-slate-700">
                                                <AvatarFallback className="text-[11px] font-medium bg-slate-100 dark:bg-slate-800">
                                                    {row.initials}
                                                </AvatarFallback>
                                            </Avatar>
                                            <div className="min-w-0">
                                                <div className="font-medium text-slate-900 dark:text-slate-100 truncate">
                                                    {row.fullName}
                                                </div>
                                                <div className="text-[11px] text-muted-foreground truncate">
                                                    {row.email}
                                                </div>
                                            </div>
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center gap-1.5">
                                            <Badge variant="outline" className="capitalize text-[10px] px-1.5 h-5">
                                                {row.role}
                                            </Badge>
                                            {row.isActive === false && (
                                                <Badge variant="outline" className="text-[10px] px-1.5 h-5 text-muted-foreground">
                                                    Inactivo
                                                </Badge>
                                            )}
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-right font-medium">
                                        {row.totalHours.toFixed(1)} h
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground">
                                        {row.uniqueDays} d
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground">
                                        {row.totalLogs}
                                    </TableCell>
                                    <TableCell className="text-right font-semibold text-slate-900 dark:text-slate-100">
                                        {formatCurrency(row.totalAmount)}
                                    </TableCell>
                                    <TableCell className="text-right pr-3">
                                        <Button asChild variant="ghost" size="icon" className="h-7 w-7">
                                            <Link href={`/manager/users/${row.userId}`}>
                                                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                            </Link>
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
