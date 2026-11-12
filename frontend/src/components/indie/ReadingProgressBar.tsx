/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { clsx } from "@/utils/helpers"

interface ReadingProgressBarProps {
  percent: number
  className?: string
}

function getLabel(percent: number): string {
  if (percent < 5) return "Just started"
  if (percent > 90) return "Almost done"
  return `${percent}% complete`
}

export default function ReadingProgressBar({ percent, className }: ReadingProgressBarProps) {
  if (percent <= 0) return null

  return (
    <div className={clsx("flex items-center gap-2", className)}>
      <div
        className="flex-1 h-1.5 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={getLabel(percent)}
      >
        <div
          className="h-full bg-lsc-blue rounded-full transition-all duration-300"
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      <span className="text-xs text-earth-600 dark:text-earth-400 whitespace-nowrap">
        {getLabel(percent)}
      </span>
    </div>
  )
}
