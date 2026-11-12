/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  Library,
  Share2,
  Calendar,
  BookOpen,
  User,
} from 'lucide-react'
import { fetchApi } from '@/lib/api-client'
import { clsx } from '@/utils/helpers'
import { useTranslation, getCurrentLocale } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface CreatorInfo {
  id: number
  name: string
  avatar: string | null
}

interface ShareStats {
  total_shares: number
  bluesky_shares: number
  mastodon_shares: number
  email_shares: number
}

interface ReadingListItem {
  id: number
  catalog_item_id: number
  title: string
  author: string | null
  isbn: string | null
  cover_image: string | null
  added_at: string | null
}

interface PublicReadingListDetail {
  id: number
  name: string
  description: string | null
  creator: CreatorInfo
  item_count: number
  share_count: number
  share_stats: ShareStats | null
  created_at: string | null
  updated_at: string | null
  items: ReadingListItem[]
}

interface GetPublicListPreviewResponse {
  success: boolean
  list: PublicReadingListDetail
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString(getCurrentLocale(), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function DetailSkeleton({ isDark }: { isDark: boolean }) {
  return (
    <div className="motion-safe:animate-pulse">
      <div className={clsx('h-8 rounded w-1/3 mb-4', isDark ? 'bg-earth-700' : 'bg-earth-200')} />
      <div className={clsx('h-5 rounded w-1/4 mb-6', isDark ? 'bg-earth-700' : 'bg-earth-200')} />
      <div className={clsx('h-20 rounded mb-8', isDark ? 'bg-earth-700' : 'bg-earth-200')} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className={clsx('h-24 rounded', isDark ? 'bg-earth-700' : 'bg-earth-200')} />
        ))}
      </div>
    </div>
  )
}

