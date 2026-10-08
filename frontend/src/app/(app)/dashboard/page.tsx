"use client";
export const dynamic = "force-dynamic";

import { useAuth } from "@/context/AuthContext"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, ChevronLeft, ChevronRight } from "lucide-react"
import { useRouter } from "next/navigation"
import { format, subMonths, addMonths } from "date-fns"
import { es } from "date-fns/locale"
import api from "@/lib/api"
import { getMyCompanies } from "@/lib/api/companies"
import { getUserRates } from "@/lib/api/settings"
import { WorkLog } from "@/lib/types"
import { getWorkLogs } from "@/lib/api/work-logs"
import { WorkLogDetailsDialog } from "@/components/work-log/details-dialog"
import { UserCreateWorkLogDialog } from "@/components/work-log/user-dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { NotificationsSection } from "@/components/notifications-section"
import { useState } from "react"

// V3 Components
import { OverviewV3 } from "@/components/dashboard/overview-v2"
import { AnalyticsV2 as AnalyticsV3 } from "@/components/dashboard/analytics-v2"

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState("overview")
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  // Dashboard Date State
  const [selectedDate, setSelectedDate] = useState(new Date())
  const handlePrevMonth = () => setSelectedDate(prev => subMonths(prev, 1))
  const handleNextMonth = () => setSelectedDate(prev => addMonths(prev, 1))

  // Edit/Details Dialog State
  const [selectedLog, setSelectedLog] = useState<WorkLog | null>(null)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)
  const [applyToGroup, setApplyToGroup] = useState(false)

  // Queries
  const { data: workLogs = [], isLoading: loadingLogs } = useQuery({
    queryKey: ["workLogs", user?.activeCompanyId],
    queryFn: () => getWorkLogs(),
    enabled: !!user,
  });

  const { data: myCompanies = [] } = useQuery({
    queryKey: ["myCompanies"],
    queryFn: getMyCompanies,
    enabled: !!user,
  });

  const { data: userRates = [] } = useQuery({
    queryKey: ["userRates"],
    queryFn: () => getUserRates(),
    enabled: !!user,
  });

  if (loading || !user) {
    return (
      <div className="flex h-full w-full items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <div className="flex items-center space-x-2">
          <UserCreateWorkLogDialog
            user={user}
            onLogUpdate={() => {
              queryClient.invalidateQueries({ queryKey: ["workLogs"] })
            }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 capitalize">
            {format(selectedDate, 'MMMM yyyy', { locale: es })}
          </h2>
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
            <button
              onClick={handlePrevMonth}
              className="p-1 hover:bg-white dark:hover:bg-slate-700 rounded-md transition-all shadow-sm"
              title="Mes anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={handleNextMonth}
              className="p-1 hover:bg-white dark:hover:bg-slate-700 rounded-md transition-all shadow-sm"
              title="Mes siguiente"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <NotificationsSection user={user} />

      <Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-slate-100 p-1 rounded-lg">
          <TabsTrigger value="overview" className="data-[state=active]:bg-white data-[state=active]:shadow-sm">Vista General</TabsTrigger>
          <TabsTrigger value="analytics" className="data-[state=active]:bg-white data-[state=active]:shadow-sm">Analitica</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4 animate-in fade-in-50 duration-300">
          <OverviewV3
            workLogs={workLogs}
            companies={myCompanies}
            activeCompanyId={user?.activeCompanyId}
            onAddRecord={() => { }}
            onNavigate={setActiveTab}
            selectedDate={selectedDate}
            onViewLog={(log) => {
              setSelectedLog(log)
              setIsDetailsOpen(true)
            }}
          />
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4 animate-in fade-in-50 duration-300">
          <AnalyticsV3
            workLogs={workLogs}
            selectedDate={selectedDate}
            companies={myCompanies}
            activeCompanyId={user?.activeCompanyId}
          />
        </TabsContent>

      </Tabs>

      {/* Edit Log Dialog */}
      <UserCreateWorkLogDialog
        user={user}
        open={isEditOpen}
        onOpenChange={setIsEditOpen}
        logToEdit={selectedLog}
        applyToGroup={applyToGroup}
        onLogUpdate={() => {
          queryClient.invalidateQueries({ queryKey: ["workLogs"] })
          setIsEditOpen(false)
        }}
      >
        <div className="hidden" />
      </UserCreateWorkLogDialog>
      
      {/* Details Dialog */}
      <WorkLogDetailsDialog
        log={selectedLog}
        open={isDetailsOpen}
        onOpenChange={setIsDetailsOpen}
        companies={myCompanies}
        userSettings={
          selectedLog
            ? userRates.find(r => r.companyId === selectedLog.companyId) || null
            : null
        }
        onEdit={(log, group) => {
          setApplyToGroup(group)
          setIsDetailsOpen(false)
          setIsEditOpen(true)
        }}
      />
    </div>
  )
}
