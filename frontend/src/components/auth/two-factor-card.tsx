"use client";

import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { activate2fa, disable2fa, setup2fa, TwoFactorSetup } from "@/lib/api/users";

type Mode = "activate" | "disable" | null;

export function twoFactorErrorMessage(err: unknown): string {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 429) return "Too many attempts. Wait a few minutes and try again.";
    if (status === 503) return "Verification service unavailable. Try again later.";
    if (status === 409) return "Two-factor authentication is already active.";
    return "Invalid or expired code.";
}

export function TwoFactorCard() {
    const { user, checkAuth } = useAuth();
    const { toast } = useToast();

    const [mode, setMode] = useState<Mode>(null);
    const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
    const [code, setCode] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const enabled = Boolean(user?.is2faEnabled);

    const close = () => {
        setMode(null);
        setSetup(null);
        setCode("");
        setError("");
    };

    const startActivation = async () => {
        setLoading(true);
        setError("");
        try {
            setSetup(await setup2fa());
            setMode("activate");
        } catch (err) {
            toast({ title: twoFactorErrorMessage(err), variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    const startDisable = () => {
        setError("");
        setCode("");
        setMode("disable");
    };

    const confirm = async () => {
        setLoading(true);
        setError("");
        try {
            if (mode === "activate") {
                await activate2fa(code);
                toast({ title: "Two-factor authentication enabled" });
            } else {
                await disable2fa(code);
                toast({ title: "Two-factor authentication disabled" });
            }
            await checkAuth();
            close();
        } catch (err) {
            setError(twoFactorErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between gap-2">
                    <CardTitle>Two-Factor Authentication</CardTitle>
                    <Badge variant={enabled ? "default" : "secondary"}>{enabled ? "Active" : "Inactive"}</Badge>
                </div>
                <CardDescription>
                    Protect your account with a 6-digit code from an authenticator app such as Google
                    Authenticator, Microsoft Authenticator or Authy.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {enabled ? (
                    <Button variant="outline" onClick={startDisable}>
                        Disable two-factor authentication
                    </Button>
                ) : (
                    <Button variant="outline" onClick={startActivation} disabled={loading}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Enable two-factor authentication
                    </Button>
                )}
            </CardContent>

            <Dialog open={mode !== null} onOpenChange={(open) => !open && close()}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {mode === "activate" ? "Enable two-factor authentication" : "Disable two-factor authentication"}
                        </DialogTitle>
                        <DialogDescription>
                            {mode === "activate"
                                ? "Scan the QR code with your authenticator app and enter the 6-digit code it shows."
                                : "Enter the current 6-digit code from your authenticator app to confirm."}
                        </DialogDescription>
                    </DialogHeader>

                    {mode === "activate" && setup && (
                        <div className="space-y-3">
                            <div className="flex justify-center rounded-md bg-white p-4">
                                <QRCodeSVG value={setup.qrCodeUri} size={176} />
                            </div>
                            <div className="space-y-1 text-center">
                                <p className="text-xs text-muted-foreground">Or enter this key manually:</p>
                                <code className="break-all text-sm font-mono">{setup.secret}</code>
                            </div>
                        </div>
                    )}

                    <div className="space-y-2">
                        <Label htmlFor="two-factor-code">Verification code</Label>
                        <Input
                            id="two-factor-code"
                            inputMode="numeric"
                            autoComplete="one-time-code"
                            maxLength={6}
                            placeholder="123456"
                            value={code}
                            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                        />
                        {error && <p className="text-sm font-medium text-red-500">{error}</p>}
                    </div>

                    <DialogFooter>
                        <Button variant="ghost" onClick={close} disabled={loading}>
                            Cancel
                        </Button>
                        <Button onClick={confirm} disabled={loading || code.length !== 6}>
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {mode === "activate" ? "Enable" : "Disable"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
