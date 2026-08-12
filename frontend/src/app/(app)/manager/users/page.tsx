"use client";
export const dynamic = "force-dynamic";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCompaniesDetailed, updateMemberStatus, updateCompanyMembersOrder } from "@/lib/api/companies";
import { DataTable } from "@/components/ui/data-table";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { Users, GripVertical } from "lucide-react";
import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";

import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

function SortableUserItem({ user }: { user: any }) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
    } = useSortable({ id: user.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    return (
        <div ref={setNodeRef} style={style} className="flex items-center gap-4 p-3 border rounded-md mb-2 bg-card shadow-sm">
            <div {...attributes} {...listeners} className="cursor-grab text-muted-foreground hover:text-foreground">
                <GripVertical size={20} />
            </div>
            <div className="flex-1">
                <div className="font-medium text-sm">{user.firstName || ""} {user.lastName || ""}</div>
                <div className="text-xs text-muted-foreground">{user.email}</div>
            </div>
            <div className="text-xs text-muted-foreground">
                {user._role}
            </div>
        </div>
    );
}

export default function ManagerUsersPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const companyIdParam = searchParams.get("companyId");

    const { toast } = useToast();
    const queryClient = useQueryClient();
    
    const [isEditingOrder, setIsEditingOrder] = useState(false);
    const [userOrder, setUserOrder] = useState<string[]>([]);

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
                        _companyId: companyIdParam ? company.id : null,
                        _status: companyIdParam ? (member.isActive ? 'active' : 'inactive') : null,
                        _role: companyIdParam ? member.role : null
                    });
                }
            });
        });
        return Array.from(map.values());
    }, [companies, companyIdParam]);

    const sortedUsersWithMeta = useMemo(() => {
        let list = [...usersWithMeta];
        if (userOrder.length > 0) {
            const orderMap = new Map();
            userOrder.forEach((id, index) => orderMap.set(id, index));
            
            list.sort((a, b) => {
                const idxA = orderMap.get(a.id);
                const idxB = orderMap.get(b.id);
                if (idxA === undefined && idxB === undefined) return 0;
                if (idxA === undefined) return 1;
                if (idxB === undefined) return -1;
                return idxA - idxB;
            });
        }
        return list;
    }, [usersWithMeta, userOrder]);

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over) return;

        if (active.id !== over.id) {
            const currentOrder = userOrder.length > 0 ? userOrder : sortedUsersWithMeta.map(u => u.id);
            const oldIndex = currentOrder.indexOf(active.id as string);
            const newIndex = currentOrder.indexOf(over.id as string);
            
            const newOrder = arrayMove(currentOrder, oldIndex, newIndex);
            setUserOrder(newOrder);
        }
    };

    const toggleEditOrder = async () => {
        if (isEditingOrder) {
            // Save
            if (companyIdParam && userOrder.length > 0) {
                try {
                    await updateCompanyMembersOrder(companyIdParam, userOrder);
                    toast({ title: "Orden guardado correctamente" });
                    queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
                } catch (err) {
                    console.error(err);
                    toast({ title: "Error al guardar el orden", variant: "destructive" });
                }
            }
            setIsEditingOrder(false);
        } else {
            // Start editing
            if (!companyIdParam) {
                toast({ title: "Selecciona una empresa primero", variant: "destructive" });
                return;
            }
            setUserOrder(sortedUsersWithMeta.map(u => u.id));
            setIsEditingOrder(true);
        }
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
                if (!role) return <span className="text-xs text-muted-foreground">-</span>;
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
                if (!user._status) return <span className="text-xs text-muted-foreground">-</span>;
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
                {companyIdParam && (
                    <Button onClick={toggleEditOrder} variant={isEditingOrder ? "default" : "outline"}>
                        {isEditingOrder ? "Guardar orden" : "Modificar orden"}
                    </Button>
                )}
            </div>

            {isEditingOrder ? (
                <div className="p-4 border rounded-md bg-muted/30">
                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                        <SortableContext items={sortedUsersWithMeta.map(u => u.id)} strategy={verticalListSortingStrategy}>
                            {sortedUsersWithMeta.map(user => (
                                <SortableUserItem key={user.id} user={user} />
                            ))}
                        </SortableContext>
                    </DndContext>
                </div>
            ) : (
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
            )}
        </div>
    );
}
