"use client";

import { useState } from "react";
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
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Settings2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateMemberSettings } from "@/lib/api/companies";

interface MemberSettingsDialogProps {
    companyId: string;
    userId: string;
    memberName: string;
    initialSettings: any;
}

export function MemberSettingsDialog({ companyId, userId, memberName, initialSettings }: MemberSettingsDialogProps) {
    const [open, setOpen] = useState(false);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const currentSettings = initialSettings || {};

    // For members, we might want to default to "Company Default" (null/undefined) vs explicit True/False?
    // But for simplicity, let's allow them to Force Disable.
    // If we want tri-state (Default/Enabled/Disabled), we need a Select or 3-state value.
    // User request: "disable things".
    // So let's implement "Disable X" switches.
    // Or better: "Enable X?" checks. If UNCHECKED, it means disabled for this user even if company enabled it.

    // Default logic: If undefined, it follows company settings.
    // But how to represent "Follow Company" vs "Force Disable"?
    // The user asked "panel... related to a user and I can disable things".
    // So explicit "Allowed for this user".
    // If I save explicit false, it overrides.

    // Let's rely on the previous assumption: `effective = company && user`.
    // So user settings default to TRUE (or undefined which treated as true).
    // If I toggle OFF, I save `false`.

    const [allowTutorial, setAllowTutorial] = useState(currentSettings.allow_tutorial !== false);
    const [allowCoordination, setAllowCoordination] = useState(currentSettings.allow_coordination !== false);

    const mutation = useMutation({
        mutationFn: (data: any) => updateMemberSettings(companyId, userId, data.settings),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["companiesDetailed"] });
            toast({ title: "Member settings updated" });
            setOpen(false);
        },
        onError: () => {
            toast({ title: "Failed to update member settings", variant: "destructive" });
        }
    });

    const handleSave = () => {
        const newSettings = {
            ...currentSettings,
            allow_tutorial: allowTutorial,
            allow_coordination: allowCoordination,
        };
        mutation.mutate({ settings: newSettings });
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-gray-900">
                    <Settings2 className="h-4 w-4" />
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Settings for {memberName}</DialogTitle>
                    <DialogDescription>
                        Override permissions for this user. Disabling here restricts the user regardless of company settings.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="flex items-center justify-between space-x-2">
                        <Label htmlFor="mem_allow_tutorial" className="flex flex-col space-y-1">
                            <span>Allow Tutorial</span>
                            <span className="font-normal text-xs text-muted-foreground">User can log 'Tutorial' days.</span>
                        </Label>
                        <Switch id="mem_allow_tutorial" checked={allowTutorial} onCheckedChange={setAllowTutorial} />
                    </div>

                    <div className="flex items-center justify-between space-x-2">
                        <Label htmlFor="mem_allow_coordination" className="flex flex-col space-y-1">
                            <span>Allow Coordination</span>
                            <span className="font-normal text-xs text-muted-foreground">User can add 'Coordination'.</span>
                        </Label>
                        <Switch id="mem_allow_coordination" checked={allowCoordination} onCheckedChange={setAllowCoordination} />
                    </div>
                </div>
                <DialogFooter>
                    <Button type="submit" onClick={handleSave} disabled={mutation.isPending}>
                        Save changes
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
