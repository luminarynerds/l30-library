/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Download } from 'lucide-react'
import { downloadICalFeed } from '@/utils/calendarExport'
import { useTranslation } from '@/i18n/I18nContext'
import type { Event } from '@/api/api'

export default function ExportEventsButton({ events }: { events: Event[] }): React.ReactElement {
  const { t } = useTranslation()
  const handleExport = () => {
    downloadICalFeed(events, 'library-events.ics')
  }

  return (
    <button
      onClick={handleExport}
      className="flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-xl text-sm font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/90 border-2 border-lsc-border dark:border-lsc-brown transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose shadow-sm hover:shadow touch-manipulation"
      aria-label={t('events.exportAllEvents')}
    >
      <Download className="w-4 h-4" aria-hidden="true" />
      <span className="hidden sm:inline">{t('events.export')}</span>
    </button>
  )
}
