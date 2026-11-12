/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * End-of-Day Automation Page
 *
 * Comprehensive UI for staff to complete end-of-day closing in ~5 minutes:
 * - Auto-generated closing checklist
 * - One-click quick close
 * - Individual task execution
 * - Real-time progress tracking
 * - Security check verification
 * - Statistics summary
 * - Auto-logout scheduling
 */

import { useState, useEffect, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "../contexts/AuthContext"
import { fetchApi } from "@/api/fetchApi"
import { useNavigate } from "react-router-dom"
import { WorkflowStatus } from "@/constants/statuses"
import {
  CheckCircle,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  BarChart3,
  Lock,
  LogOut,
  Loader,
  ChevronDown,
  ChevronUp,
  FileText,
  Package,
  Send,
  HardDrive,
  Shield,
  Calendar,
  Zap,
  AlertTriangle,
  Banknote} from "lucide-react"
import toast from "react-hot-toast"
import { getCurrentSession } from "@/api/domains/staff/cash-drawer-api"
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// Cash Drawer Status Card for EOD integration
function DrawerStatusCard() {
  const drawerQuery = useQuery({
    queryKey: ["eod-cash-drawer-status"],
    queryFn: async () => {
      try {
        return await getCurrentSession(1)
      } catch {
        return null
      }
    },
    retry: false,
  })

  const session = drawerQuery.data

  if (drawerQuery.isLoading) return null

  let bg = "bg-earth-100 dark:bg-earth-700"
  let textColor = "text-lsc-dark/70 dark:text-lsc-cream/70"
  let Icon = Banknote
  let label = "No active session"
  let detail = "Cash drawer is closed"

  if (session) {
    if (session.status === "open") {
      bg = "bg-status-warning-50 dark:bg-status-warning-900/20"
      textColor = "text-status-warning-700 dark:text-status-warning-300"
      Icon = AlertTriangle
      label = "Drawer Open"
      detail = "Reconcile before closing"
    } else if (session.status === "pending_approval") {
      bg = "bg-status-warning-50 dark:bg-status-warning-900/20"
      textColor = "text-status-warning-700 dark:text-status-warning-300"
      Icon = AlertTriangle
      label = "Pending Approval"
      detail = "Manager approval needed"
    } else {
      bg = "bg-status-success-50 dark:bg-status-success-900/20"
      textColor = "text-status-success-700 dark:text-status-success-300"
      Icon = CheckCircle
      label = "Drawer Closed"
      detail = session.discrepancy ? `Discrepancy: $${Math.abs(session.discrepancy).toFixed(2)}` : "Balanced"
    }
  }

  return (
    <div className={`${bg} rounded-lg p-4 mb-4`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Icon size={20} className={textColor} />
          <div>
            <div className={`font-semibold text-sm ${textColor}`}>{label}</div>
            <div className={`text-xs ${textColor} opacity-75`}>{detail}</div>
          </div>
        </div>
        {session?.status === "open" && (
          <a href="/staff/cash-drawer" className="text-sm font-medium text-status-warning-700 dark:text-status-warning-300 hover:underline">
            Reconcile now
          </a>
        )}
      </div>
    </div>
  )
}


// Confirmation Dialog Component
const ConfirmationDialog = ({
  isOpen,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  isDangerous = false,
  onConfirm,
  onCancel,
}: {
  isOpen: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  isDangerous?: boolean
  onConfirm: () => void
  onCancel: () => void
}) => {
  if (!isOpen) return null

  return (
    <ModalBackdrop onClose={onCancel} title="Dialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
        <div className="flex items-start gap-3 mb-4">
          {isDangerous ? (
            <AlertTriangle size={24} className="text-status-danger-600 flex-shrink-0 mt-1" />
          ) : (
            <AlertCircle size={24} className="text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-1" />
          )}
          <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">{title}</h2>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded-lg font-semibold text-white transition ${
              isDangerous
                ? "bg-status-danger-600 hover:bg-status-danger-700"
                : "bg-lsc-rose hover:bg-lsc-rose/90"
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

interface EODTask {
  id: number
  session_id: number
  task_type: string
  display_name: string
  status: "pending" | "in_progress" | "completed" | "failed" | "skipped"
  task_data: Record<string, unknown>
  started_at: string
  completed_at?: string
  duration_seconds: number
  error_message?: string
}

interface EODSession {
  id: number
  session_code: string
  branch_location: string
  status: string
  started_at: string
  completed_at?: string
  total_duration_seconds: number
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  skipped_tasks: number
  tasks: EODTask[]
  auto_logout_at?: string
  statistics_summary?: Record<string, unknown>
}

const TaskIcon = ({ taskType }: { taskType: string }) => {
  const icons: Record<string, React.ReactNode> = {
    close_registers: <Lock size={20} />,
    process_holds: <Package size={20} />,
    send_overdue_notices: <Send size={20} />,
    backup_confirmation: <HardDrive size={20} />,
    security_check: <Shield size={20} />,
    statistics_summary: <BarChart3 size={20} />,
    tomorrow_events: <Calendar size={20} />,
    holds_pull_list: <FileText size={20} />,
  }
  return icons[taskType] || <Zap size={20} />
}

const StatusBadge = ({ status }: { status: string }) => {
  const styles: Record<string, string> = {
    pending: "bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100",
    in_progress: "bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light",
    completed: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300",
    failed: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300",
    skipped: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300",
  }

  const labels: Record<string, string> = {
    pending: "Pending",
    in_progress: "In Progress",
    completed: "Completed",
    failed: "Failed",
    skipped: "Skipped",
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

export default function EndOfDayPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [session, setSession] = useState<EODSession | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [expandedTask, setExpandedTask] = useState<number | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [currentTime, setCurrentTime] = useState(new Date())

  // Confirmation dialog state
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [confirmAction, setConfirmAction] = useState<"quick-close" | "complete" | "logout" | null>(null)

  // Redirect if not authenticated or not staff
  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      navigate("/")
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
    }
  }, [authLoading, user, navigate, t])

  // Timer effect
  useEffect(() => {
    if (!session || session.status === WorkflowStatus.COMPLETED) return

    const interval = setInterval(() => {
      setElapsedSeconds((s) => s + 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [session])

  // Clock tick for landing state
  useEffect(() => {
    if (session) return
    const interval = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(interval)
  }, [session])

  const branchLocation = (user as unknown as Record<string, unknown>)?.branch_location as string || "Main Library"

  const startSession = useCallback(async () => {
    setIsLoading(true)
    try {
      const newSession: EODSession = await fetchApi("/end-of-day/sessions", {
        method: "POST",
        body: JSON.stringify({
          branch_location: branchLocation,
        }),
      })
      setSession(newSession)
      toast.success(t('toast.endOfDay.eodSessionStarted'))
    } catch (error: unknown) {
      toast.error(t('endOfDay.failedToStartEodSession'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  const executeTask = useCallback(
    async (taskId: number) => {
      if (!session) return

      setIsExecuting(true)
      try {
        await fetchApi(`/end-of-day/tasks/${taskId}/execute`, {
          method: "POST",
        })

        // Refresh session
        try {
          const updatedSession: EODSession = await fetchApi(`/end-of-day/sessions/${session.id}`)
          setSession(updatedSession)
        } catch {
          // Non-fatal: keep existing session state if refresh fails
        }

        toast.success(t('toast.endOfDay.taskCompleted'))
      } catch (error: unknown) {
        toast.error(t('endOfDay.failedToExecuteTask'))
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      } finally {
        setIsExecuting(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [session]
  )

  const quickClose = useCallback(async () => {
    setIsLoading(true)
    try {
      const result = await fetchApi(
        `/end-of-day/quick-close?branch_location=${encodeURIComponent(branchLocation)}`,
        {
          method: "POST",
        }
      )
      toast.success(t('toast.endOfDay.quickCloseCompletedInTotaldurationseconds', { totaldurationseconds: result.total_duration_seconds }))

      // Refresh session data
      if (result.session_id) {
        try {
          const updatedSession: EODSession = await fetchApi(`/end-of-day/sessions/${result.session_id}`)
          setSession(updatedSession)
        } catch {
          // Non-fatal: keep existing session state if refresh fails
        }
      }
    } catch (error: unknown) {
      toast.error(t('endOfDay.failedToCompleteQuickClose'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  const completeSession = useCallback(async () => {
    if (!session) return

    setIsLoading(true)
    try {
      const completedSession: EODSession = await fetchApi(`/end-of-day/sessions/${session.id}/complete`, {
        method: "POST",
      })
      setSession(completedSession)
      toast.success(t('toast.endOfDay.eodSessionCompleted'))
    } catch (error: unknown) {
      toast.error(t('endOfDay.failedToCompleteSession'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session])

  const scheduleLogout = useCallback(async () => {
    if (!session) return

    try {
      await fetchApi(`/end-of-day/sessions/${session.id}/schedule-logout`, {
        method: "POST",
        body: JSON.stringify({ logout_delay_minutes: 5 }),
      })

      toast.success(t('endOfDay.autoLogoutScheduledForMinutes'))
    } catch (error: unknown) {
      toast.error(t('endOfDay.failedToScheduleLogout'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session])

  // Confirmation handlers
  const handleConfirmAction = useCallback(async () => {
    setShowConfirmDialog(false)

    if (confirmAction === "quick-close") {
      await quickClose()
    } else if (confirmAction === "complete") {
      await completeSession()
    } else if (confirmAction === "logout") {
      await scheduleLogout()
    }

    setConfirmAction(null)
  }, [confirmAction, quickClose, completeSession, scheduleLogout])

  const showQuickCloseConfirm = useCallback(() => {
    setConfirmAction("quick-close")
    setShowConfirmDialog(true)
  }, [])

  const showCompleteConfirm = useCallback(() => {
    setConfirmAction("complete")
    setShowConfirmDialog(true)
  }, [])

  const showLogoutConfirm = useCallback(() => {
    setConfirmAction("logout")
    setShowConfirmDialog(true)
  }, [])

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  const progressPercent = session
    ? Math.round((session.completed_tasks / session.total_tasks) * 100)
    : 0

  const TASK_PREVIEW = [
    { type: "process_holds", label: "Process Holds" },
    { type: "send_overdue_notices", label: "Overdue Notices" },
    { type: "security_check", label: "Security Check" },
    { type: "statistics_summary", label: "Statistics" },
    { type: "tomorrow_events", label: "Tomorrow's Events" },
    { type: "holds_pull_list", label: "Holds Pull List" },
    { type: "close_registers", label: "Close Registers" },
    { type: "backup_confirmation", label: "Backup Check" },
  ]

  if (!session) {
    return (
      <AdminShell title="End of Day">
      <div className="bg-earth-50 dark:bg-earth-900 p-4 md:p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6 md:p-8">
            {/* Time + branch */}
            <div className="mb-6">
              <p className="text-5xl font-bold text-lsc-dark dark:text-lsc-cream tabular-nums">
                {currentTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">{branchLocation}</p>
            </div>

            {/* Task preview */}
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/50 mb-3">
                Tasks that will run
              </p>
              <div className="grid grid-cols-2 gap-2">
                {TASK_PREVIEW.map(({ type, label }) => (
                  <div
                    key={type}
                    className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
                  >
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/40">
                      <TaskIcon taskType={type} />
                    </span>
                    {label}
                  </div>
                ))}
              </div>
            </div>

            {/* Cash drawer status */}
            <DrawerStatusCard />

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={startSession}
                disabled={isLoading}
                className="flex-1 bg-lsc-rose text-white px-6 py-3 rounded-lg font-semibold hover:bg-lsc-rose/90 disabled:opacity-50 transition flex flex-col items-center justify-center gap-0.5 min-h-[56px]"
              >
                <span className="flex items-center gap-2">
                  {isLoading ? <Loader className="motion-safe:animate-spin" size={18} /> : <PlayCircle size={18} />}
                  Start Session
                </span>
                <span className="text-xs font-normal opacity-80">step through tasks</span>
              </button>

              <button
                onClick={showQuickCloseConfirm}
                disabled={isLoading}
                className="flex-1 bg-earth-700 dark:bg-earth-600 text-lsc-cream px-6 py-3 rounded-lg font-semibold hover:bg-earth-800 dark:hover:bg-earth-500 disabled:opacity-50 transition flex flex-col items-center justify-center gap-0.5 min-h-[56px]"
              >
                <span className="flex items-center gap-2">
                  {isLoading ? <Loader className="motion-safe:animate-spin" size={18} /> : <Zap size={18} />}
                  Quick Close
                </span>
                <span className="text-xs font-normal opacity-80">run all automatically</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      </AdminShell>
    )
  }

  return (
    <AdminShell title="End of Day">
    <div className="bg-earth-50 dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6 md:mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">End-of-Day Closing</h1>
              <p className="text-sm md:text-base text-lsc-dark/70 dark:text-lsc-cream/70">{branchLocation}</p>
            </div>
            <div className="text-right bg-lsc-white dark:bg-earth-800 rounded-lg p-3 md:bg-transparent md:p-0">
              <p className="text-3xl md:text-4xl font-bold text-lsc-rose">{formatTime(elapsedSeconds)}</p>
              <p className="text-xs md:text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Elapsed Time</p>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
            <div className="flex justify-between mb-2">
              <span className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Progress</span>
              <span className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                {session.completed_tasks} / {session.total_tasks} tasks
              </span>
            </div>
            <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-3">
              <div
                className="bg-status-success-500 h-3 rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>

          {/* Cash Drawer Status */}
          <DrawerStatusCard />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-8">
          {/* Tasks Column */}
          <div className="md:col-span-2 space-y-4">
            <h2 className="font-serif text-lg md:text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">Closing Tasks</h2>

            {session.tasks.map((task) => (
              <div
                key={task.id}
                className={`border rounded-lg overflow-hidden transition ${
                  expandedTask === task.id ? "bg-lsc-white dark:bg-earth-800 shadow-lg" : "bg-lsc-white shadow"
                }`}
              >
                <button
                  onClick={() =>
                    setExpandedTask(expandedTask === task.id ? null : task.id)
                  }
                  className="w-full p-3 md:p-4 flex items-center gap-3 md:gap-4 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition min-h-[56px] md:min-h-auto"
                >
                  <div className="flex-shrink-0">
                    {task.status === WorkflowStatus.COMPLETED ? (
                      <CheckCircle2 size={24} className="text-status-success-500" />
                    ) : task.status === WorkflowStatus.FAILED ? (
                      <AlertCircle size={24} className="text-status-danger-500" />
                    ) : (
                      <TaskIcon taskType={task.task_type} />
                    )}
                  </div>

                  <div className="flex-grow text-left">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{task.display_name}</h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{task.task_type}</p>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusBadge status={task.status} />
                    {expandedTask === task.id ? (
                      <ChevronUp size={20} className="text-lsc-dark/70 dark:text-lsc-cream/70" />
                    ) : (
                      <ChevronDown size={20} className="text-lsc-dark/70 dark:text-lsc-cream/70" />
                    )}
                  </div>
                </button>

                {expandedTask === task.id && (
                  <div className="border-t bg-earth-50 dark:bg-earth-900 p-4 space-y-4">
                    {task.status === WorkflowStatus.PENDING && (
                      <button
                        onClick={() => executeTask(task.id)}
                        disabled={isExecuting}
                        className="w-full bg-lsc-rose text-white py-2 rounded-lg font-semibold hover:bg-lsc-rose/90 disabled:opacity-50 transition flex items-center justify-center gap-2"
                      >
                        {isExecuting ? <Loader className="motion-safe:animate-spin" size={20} /> : <PlayCircle size={20} />}
                        Execute Task
                      </button>
                    )}

                    {task.status === "in_progress" && (
                      <div className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light">
                        <Loader className="motion-safe:animate-spin" size={20} />
                        <span>Executing...</span>
                      </div>
                    )}

                    {task.status === WorkflowStatus.COMPLETED && task.task_data && (
                      <div className="bg-lsc-white dark:bg-earth-800 rounded p-3 text-sm">
                        <div className="font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Results:</div>
                        <div className="space-y-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                          {Object.entries(task.task_data).map(([key, value]) => (
                            <div key={key}>
                              <span className="font-medium">{key}:</span> {String(value)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {task.error_message && (
                      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded p-3 text-sm text-status-danger-700 dark:text-status-danger-300">
                        {task.error_message}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Sidebar */}
          <div className="space-y-4 md:space-y-4">
            {/* Session Summary */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4 md:p-6">
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Session Summary</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Session Code:</span>
                  <span className="font-mono font-semibold">{session.session_code}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Status:</span>
                  <span className="font-semibold capitalize">{session.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Completed:</span>
                  <span className="font-semibold">{session.completed_tasks} / {session.total_tasks}</span>
                </div>
                {session.failed_tasks > 0 && (
                  <div className="flex justify-between text-status-danger-600">
                    <span>Failed:</span>
                    <span className="font-semibold">{session.failed_tasks}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Statistics */}
            {session.statistics_summary && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
                <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <BarChart3 size={20} />
                  Today's Stats
                </h3>
                <div className="space-y-2 text-sm">
                  {Object.entries(session.statistics_summary).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{key.replace(/_/g, " ")}:</span>
                      <span className="font-semibold">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            {session.status !== "completed" && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4 md:p-6">
                <button
                  onClick={showCompleteConfirm}
                  disabled={isLoading || session.completed_tasks < session.total_tasks}
                  className="w-full bg-status-success-600 text-white py-2.5 md:py-3 rounded-lg font-semibold hover:bg-status-success-700 disabled:opacity-50 transition mb-3 min-h-[44px]"
                >
                  Complete Session
                </button>
                <button
                  onClick={showQuickCloseConfirm}
                  disabled={isLoading}
                  className="w-full bg-lsc-rose text-white py-2.5 md:py-3 rounded-lg font-semibold hover:bg-lsc-rose/90 disabled:opacity-50 transition min-h-[44px]"
                >
                  Execute Remaining
                </button>
              </div>
            )}

            {/* Auto-Logout */}
            {session.status === WorkflowStatus.COMPLETED && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4 md:p-6">
                <button
                  onClick={showLogoutConfirm}
                  className="w-full bg-status-danger-600 text-white py-2.5 md:py-3 rounded-lg font-semibold hover:bg-status-danger-700 transition flex items-center justify-center gap-2 min-h-[44px]"
                >
                  <LogOut size={20} />
                  <span className="hidden sm:inline">Schedule Auto-Logout</span>
                  <span className="sm:hidden">Logout</span>
                </button>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center mt-3">
                  You will be automatically logged out in 5 minutes
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Confirmation Dialogs */}
        <ConfirmationDialog
          isOpen={showConfirmDialog && confirmAction === "quick-close"}
          title="Quick Close?"
          message="This will automatically execute all remaining closing tasks. Make sure you're ready before confirming."
          confirmText="Yes, Quick Close"
          isDangerous={false}
          onConfirm={handleConfirmAction}
          onCancel={() => setShowConfirmDialog(false)}
        />

        <ConfirmationDialog
          isOpen={showConfirmDialog && confirmAction === "complete"}
          title="Complete Session?"
          message="Mark this closing session as complete. You'll have the option to schedule auto-logout afterward."
          confirmText="Complete"
          isDangerous={false}
          onConfirm={handleConfirmAction}
          onCancel={() => setShowConfirmDialog(false)}
        />

        <ConfirmationDialog
          isOpen={showConfirmDialog && confirmAction === "logout"}
          title="Schedule Auto-Logout?"
          message="You will be automatically logged out in 5 minutes. Make sure all tasks are complete before confirming."
          confirmText="Schedule Logout"
          isDangerous={true}
          onConfirm={handleConfirmAction}
          onCancel={() => setShowConfirmDialog(false)}
        />
      </div>
    </div>
    </AdminShell>
  )
}
