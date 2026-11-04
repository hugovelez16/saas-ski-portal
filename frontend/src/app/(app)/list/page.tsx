"use client";
export const dynamic = "force-dynamic";


import { useAuth } from "@/context/AuthContext";
import api, { describeLoadError } from "@/lib/api";
import { getUserRates } from "@/lib/api/settings";
import { getMyCompanies } from "@/lib/api/companies";
import type { WorkLog, UserCompanyRate, Company, CompanyMember } from "@/lib/types";
import { mapMemberToLegacyRate } from "@/lib/utils/rates";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { format, parseISO } from 'date-fns';
import { Loader2, PlusCircle, Pencil, Trash2, ArrowUp, ArrowDown, ArrowUpDown, Sparkles, Moon } from "lucide-react";
import { useMemo, useState, useEffect } from "react";
import { WorkLogDetailsDialog } from "@/components/work-log/details-dialog";
import { UserCreateWorkLogDialog } from "@/components/work-log/user-dialog";
import { ExportLogsDialog } from "@/components/work-log/export-dialog";
import { FilterBar, FilterConfig } from "@/components/ui/filter-bar";
import { usePermissions } from "@/hooks/use-permissions";


import { useSearchParams } from "next/navigation";

export default function ListPage() {
  const { user, loading } = useAuth();
  const searchParams = useSearchParams();
  const targetUserId = searchParams.get('userId');

  const [editingLog, setEditingLog] = useState<WorkLog | null>(null);
  const [applyToGroup, setApplyToGroup] = useState(false);

  const [selectedLog, setSelectedLog] = useState<WorkLog | null>(null);
  const [workLogs, setWorkLogs] = useState<WorkLog[]>([]);
  const [userRates, setUserRates] = useState<UserCompanyRate[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState(true);

  const [loadError, setLoadError] = useState<string | null>(null);

  const currentCompanyId = user?.activeCompanyId ?? null;

  const fetchLogs = async () => {
    try {
      setLoadError(null);
      let url = "/work-logs";
      let queryParams = new URLSearchParams();

      if (targetUserId && user?.role === 'admin') {
        queryParams.append('user_id', targetUserId);
      }
      if (currentCompanyId) {
        queryParams.append('company_id', currentCompanyId);
      }

      if (queryParams.toString().length > 0) {
        url += `?${queryParams.toString()}`;
      }

      const res = await api.get(url);
      setWorkLogs(res.data);
    } catch (error) {
      console.error("Error fetching logs", error);
      setWorkLogs([]);
      setLoadError(describeLoadError(error, "No se pudieron cargar los turnos."));
    } finally {
      setIsLoadingLogs(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const [rates, comps] = await Promise.all([getUserRates(), getMyCompanies()]);
      setUserRates(rates.map(r => mapMemberToLegacyRate(r)));
      setCompanies(comps);
    } catch (error) {
      console.error("Error fetching rates", error);
    }
  }

  useEffect(() => {
    if (user) {
      setIsLoadingLogs(true);
      fetchLogs();
      fetchSettings();
    }
  }, [user, targetUserId, currentCompanyId]);

  const handleLogUpdate = () => {
    fetchLogs();
  };

  const [filters, setFilters] = useState<Record<string, any>>({});
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);

  const sortedWorkLogs = useMemo(() => {
    if (!workLogs) return [];
    let result = [...workLogs];

    // Filter Logic
    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(log =>
        (log.description && log.description.toLowerCase().includes(q)) ||
        (log.type && log.type.toLowerCase().includes(q))
      );
    }
    if (filters.type && filters.type.length > 0) {
      result = result.filter(log => filters.type.includes(log.type));
    }
    if (filters.date) {
      const { from, to } = filters.date || {};
      if (from || to) {
        result = result.filter(log => {
          const dateStr = log.startDate;
          if (!dateStr) return false;
          const logDate = parseISO(dateStr);
          if (from && logDate < from) return false;
          if (to) {
            const endOfDay = new Date(to);
            endOfDay.setHours(23, 59, 59, 999);
            if (logDate > endOfDay) return false;
          }
          return true;
        });
      }
    }

    // Default Sort (Date Desc) if no config
    if (!sortConfig) {
      result.sort((a, b) => {
        const dateA = a.startDate;
        const dateB = b.startDate;
        if (!dateA || !dateB) return 0;
        return parseISO(dateB).getTime() - parseISO(dateA).getTime();
      });
    } else {
      result.sort((a, b) => {
        let aVal: any = "";
        let bVal: any = "";

        switch (sortConfig.key) {
          case 'type':
            aVal = a.type;
            bVal = b.type;
            break;
          case 'date':
            aVal = a.startDate;
            bVal = b.startDate;
            break;
          case 'description':
            aVal = a.description || "";
            bVal = b.description || "";
            break;
          case 'duration':
            if (a.durationHours !== undefined || a.duration !== undefined || (a.startTime && a.endTime)) {
              aVal = Number(a.durationHours ?? a.duration) || 0;
            } else {
              aVal = a.startDate && a.endDate
                ? (new Date(a.endDate).getTime() - new Date(a.startDate).getTime())
                : 0;
            }
            if (b.durationHours !== undefined || b.duration !== undefined || (b.startTime && b.endTime)) {
              bVal = Number(b.durationHours ?? b.duration) || 0;
            } else {
              bVal = b.startDate && b.endDate
                ? (new Date(b.endDate).getTime() - new Date(b.startDate).getTime())
                : 0;
            }
            break;
          case 'amount':
            aVal = Number(a.netAmount || a.grossAmount) || 0;
            bVal = Number(b.netAmount || b.grossAmount) || 0;
            break;
          default:
            aVal = "";
            bVal = "";
        }

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [workLogs, filters, sortConfig]);

  const activeCompanyId = currentCompanyId || user?.activeCompanyId;
  const activeCompany = useMemo(() => {
    if (!activeCompanyId) return null;
    return companies.find(c => c.id === activeCompanyId);
  }, [companies, activeCompanyId]);
  const perms = usePermissions(activeCompany ?? null);

  const dynamicFields = useMemo(() => {
    const keys = new Set<string>();
    sortedWorkLogs.forEach(log => {
      if (log.extraData) {
        const datos = log.extraData.datos;
        if (datos) {
          Object.keys(datos).forEach(k => {
            const val = datos[k];
            if (val !== null && val !== undefined && (val as any) !== false && val !== "") {
              keys.add(k);
            }
          });
        }
        const opciones = log.extraData.opciones;
        if (opciones) {
          Object.keys(opciones).forEach(k => {
            const val = opciones[k];
            if (val !== null && val !== undefined && val !== false) {
              keys.add(k);
            }
          });
        }
      }
    });
    return Array.from(keys);
  }, [sortedWorkLogs]);

  const handleSort = (key: string) => {
    setSortConfig(current => {
      if (current && current.key === key) {
        if (current.direction === 'asc') return { key, direction: 'desc' };
        return null;
      }
      return { key, direction: 'asc' };
    });
  };

  const filterConfig: FilterConfig[] = [
    {
      id: "type",
      label: "Type",
      type: "select",
      options: [
        { label: "Particular", value: "particular" },
        { label: "Tutorial", value: "tutorial" },
      ]
    },
    {
      id: "date",
      label: "Date Range",
      type: "date-range"
    },
    {
      id: "groupBy",
      label: "Group By",
      type: "select",
      options: [
        { label: "None", value: "none" },
        { label: "Month", value: "month" },
        { label: "Type", value: "type" },
      ]
    }
  ];

  const handleRowClick = (log: WorkLog) => {
    setSelectedLog(log);
  };

  const handleDeleteLog = async (logId: string) => {
    if (confirm("Are you sure you want to delete this log?")) {
      try {
        await api.delete(`/work-logs/${logId}`);
        fetchLogs();
      } catch (error) {
        console.error("Error deleting log", error);
      }
    }
  };

  const totalCols = 7 + dynamicFields.length;

  return (
    <div className="space-y-8">
      {/* Edit Dialog */}
      {user && editingLog && (
        <UserCreateWorkLogDialog
          user={{ id: user.id }}
          open={!!editingLog}
          onOpenChange={(open) => {
            if (!open) {
              setEditingLog(null);
              setApplyToGroup(false);
            }
          }}
          logToEdit={editingLog}
          applyToGroup={applyToGroup}
          onLogUpdate={() => { handleLogUpdate(); setEditingLog(null); setApplyToGroup(false); }}
        />
      )}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Work Log List</h1>
          <p className="text-muted-foreground">All your work logs in one place.</p>
        </div>
        {user && (
          <div className="flex gap-2 items-center">
            <ExportLogsDialog workLogs={sortedWorkLogs} />
            {perms.canCreateWorkLog && (
              <UserCreateWorkLogDialog
                user={{ id: user.id }}
                onLogUpdate={handleLogUpdate}
              >
                <Button>
                  <PlusCircle className="mr-2 h-4 w-4" />
                  Add Work Log
                </Button>
              </UserCreateWorkLogDialog>
            )}
            {perms.role === 'worker' && perms.isManaged && (
              <p className="text-sm text-muted-foreground italic">
                En esta empresa los turnos los registra el equipo gestor
              </p>
            )}
          </div>
        )}
      </div>

      <FilterBar config={filterConfig} onFilterChange={setFilters} />

      <div className="rounded-lg border bg-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-900 hover:bg-slate-900 border-none">
              <TableHead className="cursor-pointer hover:bg-slate-800 transition-colors text-slate-50 rounded-tl-md" onClick={() => handleSort('date')}>
                <div className="flex items-center gap-1">
                  Fecha
                  {sortConfig?.key === 'date' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                  ) : <ArrowUpDown className="h-4 w-4 text-slate-50/50" />}
                </div>
              </TableHead>
              <TableHead className="cursor-pointer hover:bg-slate-800 transition-colors text-slate-50" onClick={() => handleSort('type')}>
                <div className="flex items-center gap-1">
                  Tipo
                  {sortConfig?.key === 'type' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                  ) : <ArrowUpDown className="h-4 w-4 text-slate-50/50" />}
                </div>
              </TableHead>
              <TableHead className="cursor-pointer hover:bg-slate-800 transition-colors text-slate-50" onClick={() => handleSort('description')}>
                <div className="flex items-center gap-1">
                  Descripción
                  {sortConfig?.key === 'description' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                  ) : <ArrowUpDown className="h-4 w-4 text-slate-50/50" />}
                </div>
              </TableHead>
              {dynamicFields.map(field => {
                const label = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                return (
                  <TableHead key={field} className="text-slate-50 hidden lg:table-cell">{label}</TableHead>
                );
              })}
              <TableHead className="text-slate-50">Extras</TableHead>
              <TableHead className="cursor-pointer hover:bg-slate-800 transition-colors text-slate-50" onClick={() => handleSort('duration')}>
                <div className="flex items-center gap-1">
                  Duración/Días
                  {sortConfig?.key === 'duration' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                  ) : <ArrowUpDown className="h-4 w-4 text-slate-50/50" />}
                </div>
              </TableHead>
              <TableHead className="cursor-pointer hover:bg-slate-800 transition-colors text-slate-50" onClick={() => handleSort('amount')}>
                <div className="flex items-center gap-1">
                  Importe
                  {sortConfig?.key === 'amount' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                  ) : <ArrowUpDown className="h-4 w-4 text-slate-50/50" />}
                </div>
              </TableHead>
              <TableHead className="w-[100px] bg-slate-900 rounded-tr-md"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoadingLogs ? (
              <TableRow>
                <TableCell colSpan={totalCols} className="text-center py-12">
                  <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
                </TableCell>
              </TableRow>
            ) : loadError ? (
              <TableRow>
                <TableCell colSpan={totalCols} className="text-center py-12 text-destructive" role="alert">
                  {loadError}
                </TableCell>
              </TableRow>
            ) : sortedWorkLogs.length > 0 ? (
              sortedWorkLogs.reduce((acc: React.ReactNode[], log, index, array) => {
                // Grouping Logic
                if (filters.groupBy === 'month') {
                  const getDate = (l: WorkLog) => l.type === 'tutorial' ? l.startDate : l.date;
                  const currentDateStr = getDate(log);
                  const prevDateStr = index > 0 ? getDate(array[index - 1]) : null;

                  if (currentDateStr) {
                    const currentMonth = format(parseISO(currentDateStr), 'MMMM yyyy');
                    const prevMonth = prevDateStr ? format(parseISO(prevDateStr), 'MMMM yyyy') : null;

                    if (currentMonth !== prevMonth) {
                      acc.push(
                        <TableRow key={`header-${currentMonth}`} className="bg-muted/50 hover:bg-muted/50">
                          <TableCell colSpan={totalCols} className="font-semibold text-sm py-2">
                            {currentMonth}
                          </TableCell>
                        </TableRow>
                      );
                    }
                  }
                } else if (filters.groupBy === 'type') {
                  const currentType = log.type;
                  const prevType = index > 0 ? array[index - 1].type : null;

                  if (currentType !== prevType) {
                    const logCompany = companies.find(c => c.id === log.companyId);
                    const label = logCompany?.worklogDefinitions?.[currentType]?.label || currentType;
                    acc.push(
                      <TableRow key={`header-${currentType}`} className="bg-muted/50 hover:bg-muted/50">
                        <TableCell colSpan={totalCols} className="font-semibold text-sm py-2 capitalize">
                          {label}
                        </TableCell>
                      </TableRow>
                    );
                  }
                }

                acc.push(
                  <TableRow key={log.id} onClick={() => handleRowClick(log)} className="cursor-pointer transition-colors hover:bg-slate-200 dark:hover:bg-slate-700 even:bg-slate-100 dark:even:bg-slate-800">
                    <TableCell className="py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium whitespace-nowrap">
                          {log.type === 'tutorial' && log.startDate && log.endDate
                            ? `${format(parseISO(log.startDate), "dd/MM/yyyy")} - ${format(parseISO(log.endDate), "dd/MM/yyyy")}`
                            : log.startDate
                              ? format(parseISO(log.startDate), "dd/MM/yyyy")
                              : "-"}
                        </span>
                        {log.startTime && log.endTime && (
                          <span className="text-xs text-muted-foreground whitespace-nowrap">
                            {log.startTime} - {log.endTime}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="py-2">
                      {(() => {
                        const logCompany = companies.find(c => c.id === log.companyId);
                        const label = logCompany?.worklogDefinitions?.[log.type]?.label || log.type;
                        return <span className="capitalize">{label}</span>;
                      })()}
                    </TableCell>
                    <TableCell className="py-2">
                      <div className="flex items-center gap-2 max-w-[200px] truncate" title={log.description || ''}>
                        <span className="truncate">{log.description || '-'}</span>
                      </div>
                    </TableCell>
                    {dynamicFields.map(field => {
                      const val = log.extraData?.datos?.[field] !== undefined
                        ? log.extraData?.datos?.[field]
                        : log.extraData?.opciones?.[field];

                      if (val === null || val === undefined || val === false || val === "") {
                        return <TableCell key={field} className="py-2 hidden lg:table-cell">-</TableCell>;
                      }

                      const displayVal = typeof val === 'boolean' ? 'Sí' : String(val);
                      return (
                        <TableCell key={field} className="py-2 hidden lg:table-cell truncate max-w-[100px]" title={displayVal}>
                          {displayVal}
                        </TableCell>
                      );
                    })}
                    <TableCell className="py-2">
                      <div className="flex gap-1">
                        {log.hasCoordination && (
                          <div className="p-1 bg-blue-100 text-blue-700 rounded" title="Coordination supplement applied">
                            <Sparkles className="h-3 w-3" />
                          </div>
                        )}
                        {log.hasNight && (
                          <div className="p-1 bg-indigo-100 text-indigo-700 rounded" title="Night supplement applied">
                            <Moon className="h-3 w-3" />
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="py-2">
                      {(() => {
                        const calcDuration = log.calculationSnapshot?.calculations?.duration;
                        const calcUnit = log.calculationSnapshot?.calculations?.unit;
                        
                        if (calcDuration !== undefined && calcUnit !== undefined) {
                          if (calcUnit === 'hours') return `${Number(calcDuration).toFixed(2)} h`;
                          if (calcUnit === 'days') return `${calcDuration} ${calcDuration === 1 ? 'día' : 'días'}`;
                          if (calcUnit === 'fixed') return 'Fijo';
                          return `${calcDuration} ${calcUnit}`;
                        }

                        const logCompany = companies.find(c => c.id === log.companyId);
                        const definition = logCompany?.worklogDefinitions?.[log.type];
                        
                        if (definition) {
                          const unit = definition.unit;
                          if (unit === 'hours') {
                            const hours = log.duration ?? log.durationHours ?? 0;
                            return `${Number(hours).toFixed(2)} h`;
                          }
                          if (unit === 'days') {
                            const start = new Date(log.startDate);
                            const end = new Date(log.endDate);
                            const msPerDay = 1000 * 60 * 60 * 24;
                            const days = log.startDate && log.endDate ? Math.round((end.getTime() - start.getTime()) / msPerDay) + 1 : 0;
                            return `${days} ${days === 1 ? 'día' : 'días'}`;
                          }
                          if (unit === 'fixed') {
                            return 'Fijo';
                          }
                        }

                        if (log.type === 'particular' || (log.startTime && log.endTime) || log.durationHours) {
                          return `${log.durationHours || log.duration || 0} h`;
                        }
                        if (log.startDate && log.endDate) {
                          const start = new Date(log.startDate);
                          const end = new Date(log.endDate);
                          const msPerDay = 1000 * 60 * 60 * 24;
                          const days = Math.round((end.getTime() - start.getTime()) / msPerDay) + 1;
                          return `${days} ${days === 1 ? 'día' : 'días'}`;
                        }
                        return '-';
                      })()}
                    </TableCell>
                    <TableCell className="py-2">
                      {(() => {
                        const rate = userRates.find((r: any) => r.companyId === log.companyId);
                        if (!rate) return (log.netAmount || log.grossAmount) ? `€${Number(log.netAmount || log.grossAmount).toFixed(2)}` : '-';

                        let totalGross = 0;
                        if (log.type === 'tutorial' && log.startDate && log.endDate) {
                          const start = new Date(log.startDate);
                          const end = new Date(log.endDate);
                          const msPerDay = 1000 * 60 * 60 * 24;
                          const days = Math.round((end.getTime() - start.getTime()) / msPerDay) + 1;

                          const appliedRate = Number(log.calculationSnapshot?.rate_applied) || Number(rate.dailyRate) || 0;
                          totalGross += days * appliedRate;

                          if (log.hasNight) {
                            let nightBase = days > 0 ? days - 1 : 0;
                            const nights = log.arrivesPrior ? nightBase + 1 : nightBase;
                            totalGross += nights * Number(rate.nightRate || 30);
                          }

                          if (log.hasCoordination) {
                            totalGross += days * Number(rate.coordinationRate || 10);
                          }
                        } else {
                          const duration = Number(log.durationHours) || 0;
                          const appliedRate = Number(log.calculationSnapshot?.rate_applied) || Number(rate.hourlyRate) || 0;
                          totalGross += duration * appliedRate;

                          if (log.hasNight) {
                            totalGross += Number(rate.nightRate || 30);
                          }
                          if (log.hasCoordination) {
                            totalGross += Number(rate.coordinationRate || 10);
                          }
                        }
                        return `€${totalGross.toFixed(2)}`;
                      })()}
                    </TableCell>
                    <TableCell className="py-2" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        {perms.canEditWorkLog(log) && (
                          <>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setEditingLog(log)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 hover:text-red-600" onClick={() => handleDeleteLog(log.id)}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
                return acc;
              }, [])
            ) : (
              <TableRow>
                <TableCell colSpan={totalCols} className="text-center text-muted-foreground py-12">
                  No records found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <WorkLogDetailsDialog
        log={selectedLog}
        open={!!selectedLog}
        onOpenChange={(open) => !open && setSelectedLog(null)}
        userSettings={
          selectedLog
            ? userRates.find(r => r.companyId === selectedLog.companyId) || null
            : null
        }
        onEdit={(log, group) => {
          setApplyToGroup(group);
          setSelectedLog(null);
          setEditingLog(log);
        }}
        onDelete={(log) => {
          handleDeleteLog(log.id);
          setSelectedLog(null);
        }}
      />
    </div>
  );
}
