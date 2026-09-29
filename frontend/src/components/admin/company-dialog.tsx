"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createCompany } from "@/lib/api/companies";
import { useToast } from "@/hooks/use-toast";
import { Plus } from "lucide-react";

const formSchema = z.object({
    name: z.string().min(2, {
        message: "El nombre de la empresa debe tener al menos 2 caracteres.",
    }),
    fiscalId: z.string().optional(),
    isManaged: z.boolean().default(false),
    isActive: z.boolean().default(true),
});

export function CompanyDialog() {
    const [open, setOpen] = useState(false);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            fiscalId: "",
            isManaged: false,
            isActive: true,
        },
    });

    const mutation = useMutation({
        mutationFn: createCompany,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            setOpen(false);
            form.reset();
            toast({
                title: "Company created",
                description: "The new company has been successfully created.",
            });
        },
        onError: () => {
            toast({
                title: "Error",
                description: "Failed to create company.",
                variant: "destructive",
            });
        },
    });

    function onSubmit(values: z.infer<typeof formSchema>) {
        mutation.mutate({
            ...values,
            taxConfig: { social_security: 0.0, irpf_base: 0.0 },
            worklogDefinitions: {
                particular: { unit: "hours", label: "Particular" },
                tutorial: { unit: "hours", label: "Tutorial" }
            }
        });
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button className="bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200 font-medium shadow-sm">
                    <Plus className="mr-2 h-4 w-4" />
                    Nueva Empresa
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Nueva Empresa</DialogTitle>
                    <DialogDescription>
                        Crea y da de alta una nueva empresa en la plataforma.
                    </DialogDescription>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={form.control}
                            name="name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Nombre de la empresa</FormLabel>
                                    <FormControl>
                                        <Input placeholder="Ej: Escuela Esquí Sierra" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="fiscalId"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>NIF / CIF (Opcional)</FormLabel>
                                    <FormControl>
                                        <Input placeholder="B-12345678" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="isManaged"
                            render={({ field }) => (
                                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                                    <div className="space-y-0.5 pr-2">
                                        <FormLabel className="text-sm font-medium">Modo Gestionada</FormLabel>
                                        <p className="text-xs text-muted-foreground">
                                            La direccion central fija tarifas y gestiona turnos. Los trabajadores no podran modificar turnos ni salarios.
                                        </p>
                                    </div>
                                    <FormControl>
                                        <Switch
                                            checked={field.value}
                                            onCheckedChange={field.onChange}
                                        />
                                    </FormControl>
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="isActive"
                            render={({ field }) => (
                                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                                    <div className="space-y-0.5 pr-2">
                                        <FormLabel className="text-sm font-medium">Empresa Activa</FormLabel>
                                        <p className="text-xs text-muted-foreground">
                                            Permite el acceso y registro operativo de todos los miembros.
                                        </p>
                                    </div>
                                    <FormControl>
                                        <Switch
                                            checked={field.value}
                                            onCheckedChange={field.onChange}
                                        />
                                    </FormControl>
                                </FormItem>
                            )}
                        />
                        <DialogFooter>
                            <Button type="submit" disabled={mutation.isPending}>
                                {mutation.isPending ? "Creando..." : "Crear Empresa"}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
