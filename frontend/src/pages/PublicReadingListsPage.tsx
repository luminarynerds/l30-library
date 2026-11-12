/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  Library,
  Filter,
  ChevronDown,
  Share2,
  Calendar,
  BookOpen,
  Zap,
  X,
} from 'lucide-react'
import { fetchApi } from '@/lib/api-client'
import { clsx } from '@/utils/helpers'
import { useTranslation, getCurrentLocale } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

// Types for public reading lists
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

interface PublicReadingListPreview {
  id: number
  name: string
  description: string | null
  creator: CreatorInfo
  item_count: number
  share_count: number
  share_stats: ShareStats | null
  created_at: string
  updated_at: string | null
}

interface PaginationInfo {
  total_count: number
  page: number
  per_page: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

interface BrowseResponse {
  success: boolean
  data: PublicReadingListPreview[]
  pagination: PaginationInfo
  filters: {
    search: string | null
    sort: string
    creator_id: number | null
  }
}

interface TrendingListsResponse {
  success: boolean
  trending: Array<{
    id: number
    name: string
    creator: CreatorInfo
    item_count: number
    share_count: number
    created_at: string
  }>
  count: number
}

// Sort options
const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest First', icon: '✨' },
  { value: 'most_shared', label: 'Most Shared', icon: '🔥' },
  { value: 'most_popular', label: 'Most Popular', icon: '⭐' },
  { value: 'alphabetical', label: 'A to Z', icon: '🔤' },
]

// API Functions
async function fetchPublicLists(
  search: string | null,
  sort: string,
  creatorId: number | null,
  page: number,
  perPage: number
): Promise<BrowseResponse> {
  const params = new URLSearchParams()
  if (search) params.append('search', search)
  params.append('sort', sort)
  if (creatorId) params.append('creator_id', creatorId.toString())
  params.append('page', page.toString())
  params.append('per_page', perPage.toString())

  return fetchApi<BrowseResponse>(`/reading-lists/public?${params.toString()}`)
}

async function fetchTrendingLists(limit: number = 6): Promise<TrendingListsResponse> {
  return fetchApi<TrendingListsResponse>(`/reading-lists/public/stats/trending?limit=${limit}`)
}

