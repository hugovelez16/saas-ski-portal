"use client";

import { useState, useEffect, useMemo } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Wallet, Database, Loader2, Pencil, Euro, Percent, Info } from "lucide-react";

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
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { updateMemberRates } from "@/lib/api/companies";
import { CompanyMember, Company } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { TaxOverridesFields, compactTaxOverrides } from "@/components/admin/tax-overrides-fields";

const rateFormSchema = z.object({
    rates: z.record(z.coerce.number().min(0)),
    isGross: z.boolean().default(false),
    // Fracciones 0..1 o null (sin override); NaN = entrada invalida en pantalla
    taxOverrides: z.record(z.number().min(0).max(1).nullable()).default({}),
});

type RateFormValues = z.infer<typeof rateFormSchema>;

interface UserRatesEditDialogProps {
    userId: string;
    company: Company;
    member?: CompanyMember;
    userName: string;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
}

export function UserRatesEditDialog({ userId, company, member, userName, open: externalOpen, onOpenChange }: UserRatesEditDialogProps) {
    const [internalOpen, setInternalOpen] = useState(false);
    const open = externalOpen !== undefined ? externalOpen : internalOpen;
    const setOpen = onOpenChange || setInternalOpen;

    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Worklog definitions determine the fields
    const worklogDefs = company.worklogDefinitions || {};
    const worklogKeys = Object.keys(worklogDefs);

    const form = useForm<RateFormValues>({
        resolver: zodResolver(rateFormSchema),
        defaultValues: {
            rates: {},
            isGross: false,
            taxOverrides: {},
        },
    });

    // Reset form when member or open state changes
    useEffect(() => {
        if (open && member) {
            const initialRates: Record<string, number> = {};
            worklogKeys.forEach(key => {
                initialRates[key] = member.ratesConfig?.[key]?.base_rate || 0;
            });

            // Scan all rates to find existing tax configurations (pulling from the user's data)
            const config = member.ratesConfig || {};
            const allRateEntries = Object.values(config);
            
            // Find the first rate that has these values defined
            const entryWithIsGross = allRateEntries.find(r => r.is_gross !== undefined);
            const entryWithOverrides = allRateEntries.find(r => r.tax_overrides && Object.keys(r.tax_overrides).length > 0);

            form.reset({
                rates: initialRates,
                isGross: entryWithIsGross?.is_gross !== undefined ? entryWithIsGross.is_gross : false,
                taxOverrides: { ...(entryWithOverrides?.tax_overrides || {}) },
            });
        }
    }, [member, open, form, JSON.stringify(worklogKeys)]);

    const mutation = useMutation({
        mutationFn: (values: any) => updateMemberRates(company.id, userId, values.ratesConfig),
        onSuccess: () => {
            toast({ title: "Tarifas actualizadas correctamente" });
            queryClient.invalidateQueries({ queryKey: ["companyRates", company.id] });
            setOpen(false);
        },
        onError: (error: any) => {
            toast({
                title: "Error al actualizar tarifas",
                description: error.response?.data?.detail || "Ha ocurrido un error",
                variant: "destructive",
            });
        },
    });

    function onSubmit(data: RateFormValues) {
        const ratesConfig: Record<string, any> = {};
        
        worklogKeys.forEach(key => {
            ratesConfig[key] = {
                base_rate: data.rates[key] || 0,
                is_gross: data.isGross,
                tax_overrides: compactTaxOverrides(data.taxOverrides ?? {})
            };
        });

        mutation.mutate({ ratesConfig });
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            {!onOpenChange && (
                <DialogTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 text-indigo-600">
                        <Pencil className="h-4 w-4" />
                    </Button>
                </DialogTrigger>
            )}
            <DialogContent className="max-w-2xl overflow-hidden border-slate-200 dark:border-slate-800 shadow-2xl p-0 bg-white dark:bg-slate-950">
                <div className="bg-slate-900 p-6 text-white border-b border-indigo-500/20">
                    <DialogHeader>
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-indigo-500/20 rounded-lg border border-indigo-500/30">
                                <Wallet className="h-6 w-6 text-indigo-400" />
                            </div>
                            <div>
                                <DialogTitle className="text-xl text-slate-100">Editar Tarifas: {userName}</DialogTitle>
                                <DialogDescription className="text-slate-400 text-xs">
                                    Configuración de retribuciones y fiscalidad en <span className="text-indigo-400 font-medium">{company.name}</span>.
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                </div>

                <div className="p-6">
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                            {/* RATES SECTION */}
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
                                    <Euro className="h-4 w-4 text-indigo-600" />
                                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Tarifas por Jornada</h3>
                                </div>
                                
                                <div className="grid gap-4 md:grid-cols-2">
                                    {worklogKeys.length === 0 ? (
                                        <div className="col-span-2 flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-950/20 text-amber-600 rounded-lg text-sm italic">
                                            <Info className="h-4 w-4" />
                                            No hay tipos de jornada definidos para esta empresa.
                                        </div>
                                    ) : (
                                        worklogKeys.map((key) => (
                                            <FormField
                                                key={key}
                                                control={form.control}
                                                name={`rates.${key}`}
                                                render={({ field }) => (
                                                    <FormItem className="space-y-1.5">
                                                        <FormLabel className="text-[10px] font-bold uppercase text-muted-foreground tracking-tight">
                                                            {worklogDefs[key].label || key}
                                                        </FormLabel>
                                                        <FormControl>
                                                            <div className="relative group">
                                                                <span className="absolute left-3 top-2.5 text-slate-400 text-xs group-focus-within:text-indigo-500 transition-colors">€</span>
                                                                <Input 
                                                                    type="number" 
                                                                    step="0.01" 
                                                                    {...field} 
                                                                    className="pl-7 h-10 bg-slate-50/50 dark:bg-slate-900/50 border-slate-200 focus-visible:ring-indigo-500" 
                                                                />
                                                            </div>
                                                        </FormControl>
                                                        <FormMessage className="text-[10px]" />
                                                    </FormItem>
                                                )}
                                            />
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* TAXES SECTION */}
                            <div className="space-y-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 p-5">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Database className="h-4 w-4 text-indigo-600" />
                                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Configuración Fiscal</h3>
                                    </div>
                                    <FormField
                                        control={form.control}
                                        name="isGross"
                                        render={({ field }) => (
                                            <FormItem className="flex flex-row items-center gap-3 space-y-0 bg-white dark:bg-slate-950 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-800 shadow-sm">
                                                <FormLabel className="text-xs font-semibold cursor-pointer">{field.value ? "Tarifa bruta (se descuentan los impuestos)" : "Tarifa neta (sin deduccion)"}</FormLabel>
                                                <FormControl>
                                                    <Switch
                                                        checked={field.value}
                                                        onCheckedChange={field.onChange}
                                                        className="data-[state=checked]:bg-indigo-600"
                                                    />
                                                </FormControl>
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                {form.watch("isGross") ? (
                                    <FormField
                                        control={form.control}
                                        name="taxOverrides"
                                        render={({ field }) => (
                                            <FormItem>
                                                <TaxOverridesFields
                                                    companyTaxConfig={company.taxConfig || {}}
                                                    value={field.value || {}}
                                                    onChange={field.onChange}
                                                />
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                ) : (
                                    <div className="p-4 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 rounded-lg text-xs flex items-start gap-2">
                                        <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                        <p>En el modo <b>Sobre Neto</b>, el importe introducido en las tarifas es el que percibirá el usuario finalmente. Los impuestos no se restan de estas cantidades.</p>
                                    </div>
                                )}
                            </div>

                            <DialogFooter className="bg-slate-50 dark:bg-slate-900/80 p-4 -mx-6 -mb-6 border-t border-slate-100 dark:border-slate-800">
                                <Button type="button" variant="ghost" onClick={() => setOpen(false)} className="hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500">
                                    Cancelar
                                </Button>
                                <Button type="submit" disabled={mutation.isPending} className="bg-indigo-600 hover:bg-indigo-700 shadow-md transition-all">
                                    {mutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Database className="mr-2 h-4 w-4" />}
                                    Guardar Cambios
                                </Button>
                            </DialogFooter>
                        </form>
                    </Form>
                </div>
            </DialogContent>
        </Dialog>
    );
}
