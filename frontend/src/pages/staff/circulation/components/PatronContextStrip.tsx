/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { Bookmark, Truck, DollarSign, Clock, Loader2 } from "lucide-react"
import { fetchApi } from "@/api/fetchApi"
import { useTranslation, formatCurrency } from "@/i18n"

export type PatronContextStripSection = "holds" | "transit" | "fines" | "checkouts"

export interface PatronContextStripProps {
  patronId: number
  patronName: string
  onTileClick?: (section: PatronContextStripSection) => void
}

interface ContextCardData {
  checkouts: {
    due_soon_items: Array<{ id: number; title: string; due_date: string }>
  }
  holds: {
    ready_for_pickup_count: number
    in_transit_count: number
  }
  fines?: { total_owed: number } | null
}

const isDueToday = (iso: string): boolean => {
  const due = new Date(iso)
  const now = new Date()
  return (
    due.getFullYear() === now.getFullYear() &&
    due.getMonth() === now.getMonth() &&
    due.getDate() === now.getDate()
  )
}

const defaultScrollTo = (section: PatronContextStripSection): void => {
  const targetId = `circulation-${section}-section`
  const el = typeof document !== "undefined" ? document.getElementById(targetId) : null
  if (el && typeof el.scrollIntoView === "function") {
    el.scrollIntoView({ block: "nearest", behavior: "smooth" })
  }
}

interface TileProps {
  icon: React.ReactNode
  label: string
  value: string
  count: number
  ariaLabel: string
  onClick: () => void
  testId: string
}

function Tile({ icon, label, value, count, ariaLabel, onClick, testId }: TileProps) {
  const muted = count === 0
  const baseClasses =
    "flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-colors min-w-[8rem] flex-1 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1"
  const activeClasses =
    "bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:border-lsc-rose dark:hover:border-lsc-rose-light cursor-pointer"
  const mutedClasses =
    "bg-earth-50 dark:bg-earth-900 border-earth-200 dark:border-earth-800 text-earth-500 dark:text-earth-500 cursor-default"
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={muted ? undefined : onClick}
      disabled={muted}
      aria-label={ariaLabel}
      aria-disabled={muted}
      className={`${baseClasses} ${muted ? mutedClasses : activeClasses}`}
    >
      <span aria-hidden="true" className="flex-shrink-0">{icon}</span>
      <span className="flex flex-col leading-tight">
        <span className="text-lg font-semibold">{value}</span>
        <span className="text-xs">{label}</span>
      </span>
    </button>
  )
}

export function PatronContextStrip({ patronId, patronName, onTileClick }: PatronContextStripProps) {
  const { t, language } = useTranslation()
  const [state, setState] = useState<{ patronId: number | null; data: ContextCardData | null }>({
    patronId: null,
    data: null,
  })

  const handleClick = (section: PatronContextStripSection) => {
    if (onTileClick) {
      onTileClick(section)
    } else {
      defaultScrollTo(section)
    }
  }

  useEffect(() => {
    let cancelled = false
    fetchApi(`/staff/patrons/${patronId}/context-card`)
      .then((d: ContextCardData) => {
        if (!cancelled) setState({ patronId, data: d })
      })
      .catch(() => {
        if (!cancelled) setState({ patronId, data: null })
      })
    return () => {
      cancelled = true
    }
  }, [patronId])

  const loading = state.patronId !== patronId
  const data = loading ? null : state.data

  if (loading) {
    return (
      <div
        data-testid="patron-context-strip-loading"
        className="flex items-center gap-3 p-3 rounded-xl bg-lsc-cream dark:bg-earth-800/50 border border-lsc-border dark:border-earth-700"
        role="status"
        aria-label={t('staffCirculation.contextStrip.loadingAriaLabel')}
      >
        <Loader2 className="w-4 h-4 text-lsc-rose motion-safe:animate-spin" aria-hidden="true" />
        <span className="text-sm text-earth-600 dark:text-earth-300">{t('staffCirculation.contextStrip.loadingText')}</span>
      </div>
    )
  }

  if (!data) return null

  const holdsReady = data.holds.ready_for_pickup_count
  const inTransit = data.holds.in_transit_count
  const finesOwed = data.fines?.total_owed ?? 0
  const dueToday = data.checkouts.due_soon_items.filter((i) => isDueToday(i.due_date)).length

  const finesValue = formatCurrency(finesOwed, language, 'USD')

  return (
    <div
      data-testid="patron-context-strip"
      className="flex flex-wrap items-stretch gap-2 mb-3"
      aria-label={t('staffCirculation.contextStrip.atAGlance', { name: patronName })}
    >
      <Tile
        testId="patron-context-strip-holds"
        icon={<Bookmark className="w-5 h-5" />}
        label={holdsReady === 1 ? t('staffCirculation.contextStrip.holdReadyOne') : t('staffCirculation.contextStrip.holdReadyOther')}
        value={String(holdsReady)}
        count={holdsReady}
        ariaLabel={holdsReady === 1
          ? t('staffCirculation.contextStrip.holdsAriaOne', { count: holdsReady, name: patronName })
          : t('staffCirculation.contextStrip.holdsAriaOther', { count: holdsReady, name: patronName })}
        onClick={() => handleClick("holds")}
      />
      <Tile
        testId="patron-context-strip-transit"
        icon={<Truck className="w-5 h-5" />}
        label={inTransit === 1 ? t('staffCirculation.contextStrip.itemInTransitOne') : t('staffCirculation.contextStrip.itemInTransitOther')}
        value={String(inTransit)}
        count={inTransit}
        ariaLabel={inTransit === 1
          ? t('staffCirculation.contextStrip.transitAriaOne', { count: inTransit, name: patronName })
          : t('staffCirculation.contextStrip.transitAriaOther', { count: inTransit, name: patronName })}
        onClick={() => handleClick("transit")}
      />
      <Tile
        testId="patron-context-strip-fines"
        icon={<DollarSign className="w-5 h-5" />}
        label={t('staffCirculation.contextStrip.owed')}
        value={finesValue}
        count={finesOwed > 0 ? 1 : 0}
        ariaLabel={t('staffCirculation.contextStrip.finesAria', { amount: finesValue, name: patronName })}
        onClick={() => handleClick("fines")}
      />
      <Tile
        testId="patron-context-strip-due-today"
        icon={<Clock className="w-5 h-5" />}
        label={t('staffCirculation.contextStrip.dueToday')}
        value={String(dueToday)}
        count={dueToday}
        ariaLabel={dueToday === 1
          ? t('staffCirculation.contextStrip.dueTodayAriaOne', { count: dueToday, name: patronName })
          : t('staffCirculation.contextStrip.dueTodayAriaOther', { count: dueToday, name: patronName })}
        onClick={() => handleClick("checkouts")}
      />
    </div>
  )
}
