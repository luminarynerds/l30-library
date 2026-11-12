/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Curated picks landing page.
 *
 * This page is the new home for the FanShelf experience (formerly mounted
 * on the patron home page as `<HomeBookShelves />`). The home page now
 * renders editor-managed shelves via PR #670/#671; the FanShelf moves here
 * so the visual "fan" treatment still has somewhere to live.
 */
import { Suspense, lazy } from 'react'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useTranslation } from '@/i18n/I18nContext'
import Skeleton from '@/components/Skeleton'

const HomeBookShelves = lazy(() => import('@/components/HomeBookShelves'))

export default function PicksPage(): React.ReactElement {
  const { t } = useTranslation()
  usePageTitle(t('picks.pageTitle', 'Curated picks'))

  return (
    <div className="max-w-6xl mx-auto px-6 py-12 md:py-16 space-y-10">
      <header className="space-y-3">
        <h1 className="font-serif text-4xl md:text-5xl text-lsc-dark dark:text-lsc-cream leading-tight">
          {t('picks.heading', 'Curated picks')}
        </h1>
        <p className="text-base md:text-lg text-earth-700 dark:text-earth-300 max-w-2xl">
          {t('picks.intro', 'Our newest curated picks from the staff.')}
        </p>
      </header>

      <Suspense fallback={<Skeleton variant="card" className="h-96 w-full" />}>
        <HomeBookShelves />
      </Suspense>
    </div>
  )
}
