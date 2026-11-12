/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import type { ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

export const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900'

export const REDACTED_CTX = {
  tags: { group_type: '[redacted]' },
  extra: { group_id: '[redacted]' },
} as const

export const inputCls =
  'mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose'

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/70">
        {title}
      </h3>
      {children}
    </section>
  )
}
export function Field({
  label, required, children,
}: { label: string; required?: boolean; children: ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
        {label}
        {required && <span className="text-status-danger-600 ml-1">*</span>}
      </span>
      {children}
    </label>
  )
}

export function ModalFooter({
  onCancel, cancelLabel, submitLabel, submitting, submitDisabled, destructive,
}: {
  onCancel: () => void
  cancelLabel: string
  submitLabel: string
  submitting?: boolean
  submitDisabled?: boolean
  destructive?: boolean
}) {
  return (
    <div className="flex justify-end gap-2 pt-4 border-t border-lsc-border dark:border-earth-700">
      <button
        type="button"
        onClick={onCancel}
        className={`px-4 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
      >
        {cancelLabel}
      </button>
      <button
        type="submit"
        disabled={submitting || submitDisabled}
        className={`inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg text-white disabled:opacity-50 ${
          destructive ? 'bg-status-danger-600 hover:bg-status-danger-700' : 'bg-lsc-rose hover:bg-lsc-rose/90'
        } ${FOCUS_RING}`}
      >
        {submitting && <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
        {submitLabel}
      </button>
    </div>
  )
}
