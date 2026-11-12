/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from "react"
import type { CheckInSession } from '../api/domains/circulation/book-drop-api'
import { useNavigate, useParams } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Package,
  Loader2,
  RefreshCw,
  Plus,
  Play,
  Zap,
  MapPin,
  History,
  AlertTriangle,
  BarChart3,
  AlertCircle,
  Activity,
  Inbox,
  CheckCircle,
} from "lucide-react"
import toast from "react-hot-toast"

import { useBookDrops } from "./staff/book-drops/hooks/useBookDrops"
import {
  useBookDropProcessing,
  activeSessionsQueryKey,
  sessionsQueryKey,
} from "./staff/book-drops/hooks/useBookDropProcessing"
import { useBookDropStats } from "./staff/book-drops/hooks/useBookDropStats"
import { useBookDropExceptions } from "./staff/book-drops/hooks/useBookDropExceptions"

import { BookDropList } from "./staff/book-drops/components/BookDropList"
import { BookDropDetail } from "./staff/book-drops/components/BookDropDetail"
import { BookDropProcessingPanel } from "./staff/book-drops/components/BookDropProcessingPanel"
import { BookDropItemsPanel } from "./staff/book-drops/components/BookDropItemsPanel"
import { BookDropStatsPanel } from "./staff/book-drops/components/BookDropStatsPanel"
import { BookDropExceptionsPanel } from "./staff/book-drops/components/BookDropExceptionsPanel"

import { SessionModal } from "./staff/book-drops/components/SessionModal"
import { ResolveExceptionModal } from "./staff/book-drops/components/ResolveExceptionModal"
import type { CheckInException, BookDrop } from "@/api/book-drop-api"
import { DeleteConfirmModal } from "./staff/book-drops/components/DeleteConfirmModal"
import { useTranslation } from '@/i18n'

type ViewMode = "locations" | "sessions" | "process" | "exceptions" | "statistics"
type ModalType = "bookdrop" | "session" | "resolve" | null

const VIEW_MODES: ReadonlyArray<ViewMode> = ["locations", "sessions", "process", "exceptions", "statistics"]
const DEFAULT_VIEW: ViewMode = "locations"

const isViewMode = (value: string | undefined): value is ViewMode =>
  VIEW_MODES.includes(value as ViewMode)

const sessionStatusBadgeClass = (status: string) => {
  switch (status) {
    case "active":
      return "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400"
    case "completed":
      return "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
    case "cancelled":
      return "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400"
    default:
      return "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
  }
}

