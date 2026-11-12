/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { ShieldAlert, Eye } from 'lucide-react'
import { clsx } from '@/utils/helpers'

interface ContentWarningBadgesProps {
  warnings: string[]
  flaggedWarnings?: string[]
  hiddenWarnings?: string[]
}

export default function ContentWarningBadges({
  warnings,
  flaggedWarnings = [],
  hiddenWarnings = [],
}: ContentWarningBadgesProps): React.ReactElement | null {
  const [showHidden, setShowHidden] = useState(false)

  if (!warnings || warnings.length === 0) return null

  const hasHidden = warnings.some((w) => hiddenWarnings.includes(w.toLowerCase()))

  if (hasHidden && !showHidden) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs px-2 py-1 bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 rounded flex items-center gap-1">
          <ShieldAlert className="w-3 h-3" aria-hidden="true" />
          Content warnings hidden
        </span>
        <button
          onClick={() => setShowHidden(true)}
          className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-rose flex items-center gap-1"
          aria-label="Show hidden content warnings"
        >
          <Eye className="w-3 h-3" />
          Show anyway
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap gap-1">
      {warnings.map((warning) => {
        const lower = warning.toLowerCase()
        const isFlagged = flaggedWarnings.includes(lower)
        return (
          <span
            key={warning}
            className={clsx(
              'text-xs px-2 py-0.5 rounded',
              isFlagged
                ? 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300'
                : 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300'
            )}
          >
            {warning}
          </span>
        )
      })}
    </div>
  )
}
