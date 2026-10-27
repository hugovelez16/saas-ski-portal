import React, { useState, useEffect } from 'react';
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Switch } from "@/components/ui/switch";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar-rac";
import { RangeCalendar } from "@/components/ui/calendar-rac";
import { Calendar as CalendarIcon } from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from 'date-fns/locale';
import { cn } from "@/lib/utils";
import { parseDate } from "@internationalized/date";
import type { DateValue } from "react-aria-components";
import type { WorkLogCreate } from "@/lib/types";
import { useAuth } from "@/context/AuthContext";

import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

interface WorkLogFormProps {
    formData: Partial<WorkLogCreate>;
    setFormData: React.Dispatch<React.SetStateAction<Partial<WorkLogCreate>>>;
    logType: string;
    setLogType: (type: string) => void;
    companies: any[];
    hideCompanySelector?: boolean;
}

export function WorkLogForm({ formData, setFormData, logType, setLogType, companies, hideCompanySelector }: WorkLogFormProps) {
    const [isCalendarOpen, setIsCalendarOpen] = useState(false);
    const { user } = useAuth();

    const selectedCompany = companies.find(c => c.id === formData.companyId);

    // SaaS JSON Driven Definitions
    // Example: { "particular": { "label": "Particular", "fields": ["description", "client"], "options": ["coordination"] } }
    const worklogDefinitions = React.useMemo(() => {
        return selectedCompany?.worklogDefinitions || {
            "particular": { "label": "Particular", "fields": ["description"], "options": [] }
        };
    }, [selectedCompany?.worklogDefinitions]);

    const currentDefinition = worklogDefinitions[logType] || null;

    useEffect(() => {
        console.log("DEBUG: WorkLogForm Render", {
            companyName: selectedCompany?.name,
            logType,
            availableDefs: Object.keys(worklogDefinitions),
            currentDefinitionFields: currentDefinition?.fields,
            hasDescription: currentDefinition?.fields?.includes('description')
        });
    }, [selectedCompany, logType, worklogDefinitions, currentDefinition]);

    useEffect(() => {
        if (companies.length > 0 && !formData.companyId) {
            // SaaS Context Driven: Always prefer active company from JWT context
            const targetId = user?.activeCompanyId || companies[0].id;

            if (targetId) {
                setFormData(prev => ({ ...prev, companyId: targetId }));
            }
        }
    }, [companies, formData.companyId, user?.activeCompanyId, setFormData]);

    // Ensure valid logType when company changes or mounts
    useEffect(() => {
        const availableKeys = Object.keys(worklogDefinitions);
        if (availableKeys.length > 0 && (!logType || !availableKeys.includes(logType))) {
            setLogType(availableKeys[0]);
        }
    }, [worklogDefinitions, logType, setLogType]);

    // Reset extra boolean fields when type changes so we don't bleed options between shift types
    useEffect(() => {
        setFormData(prev => {
            const next = { ...prev, arrivesPrior: false, hasNight: false, hasCoordination: false };
            if (currentDefinition?.unit === 'fixed') {
                next.startTime = null;
                next.endTime = null;
            }
            return next;
        });
    }, [logType, setFormData, currentDefinition]);

    const handleCompanyChange = (value: string) => {
        setFormData(prev => ({ ...prev, companyId: value }));
    };

    const handleDateChange = (field: 'date' | 'startDate' | 'endDate', value: DateValue) => {
        if (value) {
            setFormData(prev => ({ ...prev, [field]: value.toString() }));
        }
    };

    const handleRangeChange = (range: { start: DateValue, end: DateValue } | null) => {
        if (range) {
            setFormData(prev => ({
                ...prev,
                startDate: range.start.toString(),
                endDate: range.end.toString()
            }));
            if (range.end) {
                setIsCalendarOpen(false);
            }
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSwitchChange = (name: keyof WorkLogCreate, checked: boolean) => {
        setFormData(prev => ({ ...prev, [name]: checked }));
    };

    // Helper features check based on current definition array
    const hasOption = (opt: string) => {
        return currentDefinition?.options?.includes(opt) || false;
    };

    const isRange = currentDefinition?.unit === "days"; // unidad en dias: el turno es un rango de fechas
    const isFixed = currentDefinition?.unit === "fixed";

    return (
        <div className="grid gap-4 py-4">
            {!hideCompanySelector && (!user?.activeCompanyId || user?.isPlatformAdmin) && (
                <div className="grid grid-cols-1 sm:grid-cols-4 items-center gap-2 sm:gap-4">
                    <Label className="text-left sm:text-right">Empresa</Label>
                    <Select value={formData.companyId} onValueChange={handleCompanyChange}>
                        <SelectTrigger className="w-full sm:col-span-3">
                            <SelectValue placeholder="Selecciona una empresa" />
                        </SelectTrigger>
                        <SelectContent>
                            {companies.filter(c => c.id).map((c) => (
                                <SelectItem key={c.id} value={c.id}>
                                    {c.name}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            )}

            {Object.keys(worklogDefinitions).length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-4 items-center gap-2 sm:gap-4">
                    <Label className="text-left sm:text-right">Tipo</Label>
                    <RadioGroup value={logType} className="sm:col-span-3 flex gap-4" onValueChange={setLogType}>
                        {Object.entries(worklogDefinitions).map(([key, def]: [string, any]) => (
                            <div key={key} className="flex items-center space-x-2">
                                <RadioGroupItem value={key} id={`type_${key}`} />
                                <Label htmlFor={`type_${key}`}>{def.label || key}</Label>
                            </div>
                        ))}
                    </RadioGroup>
                </div>
            )}

            {!isRange ? (
                <>
                    <div className="grid grid-cols-1 sm:grid-cols-4 items-center gap-2 sm:gap-4">
                        <Label htmlFor="date" className="text-left sm:text-right">Fecha</Label>
                        <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
                            <PopoverTrigger asChild>
                                <Button
                                    variant={"outline"}
                                    className={cn("w-full sm:col-span-3 justify-start text-left font-normal truncate", !formData.date && "text-muted-foreground")}
                                >
                                    <CalendarIcon className="mr-2 h-4 w-4 flex-shrink-0" />
                                    {formData.date ? format(new Date(formData.date), "PPP", { locale: es }) : <span>Elige una fecha</span>}
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0">
                                <Calendar
                                    value={formData.date ? parseDate(formData.date) : undefined as any}
                                    onChange={(d: any) => { handleDateChange('date', d); setIsCalendarOpen(false); }}
                                />
                            </PopoverContent>
                        </Popover>
                    </div>
                    {!isFixed && (
                        <>
                            <div className="grid grid-cols-1 sm:grid-cols-4 items-center gap-2 sm:gap-4">
                                <Label htmlFor="startTime" className="text-left sm:text-right">Hora Inicio</Label>
                                <Input id="startTime" name="startTime" type="time" className="w-full sm:col-span-3" value={formData.startTime || ''} onChange={handleInputChange} />
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-4 items-center gap-2 sm:gap-4">
                                <Label htmlFor="endTime" className="text-left sm:text-right">Hora Fin</Label>
                                <Input id="endTime" name="endTime" type="time" className="w-full sm:col-span-3" value={formData.endTime || ''} onChange={handleInputChange} />
                            </div>
                        </>
                    )}
                </>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-4 items-center gap-2 sm:gap-4">
                    <Label className="text-left sm:text-right">Rango de Fechas</Label>
                    <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
                        <PopoverTrigger asChild>
                            <Button
                                variant={"outline"}
                                className={cn("w-full sm:col-span-3 justify-start text-left font-normal truncate", (!formData.startDate || !formData.endDate) && "text-muted-foreground")}
                            >
                                <CalendarIcon className="mr-2 h-4 w-4 flex-shrink-0" />
                                {formData.startDate && formData.endDate ? (
                                    <>
                                        {format(parseISO(formData.startDate), "PPP", { locale: es })} -{" "}
                                        {format(parseISO(formData.endDate), "PPP", { locale: es })}
                                    </>
                                ) : (
                                    <span>Selecciona un rango</span>
                                )}
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                            <RangeCalendar
                                value={formData.startDate && formData.endDate ? { start: parseDate(formData.startDate), end: parseDate(formData.endDate) } : null as any}
                                onChange={(range: any) => handleRangeChange(range)}
                            />
                        </PopoverContent>
                    </Popover>
                </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-4 items-center gap-2 sm:gap-4">
                <Label htmlFor="description" className="text-left sm:text-right">Descripción</Label>
                <Input
                    id="description"
                    name="description"
                    className="w-full sm:col-span-3"
                    value={formData.description || ''}
                    onChange={handleInputChange}
                    placeholder="Descripción general"
                />
            </div>

            {currentDefinition?.fields?.map((fieldName: string) => (
                <div key={fieldName} className="grid grid-cols-1 sm:grid-cols-4 items-center gap-2 sm:gap-4">
                    <Label htmlFor={fieldName} className="text-left sm:text-right">{fieldName}</Label>
                    <Input
                        id={fieldName}
                        name={fieldName}
                        className="w-full sm:col-span-3"
                        value={formData.extraData?.datos?.[fieldName] || ''}
                        onChange={(e) => {
                            const val = e.target.value;
                            setFormData(prev => ({
                                ...prev,
                                extraData: {
                                    ...(prev.extraData || {}),
                                    datos: {
                                        ...(prev.extraData?.datos || {}),
                                        [fieldName]: val
                                    }
                                }
                            }));
                        }}
                        placeholder={fieldName}
                    />
                </div>
            ))}

            {currentDefinition?.options?.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-4 items-start gap-2 sm:gap-4">
                    <Label className="text-left sm:text-right pt-0 sm:pt-2">Opciones</Label>
                    <div className="sm:col-span-3 space-y-2">
                        {currentDefinition.options.map((optionName: string) => (
                            <div key={optionName} className="flex items-center space-x-2">
                                <Switch
                                    id={`opt_${optionName}`}
                                    checked={formData.extraData?.opciones?.[optionName] || false}
                                    onCheckedChange={(checked) => {
                                        setFormData(prev => ({
                                            ...prev,
                                            extraData: {
                                                ...(prev.extraData || {}),
                                                opciones: {
                                                    ...(prev.extraData?.opciones || {}),
                                                    [optionName]: checked
                                                }
                                            }
                                        }));
                                    }}
                                />
                                <Label htmlFor={`opt_${optionName}`}>{optionName}</Label>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

