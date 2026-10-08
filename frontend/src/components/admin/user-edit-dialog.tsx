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
import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateUser, resetUser2fa } from "@/lib/api/users";
import { useToast } from "@/hooks/use-toast";
import { Pencil } from "lucide-react";
import { User } from "@/lib/types";

const formSchema = z.object({
    email: z.string().email(),
    firstName: z.string().min(2),
    lastName: z.string().min(2),
    role: z.enum(["admin", "user"]),
    password: z.string().min(6).optional().or(z.literal("")),
});

interface UserEditDialogProps {
    user: User;
    trigger?: React.ReactNode;
}

export function UserEditDialog({ user, trigger }: UserEditDialogProps) {
    const [open, setOpen] = useState(false);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            email: user.email,
            firstName: user.firstName || "",
            lastName: user.lastName || "",
            role: (user.role as "admin" | "user") || "user",
            password: "",
        },
    });

    useEffect(() => {
        form.reset({
            email: user.email,
            firstName: user.firstName || "",
            lastName: user.lastName || "",
            role: (user.role as "admin" | "user") || "user",
            password: "",
        });
    }, [user, form]);

    const mutation = useMutation({
        mutationFn: (values: z.infer<typeof formSchema>) => {
            const data: any = { ...values };
            if (!data.password) delete data.password; // Don't send empty string
            return updateUser(user.id, data);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
            queryClient.invalidateQueries({ queryKey: ["user"] });
            setOpen(false);
            toast({
                title: "User updated",
                description: "User details have been updated.",
            });
        },
        onError: (error: any) => {
            toast({
                title: "Error",
                description: error.response?.data?.detail || "Failed to update user.",
                variant: "destructive",
            });
        },
    });

    function onSubmit(values: z.infer<typeof formSchema>) {
        mutation.mutate(values);
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {trigger ? (
                    trigger
                ) : (
                    <Button size="sm" variant="ghost">
                        <Pencil className="h-4 w-4" />
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Edit User</DialogTitle>
                    <DialogDescription>
                        Modify user details.
                    </DialogDescription>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
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
                                control={form.control}
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
                        </div>

                        <FormField
                            control={form.control}
                            name="password"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>New Password (Optional)</FormLabel>
                                    <FormControl>
                                        <Input type="password" placeholder="Leave empty to keep current" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="flex justify-end -mt-2 mb-2">
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="text-xs h-8"
                                onClick={async () => {
                                    if (!confirm("Are you sure? This will generate a random password and email it to the user.")) return;
                                    try {
                                        const { resetPasswordEmail } = await import("@/lib/api/users");
                                        await resetPasswordEmail(user.id);
                                        toast({ title: "Email Sent", description: "New password sent to user's email." });
                                    } catch (e) {
                                        toast({ title: "Error", description: "Failed to send email.", variant: "destructive" });
                                    }
                                }}
                            >
                                <Pencil className="w-3 h-3 mr-1" />
                                Generate & Email Password
                            </Button>
                        </div>
                        {user.is2faEnabled && (
                            <div className="flex justify-end -mt-2 mb-2">
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="text-xs h-8"
                                    onClick={async () => {
                                        if (!confirm("Only reset 2FA after confirming the user's identity (call or message). This disables 2FA and signs the user out of all sessions. Continue?")) return;
                                        try {
                                            await resetUser2fa(user.id);
                                            queryClient.invalidateQueries({ queryKey: ["users"] });
                                            toast({ title: "2FA reset", description: "The user can enable 2FA again from their profile." });
                                        } catch (e) {
                                            toast({ title: "Error", description: "Failed to reset 2FA.", variant: "destructive" });
                                        }
                                    }}
                                >
                                    Reset 2FA
                                </Button>
                            </div>
                        )}
                        <FormField
                            control={form.control}
                            name="email"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Email</FormLabel>
                                    <FormControl>
                                        <Input {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="role"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Role</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select a role" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="user">User</SelectItem>
                                            <SelectItem value="admin">Admin</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <DialogFooter>
                            <Button type="submit" disabled={mutation.isPending}>
                                {mutation.isPending ? "Saving..." : "Save Changes"}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
