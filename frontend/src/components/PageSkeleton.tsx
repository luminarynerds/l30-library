/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { t } from '@/i18n'
export default function PageSkeleton(): React.ReactElement {
  return (
    <div role="status" aria-label={t('aria.pageSkeleton.loadingPageContent')}>
      <span className="sr-only">Loading...</span>

      {/* Title shimmer */}
      <div className="w-64 h-8 rounded bg-earth-200 dark:bg-earth-800 motion-safe:animate-pulse" />

      {/* Subtitle shimmer */}
      <div className="w-96 h-5 rounded bg-earth-200 dark:bg-earth-800 motion-safe:animate-pulse mt-3" />

      {/* Card grid */}
      <div className="mt-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="h-48 rounded-xl bg-earth-200 dark:bg-earth-800 motion-safe:animate-pulse" />
        <div className="h-48 rounded-xl bg-earth-200 dark:bg-earth-800 motion-safe:animate-pulse" />
        <div className="h-48 rounded-xl bg-earth-200 dark:bg-earth-800 motion-safe:animate-pulse" />
      </div>
    </div>
  )
}
