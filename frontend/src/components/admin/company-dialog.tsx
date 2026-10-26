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
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { TaxConfigBuilder } from "@/components/admin/tax-config-builder";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createCompany } from "@/lib/api/companies";
import { useToast } from "@/hooks/use-toast";
import { Plus } from "lucide-react";

const formSchema = z.object({
    name: z.string().min(2, {
        message: "El nombre de la empresa debe tener al menos 2 caracteres.",
    }),
    isManaged: z.boolean().default(false),
    isActive: z.boolean().default(true),
});

export function CompanyDialog() {
    const [open, setOpen] = useState(false);
    const { toast } = useToast();
    const queryClient = useQueryClient();
    // null = aun sin definir; {} solo es valido con la confirmacion "sin retenciones"
    const [taxConfig, setTaxConfig] = useState<Record<string, number> | null>(null);
    const [noWithholdings, setNoWithholdings] = useState(false);
    const [taxError, setTaxError] = useState<string | null>(null);

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
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
            setTaxConfig(null);
            setNoWithholdings(false);
            setTaxError(null);
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
        // El alta exige taxConfig: o impuestos confirmados, o "sin retenciones" explicito
        if (taxConfig === null || (Object.keys(taxConfig).length === 0 && !noWithholdings)) {
            setTaxError("Define los impuestos y pulsa Guardar, o confirma que la empresa no tiene retenciones.");
            return;
        }
        setTaxError(null);
        mutation.mutate({
            ...values,
            taxConfig,
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
            <DialogContent className="sm:max-w-[560px] max-h-[90vh] overflow-y-auto">
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
                        <div className="space-y-3 rounded-lg border p-3">
                            <div className="space-y-0.5">
                                <p className="text-sm font-medium">Impuestos de la empresa</p>
                                <p className="text-xs text-muted-foreground">
                                    Anade cada retencion con su nombre y porcentaje. Pulsa Guardar para confirmar la lista.
                                </p>
                            </div>
                            <TaxConfigBuilder
                                initialValue={taxConfig ?? {}}
                                onSave={(val) => {
                                    setTaxConfig(val);
                                    setTaxError(null);
                                    if (Object.keys(val).length > 0) setNoWithholdings(false);
                                }}
                            />
                            {taxConfig !== null && Object.keys(taxConfig).length > 0 && (
                                <p className="text-xs text-muted-foreground">
                                    Confirmados: {Object.entries(taxConfig).map(([k, v]) => `${k} ${parseFloat((v * 100).toFixed(4))}%`).join(", ")}
                                </p>
                            )}
                            {(taxConfig === null || Object.keys(taxConfig).length === 0) && (
                                <div className="flex items-center gap-2">
                                    <Checkbox
                                        id="no-withholdings"
                                        checked={noWithholdings}
                                        onCheckedChange={(c) => {
                                            const on = c === true;
                                            setNoWithholdings(on);
                                            if (on) {
                                                setTaxConfig({});
                                                setTaxError(null);
                                            }
                                        }}
                                    />
                                    <Label htmlFor="no-withholdings" className="text-sm font-normal">
                                        Confirmo que la empresa no tiene retenciones (sin retenciones)
                                    </Label>
                                </div>
                            )}
                            {taxError && <p className="text-sm text-destructive">{taxError}</p>}
                        </div>
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
