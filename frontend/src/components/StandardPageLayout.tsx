/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * StandardPageLayout Component
 *
 * The shared page wrapper for all core landing pages. Provides a consistent
 * structural skeleton: header (icon + title + subtitle),
 * loading skeleton, empty state, and content area.
 *
 * Each page controls its own content via children; this component owns
 * the chrome so every page looks and feels the same.
 *
 * Note: Breadcrumbs are rendered by the Layout component globally,
 * so they are NOT duplicated here.
 *
 * Accessibility:
 * - Single <h1> provided automatically
 * - Loading skeleton during data fetches (no blank pages)
 * - Empty state when no data (no blank sections)
 * - All decorative icons have aria-hidden="true"
 * - Subtitle capped at max-w-2xl for readability
 *
 * @example
 * <StandardPageLayout
 *   title="Digital Resources"
 *   subtitle="Access thousands of digital materials from anywhere."
 *   icon={Globe}
 *   isLoading={isLoading}
 * >
 *   <section aria-labelledby="databases-heading">...</section>
 * </StandardPageLayout>
 */

import { Link } from 'react-router-dom'
import { PackageOpen } from 'lucide-react'
import { type LucideIcon } from 'lucide-react'

import PageSkeleton from '@/components/PageSkeleton'
import { PAGE_WIDTH, type PageWidth } from '@/components/layout/page-width'

interface StandardPageLayoutProps {
  /** Page heading (rendered as h1) */
  title: string
  /** Page content */
  children: React.ReactNode
  /** Descriptive text below the heading */
  subtitle?: string
  /** Decorative icon next to the heading */
  icon?: LucideIcon
  /** Show loading skeleton instead of content */
  isLoading?: boolean
  /** Show empty state instead of content */
  isEmpty?: boolean
  /** Custom empty state message (default: "Nothing here yet") */
  emptyMessage?: string
  /** CTA button in the empty state */
  emptyAction?: { label: string; href: string }
  /** Max width of the page container (default: '6xl') */
  maxWidth?: PageWidth | (string & {})
}

// Resolve a (possibly legacy) maxWidth value to a content-width class.
// Canonical tiers live in PAGE_WIDTH (single source of truth); legacy values
// that historically fell back to 6xl keep doing so. The 7xl passthrough is
// deprecated (only /branches) and should migrate to a tier.
function resolveWidthClass(maxWidth: string): string {
  if (maxWidth in PAGE_WIDTH) return PAGE_WIDTH[maxWidth as PageWidth]
  if (maxWidth === 'xl') return PAGE_WIDTH.form
  if (maxWidth === '7xl') return 'max-w-7xl'
  return PAGE_WIDTH.content
}

export default function StandardPageLayout({
  title,
  children,
  subtitle,
  icon: Icon,
  isLoading = false,
  isEmpty = false,
  emptyMessage = 'Nothing here yet',
  emptyAction,
  maxWidth = '6xl',
}: StandardPageLayoutProps): React.ReactElement {
  const containerClass = resolveWidthClass(maxWidth)

  return (
    <div className={`${containerClass} mx-auto px-4 sm:px-6 lg:px-8`}>
      <header className="mb-10">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="w-10 h-10 rounded-lg bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center flex-shrink-0">
              <Icon
                className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light"
                aria-hidden="true"
              />
            </div>
          )}
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-earth-700 dark:text-lsc-cream">
            {title}
          </h1>
        </div>
        {subtitle && (
          <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 max-w-2xl">
            {subtitle}
          </p>
        )}
      </header>

      {isLoading ? (
        <PageSkeleton />
      ) : isEmpty ? (
        <div className="text-center py-16">
          <PackageOpen
            className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4"
            aria-hidden="true"
          />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg">
            {emptyMessage}
          </p>
          {emptyAction && (
            <Link
              to={emptyAction.href}
              className="text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline mt-2 inline-block"
            >
              {emptyAction.label}
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-10">{children}</div>
      )}
    </div>
  )
}
