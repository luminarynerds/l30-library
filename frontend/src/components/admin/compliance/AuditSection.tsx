/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  FileBarChart,
  FileText,
  Loader2,
  Lock,
  RefreshCw,
  Scan,
  Shield,
  ShieldAlert,
  Users,
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import type { OfficerDashboard } from '@/api/unified-compliance-api'
import {
  getDashboard,
  runComplianceScan,
} from '@/api/unified-compliance-api'
import { t } from '@/i18n'
import { SectionShell } from '../ai-settings/SectionShell'

const REGULATION_LABELS: Record<string, string> = {
  cipa: 'CIPA',
  coppa: 'COPPA',
  ferpa: 'FERPA',
  gdpr: 'GDPR',
  ada: 'ADA',
  pci_dss: 'PCI DSS',
  state_library: 'State Library',
  state_privacy: 'State Privacy',
  foia: 'FOIA',
  ecpa: 'ECPA',
  custom: 'Custom',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-200',
  major: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200',
  high: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200',
  medium: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200',
  minor: 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light/80',
  low: 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light/80',
  near_miss: 'bg-earth-100 dark:bg-earth-900/30 text-earth-800 dark:text-earth-200',
}

const TABS = [
  { id: 'overview', label: 'Overview', icon: Shield },
  { id: 'violations', label: 'Violations', icon: AlertTriangle },
  { id: 'incidents', label: 'Incidents', icon: AlertCircle },
  { id: 'audit-trail', label: 'Audit Trail', icon: ClipboardCheck },
  { id: 'reports', label: 'Reports', icon: FileBarChart },
] as const

function ScoreRing({ score }: { score: number }) {
  const radius = 45
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color =
    score >= 90 ? 'text-status-success-500' : score >= 70 ? 'text-status-warning-500' : 'text-status-danger-500'

  return (
    <div className="relative w-32 h-32">
      <svg className="w-32 h-32 -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50" cy="50" r={radius}
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          className="text-lsc-border dark:text-earth-700"
        />
        <circle
          cx="50" cy="50" r={radius}
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={color}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
          {score}%
        </span>
      </div>
    </div>
  )
}

interface AuditSectionProps {
  onBack: () => void
}

