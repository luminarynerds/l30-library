/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ChevronDown, FileText } from 'lucide-react'
import { MarkdownContent } from '../MarkdownContent'

interface Props {
  notes: string | null | undefined
  userRole: string | undefined
}

const STAFF_ROLES = ['staff', 'admin', 'super_admin']

export function FacilitatorNotes({ notes, userRole }: Props) {
  if (!notes || !userRole || !STAFF_ROLES.includes(userRole)) return null

  return (
    <div className="mt-6 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-dashed border-lsc-rose/30 dark:border-lsc-rose/20 overflow-hidden">
      <details className="group">
        <summary className="cursor-pointer p-4 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light flex items-center gap-2">
          <FileText aria-hidden="true" className="w-4 h-4" />
          Facilitator Notes
          <ChevronDown
            aria-hidden="true"
            className="w-4 h-4 group-open:rotate-180 transition-transform"
          />
        </summary>
        <div className="px-4 pb-4 prose dark:prose-invert max-w-none text-sm">
          <MarkdownContent content={notes} />
        </div>
      </details>
    </div>
  )
}
