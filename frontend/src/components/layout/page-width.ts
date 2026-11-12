/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Canonical page content-width tiers.
 *
 * Single source of truth for how wide a page's content column is. Use these
 * through <PageContainer> (or StandardPageLayout's maxWidth prop) instead of
 * hardcoding `max-w-* mx-auto px-4` on a page root, so the widths can't drift.
 */
export const PAGE_WIDTH = {
  /** 1600px - grid-heavy pages (catalog, dashboards) */
  wide: 'max-w-[1600px]',
  /** 1296px - default: listings & service pages (matches /events) */
  content: 'max-w-6xl',
  /** 768px - long-form prose (privacy, security, legal) */
  read: 'max-w-3xl',
  /** 576px - forms, auth, wizards */
  form: 'max-w-xl',
} as const

export type PageWidth = keyof typeof PAGE_WIDTH
