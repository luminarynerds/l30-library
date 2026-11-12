/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Calendar } from 'lucide-react'
import { EventsPageContent } from './events/components'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { usePageMeta } from '@/hooks/usePageMeta'

export default function EventsPage(): React.ReactElement {
  const { t } = useTranslation()
  usePageTitle(t('navigation.eventsAndPrograms'))
  // Per-route canonical + og:url. The bot-only SSR handler at /api/v1/seo/events
  // sets these for crawlers; this keeps human-loaded SPA pages in sync.
  usePageMeta({
    title: t('navigation.eventsAndPrograms'),
    description: t('events.discoverWorkshopsClassesAndCommunity'),
    canonicalPath: '/events',
    ogType: 'website',
  })
  return (
    <StandardPageLayout
      title={t('navigation.eventsAndPrograms')}
      subtitle={t('events.discoverWorkshopsClassesAndCommunity')}
      icon={Calendar}
    >
      <EventsPageContent />
    </StandardPageLayout>
  )
}
