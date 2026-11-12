/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { MapPin, Library, ExternalLink } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { getBanTypeBadge, getBanTypeIcon, formatReason, formatSource, US_STATES_MAP } from './ban-tracker-data'
import type { BanReport } from './types'
import { parseDate } from '@/utils/format-utils'

export function ReportCard({ report }: { report: BanReport }): React.ReactElement {
  const { t } = useTranslation()
  const badge = getBanTypeBadge(report.ban_type)
  const icon = getBanTypeIcon(report.ban_type)

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream text-base leading-tight truncate" title={report.title}>
            {report.title}
          </h4>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
            by {report.author}
          </p>
        </div>
        {report.has_in_catalog && (
          <span
            className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300"
            title={t('publicBanTracker.availableInOurCatalog')}
          >
            <Library className="w-3 h-3" aria-hidden="true" />
            In Our Catalog
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 mt-3">
        {/* Ban type badge */}
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full ${badge.className}`}>
          {icon}
          {badge.label}
        </span>

        {/* State */}
        <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
          <MapPin className="w-3 h-3" aria-hidden="true" />
          {US_STATES_MAP[report.state] ?? report.state}
        </span>

        {/* Reason category */}
        <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300">
          {formatReason(report.reason_category)}
        </span>

        {/* Source attribution */}
        {report.source && (
          <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
            via {formatSource(report.source)}
          </span>
        )}
      </div>

      {report.district && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-2">
          District: {report.district}
        </p>
      )}
      {report.date_reported && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
          Reported: {parseDate(report.date_reported)?.toLocaleDateString() ?? '-'}
        </p>
      )}
      {report.source_url && (
        <a
          href={report.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-lsc-rose dark:text-lsc-rose-light hover:underline mt-2"
          aria-label={`Read source for "${report.title}" (opens in new tab)`}
        >
          Read source
          <ExternalLink className="w-3 h-3" aria-hidden="true" />
        </a>
      )}
    </div>
  )
}
