"use client";

import * as React from "react";
import { FileJson } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";

interface ReadOnlyJsonButtonProps {
    title: string;
    value: unknown;
    description?: string;
}

/** Boton de solo lectura para que el administrador de plataforma consulte el JSON guardado (R-EMP-42). */
export function ReadOnlyJsonButton({ title, value, description }: ReadOnlyJsonButtonProps) {
    const formatted = React.useMemo(() => JSON.stringify(value ?? {}, null, 2), [value]);

    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button type="button" variant="outline" size="sm">
                    <FileJson className="mr-2 h-4 w-4" />
                    Ver JSON
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[640px] max-h-[85vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>
                        {description || "Vista en solo lectura de la configuracion guardada en JSON."}
                    </DialogDescription>
                </DialogHeader>
                <pre
                    tabIndex={0}
                    aria-label={`JSON de ${title}`}
                    className="mt-2 max-h-[60vh] overflow-auto rounded-md border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-slate-100"
                >
                    {formatted}
                </pre>
            </DialogContent>
        </Dialog>
    );
}
