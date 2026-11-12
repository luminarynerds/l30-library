/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import { logger } from '@/utils/logger'

interface PulseData {
  popular_item: { id: number; title: string; author: string; holds: number } | null
}

export default function MostRequested() {
  const { t } = useTranslation()

  const { data } = useQuery<PulseData | null>({
    queryKey: ['community-pulse'],
    queryFn: () => api.get(`${API_BASE}/stats/community-pulse`).catch((err) => {
      logger.error('Failed to fetch community pulse:', err)
      return null
    }) as Promise<PulseData | null>,
    refetchInterval: 60_000,
  })

  const item = data?.popular_item
  if (!item || item.id === 0 || item.holds === 0) return null

  return (
    <section aria-label={t('home.mostRequested.label', 'Most requested')}>
      <Link
        to={`/catalog/${item.id}`}
        className="group flex items-stretch gap-5 rounded-xl border border-lsc-border dark:border-earth-700/50 bg-lsc-rose/10 p-5 sm:p-6 shadow-soft-sm motion-safe:transition-transform motion-safe:hover:scale-[1.01] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
      >
        <span aria-hidden="true" className="w-2 flex-shrink-0 self-stretch rounded-full bg-lsc-rose" />
        <span className="flex min-w-0 flex-col gap-1">
          <span className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.2em] text-sage-700 dark:text-lsc-rose">
            <BookOpen className="h-4 w-4" aria-hidden="true" />
            {t('home.mostRequested.label', 'Most requested')}
          </span>
          <span className="font-serif text-xl md:text-2xl text-lsc-dark dark:text-lsc-cream leading-tight">
            {item.title}
          </span>
          {item.author && (
            <span className="text-sm text-earth-700 dark:text-earth-400">{item.author}</span>
          )}
          <span className="font-mono text-xs text-earth-700 dark:text-earth-400">
            {t('home.mostRequested.waiting', { count: item.holds })}
          </span>
        </span>
      </Link>
    </section>
  )
}
