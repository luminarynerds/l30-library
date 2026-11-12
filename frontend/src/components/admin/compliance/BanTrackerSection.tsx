/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '@/api/types'
import {
  ShieldAlert,
  BookOpen,
  MapPin,
  AlertTriangle,
  RefreshCw,
  Loader2,
  FileText,
} from 'lucide-react'
import toast from 'react-hot-toast'

import api from '@/lib/api-client'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation } from '@/i18n'
import ConfirmDialog from '@/components/ConfirmDialog'
import { formatDate } from '@/components/ban-tracker/ban-tracker-data'
import { SectionShell } from '../ai-settings/SectionShell'
import { MatchesTab } from '@/components/ban-tracker/MatchesTab'
import { AllReportsTab } from '@/components/ban-tracker/AllReportsTab'
import { LetterTemplatesTab } from '@/components/ban-tracker/LetterTemplatesTab'
import type {
  AdminBanStats,
  BanReportMatch,
  AdminBanReport,
  AlertCount,
  SyncStatus,
  LetterTemplate,
  PaginatedResponse,
  BanReportFormData,
  LetterTemplateFormData,
} from '@/components/ban-tracker/types'

const EMPTY_REPORT_FORM: BanReportFormData = {
  title: '',
  author: '',
  isbn: '',
  state: '',
  district: '',
  institution: '',
  ban_type: 'challenged',
  reason: '',
  reason_category: '',
  source: '',
  source_url: '',
  date_reported: new Date().toISOString().split('T')[0] ?? '',
  notes: '',
}

const EMPTY_TEMPLATE_FORM: LetterTemplateFormData = {
  title: '',
  subject_line: '',
  body_template: '',
  target_level: 'any',
  is_active: true,
}

