
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { DynamicBillingRow } from "@/lib/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/data-table";
import { useRouter } from "next/navigation";
import { User, Calculator } from "lucide-react";

interface BillingBreakdownDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    row: DynamicBillingRow | null;
    worklogDefs: Record<string, { unit: string; label: string }>;
}

export function BillingBreakdownDialog({ open, onOpenChange, row, worklogDefs }: BillingBreakdownDialogProps) {
    const router = useRouter();

    if (!row) return null;

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat("es-ES", {
            style: "currency",
            currency: "EUR",
        }).format(amount);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Calculator className="h-5 w-5" />
                        Desglose de Facturación
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="flex flex-col gap-1">
                        <span className="font-semibold text-lg">{row.userName}</span>
                        <span className="text-sm text-muted-foreground">{row.userEmail}</span>
                    </div>

                    <div className="border rounded-md">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Concepto</TableHead>
                                    <TableHead className="text-right">Cantidad</TableHead>
                                    <TableHead className="text-right">Importe</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {Object.entries(row.byType)
                                    .filter(([, summary]) => summary.quantity > 0 || summary.grossAmount > 0)
                                    .map(([typeKey, summary]) => {
                                        const def = worklogDefs[typeKey];
                                        const unit = def?.unit ?? 'hours';
                                        const label = def?.label ?? typeKey;
                                        const qtyStr = unit === 'hours'
                                            ? `${summary.quantity.toFixed(2)} h`
                                            : unit === 'fixed'
                                                ? `${summary.quantity} serv.`
                                                : `${summary.quantity} días`;
                                        const amount = summary.grossAmount ?? summary.netAmount ?? 0;
                                        return (
                                            <TableRow key={typeKey}>
                                                <TableCell className="font-medium">{label}</TableCell>
                                                <TableCell className="text-right">{qtyStr}</TableCell>
                                                <TableCell className="text-right">{formatCurrency(amount)}</TableCell>
                                            </TableRow>
                                        );
                                    })
                                }
                                <TableRow className="bg-muted/50 font-bold">
                                    <TableCell colSpan={2}>Total</TableCell>
                                    <TableCell className="text-right text-emerald-600">{formatCurrency(row.totalGross ?? row.totalNet ?? 0)}</TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </div>
                </div>

                <DialogFooter className="sm:justify-between gap-2">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Cerrar
                    </Button>
                    <Button onClick={() => router.push(`/manager/users/${row.userId}`)}>
                        <User className="mr-2 h-4 w-4" />
                        Ver Detalles de Usuario
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