// Format date to readable string
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString(getCurrentLocale(), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

// ListCard Component
function ListCard({ list, isDark }: { list: PublicReadingListPreview; isDark: boolean }) {
  return (
    <Link
      to={`/public-reading-lists/${list.id}`}
      className={clsx(
        'block rounded-lg border-2 p-4 transition-all hover:shadow-lg hover:border-lsc-rose cursor-pointer',
        isDark
          ? 'bg-earth-800 border-earth-600 hover:bg-earth-700'
          : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 hover:bg-lsc-cream'
      )}
    >
      {/* List Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className={clsx(
            'text-lg font-bold truncate',
            isDark ? 'text-lsc-cream' : 'text-lsc-brown'
          )} title={list.name}>
            {list.name}
          </h3>
          <p className={clsx(
            'text-sm truncate',
            isDark ? 'text-earth-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
          )} title={`by ${list.creator.name}`}>
            by {list.creator.name}
          </p>
        </div>
        <div className={clsx(
          'flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium whitespace-nowrap',
          isDark ? 'bg-earth-700 text-lsc-rose-light' : 'bg-lsc-rose/10 text-lsc-rose'
        )}>
          <Share2 className="w-4 h-4" aria-hidden="true" />
          <span>{list.share_count}</span>
        </div>
      </div>

      {/* Description */}
      {list.description && (
        <p className={clsx(
          'text-sm line-clamp-2 mb-3',
          isDark ? 'text-earth-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
        )} title={list.description}>
          {list.description}
        </p>
      )}

      {/* Metadata Row */}
      <div className={clsx(
        'flex flex-wrap items-center gap-3 text-xs pb-3 mb-3 border-b',
        isDark ? 'border-earth-600 text-earth-600' : 'border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
      )}>
        <div className="flex items-center gap-1">
          <BookOpen className="w-4 h-4" aria-hidden="true" />
          <span>{list.item_count} item{list.item_count !== 1 ? 's' : ''}</span>
        </div>
        <div className="flex items-center gap-1">
          <Calendar className="w-4 h-4" aria-hidden="true" />
          <span>{formatDate(list.created_at)}</span>
        </div>
      </div>

      {/* Share Stats */}
      {list.share_stats && list.share_stats.total_shares > 0 && (
        <div className={clsx(
          'grid grid-cols-4 gap-2 text-xs',
          isDark ? 'text-earth-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
        )}>
          <div className="text-center">
            <div className={clsx(
              'font-bold',
              isDark ? 'text-lsc-rose-light' : 'text-lsc-rose'
            )}>
              {list.share_stats.bluesky_shares}
            </div>
            <div className="text-[10px]">Bluesky</div>
          </div>
          <div className="text-center">
            <div className={clsx(
              'font-bold',
              isDark ? 'text-lsc-rose-light' : 'text-lsc-rose'
            )}>
              {list.share_stats.mastodon_shares}
            </div>
            <div className="text-[10px]">Mastodon</div>
          </div>
          <div className="text-center">
            <div className={clsx(
              'font-bold',
              isDark ? 'text-lsc-rose-light' : 'text-lsc-rose'
            )}>
              {list.share_stats.email_shares}
            </div>
            <div className="text-[10px]">Email</div>
          </div>
          <div className="text-center">
            <div className={clsx(
              'font-bold',
              isDark ? 'text-lsc-rose-light' : 'text-lsc-rose'
            )}>
              {list.share_stats.total_shares}
            </div>
            <div className="text-[10px]">Total</div>
          </div>
        </div>
      )}
    </Link>
  )
}

// Empty State Component
function EmptyState({ isDark }: { isDark: boolean }) {
  return (
    <div className={clsx(
      'rounded-lg p-12 text-center',
      isDark ? 'bg-earth-800 border-2 border-earth-600' : 'bg-lsc-cream border-2 border-lsc-border dark:border-earth-700'
    )}>
      <Library className={clsx(
        'w-12 h-12 mx-auto mb-4 opacity-50',
        isDark ? 'text-lsc-dark/70 dark:text-lsc-cream/70' : 'text-earth-600'
      )} aria-hidden="true" />
      <h3 className={clsx(
        'text-lg font-bold mb-2',
        isDark ? 'text-earth-300' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
      )}>
        No Reading Lists Found
      </h3>
      <p className={clsx(
        'text-sm',
        isDark ? 'text-earth-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
      )}>
        Try adjusting your search or filters to find reading lists to explore.
      </p>
    </div>
  )
}

// Skeleton Loading Component
function ListCardSkeleton({ isDark }: { isDark: boolean }) {
  return (
    <div className={clsx(
      'rounded-lg border-2 p-4 motion-safe:animate-pulse',
      isDark ? 'bg-earth-800 border-earth-600' : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700'
    )}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          <div className={clsx('h-5 rounded w-2/3 mb-2', isDark ? 'bg-earth-700' : 'bg-earth-200 dark:bg-earth-600')} />
          <div className={clsx('h-4 rounded w-1/2', isDark ? 'bg-earth-700' : 'bg-earth-200 dark:bg-earth-600')} />
        </div>
        <div className={clsx('h-8 w-16 rounded-full', isDark ? 'bg-earth-700' : 'bg-earth-200 dark:bg-earth-600')} />
      </div>
      <div className={clsx('h-12 rounded mb-3', isDark ? 'bg-earth-700' : 'bg-earth-200 dark:bg-earth-600')} />
      <div className={clsx('h-6 rounded', isDark ? 'bg-earth-700' : 'bg-earth-200 dark:bg-earth-600')} />
    </div>
  )
}

// Main Page Component
// eslint-disable-next-line complexity
export default function PublicReadingListsPage() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const isDark = useMemo(() => {
    if (typeof document === 'undefined') return false
    return document.documentElement.classList.contains('dark')
  }, [])

  // State from URL params
  const searchQuery = searchParams.get('search') || ''
  const sortBy = searchParams.get('sort') || 'newest'
  const currentPage = parseInt(searchParams.get('page') || '1', 10)
  const perPage = 12

  // Local state
  const [searchInput, setSearchInput] = useState(searchQuery)
  const [showFilters, setShowFilters] = useState(false)
  const [selectedSort, setSelectedSort] = useState(sortBy)

  // Update URL params when search/sort/page changes
  const updateParams = (newSearch?: string, newSort?: string, newPage?: number) => {
    const params = new URLSearchParams()
    if (newSearch || searchInput) params.set('search', newSearch || searchInput)
    if (newSort || selectedSort) params.set('sort', newSort || selectedSort)
    if (newPage && newPage > 1) params.set('page', newPage.toString())
    setSearchParams(params)
  }

  // Fetch public lists
  const { data: listsData, isLoading: isLoadingLists, error: listsError } = useQuery({
    queryKey: ['publicReadingLists', searchQuery, sortBy, currentPage, perPage],
    queryFn: () => fetchPublicLists(searchQuery || null, sortBy, null, currentPage, perPage),
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Fetch trending lists
  const { data: trendingData, isLoading: isLoadingTrending } = useQuery({
    queryKey: ['trendingReadingLists'],
    queryFn: () => fetchTrendingLists(6),
    staleTime: 1000 * 60 * 15, // 15 minutes
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    updateParams(searchInput, undefined, 1)
  }

  const handleSortChange = (newSort: string) => {
    setSelectedSort(newSort)
    updateParams(undefined, newSort, 1)
  }

  const handleClearSearch = () => {
    setSearchInput('')
    const params = new URLSearchParams()
    params.set('sort', sortBy)
    setSearchParams(params)
  }

  const pagination = listsData?.pagination

  return (
    <div className={clsx(
      'min-h-screen',
      isDark ? 'bg-earth-950' : 'bg-lsc-cream'
    )}>
      {/* Hero Section */}
      <div className={clsx(
        'border-b-2',
        isDark ? 'bg-earth-900 border-earth-800' : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700'
      )}>
        <PageContainer className="py-8 md:py-12">
          <div className="flex items-center gap-3 mb-4">
            <Library className="w-8 h-8 text-lsc-rose" aria-hidden="true" />
            <h1 className={clsx(
              'text-3xl md:text-4xl font-bold font-serif',
              isDark ? 'text-lsc-cream' : 'text-lsc-brown'
            )}>
              Public Reading Lists
            </h1>
          </div>
          <p className={clsx(
            'text-lg',
            isDark ? 'text-earth-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
          )}>
            Discover reading lists created by library patrons. Browse by topic, creator, or popularity.
          </p>
        </PageContainer>
      </div>

      {/* Main Content */}
      <PageContainer className="py-8 md:py-12">
        {/* Trending Section - Show before search results */}
        {!searchQuery && (
          <section className="mb-12">
            <div className="flex items-center gap-2 mb-6">
              <Zap className="w-6 h-6 text-lsc-rose" aria-hidden="true" />
              <h2 className={clsx(
                'text-2xl font-bold font-serif',
                isDark ? 'text-lsc-cream' : 'text-lsc-brown'
              )}>
                Trending Now
              </h2>
            </div>

            {isLoadingTrending ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(3)].map((_, i) => <ListCardSkeleton key={i} isDark={isDark} />)}
              </div>
            ) : trendingData?.trending && trendingData.trending.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {trendingData.trending.map((list) => (
                  <ListCard
                    key={list.id}
                    list={{
                      ...list,
                      description: null,
                      share_stats: null,
                      updated_at: null,
                    }}
                    isDark={isDark}
                  />
                ))}
              </div>
            ) : null}
          </section>
        )}

        {/* Search and Filters Section */}
        <section className="mb-8">
          <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center">
            {/* Search Form */}
            <form onSubmit={handleSearch} className="flex-1 flex gap-2">
              <div className={clsx(
                'flex-1 flex items-center gap-2 rounded-lg border-2 px-4 py-2 transition-colors',
                isDark
                  ? 'bg-earth-800 border-earth-600 focus-within:border-lsc-rose'
                  : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 focus-within:border-lsc-rose'
              )}>
                <Search className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder={t('publicReadingLists.searchListsCreatorsTopics')}
                  className={clsx(
                    'flex-1 bg-transparent outline-none text-sm',
                    isDark ? 'text-lsc-cream placeholder:text-earth-600' : 'text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400'
                  )}
                  aria-label={t('aria.publicReadingLists.searchReadingLists')}
                />
                {searchInput && (
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 transition-colors"
                    aria-label={t('aria.advancedStaffSearchModal.clearSearch')}
                  >
                    <X className="w-5 h-5" aria-hidden="true" />
                  </button>
                )}
              </div>
              <button
                type="submit"
                className="px-6 py-2 rounded-lg bg-lsc-rose text-white font-semibold hover:bg-lsc-rose/90 transition-colors"
                aria-label={t('aria.essentialsHomePage.search')}
              >
                Search
              </button>
            </form>

            {/* Sort Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={clsx(
                  'w-full md:w-auto px-4 py-2 rounded-lg border-2 font-semibold flex items-center gap-2 justify-center md:justify-start transition-colors',
                  isDark
                    ? 'bg-earth-800 border-earth-600 text-lsc-cream hover:bg-earth-700'
                    : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-800'
                )}
                aria-label={t('aria.publicReadingLists.sortOptions')}
                aria-expanded={showFilters}
              >
                <Filter className="w-5 h-5" aria-hidden="true" />
                <span>Sort: {SORT_OPTIONS.find((s) => s.value === selectedSort)?.label}</span>
                <ChevronDown className={clsx(
                  'w-4 h-4 transition-transform',
                  showFilters && 'rotate-180'
                )} aria-hidden="true" />
              </button>

              {/* Sort Dropdown Menu */}
              {showFilters && (
                <div className={clsx(
                  'absolute top-full right-0 mt-2 w-full md:w-56 rounded-lg shadow-lg z-10 border-2',
                  isDark ? 'bg-earth-800 border-earth-600' : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700'
                )}>
                  {SORT_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        handleSortChange(option.value)
                        setShowFilters(false)
                      }}
                      className={clsx(
                        'w-full text-left px-4 py-3 flex items-center gap-2 transition-colors',
                        selectedSort === option.value
                          ? isDark
                            ? 'bg-earth-700 text-lsc-rose'
                            : 'bg-lsc-rose/10 text-lsc-rose'
                          : isDark
                          ? 'text-lsc-cream hover:bg-earth-700'
                          : 'text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800'
                      )}
                    >
                      <span>{option.icon}</span>
                      <span>{option.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Results Section */}
        <section>
          {/* Results Header */}
          {listsData && (
            <div className="mb-6">
              <p className={clsx(
                'text-sm font-medium',
                isDark ? 'text-earth-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
              )}>
                {pagination?.total_count === 0
                  ? 'No reading lists found'
                  : `Showing ${(currentPage - 1) * perPage + 1} to ${Math.min(
                    currentPage * perPage,
                    pagination?.total_count || 0
                  )} of ${pagination?.total_count} reading lists`}
              </p>
            </div>
          )}

          {/* Error State */}
          {listsError && (
            <div className={clsx(
              'rounded-lg p-6 border-2',
              isDark ? 'bg-earth-800 border-status-danger-900 text-status-danger-300' : 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800 text-status-danger-700 dark:text-status-danger-300'
            )}>
              <p className="font-semibold">{t('publicReadingLists.failedToLoadReadingLists')}</p>
              <p className="text-sm mt-1">{t('publicReadingLists.pleaseTryAgainLater')}</p>
            </div>
          )}

          {/* Loading State */}
          {isLoadingLists ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(perPage)].map((_, i) => (
                <ListCardSkeleton key={i} isDark={isDark} />
              ))}
            </div>
          ) : listsData?.data && listsData.data.length > 0 ? (
            <>
              {/* Grid of Lists */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
                {listsData.data.map((list) => (
                  <ListCard key={list.id} list={list} isDark={isDark} />
                ))}
              </div>

              {/* Pagination */}
              {pagination && pagination.total_pages > 1 && (
                <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-lg border-2" style={{
                  backgroundColor: isDark ? 'rgb(30, 27, 23)' : 'white',
                  borderColor: isDark ? 'rgb(55, 50, 43)' : 'rgb(229, 231, 235)',
                }}>
                  <div className={clsx(
                    'text-sm font-medium',
                    isDark ? 'text-earth-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                  )}>
                    Page {pagination.page} of {pagination.total_pages}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => updateParams(undefined, undefined, currentPage - 1)}
                      disabled={!pagination.has_previous}
                      className={clsx(
                        'px-4 py-2 rounded-lg font-semibold transition-colors',
                        pagination.has_previous
                          ? isDark
                            ? 'bg-earth-700 text-lsc-cream hover:bg-earth-600'
                            : 'bg-earth-200 dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-earth-300 dark:hover:bg-earth-500'
                          : isDark
                          ? 'bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                          : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                      )}
                      aria-label={t('aria.account.previousPage')}
                    >
                      Previous
                    </button>

                    {/* Page Numbers */}
                    <div className="flex items-center gap-1 px-2">
                      {[...Array(Math.min(5, pagination.total_pages))].map((_, i) => {
                        const pageNum = i + 1
                        const isCurrentPage = pageNum === currentPage
                        return (
                          <button
                            key={pageNum}
                            onClick={() => updateParams(undefined, undefined, pageNum)}
                            className={clsx(
                              'w-8 h-8 rounded transition-colors font-medium',
                              isCurrentPage
                                ? 'bg-lsc-rose text-white'
                                : isDark
                                ? 'text-lsc-cream hover:bg-earth-700'
                                : 'text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700'
                            )}
                            aria-label={`Go to page ${pageNum}`}
                            aria-current={isCurrentPage ? 'page' : undefined}
                          >
                            {pageNum}
                          </button>
                        )
                      })}
                    </div>

                    <button
                      onClick={() => updateParams(undefined, undefined, currentPage + 1)}
                      disabled={!pagination.has_next}
                      className={clsx(
                        'px-4 py-2 rounded-lg font-semibold transition-colors',
                        pagination.has_next
                          ? isDark
                            ? 'bg-earth-700 text-lsc-cream hover:bg-earth-600'
                            : 'bg-earth-200 dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-earth-300 dark:hover:bg-earth-500'
                          : isDark
                          ? 'bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                          : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                      )}
                      aria-label={t('aria.account.nextPage')}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : !isLoadingLists && (
            <EmptyState isDark={isDark} />
          )}
        </section>
      </PageContainer>
    </div>
  )
}
