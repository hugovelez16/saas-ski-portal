"use client";
export const dynamic = "force-dynamic";


import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCompaniesDetailed, updateMemberStatus, updateCompanyMembersOrder } from "@/lib/api/companies";
import { DataTable } from "@/components/ui/data-table";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { Users, ArrowUp, ArrowDown } from "lucide-react";
import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ColumnDef } from "@tanstack/react-table";

export default function ManagerUsersPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const companyIdParam = searchParams.get("companyId");

    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [userOrder, setUserOrder] = useState<string[]>([]);

    // Fetch Managed Key Data
    const { data: companies = [], isLoading } = useQuery({
        queryFn: getCompaniesDetailed,
        queryKey: ["companiesDetailed"],
    });

    const memberStatusMutation = useMutation({
        mutationFn: ({ companyId, userId, status }: { companyId: string; userId: string; status: string }) =>
            updateMemberStatus(companyId, userId, status),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            toast({ title: "Estado membresía actualizado" });
        },
        onError: () => toast({ title: "Error al actualizar estado", variant: "destructive" })
    });

    // Deduplicate Users from Companies and Flatten with Meta
    const usersWithMeta = useMemo(() => {
        const map = new Map<string, any>();

        const filteredCompanies = companyIdParam
            ? companies.filter((c: any) => c.id === companyIdParam)
            : companies;

        filteredCompanies.forEach((company: any) => {
            if (!company.members) return;
            company.members.forEach((member: any) => {
                if (!map.has(member.userId)) {
                    map.set(member.userId, {
                        ...member.user,
                        _companyId: company.id,
                        _status: member.isActive ? 'active' : 'inactive',
                        _role: member.role
                    });
                }
            });
        });
        return Array.from(map.values());
    }, [companies, companyIdParam]);

    const sortedUsersWithMeta = useMemo(() => {
        let list = [...usersWithMeta];
        if (userOrder.length > 0) {
            list.sort((a, b) => {
                const idxA = userOrder.indexOf(a.id);
                const idxB = userOrder.indexOf(b.id);
                if (idxA === -1 && idxB === -1) return 0;
                if (idxA === -1) return 1;
                if (idxB === -1) return -1;
                return idxA - idxB;
            });
        }
        return list;
    }, [usersWithMeta, userOrder]);

    const moveUser = (userId: string, direction: 'up' | 'down', e: React.MouseEvent) => {
        e.stopPropagation();
        if (!companyIdParam) return toast({ title: "Selecciona una empresa para ordenar", variant: "destructive" });
        
        const currentOrder = userOrder.length > 0 ? userOrder : sortedUsersWithMeta.map((u: any) => u.id);
        const idx = currentOrder.indexOf(userId);
        if (idx === -1) return;

        const newOrder = [...currentOrder];
        if (direction === 'up' && idx > 0) {
            [newOrder[idx], newOrder[idx - 1]] = [newOrder[idx - 1], newOrder[idx]];
        }
        if (direction === 'down' && idx < newOrder.length - 1) {
            [newOrder[idx], newOrder[idx + 1]] = [newOrder[idx + 1], newOrder[idx]];
        }
        setUserOrder(newOrder);
        
        updateCompanyMembersOrder(companyIdParam, newOrder).catch(err => {
            console.error("Error updating order:", err);
        });
    };

    const handleToggle = (user: any, checked: boolean) => {
        if (!user._companyId) return;
        memberStatusMutation.mutate({
            companyId: user._companyId,
            userId: user.id,
            status: checked ? 'active' : 'rejected'
        });
    };

    const columns: ColumnDef<any>[] = [
        {
            id: "actions",
            header: "",
            cell: ({ row }) => {
                const user = row.original;
                if (!companyIdParam) return null; // Solo mostrar flechas si estamos viendo una empresa específica
                return (
                    <div className="flex flex-col gap-1 w-6 items-center" onClick={(e) => e.stopPropagation()}>
                        <button onClick={(e) => moveUser(user.id, 'up', e)} className="h-5 w-6 hover:bg-muted rounded flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"><ArrowUp size={14} /></button>
                        <button onClick={(e) => moveUser(user.id, 'down', e)} className="h-5 w-6 hover:bg-muted rounded flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"><ArrowDown size={14} /></button>
                    </div>
                );
            }
        },
        {
            accessorKey: "firstName",
            header: "Nombre",
            cell: ({ row }) => `${row.original.firstName || ""} ${row.original.lastName || ""}`.trim(),
        },
        {
            accessorKey: "email",
            header: "Email",
        },
        {
            accessorKey: "_role",
            header: "Rol",
            cell: ({ row }) => {
                const role = row.original._role;
                const roleMap: Record<string, { label: string, color: string }> = {
                    admin: { label: 'Admin Empresa', color: 'bg-red-600' },
                    manager: { label: 'Manager', color: 'bg-indigo-600' },
                    worker: { label: 'Trabajador', color: 'bg-slate-200 text-slate-700' }
                };
                
                const display = roleMap[role as string] || { label: role, color: 'bg-secondary text-secondary-foreground' };
                
                return (
                    <Badge 
                        variant={role === 'worker' ? 'secondary' : 'default'}
                        className={display.color + (role !== 'worker' ? " hover:opacity-90" : "")}
                    >
                        {display.label}
                    </Badge>
                );
            },
        },
        {
            accessorKey: "_status",
            header: "Estado en Empresa",
            cell: ({ row }) => {
                const user = row.original;
                return (
                    <div className="flex items-center space-x-2" onClick={(e) => e.stopPropagation()}>
                        <Switch
                            checked={user._status === 'active'}
                            onCheckedChange={(checked) => handleToggle(user, checked)}
                        />
                        <span className={user._status === 'active' ? "text-green-600 text-xs font-semibold" : "text-red-600 text-xs font-semibold"}>
                            {user._status === 'active' ? "Activo" : "Inactivo"}
                        </span>
                    </div>
                );
            }
        }
    ];

    if (isLoading) {
        return <div className="p-8">Cargando gestión de usuarios...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Users className="h-6 w-6 text-indigo-600" />
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Panel de Supervisión</h1>
                </div>
            </div>

            <DataTable
                columns={columns}
                data={sortedUsersWithMeta}
                searchKey="email"
                searchPlaceholder="Buscar por email..."
                onRowClick={(user) => {
                    const query = companyIdParam ? `?companyId=${companyIdParam}` : "";
                    router.push(`/manager/users/${user.id}${query}`);
                }}
            />
        </div>
    );
}
