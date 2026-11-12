/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { useBreadcrumbs } from '../hooks/useBreadcrumbs'
import { t } from '@/i18n'

export default function Breadcrumbs(): React.ReactElement | null {
  const breadcrumbs = useBreadcrumbs()

  // Don't show breadcrumbs on home page
  if (breadcrumbs.length <= 1) {
    return null
  }

  return (
    <nav aria-label={t('aria.breadcrumb.breadcrumb')} className="mb-6 py-2">
      <ol className="flex flex-wrap items-center gap-2 text-sm">
        {breadcrumbs.map((crumb, index) => (
          <li key={crumb.path} className="flex items-center gap-2">
            {index > 0 && (
              <ChevronRight
                className="w-4 h-4 text-lsc-dark/25 dark:text-lsc-cream/25"
                aria-hidden="true"
              />
            )}
            {crumb.isCurrentPage ? (
              <span
                className="text-lsc-dark dark:text-lsc-cream font-semibold"
                aria-current="page"
              >
                {crumb.label}
              </span>
            ) : (
              <Link
                to={crumb.path}
                className="text-lsc-rose dark:text-lsc-rose-light underline hover:text-lsc-rose/80 dark:hover:text-lsc-rose-light/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded"
              >
                {crumb.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}
