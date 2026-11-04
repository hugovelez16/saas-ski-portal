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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { FileText, AlertCircle, Loader2 } from "lucide-react";
import { format, startOfMonth, endOfMonth, setMonth, setYear } from "date-fns";
import { mkConfig, generateCsv, download } from "export-to-csv";
import { getAllWorkLogs } from "@/lib/api/work-logs";
import { Company } from "@/lib/types";

interface ReportGenerationDialogProps {
    companies?: Company[];
    children?: React.ReactNode;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
}

export function ReportGenerationDialog({ companies = [], children, open, onOpenChange }: ReportGenerationDialogProps) {
    const [internalOpen, setInternalOpen] = useState(false);

    // Controlled vs Uncontrolled logic
    const isControlled = open !== undefined;
    const isOpen = isControlled ? open : internalOpen;
    const setIsOpen = isControlled ? onOpenChange : setInternalOpen;

    const [mode, setMode] = useState<"month" | "season">("month");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    // Month Mode State
    const currentYear = new Date().getFullYear();
    const [selectedMonth, setSelectedMonth] = useState<string>(new Date().getMonth().toString());
    const [selectedYear, setSelectedYear] = useState<string>(currentYear.toString());

    // Season Mode State
    const getInitialSeason = () => {
        const now = new Date();
        const month = now.getMonth();
        const year = now.getFullYear();
        if (month >= 6) return `${year}/${year + 1}`;
        return `${year - 1}/${year}`;
    };
    const [selectedSeason, setSelectedSeason] = useState<string>(getInitialSeason());

    const generateSeasons = () => {
        const seasons = [];
        for (let i = -4; i <= 1; i++) {
            const start = currentYear + i;
            seasons.push(`${start}/${start + 1}`);
        }
        return seasons;
    };

    const getSeasonRange = (seasonStr: string) => {
        const [startYearStr, endYearStr] = seasonStr.split('/');
        const startYear = parseInt(startYearStr);
        const endYear = parseInt(endYearStr);

        // Season definition: Nov 1st of startYear to May 31st of endYear
        const start = new Date(startYear, 10, 1); // Nov 1
        const end = new Date(endYear, 4, 31); // May 31
        return { start, end };
    };

    const handleGenerate = async () => {
        setError(null);
        setLoading(true);

        let start: Date;
        let end: Date;
        let filename = "";

        if (mode === "month") {
            start = startOfMonth(setMonth(setYear(new Date(), parseInt(selectedYear)), parseInt(selectedMonth)));
            end = endOfMonth(start);
            filename = `Report_${format(start, 'MMMM_yyyy')}`;
        } else {
            const range = getSeasonRange(selectedSeason);
            start = range.start;
            end = range.end;
            filename = `Report_Season_${selectedSeason.replace('/', '-')}`;
        }

        try {
            // Fetch records from API
            // Filas de detalle del rango completo (paginadas): el CSV necesita cada registro
            const logs = await getAllWorkLogs({
                startDate: format(start, 'yyyy-MM-dd'),
                endDate: format(end, 'yyyy-MM-dd')
            });

            if (!logs || logs.length === 0) {
                setError("No hay registros dentro del rango seleccionado.");
                setLoading(false);
                return;
            }

            // Generate CSV
            const csvConfig = mkConfig({
                useKeysAsHeaders: true,
                filename: filename
            });

            // Sort by date old -> new
            logs.sort((a, b) => {
                const dateA = a.date || a.startDate || a.createdAt;
                const dateB = b.date || b.startDate || b.createdAt;
                return new Date(dateA).getTime() - new Date(dateB).getTime();
            });

            const data = logs.map(log => {
                const dateStr = log.date || (log.startDate ? format(new Date(log.startDate), 'yyyy-MM-dd') : '') || '';
                const companyName = companies.find(c => c.id === log.companyId)?.name || log.companyId || 'N/A';

                return {
                    Date: dateStr,
                    Type: log.type,
                    Description: log.description || '',
                    Hours: log.durationHours || 0,
                    Rate: log.calculationSnapshot?.rate_applied || 0,
                    Total: log.amount || 0,
                    Client: log.extraData?.client || 'N/A',
                    Company: companyName
                };
            });

            const csv = generateCsv(csvConfig)(data);
            download(csvConfig)(csv);
            setIsOpen?.(false);
        } catch (e) {
            console.error(e);
            setError("Error al obtener los datos o generar el informe.");
        } finally {
            setLoading(false);
        }
    };

    const handleOpenChange = (val: boolean) => {
        setIsOpen?.(val);
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleOpenChange}>
            {children && (
                <DialogTrigger asChild>
                    {children}
                </DialogTrigger>
            )}
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Generar Informe</DialogTitle>
                    <DialogDescription>
                        Selecciona el rango de fechas para generar el informe de actividad.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    <RadioGroup defaultValue="month" value={mode} onValueChange={(v) => { setMode(v as "month" | "season"); setError(null); }} className="grid grid-cols-2 gap-4">
                        <div>
                            <RadioGroupItem value="month" id="month" className="peer sr-only" />
                            <Label
                                htmlFor="month"
                                className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                            >
                                <span className="mb-2 text-lg font-semibold">Mes</span>
                                <span className="text-sm text-muted-foreground text-center">Mes completo</span>
                            </Label>
                        </div>
                        <div>
                            <RadioGroupItem value="season" id="season" className="peer sr-only" />
                            <Label
                                htmlFor="season"
                                className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                            >
                                <span className="mb-2 text-lg font-semibold">Temporada</span>
                                <span className="text-sm text-muted-foreground text-center">Nov - May</span>
                            </Label>
                        </div>
                    </RadioGroup>

                    {mode === "month" ? (
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Mes</Label>
                                <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {Array.from({ length: 12 }).map((_, i) => (
                                            <SelectItem key={i} value={i.toString()}>
                                                {format(new Date(2000, i, 1), 'MMMM')}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label>Año</Label>
                                <Select value={selectedYear} onValueChange={setSelectedYear}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {Array.from({ length: 5 }).map((_, i) => (
                                            <SelectItem key={i} value={(currentYear - 2 + i).toString()}>
                                                {currentYear - 2 + i}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            <Label>Temporada</Label>
                            <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {generateSeasons().map((s) => (
                                        <SelectItem key={s} value={s}>
                                            Temporada {s}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">
                                Incluye desde el 1 de Noviembre hasta el 31 de Mayo.
                            </p>
                        </div>
                    )}

                    {error && (
                        <div className="flex items-center gap-2 p-3 text-sm text-red-600 bg-red-50 rounded-md border border-red-100 animate-in fade-in slide-in-from-top-1">
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button onClick={handleGenerate} className="w-full sm:w-auto" disabled={loading}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {loading ? "Generando..." : "Generar Informe"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
