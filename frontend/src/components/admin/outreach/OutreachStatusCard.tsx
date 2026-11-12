/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'
import { ChannelBadge, type ChannelType } from './ChannelBadge'

interface OutreachStatusCardProps {
  id: string
  icon: ReactNode
  title: string
  description: string
  channel: ChannelType
  statusLine: string | null
  statusError?: boolean
  onClick: (id: string) => void
}

export function OutreachStatusCard({
  id,
  icon,
  title,
  description,
  channel,
  statusLine,
  statusError,
  onClick,
}: OutreachStatusCardProps) {
  return (
    <button
      onClick={() => onClick(id)}
      className="w-full text-left bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5 hover:border-lsc-rose/50 dark:hover:border-lsc-rose/50 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 focus:ring-offset-2 dark:focus:ring-offset-earth-900 group"
      aria-label={`${title}. ${description}. Click to view details.`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-lsc-cream dark:bg-earth-700 rounded-lg" aria-hidden="true">
            {icon}
          </div>
          <div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h3>
            <ChannelBadge channel={channel} className="mt-1" />
          </div>
        </div>
        <ChevronRight
          className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/30 group-hover:text-lsc-rose transition-colors flex-shrink-0 mt-1"
          aria-hidden="true"
        />
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
        {description}
      </p>
      {statusLine && (
        <span className={`text-xs font-medium ${
          statusError
            ? 'text-lsc-dark/70 dark:text-lsc-cream/40'
            : 'text-lsc-dark/70 dark:text-lsc-cream/60'
        }`}>
          {statusLine}
        </span>
      )}
    </button>
  )
}
