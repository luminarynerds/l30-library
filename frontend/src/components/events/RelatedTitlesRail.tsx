/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { BookOpen } from 'lucide-react'
import type { Event } from '@/api/api'
import { searchCatalog, placeHold, type CatalogItem } from '@/api/api'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation } from '@/i18n/I18nContext'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { CatalogCover } from '@/pages/catalog/components/CatalogItemThumbnail'

const BOOKISH_PATTERNS = [
  'book-club',
  'book_club',
  'bookclub',
  'author-talk',
  'author_talk',
  'authortalk',
  'storytime',
  'story-time',
  'reading-program',
  'reading_program',
  'summer-reading',
  'summer_reading',
] as const

const STOPWORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'of', 'for', 'with', 'to', 'in', 'on', 'at',
  'club', 'storytime', 'talk', 'program', 'event', 'series', 'group', 'session',
])

export function isBookishEvent(event: Event): boolean {
  const haystack: string[] = []
  if (event.category) haystack.push(event.category)
  if (event.tags) haystack.push(...event.tags)
  const lowered = haystack.map((s) => s.toLowerCase())
  return lowered.some((s) => BOOKISH_PATTERNS.some((p) => s === p || s.includes(p)))
}

function deriveQuery(event: Event): string {
  if (event.tags && event.tags.length > 0) {
    const cleaned = event.tags
      .map((tag) => tag.replace(/[-_]/g, ' ').trim())
      .filter(Boolean)
      .join(' ')
    if (cleaned) return cleaned
  }
  return event.title
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 2 && !STOPWORDS.has(w))
    .slice(0, 6)
    .join(' ')
}

interface RelatedTitlesRailProps {
  event: Event
  onPlaceHold?: (workId: number) => void
}

export default function RelatedTitlesRail({
  event,
  onPlaceHold,
}: RelatedTitlesRailProps): React.ReactElement | null {
  const { t } = useTranslation()
  const auth = useAuth()
  const navigate = useNavigate()
  const [hadError, setHadError] = useState(false)

  const enabled = isBookishEvent(event)
  const query = enabled ? deriveQuery(event) : ''

  const { data, isLoading, isError } = useQuery({
    queryKey: ['related-titles', event.id, query],
    queryFn: () => searchCatalog({ query, per_page: 3, page: 1, availableForHold: true }),
    enabled: enabled && query.length > 0,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  if (!enabled) return null

  if (isError) {
    if (!hadError) {
      console.error('[RelatedTitlesRail] catalog search failed for event', event.id)
      setHadError(true)
    }
    return null
  }

  if (isLoading) {
    return (
      <section
        className="border-t border-lsc-border dark:border-earth-700 pt-6"
        aria-label={t('events.detail.relatedTitles.heading', 'Bring the book to this event')}
        aria-busy="true"
      >
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          {t('events.detail.relatedTitles.heading', 'Bring the book to this event')}
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t(
            'events.detail.relatedTitles.subtext',
            'These titles pair well with this program. Place a hold and pick up before you come.',
          )}
        </p>
        <div
          className="grid grid-cols-1 sm:grid-cols-3 gap-3 motion-safe:animate-pulse motion-reduce:animate-none"
          data-testid="related-titles-skeleton"
        >
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="flex flex-col gap-2 p-3 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl"
              aria-hidden="true"
            >
              <div className="w-full aspect-[2/3] bg-lsc-border dark:bg-earth-700 rounded-lg" />
              <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-3/4" />
              <div className="h-3 bg-lsc-border dark:bg-earth-700 rounded w-1/2" />
              <div className="h-8 bg-lsc-border dark:bg-earth-700 rounded mt-1" />
            </div>
          ))}
        </div>
      </section>
    )
  }

  const items = (data?.items ?? []).slice(0, 3)
  if (items.length === 0) return null

  return (
    <section
      className="border-t border-lsc-border dark:border-earth-700 pt-6"
      aria-label={t('events.detail.relatedTitles.heading', 'Bring the book to this event')}
    >
      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
        <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        {t('events.detail.relatedTitles.heading', 'Bring the book to this event')}
      </h3>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        {t(
          'events.detail.relatedTitles.subtext',
          'These titles pair well with this program. Place a hold and pick up before you come.',
        )}
      </p>
      <ul
        className="grid grid-cols-1 sm:grid-cols-3 gap-3"
        role="list"
        data-testid="related-titles-list"
      >
        {items.map((item) => (
          <RelatedTitleCard
            key={item.id}
            item={item}
            authToken={auth.token}
            onNeedLogin={() => navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)}
            {...(onPlaceHold ? { onPlaceHold } : {})}
          />
        ))}
      </ul>
    </section>
  )
}

interface RelatedTitleCardProps {
  item: CatalogItem
  authToken: string | null
  onPlaceHold?: (workId: number) => void
  onNeedLogin: () => void
}

function RelatedTitleCard({
  item,
  authToken,
  onPlaceHold,
  onNeedLogin,
}: RelatedTitleCardProps): React.ReactElement {
  const { t } = useTranslation()
  const [placed, setPlaced] = useState(false)

  const mutation = useMutation({
    mutationFn: () => {
      if (!authToken) {
        return Promise.reject(new Error('not-logged-in'))
      }
      return placeHold(authToken, item.id)
    },
    onSuccess: () => {
      setPlaced(true)
      toast.success(t('toast.indie.holdPlacedSuccessfully', 'Hold placed successfully!'))
    },
    onError: (error: Error) => {
      if (error.message === 'not-logged-in') {
        onNeedLogin()
        return
      }
      toast.error(friendlyErrorMessage(error))
    },
  })

  const handleClick = () => {
    if (placed) return
    if (onPlaceHold) {
      onPlaceHold(item.id)
      setPlaced(true)
      return
    }
    mutation.mutate()
  }

  const ariaLabel = t(
    'events.detail.relatedTitles.placeHoldFor',
    'Place hold on {{title}}',
  ).replace('{{title}}', item.title)

  return (
    <li
      className="flex flex-col gap-2 p-3 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl"
      role="listitem"
    >
      <div className="w-full aspect-[2/3] rounded-lg overflow-hidden bg-lsc-border dark:bg-earth-700">
        <CatalogCover
          coverUrl={item.cover_url}
          alt=""
          title={item.title}
          itemType={item.item_type}
        />
      </div>
      <h4
        className="font-medium text-sm text-lsc-dark dark:text-lsc-cream line-clamp-2"
        title={item.title}
      >
        {item.title}
      </h4>
      {item.author && (
        <p
          className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-1"
          title={item.author}
        >
          {item.author}
        </p>
      )}
      <button
        type="button"
        onClick={handleClick}
        disabled={mutation.isPending || placed}
        className="mt-auto px-3 py-2 text-sm rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium transition-colors"
        aria-label={ariaLabel}
      >
        {placed
          ? t('events.detail.relatedTitles.holdPlaced', 'Hold placed')
          : mutation.isPending
            ? t('events.detail.relatedTitles.placingHold', 'Placing hold...')
            : t('events.detail.relatedTitles.placeHold', 'Place Hold')}
      </button>
    </li>
  )
}
