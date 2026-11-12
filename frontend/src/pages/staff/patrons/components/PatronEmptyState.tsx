/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { Barcode, UserPlus, Users, ChevronDown } from "lucide-react"
import { useTranslation } from "@/i18n"
import { readRecentPatrons, type RecentPatronEntry } from "../utils/recentPatrons"

interface PatronEmptyStateProps {
  userId: number | null | undefined
  headline: string
  onScanCard: () => void
  onRegisterPatron: () => void
  onSelectRecent: (patronId: number) => void
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(diff / 86400000)
  return `${days}d ago`
}

export function PatronEmptyState({
  userId,
  headline,
  onScanCard,
  onRegisterPatron,
  onSelectRecent,
}: PatronEmptyStateProps): React.ReactElement {
  const { t } = useTranslation()
  const [recent, setRecent] = useState<RecentPatronEntry[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    setRecent(readRecentPatrons(userId))
  }, [userId])

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-12 text-center">
      <Users
        className="w-16 h-16 mx-auto mb-4 text-lsc-dark/30 dark:text-lsc-cream/30"
        aria-hidden="true"
      />
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
        {headline}
      </h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t("staffPatrons.emptyState.subtitle", "Pick how you want to start.")}
      </p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={onScanCard}
          className="flex items-center gap-2 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
        >
          <Barcode className="w-5 h-5" />
          {t("staffPatrons.emptyState.scanCard", "Scan card")}
        </button>
        <button
          onClick={onRegisterPatron}
          className="flex items-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/50 dark:hover:bg-earth-800 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium transition-colors"
        >
          <UserPlus className="w-5 h-5" />
          {t("staffPatrons.emptyState.registerPatron", "Register patron")}
        </button>

        <div className="relative">
          <button
            onClick={() => setOpen((v) => !v)}
            disabled={recent.length === 0}
            aria-haspopup="listbox"
            aria-expanded={open}
            className="flex items-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/50 dark:hover:bg-earth-800 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Users className="w-5 h-5" />
            {recent.length === 0
              ? t("staffPatrons.emptyState.noRecent", "No recent patrons")
              : t("staffPatrons.emptyState.openRecent", "Open recent patron")}
            <ChevronDown className="w-4 h-4" />
          </button>
          {open && recent.length > 0 && (
            <ul
              role="listbox"
              aria-label={t("staffPatrons.emptyState.recentList", "Recent patrons")}
              className="absolute z-10 mt-1 right-0 min-w-[240px] bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg shadow-lg overflow-hidden text-left"
            >
              {recent.map((entry) => (
                <li key={entry.id}>
                  <button
                    role="option"
                    aria-selected={false}
                    onClick={() => {
                      setOpen(false)
                      onSelectRecent(entry.id)
                    }}
                    className="w-full px-4 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/40 dark:hover:bg-earth-700 flex items-center justify-between gap-3"
                  >
                    <span className="truncate">{entry.displayName}</span>
                    <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 shrink-0">
                      {formatRelative(entry.viewedAt)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
