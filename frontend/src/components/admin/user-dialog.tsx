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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { createUser } from "@/lib/api/users";
import { getCompanies } from "@/lib/api/companies";
import { useToast } from "@/hooks/use-toast";
import { Plus, Mail, User, Shield, UserPlus, CheckCircle2, Activity, Building } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { CompanyResponse } from "@/lib/types";

const formSchema = z.object({
    email: z.string().email("Please enter a valid email address"),
    firstName: z.string().min(2, "First name must be at least 2 characters"),
    lastName: z.string().min(2, "Last name must be at least 2 characters"),
    role: z.enum(["admin", "user"]),
    isActive: z.boolean().default(true),
    company_id: z.string().min(1, "Please select a company or 'No company'"),
    send_email: z.boolean().default(true),
});

export function UserDialog() {
    const [open, setOpen] = useState(false);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            email: "",
            firstName: "",
            lastName: "",
            role: "user",
            isActive: true,
            company_id: "none",
            send_email: true,
        },
    });

    const { data: companies = [] } = useQuery({
        queryKey: ["companies"],
        queryFn: getCompanies,
        enabled: open,
    });

    const mutation = useMutation({
        mutationFn: (values: z.infer<typeof formSchema>) =>
            createUser(values),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
            setOpen(false);
            form.reset();
            toast({
                title: "User created successfully",
                description: "The new user has been added to the system.",
            });
        },
        // El error HTTP lo muestra el interceptor de lib/api.ts.
    });

    function onSubmit(values: z.infer<typeof formSchema>) {
        const payload = {
            ...values,
            companyId: values.company_id === "none" ? null : values.company_id,
            sendEmail: values.send_email,
        };
        mutation.mutate(payload);
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg transition-all duration-200 hover:scale-105 active:scale-95">
                    <Plus className="mr-2 h-4 w-4" />
                    Add New User
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px] p-0 overflow-hidden rounded-xl border-none shadow-2xl">
                <div className="bg-gradient-to-br from-primary/10 via-background to-background p-6">
                    <DialogHeader className="mb-6">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-primary/10 rounded-lg text-primary">
                                <UserPlus className="h-6 w-6" />
                            </div>
                            <div>
                                <DialogTitle className="text-2xl font-bold tracking-tight">Create User</DialogTitle>
                                <DialogDescription className="text-muted-foreground">
                                    Define the core identity and permissions for the new member.
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>

                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="firstName"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                                <User className="h-3.5 w-3.5 text-muted-foreground" />
                                                First Name
                                            </FormLabel>
                                            <FormControl>
                                                <Input 
                                                    placeholder="e.g. John" 
                                                    className="bg-background/50 border-muted-foreground/20 focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                                                    {...field} 
                                                />
                                            </FormControl>
                                            <FormMessage className="text-xs" />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="lastName"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                                <User className="h-3.5 w-3.5 text-muted-foreground" />
                                                Last Name
                                            </FormLabel>
                                            <FormControl>
                                                <Input 
                                                    placeholder="e.g. Doe" 
                                                    className="bg-background/50 border-muted-foreground/20 focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                                                    {...field} 
                                                />
                                            </FormControl>
                                            <FormMessage className="text-xs" />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control}
                                name="email"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                            <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                                            Email Address
                                        </FormLabel>
                                        <FormControl>
                                            <Input 
                                                type="email"
                                                placeholder="john.doe@example.com" 
                                                className="bg-background/50 border-muted-foreground/20 focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                                                {...field} 
                                            />
                                        </FormControl>
                                        <FormMessage className="text-xs" />
                                    </FormItem>
                                )}
                            />

                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="role"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                                <Shield className="h-3.5 w-3.5 text-muted-foreground" />
                                                System Role
                                            </FormLabel>
                                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                <FormControl>
                                                    <SelectTrigger className="bg-background/50 border-muted-foreground/20">
                                                        <SelectValue placeholder="Select role" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="user">Regular User</SelectItem>
                                                    <SelectItem value="admin">Administrator</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage className="text-xs" />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="isActive"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                                <Activity className="h-3.5 w-3.5 text-muted-foreground" />
                                                Active Status
                                            </FormLabel>
                                            <FormControl>
                                                <div className="flex items-center justify-between rounded-lg border border-muted-foreground/20 px-3 bg-background/50 h-[40px]">
                                                    <span className="text-sm text-muted-foreground">Enabled</span>
                                                    <Switch
                                                        checked={field.value}
                                                        onCheckedChange={field.onChange}
                                                    />
                                                </div>
                                            </FormControl>
                                            <FormMessage className="text-xs" />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="company_id"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                                <Building className="h-3.5 w-3.5 text-muted-foreground" />
                                                Company Link
                                            </FormLabel>
                                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                <FormControl>
                                                    <SelectTrigger className="bg-background/50 border-muted-foreground/20">
                                                        <SelectValue placeholder="No company (Personal)" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="none">No company (Personal)</SelectItem>
                                                    {companies.map((company: CompanyResponse) => (
                                                        <SelectItem key={company.id} value={company.id}>
                                                            {company.name}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage className="text-xs" />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="send_email"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                                <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                                                Welcome Email
                                            </FormLabel>
                                            <FormControl>
                                                <div className="flex items-center justify-between rounded-lg border border-muted-foreground/20 px-3 bg-background/50 h-[40px]">
                                                    <span className="text-sm text-muted-foreground">Notify User</span>
                                                    <Switch
                                                        checked={field.value}
                                                        onCheckedChange={field.onChange}
                                                    />
                                                </div>
                                            </FormControl>
                                            <FormMessage className="text-xs" />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <DialogFooter className="pt-4 border-t border-muted-foreground/10 gap-2 sm:gap-0">
                                <Button 
                                    type="button" 
                                    variant="ghost" 
                                    onClick={() => setOpen(false)}
                                    className="hover:bg-muted"
                                >
                                    Cancel
                                </Button>
                                <Button 
                                    type="submit" 
                                    disabled={mutation.isPending}
                                    className="min-w-[120px] bg-primary relative overflow-hidden group transition-all"
                                >
                                    <AnimatePresence mode="wait">
                                        {mutation.isPending ? (
                                            <motion.span
                                                key="loading"
                                                initial={{ opacity: 0, y: 10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0, y: -10 }}
                                                className="flex items-center"
                                            >
                                                Creating...
                                            </motion.span>
                                        ) : (
                                            <motion.span
                                                key="idle"
                                                initial={{ opacity: 0, y: 10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0, y: -10 }}
                                                className="flex items-center gap-2"
                                            >
                                                <CheckCircle2 className="h-4 w-4" />
                                                Create User
                                            </motion.span>
                                        )}
                                    </AnimatePresence>
                                </Button>
                            </DialogFooter>
                        </form>
                    </Form>
                </div>
            </DialogContent>
        </Dialog>
    );
}
