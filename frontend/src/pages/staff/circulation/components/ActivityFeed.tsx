/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef } from "react"
import { LogIn, LogOut, RefreshCw, Clock } from "lucide-react"
import { useTranslation } from "@/i18n"

export type ActivityType = "checkout" | "checkin" | "renewal"

export interface ActivityEntry {
  id: string
  type: ActivityType
  title: string
  barcode?: string
  patronName?: string
  timestamp: Date
}

interface ActivityFeedProps {
  entries: ActivityEntry[]
}

const ICON_MAP = {
  checkout: LogOut,
  checkin: LogIn,
  renewal: RefreshCw,
}

const COLOR_MAP = {
  checkout: "text-lsc-rose",
  checkin: "text-status-success-600 dark:text-status-success-400",
  renewal: "text-category-600 dark:text-category-400",
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

export function ActivityFeed({ entries }: ActivityFeedProps): React.ReactElement {
  const { t } = useTranslation()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [entries.length])

  if (entries.length === 0) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <h3 className="font-serif text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
          <Clock className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
          {t('staffCirculation.sessionActivity')}
        </h3>
        <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 text-center py-3">{t('staffCirculation.noActivityYet')}</p>
      </div>
    )
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
      <h3 className="font-serif text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
        <Clock className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
        {t('staffCirculation.sessionActivity')}
        <span className="ml-auto text-xs font-normal text-lsc-dark/50 dark:text-lsc-cream/50">{entries.length}</span>
      </h3>
      <div className="max-h-48 overflow-y-auto space-y-1">
        {entries.map((entry) => {
          const Icon = ICON_MAP[entry.type]
          return (
            <div key={entry.id} className="flex items-center gap-2 py-1 text-xs">
              <Icon className={`w-3.5 h-3.5 shrink-0 ${COLOR_MAP[entry.type]}`} aria-hidden="true" />
              <span className="flex-1 truncate text-lsc-dark dark:text-lsc-cream">{entry.title}</span>
              {entry.barcode && <code className="text-lsc-dark/70 dark:text-lsc-cream/70 font-mono hidden sm:block">{entry.barcode}</code>}
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums shrink-0">{formatTime(entry.timestamp)}</span>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
