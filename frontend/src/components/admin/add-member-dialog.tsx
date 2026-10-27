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
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addCompanyMember } from "@/lib/api/companies";
import { getUsers } from "@/lib/api/users";
import { useToast } from "@/hooks/use-toast";
import { UserPlus, Loader2 } from "lucide-react";
import { CompanyMemberResponse } from "@/lib/types";

const formSchema = z.object({
    email: z.string().email("Invalid email address"),
});

interface AddMemberDialogProps {
    companyId: string;
    companyName: string;
    existingMembers?: CompanyMemberResponse[];
}

export function AddMemberDialog({ companyId, companyName, existingMembers = [] }: AddMemberDialogProps) {
    const [open, setOpen] = useState(false);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const { data: users = [], isLoading: isLoadingUsers } = useQuery({
        queryKey: ["users"],
        queryFn: getUsers,
        enabled: open, // Only fetch when dialog opens
    });

    // Filter users: Exclude those who are already active members
    // We want to show: Non-members AND Inactive members
    const eligibleUsers = users.filter(user => {
        const member = existingMembers.find(m => m.userId === user.id);
        if (!member) return true; // Not in company -> Eligible
        return member.status === 'rejected'; // In company but rejected -> Eligible
    });

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            email: "",
        },
    });

    const mutation = useMutation({
        mutationFn: ({ email }: { email: string }) => addCompanyMember(companyId, email),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            setOpen(false);
            form.reset();
            toast({
                title: "Member added",
                description: `User added to ${companyName} successfully.`,
            });
        },
        // El error HTTP lo muestra el interceptor de lib/api.ts.
    });

    function onSubmit(values: z.infer<typeof formSchema>) {
        mutation.mutate(values);
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button size="sm" variant="outline" className="gap-2">
                    <UserPlus className="h-4 w-4" />
                    Add Member
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Add Member to {companyName}</DialogTitle>
                    <DialogDescription>
                        Select a user to add to this company from the list below.
                    </DialogDescription>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={form.control}
                            name="email"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>User</FormLabel>
                                    <Select
                                        onValueChange={field.onChange}
                                        defaultValue={field.value}
                                        disabled={isLoadingUsers}
                                    >
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder={isLoadingUsers ? "Loading users..." : "Select a user"} />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {eligibleUsers.length === 0 ? (
                                                <div className="p-2 text-sm text-center text-muted-foreground">
                                                    No eligible users found.
                                                </div>
                                            ) : (
                                                eligibleUsers.map((user) => {
                                                    const isRejected = existingMembers.some(m => m.userId === user.id && m.status === 'rejected');
                                                    return (
                                                        <SelectItem key={user.id} value={user.email}>
                                                            {user.firstName} {user.lastName} ({user.email})
                                                            {isRejected && " (Rejected)"}
                                                        </SelectItem>
                                                    );
                                                })
                                            )}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <DialogFooter>
                            <Button type="submit" disabled={mutation.isPending || eligibleUsers.length === 0}>
                                {mutation.isPending ? "Adding..." : "Add Member"}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
