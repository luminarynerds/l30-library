/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { ChevronDown, ChevronUp, CheckCircle, XCircle, Clock, Info } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { BibframeInstance, BibframeItemRecord } from '@/api/domains/catalog/bibframe-api'

function CirculationBadge({ status }: { status: string | null }): React.ReactElement {
  const cfg: Record<string, { label: string; className: string; icon: React.ReactNode }> = {
    available: {
      label: 'Available',
      className: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/40 dark:text-status-success-300',
      icon: <CheckCircle className="w-3 h-3" aria-hidden="true" />,
    },
    checked_out: {
      label: 'Checked Out',
      className: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/40 dark:text-status-warning-300',
      icon: <Clock className="w-3 h-3" aria-hidden="true" />,
    },
    on_hold: {
      label: 'On Hold',
      className: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/40 dark:text-lsc-rose-light',
      icon: <Clock className="w-3 h-3" aria-hidden="true" />,
    },
    lost: {
      label: 'Lost',
      className: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/40 dark:text-status-danger-300',
      icon: <XCircle className="w-3 h-3" aria-hidden="true" />,
    },
  }

  const raw = (status ?? 'unknown').toLowerCase()
  const c = cfg[raw] ?? {
    label: status ?? 'Unknown',
    className: 'bg-lsc-cream text-lsc-dark dark:bg-earth-700 dark:text-lsc-cream',
    icon: <Info className="w-3 h-3" aria-hidden="true" />,
  }

  return (
    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', c.className)}>
      {c.icon}
      {c.label}
    </span>
  )
}

function ItemRow({ item }: { item: BibframeItemRecord }): React.ReactElement {
  return (
    <tr className="border-t border-lsc-border/40 dark:border-earth-700/40 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/20 transition-colors">
      <td className="py-2 px-3 text-sm font-mono text-lsc-dark dark:text-lsc-cream">{item.barcode ?? '—'}</td>
      <td className="py-2 px-3 text-sm text-lsc-dark dark:text-lsc-cream">{item.call_number ?? '—'}</td>
      <td className="py-2 px-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">{item.library_branch ?? '—'}</td>
      <td className="py-2 px-3">
        <CirculationBadge status={item.circulation_status} />
      </td>
    </tr>
  )
}

interface InstancePanelProps {
  instance: BibframeInstance
  index: number
}

export function InstancePanel({ instance, index }: InstancePanelProps): React.ReactElement {
  const [expanded, setExpanded] = useState(index === 0)

  const availableCount = instance.items.filter(
    (it) => (it.circulation_status ?? '').toLowerCase() === 'available'
  ).length

  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start justify-between gap-3 px-4 py-3 bg-lsc-cream/60 dark:bg-earth-800/60 hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors text-left"
        aria-expanded={expanded}
      >
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={instance.title ?? `Edition ${index + 1}`}>
              {instance.title ?? `Edition ${index + 1}`}
            </span>
            {instance.instance_type && (
              <span className="text-xs px-2 py-0.5 rounded bg-lsc-rose/10 text-lsc-rose dark:text-lsc-rose-light">
                {instance.instance_type}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex-wrap">
            {instance.publisher && (
              <span>{instance.publisher}</span>
            )}
            {instance.publication_date && (
              <span>{instance.publication_date}</span>
            )}
            {instance.isbn_13 && (
              <span className="font-mono">ISBN {instance.isbn_13}</span>
            )}
            {instance.media_type && (
              <span className="capitalize">{instance.media_type}</span>
            )}
            {instance.carrier_type && (
              <span className="capitalize">{instance.carrier_type}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {instance.items.length > 0 && (
            <span className={clsx(
              'text-xs px-2 py-0.5 rounded-full font-medium',
              availableCount > 0
                ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/40 dark:text-status-success-300'
                : 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700 dark:text-lsc-cream/70'
            )}>
              {availableCount}/{instance.items.length} available
            </span>
          )}
          {expanded
            ? <ChevronUp className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            : <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          }
        </div>
      </button>

      {expanded && (
        <div className="bg-lsc-white dark:bg-earth-800">
          {instance.items.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 px-4 py-3 italic">
              No physical copies recorded for this edition.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" aria-label={`Copies of ${instance.title ?? 'this edition'}`}>
                <thead>
                  <tr className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide border-b border-lsc-border dark:border-earth-700">
                    <th className="py-2 px-3 text-left">Barcode</th>
                    <th className="py-2 px-3 text-left">Call Number</th>
                    <th className="py-2 px-3 text-left">Branch</th>
                    <th className="py-2 px-3 text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {instance.items.map((item) => (
                    <ItemRow key={item.id} item={item} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
