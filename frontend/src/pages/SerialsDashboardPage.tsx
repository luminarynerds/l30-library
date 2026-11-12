/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Newspaper,
  CalendarClock,
  AlertTriangle,
  Inbox,
  CheckCircle2,
  Clock,
  BookOpen,
  ArrowRight,
} from 'lucide-react'
import * as Sentry from "@/lib/sentry-lazy"
import { AdminShell } from '../components/shells'
import { getSerialsDashboard, type SerialsDashboard } from '../api/domains/admin/serials-api'

interface KPI {
  label: string
  value: number
  icon: React.ElementType
  tone: 'neutral' | 'warning' | 'danger' | 'success'
  href?: string
  hint?: string
}

const TONE_CLASSES: Record<KPI['tone'], string> = {
  neutral: 'bg-earth-50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-700',
  warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-900 dark:text-status-warning-200 border-status-warning-200 dark:border-status-warning-800',
  danger: 'bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-900 dark:text-status-danger-200 border-status-danger-200 dark:border-status-danger-800',
  success: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-900 dark:text-status-success-200 border-status-success-200 dark:border-status-success-800',
}

export default function SerialsDashboardPage(): React.ReactElement {
  const [data, setData] = useState<SerialsDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data-fetching effect
    setLoading(true)
    getSerialsDashboard()
      .then((d) => {
        if (!cancelled) setData(d)
      })
      .catch((e: unknown) => {
        Sentry.captureException(e instanceof Error ? e : new Error(String(e)))
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load serials dashboard')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const kpis: KPI[] = data
    ? [
        {
          label: 'Expected today',
          value: data.expected_today,
          icon: CalendarClock,
          tone: 'neutral',
          href: '/staff/admin/serials/issues?status=expected',
          hint: 'Issues due to arrive today',
        },
        {
          label: 'Overdue',
          value: data.overdue_count,
          icon: AlertTriangle,
          tone: data.overdue_count > 0 ? 'warning' : 'neutral',
          href: '/staff/admin/serials/issues?status=late',
          hint: 'Past expected delivery date',
        },
        {
          label: 'Claimed',
          value: data.claimed_count,
          icon: Inbox,
          tone: data.claimed_count > 0 ? 'danger' : 'neutral',
          href: '/staff/admin/serials/issues?status=claimed',
          hint: 'Outstanding claims with vendors',
        },
        {
          label: 'Received this week',
          value: data.received_this_week,
          icon: CheckCircle2,
          tone: 'success',
          href: '/staff/admin/serials/issues?status=received',
        },
        {
          label: 'Subscriptions expiring (30 days)',
          value: data.expiring_subscriptions,
          icon: Clock,
          tone: data.expiring_subscriptions > 0 ? 'warning' : 'neutral',
          hint: 'Renewal review needed',
        },
        {
          label: 'Active titles',
          value: data.total_active_titles,
          icon: BookOpen,
          tone: 'neutral',
          href: '/staff/admin/serials/titles',
        },
        {
          label: 'Active subscriptions',
          value: data.total_active_subscriptions,
          icon: Newspaper,
          tone: 'neutral',
        },
      ]
    : []

  return (
    <AdminShell
      title="Serials Dashboard"
      subtitle="Periodicals, journals, and standing orders"
      icon={<Newspaper className="w-7 h-7 text-lsc-rose" />}
      loading={loading}
      error={error}
      actions={
        <Link
          to="/staff/admin/serials/titles"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors text-sm font-medium"
        >
          Manage titles
          <ArrowRight className="w-4 h-4" />
        </Link>
      }
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon
          const card = (
            <div
              className={`p-5 rounded-xl border ${TONE_CLASSES[kpi.tone]} transition-shadow ${
                kpi.href ? 'hover:shadow-md cursor-pointer' : ''
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <Icon className="w-5 h-5" aria-hidden="true" />
                {kpi.href && <ArrowRight className="w-4 h-4 opacity-50" aria-hidden="true" />}
              </div>
              <div className="text-3xl font-bold tabular-nums">{kpi.value}</div>
              <div className="mt-1 text-sm font-medium">{kpi.label}</div>
              {kpi.hint && <div className="mt-1 text-xs opacity-70">{kpi.hint}</div>}
            </div>
          )
          return kpi.href ? (
            <Link key={kpi.label} to={kpi.href} className="block">
              {card}
            </Link>
          ) : (
            <div key={kpi.label}>{card}</div>
          )
        })}
      </div>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/staff/admin/serials/issues"
          className="p-5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose transition-colors group"
        >
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose mb-1">
            Check in issues
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Mark received issues, bulk check-in by barcode or list.
          </p>
        </Link>
        <Link
          to="/staff/admin/serials/titles"
          className="p-5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose transition-colors group"
        >
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose mb-1">
            Manage titles
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Add new periodicals, edit ISSNs, and configure prediction patterns.
          </p>
        </Link>
        <Link
          to="/staff/admin/serials/issues?status=late"
          className="p-5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose transition-colors group"
        >
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose mb-1">
            Resolve overdue
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            File claims for issues that haven&apos;t arrived.
          </p>
        </Link>
      </div>
    </AdminShell>
  )
}