export default function BookDropManagementPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { tab } = useParams<{ tab?: string }>()

  const viewMode: ViewMode = isViewMode(tab) ? tab : DEFAULT_VIEW

  const [modalType, setModalType] = useState<ModalType>(null)
  const [deletingItem, setDeletingItem] = useState<BookDrop | null>(null)
  const [selectedException, setSelectedException] = useState<CheckInException | null>(null)

  const bookDropsHook = useBookDrops(token)
  const processingHook = useBookDropProcessing(token)
  const statsHook = useBookDropStats(token)
  const exceptionsHook = useBookDropExceptions(token)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, user, navigate, t])

  // Redirect /staff/book-drop -> /staff/book-drop/locations so deep links and back-button work
  useEffect(() => {
    if (tab === undefined) {
      navigate(`/staff/book-drop/${DEFAULT_VIEW}`, { replace: true })
    } else if (!isViewMode(tab)) {
      navigate(`/staff/book-drop/${DEFAULT_VIEW}`, { replace: true })
    }
  }, [tab, navigate])

  const setViewMode = useCallback((next: ViewMode) => {
    navigate(`/staff/book-drop/${next}`)
  }, [navigate])

  const handleRefresh = useCallback(() => {
    switch (viewMode) {
      case "locations":
        queryClient.invalidateQueries({ queryKey: ["book-drops"] })
        break
      case "sessions":
      case "process":
        queryClient.invalidateQueries({ queryKey: sessionsQueryKey })
        queryClient.invalidateQueries({ queryKey: activeSessionsQueryKey })
        break
      case "exceptions":
        queryClient.invalidateQueries({ queryKey: ["book-drop-exceptions"] })
        break
      case "statistics":
        queryClient.invalidateQueries({ queryKey: ["book-drop-stats"] })
        break
    }
  }, [viewMode, queryClient])

  const handleSaveBookDrop = useCallback(async () => {
    const success = await bookDropsHook.handleSaveBookDrop()
    if (success) setModalType(null)
  }, [bookDropsHook])

  const handleDeleteBookDrop = useCallback(async () => {
    if (!deletingItem) return
    const success = await bookDropsHook.handleDeleteBookDrop(deletingItem)
    if (success) setDeletingItem(null)
  }, [deletingItem, bookDropsHook])

  const handleStartSession = useCallback(async () => {
    const success = await processingHook.handleStartSession()
    if (success) {
      setModalType(null)
      setViewMode("process")
    }
  }, [processingHook, setViewMode])

  const handleEndSession = useCallback(
    (sessionId: number) => processingHook.handleEndSession(sessionId),
    [processingHook]
  )

  const handleSelectSession = useCallback(
    (session: CheckInSession) => processingHook.handleSelectSession(session),
    [processingHook]
  )

  const handleResolveException = useCallback(
    async (action: string) => {
      if (!selectedException) return
      const success = await exceptionsHook.handleResolveException(selectedException.id, action)
      if (success) {
        setModalType(null)
        setSelectedException(null)
      }
    },
    [selectedException, exceptionsHook]
  )

  const pendingExceptionsCount = exceptionsHook.exceptions.length
  const todayCheckins = statsHook.todaySummary?.total_checkins ?? null

  const viewOptions: ReadonlyArray<{ id: ViewMode; label: string; icon: typeof MapPin }> = [
    { id: "locations", label: "Locations", icon: MapPin },
    { id: "sessions", label: "Sessions", icon: History },
    { id: "process", label: "Process Returns", icon: Package },
    { id: "exceptions", label: "Exceptions", icon: AlertTriangle },
    { id: "statistics", label: "Statistics", icon: BarChart3 },
  ]

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === "patron") {
    return <></>
  }

  return (
    <AdminShell title="Book Drop Operations">
      <div>
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Book Drop Operations
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Manage book drops, process returns, and handle exceptions
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            {viewMode === "locations" && (
              <button
                onClick={() => {
                  bookDropsHook.resetForm()
                  setModalType("bookdrop")
                }}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <Plus className="w-4 h-4" />
                New Book Drop
              </button>
            )}
            {(viewMode === "sessions" || viewMode === "process") && (
              <button
                onClick={() => setModalType("session")}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <Play className="w-4 h-4" />
                Start Session
              </button>
            )}
            <button
              onClick={() => navigate("/staff/book-drop/fast-process")}
              className="flex items-center gap-2 px-4 py-2 border border-lsc-rose text-lsc-rose dark:text-lsc-rose-light dark:border-lsc-rose-light hover:bg-lsc-rose/10 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              title={t('bookDropManagement.fastContinuousScanningItemsIn')}
            >
              <Zap className="w-4 h-4" />
              Fast Process
            </button>
          </div>
        </div>

        {/* Quick Stats — fetched independently of active view */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              <Inbox className="w-4 h-4" />
              <span className="text-xs uppercase">Book Drops</span>
            </div>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {bookDropsHook.bookDrops.filter((d) => d.status === "active").length}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Active locations</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              <Activity className="w-4 h-4" />
              <span className="text-xs uppercase">Active Sessions</span>
            </div>
            <p className="text-2xl font-bold text-lsc-green dark:text-status-success-400">
              {processingHook.activeSessions.length}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Currently processing</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              <AlertCircle className="w-4 h-4" />
              <span className="text-xs uppercase">Exceptions</span>
            </div>
            <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
              {pendingExceptionsCount}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Pending resolution</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              <CheckCircle className="w-4 h-4" />
              <span className="text-xs uppercase">Today's Check-ins</span>
            </div>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {todayCheckins ?? "-"}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Across all branches</p>
          </div>
        </div>

        {/* View Toggle (tablist) */}
        <div
          role="tablist"
          aria-label="Book drop views"
          className="flex flex-wrap items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl w-fit"
        >
          {viewOptions.map(({ id, label, icon: Icon }) => {
            const selected = viewMode === id
            return (
              <button
                key={id}
                role="tab"
                type="button"
                aria-selected={selected}
                aria-label={label}
                tabIndex={selected ? 0 : -1}
                onClick={() => setViewMode(id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
                  selected
                    ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
                    : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                }`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            )
          })}
        </div>

        {/* Content Views */}
        {viewMode === "locations" && (
          <BookDropList
            bookDrops={bookDropsHook.bookDrops}
            isLoading={bookDropsHook.isLoading}
            filter={bookDropsHook.bookDropFilter}
            onFilterChange={bookDropsHook.setBookDropFilter}
            onProcess={(drop) => {
              bookDropsHook.setSelectedItem(drop)
              setViewMode("process")
            }}
            onEdit={bookDropsHook.openEditBookDrop}
            onDelete={(drop) => setDeletingItem(drop)}
            onAddNew={() => {
              bookDropsHook.resetForm()
              setModalType("bookdrop")
            }}
          />
        )}

        {viewMode === "sessions" && (
          <>
            {processingHook.activeSessions.length > 0 && (
              <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-4">
                <h3 className="font-serif font-semibold text-status-success-700 dark:text-status-success-400 mb-3 flex items-center gap-2">
                  <Activity className="w-5 h-5" aria-hidden="true" />
                  Active Sessions
                </h3>
                <div className="grid gap-3">
                  {processingHook.activeSessions.map((session) => (
                    <div
                      key={session.id}
                      className="bg-lsc-white dark:bg-earth-800 rounded-lg p-3 flex items-center justify-between"
                    >
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {session.session_code}
                        </p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {session.branch_location} | {session.total_items} items
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            handleSelectSession(session)
                            setViewMode("process")
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-status-success-700 dark:text-status-success-400 hover:bg-status-success-100 dark:hover:bg-status-success-900/30 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                        >
                          <Play className="w-4 h-4" aria-hidden="true" />
                          Continue
                        </button>
                        <button
                          onClick={() => handleEndSession(session.id)}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                        >
                          <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                          End
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  Recent Sessions
                </h3>
              </div>
              {processingHook.isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
                </div>
              ) : processingHook.sessions.length === 0 ? (
                <div className="p-8 text-center">
                  <History className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4 opacity-50" aria-hidden="true" />
                  <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                    No Sessions Found
                  </h3>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    Start a new check-in session to begin processing returns
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-lsc-cream dark:bg-earth-700">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                          Session
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                          Branch
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                          Items
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                      {processingHook.sessions.map((session) => (
                        <tr
                          key={session.id}
                          className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors"
                        >
                          <td className="px-4 py-3 whitespace-nowrap font-medium text-lsc-dark dark:text-lsc-cream">
                            {session.session_code}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-lsc-dark dark:text-lsc-cream">
                            {session.branch_location}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-lsc-dark dark:text-lsc-cream">
                            {session.total_items}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${sessionStatusBadgeClass(session.status)}`}>
                              {session.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}

        {viewMode === "process" && (
          <>
            <BookDropProcessingPanel
              currentSession={processingHook.currentSession}
              activeSessions={processingHook.activeSessions}
              barcodeInput={processingHook.barcodeInput}
              isProcessing={processingHook.isProcessing}
              onBarcodeChange={processingHook.setBarcodeInput}
              onSubmit={processingHook.handleCheckIn}
              onEndSession={() => {
                if (processingHook.currentSession) {
                  handleEndSession(processingHook.currentSession.id)
                }
              }}
              onSelectSession={() => setViewMode("sessions")}
              onStartSession={() => setModalType("session")}
            />
            <BookDropItemsPanel results={processingHook.recentResults} />
          </>
        )}

        {viewMode === "exceptions" && (
          <BookDropExceptionsPanel
            exceptions={exceptionsHook.exceptions}
            isLoading={exceptionsHook.isLoading}
            filter={exceptionsHook.filter}
            onFilterChange={exceptionsHook.setFilter as (filter: string) => void}
            onResolve={(exception) => {
              setSelectedException(exception)
              setModalType("resolve")
            }}
          />
        )}

        {viewMode === "statistics" && (
          <BookDropStatsPanel
            summary={statsHook.statisticsSummary}
            isLoading={statsHook.isLoading}
            dateRange={statsHook.statsDateRange}
            onDateRangeChange={statsHook.setStatsDateRange}
            onUpdate={() => queryClient.invalidateQueries({ queryKey: ["book-drop-stats"] })}
          />
        )}

        {/* Modals */}
        {modalType === "bookdrop" && (
          <BookDropDetail
            form={bookDropsHook.bookDropForm}
            isEditing={bookDropsHook.isEditing}
            isSaving={bookDropsHook.isSaving}
            onFormChange={bookDropsHook.setBookDropForm}
            onSave={handleSaveBookDrop}
            onCancel={() => {
              setModalType(null)
              bookDropsHook.resetForm()
            }}
          />
        )}

        {modalType === "session" && token && (
          <SessionModal
            form={processingHook.sessionForm}
            isSaving={processingHook.isSaving}
            bookDrops={bookDropsHook.bookDrops}
            onFormChange={processingHook.setSessionForm}
            onSubmit={handleStartSession}
            onCancel={() => setModalType(null)}
          />
        )}

        {modalType === "resolve" && selectedException && (
          <ResolveExceptionModal
            exception={selectedException}
            isSaving={exceptionsHook.isSaving}
            onSubmit={handleResolveException}
            onCancel={() => {
              setModalType(null)
              setSelectedException(null)
            }}
          />
        )}

        {deletingItem && (
          <DeleteConfirmModal
            itemName={deletingItem.name}
            isDeleting={bookDropsHook.isDeleting}
            onConfirm={handleDeleteBookDrop}
            onCancel={() => setDeletingItem(null)}
          />
        )}
      </div>
    </AdminShell>
  )
}