export default function PublicReadingListDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const isDark = useMemo(() => {
    if (typeof document === 'undefined') return false
    return document.documentElement.classList.contains('dark')
  }, [])

  const { data, isLoading, error } = useQuery({
    queryKey: ['publicReadingListDetail', id],
    queryFn: () => fetchApi<GetPublicListPreviewResponse>(`/reading-lists/public/${id}/preview`),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
  })

  const list = data?.list

  return (
    <div className={clsx('min-h-screen', isDark ? 'bg-earth-950' : 'bg-lsc-cream')}>
      <PageContainer className="py-8 md:py-12">
        {/* Back Link */}
        <Link
          to="/public-reading-lists"
          className="inline-flex items-center gap-2 text-sm mb-6 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Reading Lists
        </Link>

        {/* Error State */}
        {error && (
          <div className={clsx(
            'rounded-lg p-6 border-2',
            isDark ? 'bg-earth-800 border-status-danger-900 text-status-danger-300' : 'bg-status-danger-50 border-status-danger-200 text-status-danger-700'
          )}>
            <p className="font-semibold">{t('publicReadingListDetail.readingListNotFound')}</p>
            <p className="text-sm mt-1">{t('publicReadingListDetail.thisReadingListMayHave')}</p>
          </div>
        )}

        {/* Loading State */}
        {isLoading && <DetailSkeleton isDark={isDark} />}

        {/* Detail Content */}
        {list && (
          <>
            {/* Header */}
            <div className={clsx(
              'rounded-lg border-2 p-6 mb-6',
              isDark ? 'bg-earth-800 border-earth-600' : 'bg-lsc-white border-lsc-border'
            )}>
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="flex items-center gap-3">
                  <Library className="w-7 h-7 text-lsc-rose flex-shrink-0" aria-hidden="true" />
                  <h1 className={clsx(
                    'text-2xl md:text-3xl font-bold font-serif',
                    isDark ? 'text-lsc-cream' : 'text-lsc-brown'
                  )}>
                    {list.name}
                  </h1>
                </div>
                <div className={clsx(
                  'flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap',
                  isDark ? 'bg-earth-700 text-lsc-rose-light' : 'bg-lsc-rose/10 text-lsc-rose'
                )}>
                  <Share2 className="w-4 h-4" aria-hidden="true" />
                  <span>{list.share_count} shares</span>
                </div>
              </div>

              {/* Creator */}
              <div className="flex items-center gap-2 mb-4">
                <User className="w-4 h-4 text-earth-600" aria-hidden="true" />
                <span className={clsx(
                  'text-sm',
                  isDark ? 'text-earth-600' : 'text-earth-600 dark:text-earth-200'
                )}>
                  Created by <span className="font-semibold">{list.creator.name}</span>
                </span>
              </div>

              {/* Description */}
              {list.description && (
                <p className={clsx(
                  'text-sm leading-relaxed mb-4',
                  isDark ? 'text-earth-600' : 'text-earth-600 dark:text-earth-200'
                )}>
                  {list.description}
                </p>
              )}

              {/* Metadata */}
              <div className={clsx(
                'flex flex-wrap items-center gap-4 text-xs',
                isDark ? 'text-earth-600' : 'text-earth-600'
              )}>
                <div className="flex items-center gap-1">
                  <BookOpen className="w-4 h-4" aria-hidden="true" />
                  <span>{list.item_count} item{list.item_count !== 1 ? 's' : ''}</span>
                </div>
                {list.created_at && (
                  <div className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" aria-hidden="true" />
                    <span>{formatDate(list.created_at)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Items List */}
            <div>
              <h2 className={clsx(
                'text-xl font-bold font-serif mb-4',
                isDark ? 'text-lsc-cream' : 'text-lsc-brown'
              )}>
                Books in this list
              </h2>

              {list.items.length === 0 ? (
                <div className={clsx(
                  'rounded-lg border-2 p-8 text-center',
                  isDark ? 'bg-earth-800 border-earth-600' : 'bg-lsc-white border-lsc-border'
                )}>
                  <BookOpen className="w-10 h-10 mx-auto mb-3 text-earth-600" aria-hidden="true" />
                  <p className={clsx(
                    'text-sm',
                    isDark ? 'text-earth-600' : 'text-earth-600'
                  )}>
                    This reading list is empty.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {list.items.map((item) => (
                    <Link
                      key={item.id}
                      to={`/catalog/${item.catalog_item_id}`}
                      className={clsx(
                        'rounded-lg border-2 p-4 flex gap-4 transition-all hover:shadow-md group',
                        isDark
                          ? 'bg-earth-800 border-earth-600 hover:border-lsc-rose/50'
                          : 'bg-lsc-white border-lsc-border hover:border-lsc-rose/50'
                      )}
                    >
                      {/* Cover Image */}
                      {item.cover_image ? (
                        <img
                          src={item.cover_image}
                          alt={`Cover of ${item.title}`}
                          className="w-16 h-24 object-cover rounded flex-shrink-0"
                        />
                      ) : (
                        <div className={clsx(
                          'w-16 h-24 rounded flex-shrink-0 flex items-center justify-center',
                          isDark ? 'bg-earth-700' : 'bg-earth-100'
                        )}>
                          <BookOpen className="w-6 h-6 text-earth-600" aria-hidden="true" />
                        </div>
                      )}

                      {/* Item Info */}
                      <div className="flex-1 min-w-0">
                        <h3 className={clsx(
                          'font-bold truncate group-hover:text-lsc-rose transition-colors',
                          isDark ? 'text-lsc-cream' : 'text-lsc-brown'
                        )} title={item.title}>
                          {item.title}
                        </h3>
                        {item.author && (
                          <p className={clsx(
                            'text-sm mt-0.5',
                            isDark ? 'text-earth-600' : 'text-earth-600 dark:text-earth-200'
                          )}>
                            {item.author}
                          </p>
                        )}
                        {item.isbn && (
                          <p className={clsx(
                            'text-xs mt-1',
                            isDark ? 'text-earth-600 dark:text-earth-200' : 'text-earth-600'
                          )}>
                            ISBN: {item.isbn}
                          </p>
                        )}
                        {item.added_at && (
                          <p className={clsx(
                            'text-xs mt-1',
                            isDark ? 'text-earth-600 dark:text-earth-200' : 'text-earth-600'
                          )}>
                            Added {formatDate(item.added_at)}
                          </p>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </PageContainer>
    </div>
  )
}
