"use client";
export const dynamic = "force-dynamic";



import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import {
  type CalendarEvent,
  EventCalendar,
} from "@/components/event-calendar";
import { Button } from "@/components/ui/button";
import { WorkLogDetailsDialog } from "@/components/work-log/details-dialog";
import { getWorkLogs } from "@/lib/api/work-logs";
import { getUserRates } from "@/lib/api/settings";

import { useAuth } from "@/context/AuthContext";
import { UserCreateWorkLogDialog } from "@/components/work-log/user-dialog";
import { usePermissions } from "@/hooks/use-permissions";

export default function CalendarPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { canCreateWorkLog, role, isManaged } = usePermissions();
  const [selectedLogs, setSelectedLogs] = useState<any[]>([]);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Fetch work logs
  const { data: workLogs = [], refetch: refetchWorkLogs } = useQuery({
    queryFn: () => getWorkLogs(),
    queryKey: ["workLogs"],
  });

  // Fetch user rates
  const { data: userRates = [] } = useQuery({
    queryFn: () => getUserRates(),
    queryKey: ["userRates"],
  });

  const events = useMemo(() => {
    return workLogs.map((log: any) => {
      // Default: treated as allDay unless we have specific times for 'particular' type
      let allDay = true;
      let startTime = new Date(log.date || log.startDate);
      let endTime = new Date(log.date || log.endDate || log.startDate);

      // Default visual times for all-day events (just for consistency, won't affect view if allDay=true)
      startTime.setHours(9, 0, 0, 0);
      endTime.setHours(17, 0, 0, 0);

      if (log.startTime && log.endTime) {
        try {
          const [startH, startM] = log.startTime.split(':').map(Number);
          const [endH, endM] = log.endTime.split(':').map(Number);

          if (!isNaN(startH) && !isNaN(startM) && !isNaN(endH) && !isNaN(endM)) {
            // Reset to log date
            const baseDate = new Date(log.date || log.startDate);
            startTime = new Date(baseDate);
            startTime.setHours(startH, startM, 0, 0);

            endTime = new Date(baseDate);
            endTime.setHours(endH, endM, 0, 0);

            allDay = false;
          }
        } catch (e) {
          console.error("Error parsing time for log", log.id, e);
        }
      } else if (log.type === "tutorial" && log.startDate && log.endDate) {
        startTime = new Date(log.startDate);
        endTime = new Date(log.endDate);
      }

      let color = "sky";
      if (log.type === "Vacaciones") color = "emerald";
      else if (log.type === "Baja médica") color = "rose";
      else if (log.type === "Asuntos propios") color = "amber";

      return {
        allDay,
        color,
        description: log.notes,
        end: endTime,
        id: log.id,
        start: startTime,
        title: log.description || log.type,
        extendedProps: log,
      } as CalendarEvent & { extendedProps: any };
    });
  }, [workLogs]);

  const handleEventClick = (event: CalendarEvent) => {
    const extendedEvent = event as CalendarEvent & { extendedProps: any };
    if (extendedEvent.extendedProps) {
      setSelectedLogs([extendedEvent.extendedProps]);
      setIsDetailsOpen(true);
    }
  };

  const handleDateClick = (date: Date) => {
    if (!canCreateWorkLog) return;
    setSelectedDate(date);
    setIsCreateOpen(true);
  };

  if (!user) return null;

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 md:gap-8 md:p-8 h-full">
      <div className="flex items-center justify-between">
        <h1 className="font-semibold text-lg md:text-2xl">Calendar (Calendario)</h1>
        {canCreateWorkLog && <Button onClick={() => setIsCreateOpen(true)}>Add Work Log</Button>}
        {!canCreateWorkLog && role === 'worker' && isManaged && (
          <p className="text-sm text-muted-foreground italic">
            En esta empresa los turnos los registra el equipo gestor
          </p>
        )}
      </div>
      <div className="flex-1 min-h-0 h-full">
        <EventCalendar
          events={events}
          initialView="month"
          onEventClick={handleEventClick}
          onDateClick={handleDateClick}
          showAddButton={false}
        />
      </div>

      <WorkLogDetailsDialog
        open={isDetailsOpen}
        onOpenChange={setIsDetailsOpen}
        log={selectedLogs[0]}
        userSettings={
          selectedLogs[0]
            ? userRates.find((r: any) => r.companyId === selectedLogs[0].companyId) || null
            : null
        }
      />

      {canCreateWorkLog && (
        <UserCreateWorkLogDialog
          open={isCreateOpen}
          onOpenChange={setIsCreateOpen}
          user={user}
          initialDate={selectedDate}
          onLogUpdate={() => refetchWorkLogs()}
        >
          <span className="hidden" />
        </UserCreateWorkLogDialog>
      )}
    </div>
  );
}
