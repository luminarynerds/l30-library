/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

export interface BanReportRationaleViewerProps {
  /** Whether an acquisition_rationale row exists for the catalog match. */
  rationalePresent: boolean
  /** True iff the ban's reason_category is in the rationale's anticipated list. */
  rationaleAnticipated: boolean
  /** Primary use case slug from the rationale (tooltip context). */
  primaryUseCase: string | null
  /** Ban report's reason_category (rendered inline for context). */
  banCategory: string
}

export function BanReportRationaleViewer({
  rationalePresent,
  rationaleAnticipated,
  primaryUseCase,
  banCategory,
}: BanReportRationaleViewerProps) {
  const { t } = useTranslation()

  if (!rationalePresent) {
    return (
      <span
        className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100"
        data-rationale-state="missing"
      >
        {t('banReports.noRationale')}
      </span>
    )
  }

  if (rationaleAnticipated) {
    return (
      <span
        className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-100"
        title={primaryUseCase ?? ''}
        data-rationale-state="anticipated"
      >
        {t('banReports.anticipated', { reason: banCategory })}
      </span>
    )
  }

  return (
    <span
      className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-900 dark:bg-rose-900/40 dark:text-rose-100"
      title={primaryUseCase ?? ''}
      data-rationale-state="not-anticipated"
    >
      {t('banReports.notAnticipated', { reason: banCategory })}
    </span>
  )
}
