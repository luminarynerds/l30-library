/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ChevronDown } from 'lucide-react'

export interface ProbeLogEntry {
  ts: Date
  integrationId: string
  integrationName: string
  status: 'ok' | 'error' | 'unconfigured'
  detail?: string | null
}

interface ProbeLogProps {
  log: ProbeLogEntry[]
  maxRows?: number
}

function formatTime(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

function statusBadgeClass(status: ProbeLogEntry['status']): string {
  switch (status) {
    case 'ok':
      return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
    case 'error':
      return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-900 dark:text-status-danger-200'
    case 'unconfigured':
    default:
      return 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
  }
}

export function ProbeLog({ log, maxRows = 50 }: ProbeLogProps): JSX.Element {
  const rows = log.slice(0, maxRows)

  return (
    <details className="mt-8 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-sm group">
      <summary className="cursor-pointer list-none px-5 py-3 flex items-center justify-between gap-3 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors rounded-xl">
        <div className="flex items-center gap-2">
          {/* TODO: i18n -- adminIntegrations.probeLogTitle */}
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Recent probes
          </h2>
          <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
            ({rows.length})
          </span>
        </div>
        <ChevronDown
          className="w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50 group-open:rotate-180 transition-transform"
          aria-hidden="true"
        />
      </summary>

      <div className="border-t border-lsc-border dark:border-earth-700 max-h-80 overflow-y-auto">
        {rows.length === 0 ? (
          <p className="px-5 py-6 text-sm text-center text-lsc-dark/60 dark:text-lsc-cream/60">
            No probes run yet this session.
          </p>
        ) : (
          <ul className="divide-y divide-lsc-border/50 dark:divide-earth-700/50">
            {rows.map((entry, idx) => (
              <li
                key={`${entry.ts.getTime()}-${entry.integrationId}-${idx}`}
                className="px-5 py-2 grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm"
              >
                <time
                  className="font-mono text-xs text-lsc-dark/60 dark:text-lsc-cream/60"
                  dateTime={entry.ts.toISOString()}
                >
                  {formatTime(entry.ts)}
                </time>
                <div className="min-w-0">
                  <p className="text-lsc-dark dark:text-lsc-cream truncate">
                    {entry.integrationName}
                  </p>
                  {entry.detail ? (
                    <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 truncate">
                      {entry.detail}
                    </p>
                  ) : null}
                </div>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded ${statusBadgeClass(entry.status)}`}
                >
                  {entry.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </details>
  )
}

export default ProbeLog