export function AuditSection({ onBack }: AuditSectionProps) {
  const [dashboard, setDashboard] = useState<OfficerDashboard | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)

  const fetchDashboard = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await getDashboard()
      setDashboard(data)
    } catch (_err: unknown) {
      setError('Failed to load compliance dashboard')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard()
  }, [])

  const handleScan = async () => {
    setIsScanning(true)
    try {
      const result = await runComplianceScan()
      toast.success(t('toast.unifiedComplianceAudit.scanCompleteViolationsfoundViolationsFound', { violationsfound: result.violations_found }))
      await fetchDashboard()
    } catch (_err: unknown) {
      toast.error(t('toast.unifiedComplianceAudit.complianceScanFailed'))
    } finally {
      setIsScanning(false)
    }
  }

  if (isLoading && !dashboard) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <Loader2 className="w-12 h-12 motion-safe:animate-spin text-lsc-rose mx-auto mb-4" />
          <p className="text-lsc-dark dark:text-lsc-cream">
            Loading unified compliance dashboard...
          </p>
        </div>
      </div>
    )
  }

  if (error && !dashboard) {
    return (
      <div className="p-6">
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
            <div>
              <h3 className="font-serif font-semibold text-status-danger-800 dark:text-status-danger-200">
                Error Loading Dashboard
              </h3>
              <p className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
                {error}
              </p>
            </div>
          </div>
          <button
            onClick={fetchDashboard}
            className="mt-4 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const totalViolations = dashboard?.violations.total_open ?? 0
  const totalIncidents = dashboard?.incidents.total_open ?? 0
  const pendingNotifications = dashboard?.incidents.pending_notifications ?? 0

  return (
    <SectionShell
      title="Compliance Overview"
      description="Cross-regulation compliance overview. Shows where your library stands across all requirements."
      tabs={[...TABS]}
      defaultTab="overview"
      onBack={onBack}
    >
      {(activeTab) => (
        <>
          {/* Action buttons */}
          <div className="flex items-center gap-3 mb-6">
            <button
              onClick={handleScan}
              disabled={isScanning}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-50 text-white rounded-lg transition-colors"
            >
              {isScanning ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <Scan className="w-4 h-4" />
              )}
              Run Scan
            </button>
            <button
              onClick={fetchDashboard}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-50 text-white rounded-lg transition-colors"
            >
              <RefreshCw className={clsx('w-4 h-4', isLoading && 'motion-safe:animate-spin')} />
              Refresh
            </button>
          </div>

          {activeTab === 'overview' && dashboard && (
            <>
              {/* Top KPI Row */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
                {/* Compliance Score */}
                <div className="lg:col-span-1 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6 flex flex-col items-center">
                  <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                    Compliance Score
                  </p>
                  <ScoreRing score={dashboard.compliance_score} />
                </div>

                {/* Requirements */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-status-success-100 dark:bg-status-success-900/30 rounded-lg flex items-center justify-center">
                      <ClipboardCheck className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
                    </div>
                    <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                      Requirements
                    </p>
                  </div>
                  <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {dashboard.requirements.total}
                  </p>
                  <div className="flex gap-2 mt-2 text-xs">
                    <span className="text-status-success-600 dark:text-status-success-400">
                      {(dashboard.requirements.by_status.verified ?? 0) +
                        (dashboard.requirements.by_status.implemented ?? 0)}{' '}
                      compliant
                    </span>
                    <span className="text-status-danger-600 dark:text-status-danger-400">
                      {dashboard.requirements.by_status.non_compliant ?? 0} non-compliant
                    </span>
                  </div>
                </div>

                {/* Open Violations */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-status-danger-100 dark:bg-status-danger-900/30 rounded-lg flex items-center justify-center">
                      <ShieldAlert className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
                    </div>
                    <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                      Open Violations
                    </p>
                  </div>
                  <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {totalViolations}
                  </p>
                  <div className="flex gap-2 mt-2 text-xs">
                    {Object.entries(dashboard.violations.open_by_severity).map(
                      ([sev, count]) => (
                        <span
                          key={sev}
                          className={clsx(
                            'px-1.5 py-0.5 rounded font-medium',
                            SEVERITY_COLORS[sev] ?? 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                          )}
                        >
                          {count} {sev}
                        </span>
                      )
                    )}
                  </div>
                </div>

                {/* Open Incidents */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-lg flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />
                    </div>
                    <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                      Open Incidents
                    </p>
                  </div>
                  <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {totalIncidents}
                  </p>
                  {pendingNotifications > 0 && (
                    <p className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-2 font-medium">
                      {pendingNotifications} pending notification(s)
                    </p>
                  )}
                </div>

                {/* Flagged Access */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-category-100 dark:bg-category-900/30 rounded-lg flex items-center justify-center">
                      <Users className="w-5 h-5 text-category-600 dark:text-category-400" />
                    </div>
                    <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                      Flagged Access (30d)
                    </p>
                  </div>
                  <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {dashboard.staff_access.flagged_last_30_days}
                  </p>
                  {dashboard.law_enforcement.pending_requests > 0 && (
                    <p className="text-xs text-status-warning-600 dark:text-status-warning-400 mt-2 font-medium">
                      {dashboard.law_enforcement.pending_requests} LE request(s) pending
                    </p>
                  )}
                </div>
              </div>

              {/* Regulation Breakdown */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                    <Shield className="w-5 h-5 text-lsc-rose" />
                    Compliance by Regulation
                  </h2>
                  <div className="space-y-3">
                    {Object.entries(dashboard.requirements.by_regulation).map(
                      ([reg, data]) => (
                        <div key={reg}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                              {REGULATION_LABELS[reg] ?? reg.toUpperCase()}
                            </span>
                            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {data.compliant}/{data.total} ({data.score}%)
                            </span>
                          </div>
                          <div className="w-full bg-lsc-border dark:bg-earth-700 rounded-full h-2">
                            <div
                              className={clsx(
                                'h-2 rounded-full transition-all',
                                data.score >= 90
                                  ? 'bg-status-success-500'
                                  : data.score >= 70
                                    ? 'bg-status-warning-500'
                                    : 'bg-status-danger-500'
                              )}
                              style={{ width: `${data.score}%` }}
                            />
                          </div>
                        </div>
                      )
                    )}
                    {Object.keys(dashboard.requirements.by_regulation).length === 0 && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-4">
                        No requirements registered yet
                      </p>
                    )}
                  </div>
                </div>

                {/* Upcoming Deadlines */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                    <CalendarDays className="w-5 h-5 text-lsc-rose" />
                    Upcoming Deadlines
                  </h2>
                  {dashboard.upcoming_deadlines.length === 0 ? (
                    <div className="text-center py-8">
                      <CheckCircle2 className="w-10 h-10 text-status-success-500 mx-auto mb-2 opacity-50" />
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        No upcoming deadlines
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-80 overflow-y-auto">
                      {dashboard.upcoming_deadlines.map((dl, i) => (
                        <div
                          key={i}
                          className={clsx(
                            'flex items-center justify-between p-3 rounded-lg',
                            dl.overdue
                              ? 'bg-status-danger-50 dark:bg-status-danger-900/10 border border-status-danger-200 dark:border-status-danger-800'
                              : 'bg-lsc-cream/50 dark:bg-earth-700/50'
                          )}
                        >
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={dl.title}>
                              {dl.title}
                            </p>
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              {REGULATION_LABELS[dl.regulation] ?? dl.regulation}
                            </p>
                          </div>
                          <div className="text-right flex-shrink-0 ml-3">
                            {dl.overdue ? (
                              <span className="text-xs font-bold text-status-danger-600 dark:text-status-danger-400">
                                {Math.abs(dl.days_until)}d overdue
                              </span>
                            ) : (
                              <span className="text-xs font-medium text-lsc-dark dark:text-lsc-cream">
                                {dl.days_until}d
                              </span>
                            )}
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              {dl.due_date}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  {
                    to: '/staff/admin/compliance/cipa',
                    icon: Shield,
                    label: 'CIPA Compliance',
                    color: 'bg-earth-100 dark:bg-earth-800/30',
                    iconColor: 'text-lsc-rose dark:text-lsc-rose-light',
                  },
                  {
                    to: '/staff/admin/law-enforcement',
                    icon: Lock,
                    label: 'Law Enforcement Requests',
                    color: 'bg-status-warning-100 dark:bg-status-warning-900/30',
                    iconColor: 'text-status-warning-600 dark:text-status-warning-400',
                  },
                  {
                    to: '/staff/admin/compliance/policies',
                    icon: FileText,
                    label: 'Policy Reviews',
                    color: 'bg-teal-100 dark:bg-teal-900/30',
                    iconColor: 'text-teal-600 dark:text-teal-400',
                  },
                  {
                    to: '/staff/admin/state-compliance',
                    icon: ClipboardCheck,
                    label: 'State Compliance',
                    color: 'bg-lsc-rose/10 dark:bg-lsc-rose/20',
                    iconColor: 'text-lsc-rose dark:text-lsc-rose-light',
                  },
                ].map(({ to, icon: Icon, label, color, iconColor }) => (
                  <Link
                    key={to}
                    to={to}
                    className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4 hover:shadow-md hover:border-lsc-rose/50 transition-all group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', color)}>
                          <Icon className={clsx('w-5 h-5', iconColor)} />
                        </div>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {label}
                        </span>
                      </div>
                      <ChevronRight className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60 group-hover:text-lsc-rose transition-colors" />
                    </div>
                  </Link>
                ))}
              </div>
            </>
          )}

          {activeTab === 'violations' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-status-danger-500" />
                Compliance Violations
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                View and manage detected compliance violations. Run a scan to detect new violations.
              </p>
              <button disabled title="Coming soon" className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose/60 text-white rounded-lg opacity-60 cursor-not-allowed">
                View All Violations <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {activeTab === 'incidents' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-status-warning-500" />
                Incident Reporting
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                Report, track, and manage compliance incidents through their full lifecycle.
                {pendingNotifications > 0 && (
                  <span className="ml-2 font-medium text-status-danger-600 dark:text-status-danger-400">
                    {pendingNotifications} incident(s) require regulatory notification.
                  </span>
                )}
              </p>
              <button disabled title="Coming soon" className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose/60 text-white rounded-lg opacity-60 cursor-not-allowed">
                View All Incidents <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {activeTab === 'audit-trail' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <ClipboardCheck className="w-5 h-5 text-lsc-rose" />
                Immutable Audit Trail
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                Tamper-evident, hash-chained audit log. Query who accessed what, when, and why.
                Verify chain integrity to detect any unauthorized modifications.
              </p>
              <div className="flex gap-3">
                <button disabled title="Coming soon" className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose/60 text-white rounded-lg opacity-60 cursor-not-allowed">
                  Browse Audit Trail <ChevronRight className="w-4 h-4" />
                </button>
                <button disabled title="Coming soon" className="inline-flex items-center gap-2 px-4 py-2 bg-category-600/60 text-white rounded-lg opacity-60 cursor-not-allowed">
                  <Users className="w-4 h-4" /> Staff Access Logs
                </button>
              </div>
            </div>
          )}

          {activeTab === 'reports' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <FileBarChart className="w-5 h-5 text-teal-500" />
                Compliance Reports
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                Generate reports for regulators and board: CIPA E-Rate, law enforcement transparency,
                board executive summary, staff access review, incident/violation summaries, and more.
              </p>
              <button disabled title="Coming soon" className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose/60 text-white rounded-lg opacity-60 cursor-not-allowed">
                View & Generate Reports <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
    </SectionShell>
  )
}
