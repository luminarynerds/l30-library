/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Up Next rail: chronological worklist scoped to the signed-in coordinator.
 *
 * Collapses what used to be three separate panels (Recent Sessions, Overdue
 * Check-ins, Upcoming Home Visits) into one date-bucketed list. See spec
 * 2026-05-18-l30-parent-onboarding-dashboard-up-next-rail.md.
 *
 * A11y notes:
 *   - The rail is a single landmark <section aria-labelledby="up-next-heading">.
 *   - Bucket sub-headers are <h3>; counts are inline visible text, not aria-label only.
 *   - Each row is a <Link>; ChevronRight is aria-hidden. Entity word ("Session",
 *     "Check-in", "Home visit") is part of the visible row, so colour-by-entity
 *     never carries meaning alone (WCAG 1.4.1).
 *   - The rail itself sits inside an aria-live="polite" wrapper so screen
 *     readers hear "Up Next updated" after a refresh without stealing focus.
 *   - Fade-in animation is gated on `motion-safe:` (Tailwind) so
 *     prefers-reduced-motion suppresses it.
 */
import { Link } from 'react-router-dom'
import { ChevronRight, AlertTriangle, Calendar, Clock, Home, type LucideIcon } from 'lucide-react'
import type { RailItem, UpNextBuckets } from './bucketUpNext'
import type { RiskLevel } from '@/api/parent-onboarding-api'

interface UpNextRailProps {
  buckets: UpNextBuckets
  t: (k: string, fallback?: string, opts?: Record<string, string | number>) => string
}

interface BucketProps {
  headingId: string
  title: string
  items: RailItem[]
  emptyText: string
  countLabel: (n: number) => string
  t: UpNextRailProps['t']
  /** Variant tunes the empty-state colour: 'danger' for Overdue, 'muted' otherwise. */
  variant?: 'danger' | 'muted'
}

const ENTITY_ICON: Record<RailItem['entity'], LucideIcon> = {
  session: Calendar,
  assignment: Clock,
  visit: Home,
}

/**
 * Tailwind classes for the row's left rail-edge. Colour is decorative: the
 * entity word is also in the visible link text so screen readers and
 * non-colour-perceiving users get the entity from the words, not the swatch.
 */
const ENTITY_EDGE_CLASS: Record<RailItem['entity'], string> = {
  session: 'border-l-status-info-400 dark:border-l-status-info-500',
  assignment: 'border-l-lsc-rose dark:border-l-status-danger-400',
  visit: 'border-l-teal-500 dark:border-l-teal-400',
}

function entityLabel(item: RailItem, t: UpNextRailProps['t']): string {
  switch (item.entity) {
    case 'session':
      return t('parentOnboarding.dashboard.upNext.entitySession', 'Session')
    case 'assignment':
      return t('parentOnboarding.dashboard.upNext.entityAssignment', 'Check-in')
    case 'visit':
      return t('parentOnboarding.dashboard.upNext.entityVisit', 'Home visit')
  }
}

