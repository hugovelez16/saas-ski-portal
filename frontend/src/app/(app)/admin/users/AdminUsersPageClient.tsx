"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getUsers, updateUserStatus, impersonateUser } from "@/lib/api/users";
import { User } from "@/lib/types";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { UserDialog } from "@/components/admin/user-dialog";
import { Badge } from "@/components/ui/badge";
import { Users, Ghost } from "lucide-react";
import { useRouter } from "next/navigation";
import { ColumnDef } from "@tanstack/react-table";
import { setAuthToken } from "@/lib/api";

export default function AdminUsersPage() {
    const router = useRouter();
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const { data: users = [], isLoading } = useQuery({
        queryFn: getUsers,
        queryKey: ["users"],
    });

    const toggleStatusMutation = useMutation({
        mutationFn: ({ userId, isActive }: { userId: string, isActive: boolean }) =>
            updateUserStatus(userId, isActive),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
            toast({ title: "Estado actualizado" });
        },    });

    const impersonateMutation = useMutation({
        mutationFn: impersonateUser,
        onSuccess: (data) => {
            setAuthToken(data.accessToken);
            window.location.href = "/dashboard";
            toast({ title: "Simulación iniciada", description: "Ahora actúas como el usuario seleccionado." });
        },    });

    const columns: ColumnDef<User>[] = [
        {
            accessorKey: "firstName",
            header: "Nombre",
            cell: ({ row }) => `${row.original.firstName} ${row.original.lastName}`,
        },
        {
            accessorKey: "email",
            header: "Email",
        },
        {
            accessorKey: "role",
            header: "Rol",
            cell: ({ row }) => (
                <Badge variant={row.original.role === 'admin' ? 'default' : 'secondary'}>
                    {row.original.role}
                </Badge>
            ),
        },
        {
            accessorKey: "isActive",
            header: "Estado",
            cell: ({ row }) => (
                <span className={row.original.isActive ? "text-green-600 font-medium" : "text-red-600 font-medium"}>
                    {row.original.isActive ? "Activo" : "Inactivo"}
                </span>
            ),
        },
        {
            id: "actions",
            header: "Acciones",
            cell: ({ row }) => {
                const user = row.original;
                return (
                    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                            onClick={() => impersonateMutation.mutate(user.id)}
                            disabled={impersonateMutation.isPending}
                            title="Simular Usuario"
                        >
                            <Ghost className="h-4 w-4" />
                        </Button>
                    </div>
                );
            }
        }
    ];

    if (isLoading) {
        return <div className="p-8">Cargando usuarios...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Users className="h-6 w-6 text-indigo-600" />
                    <h1 className="text-2xl font-bold tracking-tight">Gestión de Usuarios</h1>
                </div>
                <UserDialog />
            </div>

            <DataTable
                columns={columns}
                data={users}
                searchKey="email"
                searchPlaceholder="Buscar por email..."
                onRowClick={(user) => router.push(`/admin/users/${user.id}`)}
            />
        </div>
    );
}
