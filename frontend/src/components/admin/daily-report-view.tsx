"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getWorkLogs } from "@/lib/api/work-logs";
import { getCompanyMembers } from "@/lib/api/companies";
import { format, addDays, startOfDay, endOfDay, isSameDay, parseISO } from "date-fns";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface DailyReportViewProps {
    companyId: string;
}

export function DailyReportView({ companyId }: DailyReportViewProps) {
    const router = useRouter();
    const [date, setDate] = useState<Date>(new Date());
    const [sortMode, setSortMode] = useState<"default" | "name">("default");

    // Format date for API (YYYY-MM-DD)
    const dateStr = format(date, "yyyy-MM-dd");

    const { data: members = [], isLoading: loadingMembers } = useQuery({
        queryKey: ["companyMembers", companyId],
        queryFn: () => getCompanyMembers(companyId), // This needs to exist or use the one from detailed company query logic
    });

    // Note: getCompanyMembers might not be exported or might need status filter. 
    // We reused the one from company page logic which calls getCompaniesDetailed usually.
    // Ideally we use a direct call. I'll assume we can pass members as prop or fetch them.
    // The previous file imported `getCompaniesDetailed` and filtered.
    // Let's use `getCompanyMembers` API which I saw in api/companies.ts BUT it takes (id, status).
    // Let's fetch ALL members.

    // Fetch logs for the selected date
    const { data: logs = [], isLoading: loadingLogs } = useQuery({
        queryKey: ["workLogs", companyId, dateStr],
        queryFn: () => getWorkLogs({
            companyId: companyId,
            startDate: dateStr,
            endDate: dateStr
        }),
    });

    // Process Data
    const hours = Array.from({ length: 12 }, (_, i) => i + 8); // 8 to 19 (19 is end of 18:00-19:00 block? or inclusive point?)
    // 8,9,10,11,12,13,14,15,16,17,18,19. Total 12 points.

    // Sorting Logic
    const sortedMembers = useMemo(() => {
        let sorted = [...members];
        if (sortMode === 'default') {
            // Active Workers > Inactive Workers > Managers
            sorted.sort((a, b) => {
                const score = (m: any) => {
                    if (m.role === 'manager') return 3;
                    if (m.status === 'active') return 1;
                    return 2; // Inactive worker
                };
                return score(a) - score(b);
            });
        } else {
            sorted.sort((a, b) => (a.user?.firstName || "").localeCompare(b.user?.firstName || ""));
        }
        return sorted;
    }, [members, sortMode]);

    if (loadingMembers || loadingLogs) return <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b pb-4">
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="icon" onClick={() => setDate(addDays(date, -1))}>
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Popover>
                        <PopoverTrigger asChild>
                            <Button variant="outline" className={cn("w-[240px] justify-start text-left font-normal", !date && "text-muted-foreground")}>
                                <CalendarIcon className="mr-2 h-4 w-4" />
                                {date ? format(date, "PPP") : <span>Pick a date</span>}
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                            <Calendar mode="single" selected={date} onSelect={(d) => d && setDate(d)} initialFocus />
                        </PopoverContent>
                    </Popover>
                    <Button variant="outline" size="icon" onClick={() => setDate(addDays(date, 1))}>
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>

                <Button variant="ghost" size="sm" onClick={() => setSortMode(prev => prev === 'default' ? 'name' : 'default')}>
                    <ArrowUpDown className="mr-2 h-4 w-4" />
                    Sort: {sortMode === 'default' ? 'Role/Status' : 'Name'}
                </Button>
            </div>

            <div className="border rounded-lg overflow-x-auto relative">
                <div className="min-w-[800px]">
                    {/* Header Row */}
                    <div className="flex border-b bg-muted/50">
                        <div className="w-48 p-2 font-medium shrink-0 sticky left-0 bg-background z-10 border-r">User</div>
                        <div className="flex-1 grid grid-cols-12 divide-x">
                            {hours.map(h => (
                                <div key={h} className="text-sm text-center py-2 text-muted-foreground">
                                    {h}:00
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Member Rows */}
                    <div className="divide-y">
                        {sortedMembers.map(member => {
                            const userLogs = logs.filter((l: any) => l.userId === member.userId);

                            return (
                                <div key={member.userId} className="flex hover:bg-muted/20 transition-colors group">
                                    {/* User Name Cell */}
                                    <div
                                        className="w-48 p-2 shrink-0 flex items-center gap-2 sticky left-0 bg-background z-10 border-r cursor-pointer hover:underline"
                                        onClick={() => router.push(`/admin/users/${member.userId}`)}
                                    >
                                        <Avatar className="h-8 w-8">
                                            <AvatarFallback className="bg-primary/10 text-primary text-xs">
                                                {member.user?.firstName?.[0]}{member.user?.lastName?.[0]}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="overflow-hidden">
                                            <div className="font-medium text-sm truncate">{member.user?.firstName} {member.user?.lastName}</div>
                                            <div className="text-xs text-muted-foreground flex gap-1">
                                                {member.role === 'manager' && <Badge variant="secondary" className="text-[10px] px-1 h-4">Mgr</Badge>}
                                                {member.status !== 'active' && <Badge variant="destructive" className="text-[10px] px-1 h-4">{member.status}</Badge>}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Timeline Cells */}
                                    <div className="flex-1 grid grid-cols-12 relative h-12">
                                        {/* Grid Lines */}
                                        {hours.map((h, i) => (
                                            <div key={h} className="border-r h-full" />
                                        ))}

                                        {/* Render Work Logs */}
                                        {userLogs.map((log: any) => {
                                            // Calculate position
                                            let start = 8;
                                            let duration = 1;
                                            let isFullDay = false;

                                            if (log.startTime && log.endTime) {
                                                const [sh, sm] = log.startTime.split(':').map(Number);
                                                const [eh, em] = log.endTime.split(':').map(Number);

                                                const startDecimal = sh + sm / 60;
                                                const endDecimal = eh + em / 60;

                                                const clampedStart = Math.min(Math.max(startDecimal, 8), 19);
                                                const clampedEnd = Math.min(Math.max(endDecimal, 8), 19);

                                                start = clampedStart;
                                                duration = Math.max(clampedEnd - clampedStart, 0.4);
                                            } else {
                                                // Tutorial or whole day
                                                isFullDay = true;
                                                start = 8;
                                                duration = 11; // Full width
                                            }

                                            // Convert to percentage
                                            // Scale: 8 to 19 = 11 hours
                                            const totalHours = 11;
                                            const rawLeft = ((start - 8) / totalHours) * 100;
                                            const left = Math.min(Math.max(0, rawLeft), 96);
                                            const width = Math.min(Math.max(4, (duration / totalHours) * 100), 100 - left);

                                            return (
                                                <TooltipProvider key={log.id}>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <div
                                                                className={cn(
                                                                    "absolute top-1 bottom-1 rounded-sm border cursor-pointer hover:brightness-110 transition-all text-[10px] overflow-hidden px-1 flex items-center",
                                                                    isFullDay ? "bg-blue-100 border-blue-300 text-blue-800" : "bg-green-100 border-green-300 text-green-800"
                                                                )}
                                                                style={{
                                                                    left: `${Math.max(0, left)}%`,
                                                                    width: `${Math.min(100, width)}%`
                                                                }}
                                                                onClick={() => {
                                                                    // Visualizacion de parte
                                                                }}
                                                            >
                                                                {isFullDay ? "Full Day" : `${log.startTime}-${log.endTime}`}
                                                            </div>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            <div className="text-xs">
                                                                <p className="font-semibold">{log.type}</p>
                                                                <p>{log.startTime} - {log.endTime}</p>
                                                                <p>{log.description}</p>
                                                            </div>
                                                        </TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
