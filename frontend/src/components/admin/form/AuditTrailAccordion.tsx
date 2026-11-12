/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { Calendar, ChevronDown, ChevronRight } from 'lucide-react'

export interface AuditTrailChange {
  field: string
  before: string | number
  after: string | number
}

export interface AuditTrailEntry {
  timestamp: string
  updated_by: string
  changes: AuditTrailChange[]
}

export interface AuditTrailAccordionProps {
  entries: ReadonlyArray<AuditTrailEntry>
  title?: string
  maxShown?: number
  defaultOpen?: boolean
  fieldLabelMap?: Record<string, string>
}

export function AuditTrailAccordion({
  entries,
  title = 'Audit Trail',
  maxShown = 20,
  defaultOpen = false,
  fieldLabelMap,
}: AuditTrailAccordionProps): React.ReactElement {
  const [open, setOpen] = useState(defaultOpen)
  const visible = entries.slice(0, maxShown)
  const hasMore = entries.length > maxShown

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 border border-lsc-border dark:border-earth-700">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center gap-2 text-lg font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
      >
        {open ? (
          <ChevronDown className="w-5 h-5" aria-hidden="true" />
        ) : (
          <ChevronRight className="w-5 h-5" aria-hidden="true" />
        )}
        <Calendar className="w-5 h-5" aria-hidden="true" />
        {title} ({entries.length})
      </button>

      {open && entries.length > 0 && (
        <div className="mt-4 space-y-3 border-t border-lsc-border dark:border-earth-700 pt-4">
          {visible.map((entry, idx) => (
            <div
              key={`${entry.timestamp}-${idx}`}
              className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg text-sm"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  By: {entry.updated_by}
                </span>
              </div>
              <div className="space-y-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                {entry.changes.map((change, cidx) => (
                  <div key={cidx} className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {fieldLabelMap?.[change.field] ?? change.field}:
                    </span>
                    <span className="text-status-danger-600 dark:text-status-danger-400">{change.before}</span>
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true">
                      →
                    </span>
                    <span className="text-status-success-600 dark:text-status-success-400">{change.after}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {hasMore && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 pt-2">
              Showing latest {maxShown} entries. Total entries: {entries.length}
            </p>
          )}
        </div>
      )}

      {open && entries.length === 0 && (
        <p className="mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No audit history yet.</p>
      )}
    </div>
  )
}
