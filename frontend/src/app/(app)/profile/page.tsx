"use client";
export const dynamic = "force-dynamic";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Building2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

import { useToast } from "@/hooks/use-toast";
import { getUserRates, updateUserRates, getCompanies } from "@/lib/api/settings";
import { getMyCompanies } from "@/lib/api/companies";
import { updateMe, changePassword } from "@/lib/api/users";
import { useAuth } from "@/context/AuthContext";
import { Company, CompanyMember } from "@/lib/types";

// User Info Form
const userFormSchema = z.object({
  firstName: z.string().min(2),
  lastName: z.string().min(2),
  defaultCompanyId: z.string().optional(),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, "Current password is required"),
  new_password: z.string().min(6, "New password must be at least 6 characters"),
  confirm_password: z.string().min(6, "Confirm password must be at least 6 characters"),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
});

const rateFormSchema = z.object({
  rates: z.record(z.coerce.number().min(0)).default({}),
  isGross: z.boolean().default(true),
  deductionSs: z.coerce.number().min(0).max(100).optional(),
  deductionIrpf: z.coerce.number().min(0).max(100).default(0),
  deductionExtra: z.coerce.number().min(0).max(100).default(0),
});

type RateFormValues = z.infer<typeof rateFormSchema>;

export default function ProfilePage() {
  const { user, checkAuth } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  // Queries



  const { data: myCompanies = [] } = useQuery({
    queryKey: ["myCompanies"],
    queryFn: getMyCompanies,
  });

  const activeCompanyId = user?.activeCompanyId;
  const currentCompany = myCompanies.find((c: Company) => c.id === activeCompanyId);
  const worklogDefinitions = currentCompany?.worklogDefinitions || {};

  const isCompanyManaged = Boolean(
    currentCompany?.settings?.is_managed || 
    (currentCompany as any)?.is_managed
  );
  const isWorker = !user?.isPlatformAdmin && currentCompany?.role !== "manager" && currentCompany?.role !== "admin";
  const canEditRates = !isCompanyManaged || !isWorker;

  const { data: rates, isLoading: isLoadingRates } = useQuery({
    queryKey: ["rates", activeCompanyId],
    queryFn: () => getUserRates(activeCompanyId as string),
    enabled: !!activeCompanyId,
  });

  // Forms
  const userForm = useForm({
    resolver: zodResolver(userFormSchema),
    defaultValues: {
      firstName: user?.firstName || "",
      lastName: user?.lastName || "",
      defaultCompanyId: user?.defaultCompanyId || "",
    }
  });

  const rateForm = useForm<RateFormValues>({
    resolver: zodResolver(rateFormSchema),
    defaultValues: {
      rates: {},
      isGross: false,
      deductionSs: undefined,
      deductionIrpf: 0,
      deductionExtra: 0,
    }
  });

  const passwordForm = useForm({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    }
  });

  // Sync user form
  useEffect(() => {
    if (user) {
      userForm.reset({
        firstName: user.firstName || "",
        lastName: user.lastName || "",
        defaultCompanyId: user.defaultCompanyId || "",
      });
    }
  }, [user?.id, userForm]);

  // Sync rate form
  useEffect(() => {
    if (rates && rates.length > 0) {
      const member = rates[0] as CompanyMember;
      const ratesConfig = member.ratesConfig || {};
      
      let isGross = false;
      let deductionSs: number | undefined = undefined;
      let deductionIrpf: number | undefined = undefined;
      let deductionExtra: number | undefined = undefined;
      
      const shiftKeys = Object.keys(worklogDefinitions || {});
      const shiftRates: Record<string, number> = {};
      
      let foundTaxes = false;
      
      for (const key of shiftKeys) {
         const shiftData = ratesConfig[key] as any;
         if (shiftData && typeof shiftData === 'object') {
             shiftRates[key] = shiftData.base_rate || 0;
             if (!foundTaxes) {
                 isGross = shiftData.is_gross !== undefined ? shiftData.is_gross : false;
                 if (shiftData.tax_overrides) {
                     deductionSs = (shiftData.tax_overrides.ss !== undefined && shiftData.tax_overrides.ss !== null) ? shiftData.tax_overrides.ss * 100 : undefined;
                     deductionIrpf = (shiftData.tax_overrides.irpf !== undefined && shiftData.tax_overrides.irpf !== null) ? shiftData.tax_overrides.irpf * 100 : undefined;
                     deductionExtra = (shiftData.tax_overrides.extra !== undefined && shiftData.tax_overrides.extra !== null) ? shiftData.tax_overrides.extra * 100 : undefined;
                     foundTaxes = true;
                 }
             }
         } else {
             shiftRates[key] = 0;
         }
      }

      rateForm.reset({
        rates: shiftRates,
        isGross,
        deductionSs,
        deductionIrpf,
        deductionExtra,
      });
    } else {
      rateForm.reset({
        rates: {},
        isGross: false,
        deductionSs: undefined,
        deductionIrpf: undefined,
        deductionExtra: undefined,
      });
    }
  }, [rates, rateForm, JSON.stringify(worklogDefinitions)]);

  // Mutations
  const userMutation = useMutation({
    mutationFn: (values: { firstName: string; lastName: string; defaultCompanyId?: string }) => updateMe(values),
    onSuccess: async () => {
      await checkAuth();
      toast({ title: "Profile updated" });
    },
    onError: () => toast({ title: "Failed to update profile", variant: "destructive" }),
  });

  const passwordMutation = useMutation({
    mutationFn: (values: any) => changePassword({
      current_password: values.current_password,
      new_password: values.new_password
    }),
    onSuccess: () => {
      toast({ title: "Password updated successfully" });
      passwordForm.reset();
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update password",
        description: error.response?.data?.detail || "Please check your current password",
        variant: "destructive"
      });
    },
  });


  const rateMutation = useMutation({
    mutationFn: (payload: any) => {
      const { companyId, ...data } = payload;
      return updateUserRates(companyId, user!.id, data);
    },
    onSuccess: () => {
      toast({ title: "Tarifas actualizadas correctamente" });
      queryClient.invalidateQueries({ queryKey: ["rates", activeCompanyId] });
      queryClient.invalidateQueries({ queryKey: ["myCompanies"] });
    },
    onError: (error: any) => {
      toast({ 
        title: "Error al actualizar las tarifas", 
        description: error.response?.data?.detail || "Asegúrate de que todos los valores son correctos.",
        variant: "destructive" 
      });
    },
  });

  function onRateSubmit(data: RateFormValues) {
    if (!activeCompanyId) {
      toast({ title: "Por favor, selecciona una empresa activa en el menú principal primero", variant: "destructive" });
      return;
    }

    if (!canEditRates) {
      toast({
        title: "Acción no permitida",
        description: "Esta empresa está en modo gestionado. Las tarifas son administradas por la dirección.",
        variant: "destructive"
      });
      return;
    }

    const member = rates && rates.length > 0 ? (rates[0] as CompanyMember) : null;
    const existingRatesConfig = member?.ratesConfig ? { ...member.ratesConfig } : {};

    const ratesConfig: Record<string, any> = { ...existingRatesConfig };
    const shiftKeys = Object.keys(worklogDefinitions || {});
    
    for (const key of shiftKeys) {
        ratesConfig[key] = {
            base_rate: data.rates[key] || 0,
            is_gross: data.isGross,
            tax_overrides: {
                ss: (data.deductionSs !== undefined && data.deductionSs !== null && !isNaN(data.deductionSs)) ? data.deductionSs / 100 : undefined,
                irpf: (data.deductionIrpf !== undefined && data.deductionIrpf !== null && !isNaN(data.deductionIrpf)) ? data.deductionIrpf / 100 : undefined,
                extra: (data.deductionExtra !== undefined && data.deductionExtra !== null && !isNaN(data.deductionExtra)) ? data.deductionExtra / 100 : undefined
            }
        };
    }

    const payload = {
      companyId: activeCompanyId,
      ratesConfig,
      existingSettings: member?.settings
    };

    rateMutation.mutate(payload);
  }

  function onUserSubmit(data: { firstName: string; lastName: string; defaultCompanyId?: string }) {
    userMutation.mutate(data);
  }

  if (isLoadingRates) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 md:gap-8 md:p-8">
      <div className="flex items-center justify-between">
        <h1 className="font-semibold text-lg md:text-2xl">Profile</h1>
        <Button variant="outline" onClick={() => router.push("/login")}>
          Logout
        </Button>
      </div>

      <div className="grid gap-6">
        {/* User Info Section */}
        <Card>
          <CardHeader>
            <CardTitle>User Information</CardTitle>
            <CardDescription>Update your personal details.</CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...userForm}>
              <form onSubmit={userForm.handleSubmit(onUserSubmit)} className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={userForm.control}
                  name="firstName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>First Name</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={userForm.control}
                  name="lastName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Last Name</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={userForm.control}
                  name="defaultCompanyId"
                  render={({ field }) => (
                    <FormItem className="md:col-span-2">
                      <FormLabel>Empresa de Inicio (Login)</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value || ""} disabled={myCompanies.length === 0}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Seleccionar empresa de inicio" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {myCompanies.map((c: any) => (
                            <SelectItem key={c.id} value={c.id}>
                              {c.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription>Esta empresa se seleccionará automáticamente al iniciar sesión si no eliges otra.</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="md:col-span-2">
                  <Button type="submit" disabled={userMutation.isPending}>
                    {userMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Save Details
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>

        {/* Password Change Section */}
        <Card>
          <CardHeader>
            <CardTitle>Change Password</CardTitle>
            <CardDescription>Ensure your account is using a long, random password to stay secure.</CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...passwordForm}>
              <form onSubmit={passwordForm.handleSubmit((data) => passwordMutation.mutate(data))} className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={passwordForm.control}
                  name="current_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Current Password</FormLabel>
                      <FormControl>
                        <Input type="password" placeholder="******" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="hidden md:block"></div> {/* Spacer */}

                <FormField
                  control={passwordForm.control}
                  name="new_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>New Password</FormLabel>
                      <FormControl>
                        <Input type="password" placeholder="******" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={passwordForm.control}
                  name="confirm_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Confirm New Password</FormLabel>
                      <FormControl>
                        <Input type="password" placeholder="******" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="md:col-span-2">
                  <Button type="submit" disabled={passwordMutation.isPending} variant="outline">
                    {passwordMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Update Password
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>

        <div className="space-y-6">

            {/* Rates Section */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Tarifas de la Empresa</CardTitle>
                    <CardDescription>
                      {canEditRates 
                        ? "Gestiona tus tarifas para la empresa activa."
                        : "Consulta las tarifas fijadas por la dirección (Modo Gestionado)."}
                    </CardDescription>
                  </div>
                  {isCompanyManaged && (
                    <Badge variant="secondary" className="bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                      Modo Gestionado
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {!activeCompanyId ? (
                  <div className="mb-6 text-center p-4 text-muted-foreground border rounded-md">
                    Selecciona una empresa en el menú principal para configurar tus tarifas.
                  </div>
                ) : (
                  <>
                    {currentCompany && (
                      <div className="mb-6 flex items-center justify-between px-4 py-3 bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900 rounded-lg">
                        <div className="flex items-center gap-2">
                          <Building2 className="h-5 w-5 text-indigo-600" />
                          <div>
                            <p className="text-sm font-medium text-indigo-900 dark:text-indigo-100">Empresa activa:</p>
                            <p className="text-lg font-bold text-indigo-700 dark:text-indigo-400">{currentCompany.name}</p>
                          </div>
                        </div>
                        {isCompanyManaged && (
                          <Badge variant="outline" className="border-amber-300 text-amber-700 dark:text-amber-300">
                            Tarifas fijadas por empresa
                          </Badge>
                        )}
                      </div>
                    )}

                    {isCompanyManaged && !canEditRates && (
                      <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-lg text-sm text-amber-800 dark:text-amber-200">
                        La administración de esta empresa gestiona directamente los convenios y tarifas. Los valores mostrados a continuación son exclusivamente de consulta.
                      </div>
                    )}

                    <Form {...rateForm}>
                      <form className="space-y-8" onSubmit={rateForm.handleSubmit(onRateSubmit)}>
                        <fieldset disabled={!canEditRates} className="space-y-8">
                          <div className="grid gap-4 md:grid-cols-2">
                            {Object.entries(worklogDefinitions || {}).map(([key, def]: [string, any]) => (
                              <FormField
                                key={key}
                                control={rateForm.control}
                                name={`rates.${key}`}
                                render={({ field }) => (
                                  <FormItem>
                                    <FormLabel>Tarifa para {def.label} (€)</FormLabel>
                                    <FormControl>
                                      <Input 
                                        type="number" 
                                        step="0.01" 
                                        disabled={!canEditRates}
                                        {...field} 
                                        value={field.value ?? ""} 
                                        onChange={e => field.onChange(e.target.value === "" ? undefined : parseFloat(e.target.value))} 
                                      />
                                    </FormControl>
                                    {def.is_range ? (
                                      <FormDescription>Se calculará por día</FormDescription>
                                    ) : def.unit === "fixed" ? (
                                      <FormDescription>Se calculará por evento fijo</FormDescription>
                                    ) : (
                                      <FormDescription>Se calculará por hora</FormDescription>
                                    )}
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                            ))}
                            {Object.keys(worklogDefinitions || {}).length === 0 && (
                              <div className="col-span-2 text-center p-4 text-muted-foreground border rounded-md">
                                La empresa no ha definido tipos de turnos todavía.
                              </div>
                            )}
                          </div>

                          <div className="space-y-4 border-t pt-4">
                            <div className="flex items-center justify-between">
                              <div className="space-y-0.5">
                                <h3 className="text-base font-semibold">Configuración de Impuestos</h3>
                                <p className="text-sm text-muted-foreground">Configura las retenciones para tus tarifas.</p>
                              </div>
                              <FormField
                                control={rateForm.control}
                                name="isGross"
                                render={({ field }) => (
                                  <FormItem className="flex flex-row items-center gap-2 space-y-0">
                                    <FormLabel className="text-base">Precios en Bruto</FormLabel>
                                    <FormControl>
                                      <Switch
                                        disabled={!canEditRates}
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                      />
                                    </FormControl>
                                  </FormItem>
                                )}
                              />
                            </div>

                            {rateForm.watch("isGross") && (
                              <div className="grid gap-4 md:grid-cols-3">
                                <FormField
                                  control={rateForm.control}
                                  name="deductionSs"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormLabel>Seguridad Social (SS) (%)</FormLabel>
                                      <FormControl>
                                        <Input
                                          type="number"
                                          step="0.0001"
                                          disabled={!canEditRates}
                                          placeholder={(currentCompany as any)?.taxConfig?.social_security ? `Por Defecto: ${((currentCompany as any).taxConfig.social_security * 100).toFixed(2)}` : "0"}
                                          {...field}
                                          value={field.value ?? ""}
                                          onChange={e => field.onChange(e.target.value === "" ? undefined : Number(e.target.value))}
                                        />
                                      </FormControl>
                                      <FormDescription>
                                        Déjalo en blanco para valor por defecto ({(currentCompany as any)?.taxConfig?.social_security ? ((currentCompany as any).taxConfig.social_security * 100).toFixed(2) : 0}%)
                                      </FormDescription>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />
                                <FormField
                                  control={rateForm.control}
                                  name="deductionIrpf"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormLabel>IRPF (%)</FormLabel>
                                      <FormControl>
                                        <Input 
                                          type="number" 
                                          step="0.01" 
                                          disabled={!canEditRates}
                                          {...field} 
                                          value={field.value ?? ""} 
                                          onChange={e => field.onChange(e.target.value === "" ? undefined : parseFloat(e.target.value))} 
                                        />
                                      </FormControl>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />
                                <FormField
                                  control={rateForm.control}
                                  name="deductionExtra"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormLabel>Extra (%)</FormLabel>
                                      <FormControl>
                                        <Input 
                                          type="number" 
                                          step="0.01" 
                                          disabled={!canEditRates}
                                          {...field} 
                                          value={field.value ?? ""} 
                                          onChange={e => field.onChange(e.target.value === "" ? undefined : parseFloat(e.target.value))} 
                                        />
                                      </FormControl>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />
                              </div>
                            )}
                          </div>
                        </fieldset>

                        {canEditRates && (
                          <Button disabled={rateMutation.isPending} type="submit">
                            {rateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Guardar Tarifas
                          </Button>
                        )}
                      </form>
                    </Form>
                  </>
                )}
              </CardContent>
            </Card>

        </div>
      </div>
    </div>
  );
}