// Backend returns by_type as a {type: count} map; derive the leading entry.
// Returns ['None', 0] when there are no reports, so the stat card never reads
// a method off undefined (was the crash: top_ban_type_count.toLocaleString()).
function topByType(byType: Record<string, number>): [string, number] {
  const entries = Object.entries(byType ?? {})
  if (entries.length === 0) return ['None', 0]
  return entries.reduce((a, b) => (b[1] > a[1] ? b : a))
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string
  color: string
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

const TABS = [
  { id: 'matches', label: 'Catalog Matches', icon: ShieldAlert },
  { id: 'all', label: 'All Reports', icon: BookOpen },
  { id: 'templates', label: 'Letter Templates', icon: FileText },
] as const

function TabContent({
  activeTab,
  onFetchData,
  statsLoading,
  stats,
  matches,
  matchesLoading,
  alertCount,
  onMarkAllSeen,
  fetchMatches,
  reports,
  reportsLoading,
  reportSearch,
  setReportSearch,
  reportStateFilter,
  setReportStateFilter,
  reportTypeFilter,
  setReportTypeFilter,
  reportPage,
  reportTotalPages,
  reportTotal,
  setReportPage,
  showReportForm,
  setShowReportForm,
  reportForm,
  setReportForm,
  handleSubmitReport,
  reportSubmitting,
  templates,
  templatesLoading,
  showTemplateForm,
  setShowTemplateForm,
  editingTemplateId,
  setEditingTemplateId,
  templateForm,
  setTemplateForm,
  handleSubmitTemplate,
  handleEditTemplate,
  handleDeleteTemplate,
  handleToggleTemplateActive,
  templateSubmitting,
  expandedTemplateId,
  setExpandedTemplateId,
  isAdmin,
  syncStatus,
  syncing,
  handleSync,
}: {
  activeTab: string
  onFetchData: (tab: string) => void
  statsLoading: boolean
  stats: AdminBanStats | null
  matches: BanReportMatch[]
  matchesLoading: boolean
  alertCount: number
  onMarkAllSeen: () => void
  fetchMatches: () => void
  reports: AdminBanReport[]
  reportsLoading: boolean
  reportSearch: string
  setReportSearch: (v: string) => void
  reportStateFilter: string
  setReportStateFilter: (v: string) => void
  reportTypeFilter: string
  setReportTypeFilter: (v: string) => void
  reportPage: number
  reportTotalPages: number
  reportTotal: number
  setReportPage: (v: number) => void
  showReportForm: boolean
  setShowReportForm: (v: boolean) => void
  reportForm: BanReportFormData
  setReportForm: (v: BanReportFormData) => void
  handleSubmitReport: (e: React.FormEvent) => void
  reportSubmitting: boolean
  templates: LetterTemplate[]
  templatesLoading: boolean
  showTemplateForm: boolean
  setShowTemplateForm: (v: boolean) => void
  editingTemplateId: number | null
  setEditingTemplateId: (v: number | null) => void
  templateForm: LetterTemplateFormData
  setTemplateForm: (v: LetterTemplateFormData) => void
  handleSubmitTemplate: (e: React.FormEvent) => void
  handleEditTemplate: (t: LetterTemplate) => void
  handleDeleteTemplate: (id: number) => void
  handleToggleTemplateActive: (t: LetterTemplate) => void
  templateSubmitting: boolean
  expandedTemplateId: number | null
  setExpandedTemplateId: (v: number | null) => void
  isAdmin: boolean
  syncStatus: SyncStatus | null
  syncing: boolean
  handleSync: () => void
}) {
  useEffect(() => {
    onFetchData(activeTab)
  }, [activeTab, onFetchData])

  return (
    <>
      {/* Stats Header */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 motion-safe:animate-pulse"
            >
              <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-1/2 mb-2" />
              <div className="h-8 bg-earth-200 dark:bg-earth-700 rounded w-1/3" />
            </div>
          ))
        ) : stats ? (
          <>
            <StatCard
              icon={ShieldAlert}
              label="Total Reports"
              value={(stats.total_reports ?? 0).toLocaleString()}
              color="text-status-danger-600 dark:text-status-danger-400"
            />
            <StatCard
              icon={MapPin}
              label="States Affected"
              value={String(stats.total_states)}
              color="text-lsc-rose dark:text-lsc-rose-light"
            />
            <StatCard
              icon={BookOpen}
              label="Catalog Matches"
              value={String(stats.total_catalog_matches)}
              color="text-lsc-rose"
            />
            <StatCard
              icon={AlertTriangle}
              label={`Top: ${topByType(stats.by_type)[0]}`}
              value={topByType(stats.by_type)[1].toLocaleString()}
              color="text-status-warning-600 dark:text-status-warning-400"
            />
          </>
        ) : (
          <div className="col-span-full text-center py-4 text-lsc-dark/70 dark:text-lsc-cream/70">
            Unable to load statistics
          </div>
        )}
      </div>

      {activeTab === 'matches' && (
        <MatchesTab
          matches={matches}
          loading={matchesLoading}
          alertCount={alertCount}
          onMarkAllSeen={onMarkAllSeen}
          onRefresh={fetchMatches}
        />
      )}

      {activeTab === 'all' && (
        <AllReportsTab
          reports={reports}
          loading={reportsLoading}
          search={reportSearch}
          onSearchChange={setReportSearch}
          stateFilter={reportStateFilter}
          onStateFilterChange={setReportStateFilter}
          typeFilter={reportTypeFilter}
          onTypeFilterChange={setReportTypeFilter}
          page={reportPage}
          totalPages={reportTotalPages}
          total={reportTotal}
          onPageChange={setReportPage}
          showForm={showReportForm}
          onToggleForm={() => {
            setShowReportForm(!showReportForm)
            if (showReportForm) setReportForm(EMPTY_REPORT_FORM)
          }}
          form={reportForm}
          onFormChange={setReportForm}
          onSubmitReport={handleSubmitReport}
          submitting={reportSubmitting}
        />
      )}

      {activeTab === 'templates' && (
        <LetterTemplatesTab
          templates={templates}
          loading={templatesLoading}
          showForm={showTemplateForm}
          editingId={editingTemplateId}
          form={templateForm}
          onFormChange={setTemplateForm}
          onToggleForm={() => {
            setShowTemplateForm(!showTemplateForm)
            if (showTemplateForm) {
              setEditingTemplateId(null)
              setTemplateForm(EMPTY_TEMPLATE_FORM)
            }
          }}
          onSubmit={handleSubmitTemplate}
          onEdit={handleEditTemplate}
          onDelete={handleDeleteTemplate}
          onToggleActive={handleToggleTemplateActive}
          submitting={templateSubmitting}
          expandedId={expandedTemplateId}
          onToggleExpand={(id) =>
            setExpandedTemplateId(expandedTemplateId === id ? null : id)
          }
        />
      )}

      {isAdmin && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 mt-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <RefreshCw className="w-5 h-5" />
                Data Sync
              </h3>
              {syncStatus && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Last sync: {syncStatus.last_sync_at ? formatDate(syncStatus.last_sync_at) : 'Never'}
                  {syncStatus.status === 'completed' && (
                    <span className="ml-2 text-status-success-600 dark:text-status-success-400">
                      ({syncStatus.records_synced} records)
                    </span>
                  )}
                  {syncStatus.status === 'failed' && (
                    <span className="ml-2 text-status-danger-600 dark:text-status-danger-400">
                      Failed: {syncStatus.error_message}
                    </span>
                  )}
                  {syncStatus.status === 'running' && (
                    <span className="ml-2 text-lsc-rose">Running...</span>
                  )}
                </p>
              )}
            </div>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
            >
              {syncing ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Sync Now
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export function BanTrackerSection({ onBack }: { onBack: () => void }) {
  const { t } = useTranslation()
  const { user } = useAuth()

  const [stats, setStats] = useState<AdminBanStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const [matches, setMatches] = useState<BanReportMatch[]>([])
  const [matchesLoading, setMatchesLoading] = useState(false)
  const [alertCount, setAlertCount] = useState(0)

  const [reports, setReports] = useState<AdminBanReport[]>([])
  const [reportsLoading, setReportsLoading] = useState(false)
  const [reportSearch, setReportSearch] = useState('')
  const [reportStateFilter, setReportStateFilter] = useState('')
  const [reportTypeFilter, setReportTypeFilter] = useState('')
  const [reportPage, setReportPage] = useState(1)
  const [reportTotalPages, setReportTotalPages] = useState(1)
  const [reportTotal, setReportTotal] = useState(0)
  const [showReportForm, setShowReportForm] = useState(false)
  const [reportForm, setReportForm] = useState<BanReportFormData>(EMPTY_REPORT_FORM)
  const [reportSubmitting, setReportSubmitting] = useState(false)

  const [templates, setTemplates] = useState<LetterTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [showTemplateForm, setShowTemplateForm] = useState(false)
  const [editingTemplateId, setEditingTemplateId] = useState<number | null>(null)
  const [templateForm, setTemplateForm] = useState<LetterTemplateFormData>(EMPTY_TEMPLATE_FORM)
  const [templateSubmitting, setTemplateSubmitting] = useState(false)
  const [expandedTemplateId, setExpandedTemplateId] = useState<number | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [syncing, setSyncing] = useState(false)

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'

  const fetchStats = useCallback(async () => {
    setStatsLoading(true)
    try {
      const data = await api.get(`${API_BASE}/ban-tracker/reports/stats`)
      setStats(data as AdminBanStats)
    } catch {
      setStats(null)
    } finally {
      setStatsLoading(false)
    }
  }, [])

  const fetchAlertCount = useCallback(async () => {
    try {
      const data = (await api.get(`${API_BASE}/ban-tracker/alerts/count`)) as AlertCount
      setAlertCount(data.unseen_count)
    } catch {
      setAlertCount(0)
    }
  }, [])

  const fetchMatches = useCallback(async () => {
    setMatchesLoading(true)
    try {
      const data = (await api.get(`${API_BASE}/ban-tracker/reports/matches`)) as PaginatedResponse<BanReportMatch>
      setMatches(data.items)
    } catch (err: unknown) {
      const message = (err as { message?: string })?.message || 'Failed to load matches'
      toast.error(message)
    } finally {
      setMatchesLoading(false)
    }
  }, [])

  const fetchReports = useCallback(async () => {
    setReportsLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', String(reportPage))
      params.set('per_page', '20')
      if (reportSearch) params.set('search', reportSearch)
      if (reportStateFilter) params.set('state', reportStateFilter)
      if (reportTypeFilter) params.set('ban_type', reportTypeFilter)
      const data = (await api.get(
        `${API_BASE}/ban-tracker/reports?${params.toString()}`
      )) as PaginatedResponse<AdminBanReport>
      setReports(data.items)
      setReportTotalPages(data.pages)
      setReportTotal(data.total)
    } catch (err: unknown) {
      const message = (err as { message?: string })?.message || 'Failed to load reports'
      toast.error(message)
    } finally {
      setReportsLoading(false)
    }
  }, [reportPage, reportSearch, reportStateFilter, reportTypeFilter])

  const fetchTemplates = useCallback(async () => {
    setTemplatesLoading(true)
    try {
      const data = (await api.get(`${API_BASE}/advocacy/letter-templates`)) as LetterTemplate[]
      setTemplates(data)
    } catch (err: unknown) {
      const message = (err as { message?: string })?.message || 'Failed to load templates'
      toast.error(message)
    } finally {
      setTemplatesLoading(false)
    }
  }, [])

  const fetchSyncStatus = useCallback(async () => {
    try {
      const data = (await api.get(`${API_BASE}/ban-tracker/sync/status`)) as SyncStatus
      setSyncStatus(data)
    } catch {
      setSyncStatus(null)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    fetchAlertCount()
    if (isAdmin) fetchSyncStatus()
  }, [fetchStats, fetchAlertCount, fetchSyncStatus, isAdmin])

  const handleTabData = useCallback(
    (tab: string) => {
      if (tab === 'matches') fetchMatches()
      else if (tab === 'all') fetchReports()
      else if (tab === 'templates') fetchTemplates()
    },
    [fetchMatches, fetchReports, fetchTemplates]
  )

  const handleMarkAllSeen = async () => {
    try {
      await api.post(`${API_BASE}/ban-tracker/alerts/mark-all-seen`)
      setAlertCount(0)
      toast.success(t('admin.adminBanTracker.allAlertsMarkedAsSeen'))
    } catch (err: unknown) {
      const message = (err as { message?: string })?.message || 'Failed to mark alerts'
      toast.error(message)
    }
  }

  const handleSubmitReport = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reportForm.title.trim() || !reportForm.author.trim()) {
      toast.error(t('admin.adminBanTracker.titleAndAuthorAreRequired'))
      return
    }
    setReportSubmitting(true)
    try {
      await api.post(`${API_BASE}/ban-tracker/reports`, reportForm)
      toast.success(t('toast.adminBanTracker.reportAddedSuccessfully'))
      setShowReportForm(false)
      setReportForm(EMPTY_REPORT_FORM)
      fetchReports()
      fetchStats()
    } catch (err: unknown) {
      const message = (err as { message?: string })?.message || 'Failed to add report'
      toast.error(message)
    } finally {
      setReportSubmitting(false)
    }
  }

  const handleSubmitTemplate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!templateForm.title.trim() || !templateForm.body_template.trim()) {
      toast.error(t('admin.adminBanTracker.titleAndBodyAreRequired'))
      return
    }
    setTemplateSubmitting(true)
    try {
      if (editingTemplateId) {
        await api.put(`${API_BASE}/advocacy/letter-templates/${editingTemplateId}`, templateForm)
        toast.success(t('toast.adminBanTracker.templateUpdated'))
      } else {
        await api.post(`${API_BASE}/advocacy/letter-templates`, templateForm)
        toast.success(t('toast.adminBanTracker.templateCreated'))
      }
      setShowTemplateForm(false)
      setEditingTemplateId(null)
      setTemplateForm(EMPTY_TEMPLATE_FORM)
      fetchTemplates()
    } catch (err: unknown) {
      const message = (err as { message?: string })?.message || 'Failed to save template'
      toast.error(message)
    } finally {
      setTemplateSubmitting(false)
    }
  }

  const handleDeleteTemplate = (id: number) => {
    setPendingAction(() => async () => {
      try {
        await api.delete(`${API_BASE}/advocacy/letter-templates/${id}`)
        toast.success(t('toast.adminBanTracker.templateDeleted'))
        fetchTemplates()
      } catch (err: unknown) {
        const message = (err as { message?: string })?.message || 'Failed to delete template'
        toast.error(message)
      }
    })
    setConfirmOpen(true)
  }

  const handleToggleTemplateActive = async (template: LetterTemplate) => {
    try {
      await api.put(`${API_BASE}/advocacy/letter-templates/${template.id}`, {
        ...template,
        is_active: !template.is_active,
      })
      toast.success(template.is_active ? 'Template deactivated' : 'Template activated')
      fetchTemplates()
    } catch (err: unknown) {
      const message = (err as { message?: string })?.message || 'Failed to update template'
      toast.error(message)
    }
  }

  const handleEditTemplate = (template: LetterTemplate) => {
    setEditingTemplateId(template.id)
    setTemplateForm({
      title: template.title,
      subject_line: template.subject_line,
      body_template: template.body_template,
      target_level: template.target_level,
      is_active: template.is_active,
    })
    setShowTemplateForm(true)
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      await api.post(`${API_BASE}/ban-tracker/sync`)
      toast.success(t('toast.adminBanTracker.syncStarted'))
      setTimeout(async () => {
        await fetchSyncStatus()
        await fetchStats()
        setSyncing(false)
      }, 3000)
    } catch (err: unknown) {
      const message = (err as { message?: string })?.message || 'Failed to start sync'
      toast.error(message)
      setSyncing(false)
    }
  }

  return (
    <>
      <SectionShell
        title="Book Challenge Tracker"
        description="Track book challenges, bans, and your library's response. Public transparency page included."
        tabs={[...TABS]}
        onBack={onBack}
      >
        {(activeTab) => (
          <TabContent
            activeTab={activeTab}
            onFetchData={handleTabData}
            statsLoading={statsLoading}
            stats={stats}
            matches={matches}
            matchesLoading={matchesLoading}
            alertCount={alertCount}
            onMarkAllSeen={handleMarkAllSeen}
            fetchMatches={fetchMatches}
            reports={reports}
            reportsLoading={reportsLoading}
            reportSearch={reportSearch}
            setReportSearch={setReportSearch}
            reportStateFilter={reportStateFilter}
            setReportStateFilter={setReportStateFilter}
            reportTypeFilter={reportTypeFilter}
            setReportTypeFilter={setReportTypeFilter}
            reportPage={reportPage}
            reportTotalPages={reportTotalPages}
            reportTotal={reportTotal}
            setReportPage={setReportPage}
            showReportForm={showReportForm}
            setShowReportForm={setShowReportForm}
            reportForm={reportForm}
            setReportForm={setReportForm}
            handleSubmitReport={handleSubmitReport}
            reportSubmitting={reportSubmitting}
            templates={templates}
            templatesLoading={templatesLoading}
            showTemplateForm={showTemplateForm}
            setShowTemplateForm={setShowTemplateForm}
            editingTemplateId={editingTemplateId}
            setEditingTemplateId={setEditingTemplateId}
            templateForm={templateForm}
            setTemplateForm={setTemplateForm}
            handleSubmitTemplate={handleSubmitTemplate}
            handleEditTemplate={handleEditTemplate}
            handleDeleteTemplate={handleDeleteTemplate}
            handleToggleTemplateActive={handleToggleTemplateActive}
            templateSubmitting={templateSubmitting}
            expandedTemplateId={expandedTemplateId}
            setExpandedTemplateId={setExpandedTemplateId}
            isAdmin={isAdmin}
            syncStatus={syncStatus}
            syncing={syncing}
            handleSync={handleSync}
          />
        )}
      </SectionShell>
      <ConfirmDialog
        isOpen={confirmOpen}
        title="Delete this letter template?"
        message="This cannot be undone."
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
        onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
      />
    </>
  )
}