function RiskBadge({ level, t }: { level: RiskLevel; t: UpNextRailProps['t'] }) {
  const isHigh = level === 'high'
  const isMedium = level === 'medium'
  const tone = isHigh
    ? 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300 border border-status-danger-300 dark:border-status-danger-700'
    : isMedium
    ? 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    : 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
  const urgencySuffix = isHigh ? ` - ${t('common.urgent', 'urgent')}` : ''
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${tone}`}
      aria-label={`${t('common.riskLevel', 'Risk level')}: ${level}${urgencySuffix}`}
    >
      {isHigh && <AlertTriangle aria-hidden="true" className="w-3 h-3" />}
      {level}
    </span>
  )
}

function RailRow({ item, t }: { item: RailItem; t: UpNextRailProps['t'] }) {
  const EntityIcon = ENTITY_ICON[item.entity]
  const label = entityLabel(item, t)
  // Accessible name: "<entity> - <patron> - <date>[ at <time>]"
  // The visible text contains the same words so colour isn't the only signal.
  const dateTimeSpoken = item.time ? `${item.date} ${item.time}` : item.date
  const accessibleName = `${label} - ${item.patronName} - ${dateTimeSpoken}`

  return (
    <li>
      <Link
        to={item.link}
        aria-label={accessibleName}
        className={`group flex items-center gap-3 p-3 rounded-lg border-l-4 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 ${ENTITY_EDGE_CLASS[item.entity]} hover:border-lsc-rose/30 transition-colors motion-safe:transition-opacity focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:outline-none`}
      >
        <EntityIcon
          className="w-4 h-4 shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70"
          aria-hidden={true}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {label}
            </span>
            {item.entity === 'visit' && item.visitPurpose && (
              <span className="text-xs italic text-lsc-dark/60 dark:text-lsc-cream/60">
                {item.visitPurpose.replace(/_/g, ' ')}
              </span>
            )}
            <span className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 truncate">
              {item.patronName}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
              {item.entity === 'assignment'
                ? t('parentOnboarding.dashboard.upNext.dueLabel', 'Due {date}').replace('{date}', item.date)
                : item.date}
              {item.time ? ` ${t('parentOnboarding.dashboard.upNext.atTime', 'at {time}').replace('{time}', item.time)}` : ''}
            </span>
            {item.entity === 'assignment' && item.riskLevel && (
              <RiskBadge level={item.riskLevel} t={t} />
            )}
          </div>
        </div>
        <ChevronRight
          className="w-4 h-4 shrink-0 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose transition-colors"
          aria-hidden={true}
        />
      </Link>
    </li>
  )
}

function Bucket({ headingId, title, items, emptyText, countLabel, t, variant = 'muted' }: BucketProps) {
  const isEmpty = items.length === 0
  const emptyClass =
    variant === 'danger' && isEmpty
      ? 'text-lsc-dark/60 dark:text-lsc-cream/60'
      : 'text-lsc-dark/60 dark:text-lsc-cream/60'

  return (
    <section aria-labelledby={headingId} className="space-y-2">
      <h3
        id={headingId}
        className={`text-sm font-semibold uppercase tracking-wide ${
          isEmpty ? 'text-lsc-dark/50 dark:text-lsc-cream/50' : 'text-lsc-dark dark:text-lsc-cream'
        }`}
      >
        <span>{title}</span>{' '}
        <span className="text-lsc-dark/60 dark:text-lsc-cream/60 font-normal">
          {countLabel(items.length)}
        </span>
      </h3>
      {isEmpty ? (
        <p className={`text-sm pl-1 ${emptyClass}`}>{emptyText}</p>
      ) : (
        <ul className="space-y-2 list-none p-0">
          {items.map((item) => (
            <RailRow key={item.key} item={item} t={t} />
          ))}
        </ul>
      )}
    </section>
  )
}

export default function UpNextRail({ buckets, t }: UpNextRailProps) {
  const countLabel = (n: number): string =>
    t('parentOnboarding.dashboard.upNext.bucketCount', '({count})').replace('{count}', String(n))

  return (
    <section
      aria-labelledby="up-next-heading"
      aria-live="polite"
      className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 space-y-5"
    >
      <h2
        id="up-next-heading"
        className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
      >
        {t('parentOnboarding.dashboard.upNext.heading', 'Up Next')}
      </h2>

      <Bucket
        headingId="up-next-overdue"
        title={t('parentOnboarding.dashboard.upNext.bucketOverdue', 'Overdue')}
        items={buckets.overdue}
        emptyText={t('parentOnboarding.dashboard.upNext.emptyOverdue', 'Nothing overdue. Nice work.')}
        countLabel={countLabel}
        t={t}
        variant="danger"
      />

      <Bucket
        headingId="up-next-today"
        title={t('parentOnboarding.dashboard.upNext.bucketToday', 'Today')}
        items={buckets.today}
        emptyText={t('parentOnboarding.dashboard.upNext.emptyToday', 'Nothing scheduled today.')}
        countLabel={countLabel}
        t={t}
      />

      <Bucket
        headingId="up-next-this-week"
        title={t('parentOnboarding.dashboard.upNext.bucketThisWeek', 'This Week')}
        items={buckets.thisWeek}
        emptyText={t('parentOnboarding.dashboard.upNext.emptyThisWeek', 'Nothing scheduled this week.')}
        countLabel={countLabel}
        t={t}
      />
    </section>
  )
}
