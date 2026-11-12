/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import {
  Mail,
  MessageSquare,
  CreditCard,
  HardDrive,
  Activity,
  KeyRound,
  Cpu,
  Settings,
  Loader2,
  Send,
} from 'lucide-react'
import type { IntegrationRow, IntegrationCategory } from '@/api/admin/integrations-api'

interface IntegrationCardProps {
  row: IntegrationRow
  onProbe: () => void
  onSendTest?: () => void
  probing: boolean
}

const CATEGORY_ICON: Record<IntegrationCategory, React.ElementType> = {
  Email: Mail,
  SMS: MessageSquare,
  Payments: CreditCard,
  Storage: HardDrive,
  Observability: Activity,
  Auth: KeyRound,
  AI: Cpu,
  Other: Settings,
}

interface StatusDisplay {
  dot: string
  label: string
  text: string
}

function getStatusDisplay(row: IntegrationRow): StatusDisplay {
  // TODO: i18n
  if (!row.configured) {
    return {
      dot: 'bg-earth-400 dark:bg-earth-500',
      label: 'Not configured',
      text: 'text-lsc-dark/60 dark:text-lsc-cream/60',
    }
  }
  if (row.status === 'ok') {
    return {
      dot: 'bg-status-success-500',
      label: 'Connected',
      text: 'text-status-success-700 dark:text-status-success-300',
    }
  }
  if (row.status === 'error') {
    return {
      dot: 'bg-status-danger-500',
      label: 'Failing',
      text: 'text-status-danger-700 dark:text-status-danger-300',
    }
  }
  // configured but never probed
  return {
    dot: 'bg-status-warning-500',
    label: 'Configured (not tested)',
    text: 'text-status-warning-700 dark:text-status-warning-300',
  }
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return 'Never tested' // TODO: i18n
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return 'Never tested'
  const diffMs = Date.now() - then
  const sec = Math.floor(diffMs / 1000)
  if (sec < 60) return 'just now'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} min ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} hr ago`
  return new Date(iso).toLocaleDateString()
}

export function IntegrationCard({
  row,
  onProbe,
  onSendTest,
  probing,
}: IntegrationCardProps): JSX.Element {
  const status = getStatusDisplay(row)
  const Icon = CATEGORY_ICON[row.category] ?? Settings
  const relTime = useMemo(() => formatRelativeTime(row.last_probe_at), [row.last_probe_at])

  const showEmailTestButton = row.category === 'Email' && typeof onSendTest === 'function'

  return (
    <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-sm p-5 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 p-2 rounded-lg flex-shrink-0">
          <Icon className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate">
            {row.name}
          </h3>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">{row.category}</p>
        </div>
      </div>

      {/* Status line */}
      <div className="flex items-center gap-2 text-sm">
        <span
          className={`inline-block w-2.5 h-2.5 rounded-full ${status.dot}`}
          aria-hidden="true"
        />
        <span className={`font-medium ${status.text}`}>{status.label}</span>
      </div>

      {/* Error detail (only when failing) */}
      {row.configured && row.status === 'error' && row.last_probe_detail && (
        <p className="text-xs text-status-danger-700 dark:text-status-danger-300 bg-status-danger-50 dark:bg-status-danger-900/20 rounded px-2 py-1 break-words">
          {row.last_probe_detail}
        </p>
      )}

      {/* Last test timestamp */}
      <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
        {/* TODO: i18n -- adminIntegrations.lastTested */}
        {row.last_probe_at ? `Last test: ${relTime}` : 'Never tested'}
      </p>

      {/* Actions */}
      <div className="flex flex-wrap gap-2 mt-auto pt-2">
        <button
          type="button"
          onClick={onProbe}
          disabled={probing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-60 disabled:cursor-not-allowed transition"
        >
          {probing ? (
            <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" aria-hidden="true" />
          ) : null}
          {/* TODO: i18n -- adminIntegrations.testButton */}
          <span>Test connection</span>
        </button>

        {showEmailTestButton && (
          <button
            type="button"
            onClick={onSendTest}
            disabled={probing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/40 dark:hover:bg-earth-700/60 disabled:opacity-60 disabled:cursor-not-allowed transition"
          >
            <Send className="w-3.5 h-3.5" aria-hidden="true" />
            {/* TODO: i18n -- adminIntegrations.sendTestEmailButton */}
            <span>Send test email to me</span>
          </button>
        )}
      </div>
    </div>
  )
}

export default IntegrationCard
