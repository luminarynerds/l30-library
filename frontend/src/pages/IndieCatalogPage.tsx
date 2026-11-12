/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Indie Ebook Catalog Page
 * Browse and borrow indie ebooks from local authors
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Search,
  BookOpen,
  Bookmark,
  Loader2,
  Star,
  Clock,
  Users,
  AlertCircle,
  CheckCircle,
  Filter,
  X,
  BookMarked,
  Heart,
  CalendarClock,
  Bell,
  ShoppingCart,
  TrendingUp,
  Rss,
  Settings} from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import {
  browseIndieCatalog,
  borrowEbook,
  joinWaitlist,
  placePreorderHold,
  getPreorderEbooks,
  generateSlug,
  getDiscoveryPage,
  getRssFeedUrl,
  getJustAvailableEbooks,
  getPublicBookDetail,
  getPublicReadingLists,
  getUpcomingIndieEvents,
  type IndieEbookPublic,
  type ContentRating,
  getFeaturedAuthor,
  penNameToSlug,
} from '@/api/indie-catalog-api'
import ContinueReadingRail from '@/components/indie/ContinueReadingRail'
import FeaturedBookHero from '@/components/indie/FeaturedBookHero'
import StaffPicksSection from '@/components/indie/StaffPicksSection'
import NewThisWeekSection from '@/components/indie/NewThisWeekSection'
import JustAvailableSection from '@/components/indie/JustAvailableSection'
import UpcomingEventsRail from '@/components/indie/UpcomingEventsRail'
import PublicListsRail from '@/components/indie/PublicListsRail'
import AuthorSpotlight from "@/components/indie/AuthorSpotlight"
import ShareButton from '@/components/ShareButton'
import BookPreviewModal from '@/components/indie/BookPreviewModal'
import BookmarkButton from '@/components/indie/BookmarkButton'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { getContentPreferences } from '@/api/indie-engagement-api'
import ContentPreferencesPanel from '@/components/indie/ContentPreferencesPanel'
import ContentWarningBadges from '@/components/indie/ContentWarningBadges'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { usePageTitle } from '@/hooks/usePageTitle'

import { getRatingInfo } from '@/utils/content-ratings'
import { t } from '@/i18n'
import { parseDate } from '@/utils/format-utils'

function formatGenre(genre: string): string {
  try {
    return decodeURIComponent(genre)
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())
  } catch {
    return genre.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }
}

function getGenres(t: (key: string, fallback?: string) => string): { value: string; label: string }[] {
  return [
    { value: 'Fiction', label: t('indieCatalog.genreFiction', 'Fiction') },
    { value: 'Literary Fiction', label: t('indieCatalog.genreLiteraryFiction', 'Literary Fiction') },
    { value: 'Non-Fiction', label: t('indieCatalog.genreNonfiction', 'Non-Fiction') },
    { value: 'Mystery', label: t('indieCatalog.genreMystery', 'Mystery') },
    { value: 'Romance', label: t('indieCatalog.genreRomance', 'Romance') },
    { value: 'Science Fiction', label: t('indieCatalog.genreScienceFiction', 'Science Fiction') },
    { value: 'Fantasy', label: t('indieCatalog.genreFantasy', 'Fantasy') },
    { value: 'LitRPG', label: t('indieCatalog.genreLitrpg', 'LitRPG') },
    { value: 'Thriller', label: t('indieCatalog.genreThriller', 'Thriller') },
    { value: 'Horror', label: t('indieCatalog.genreHorror', 'Horror') },
    { value: 'Historical', label: t('indieCatalog.genreHistorical', 'Historical') },
    { value: 'Biography', label: t('indieCatalog.genreBiography', 'Biography') },
    { value: 'Self-Help', label: t('indieCatalog.genreSelfhelp', 'Self-Help') },
    { value: 'Poetry', label: t('indieCatalog.genrePoetry', 'Poetry') },
    { value: 'Local History', label: t('indieCatalog.genreLocalHistory', 'Local History') },
    { value: 'Other', label: t('indieCatalog.genreOther', 'Other') },
  ]
}

function getGenreChips(t: (key: string, fallback?: string) => string): { label: string; value: string }[] {
  return [
    { label: t('indieCatalog.genreChipAll', 'All'), value: '' },
    { label: t('indieCatalog.genreRomance', 'Romance'), value: 'Romance' },
    { label: t('indieCatalog.genreChipSciFi', 'Sci-Fi'), value: 'Science Fiction' },
    { label: t('indieCatalog.genreFantasy', 'Fantasy'), value: 'Fantasy' },
    { label: t('indieCatalog.genreLitrpg', 'LitRPG'), value: 'LitRPG' },
    { label: t('indieCatalog.genreHorror', 'Horror'), value: 'Horror' },
    { label: t('indieCatalog.genrePoetry', 'Poetry'), value: 'Poetry' },
    { label: t('indieCatalog.genreLiteraryFiction', 'Literary Fiction'), value: 'Literary Fiction' },
  ]
}

// Subtle per-genre tint for the UNSELECTED filter pills (selected stays brand rose).
// Deterministic by genre name so API-driven genres get a stable color too.
const GENRE_TINT_CLASSES: string[] = [
  'bg-rose-50 text-rose-700 hover:bg-rose-100 dark:bg-rose-950/40 dark:text-rose-200 dark:hover:bg-rose-900/50',
  'bg-sky-50 text-sky-700 hover:bg-sky-100 dark:bg-sky-950/40 dark:text-sky-200 dark:hover:bg-sky-900/50',
  'bg-violet-50 text-violet-700 hover:bg-violet-100 dark:bg-violet-950/40 dark:text-violet-200 dark:hover:bg-violet-900/50',
  'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-200 dark:hover:bg-emerald-900/50',
  'bg-amber-50 text-amber-800 hover:bg-amber-100 dark:bg-amber-950/40 dark:text-amber-200 dark:hover:bg-amber-900/50',
  'bg-teal-50 text-teal-700 hover:bg-teal-100 dark:bg-teal-950/40 dark:text-teal-200 dark:hover:bg-teal-900/50',
  'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950/40 dark:text-indigo-200 dark:hover:bg-indigo-900/50',
  'bg-orange-50 text-orange-800 hover:bg-orange-100 dark:bg-orange-950/40 dark:text-orange-200 dark:hover:bg-orange-900/50',
]

function genreTint(value: string): string | null {
  if (!value) return null
  let h = 0
  for (let i = 0; i < value.length; i++) h = (h * 31 + value.charCodeAt(i)) >>> 0
  return GENRE_TINT_CLASSES[h % GENRE_TINT_CLASSES.length] ?? null
}

function EbookCard({ ebook, onBorrow, onJoinWaitlist, onPlaceHold, isBorrowing, flaggedWarnings = [], hiddenWarnings = [] }: {
  ebook: IndieEbookPublic
  onBorrow: (id: number) => void
  onJoinWaitlist: (id: number) => void
  onPlaceHold: (id: number) => void
  isBorrowing: boolean
  flaggedWarnings?: string[]
  hiddenWarnings?: string[]
}): React.ReactElement {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { settings } = useAccessibility()
  const isAvailable = ebook.available_copies > 0
  const ratingInfo = getRatingInfo(ebook.content_rating)
  const [showPreview, setShowPreview] = useState(false)

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 hover:shadow-md transition-shadow">
      <div className="flex gap-4">
        {/* Cover Image */}
        <div className="w-20 h-28 bg-lsc-cream dark:bg-lsc-brown rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
          {ebook.cover_url ? (
            <img
              src={ebook.cover_url}
              alt={t('indieCatalog.coverOfTitle', { title: ebook.title })}
              className="w-full h-full object-cover"
              loading="lazy"
              decoding="async"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          ) : (
            <BookOpen className="w-8 h-8 text-lsc-rose/50" aria-hidden="true" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={ebook.title}>
                {ebook.title}
              </h3>
              <Link
                to={`/indie/author/${penNameToSlug(ebook.author_pen_name)}`}
                className="text-sm text-lsc-rose underline hover:text-lsc-rose/80"
              >
                {t('indieCatalog.byAuthor', { author: ebook.author_pen_name })}
              </Link>
            </div>
          </div>

          {/* Badges */}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {ebook.genre && (
              <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
                {formatGenre(ebook.genre)}
              </span>
            )}
            {ebook.content_rating && ebook.content_rating !== 'unrated' && (
              <span
                className={clsx('text-xs px-2 py-1 rounded', ratingInfo.color)}
                title={ratingInfo.description}
                aria-label={ratingInfo.description}
              >
                {ratingInfo.label}
              </span>
            )}
            {ebook.content_warnings && ebook.content_warnings.length > 0 && (
              <ContentWarningBadges
                warnings={ebook.content_warnings}
                flaggedWarnings={flaggedWarnings}
                hiddenWarnings={hiddenWarnings}
              />
            )}
            {ebook.is_preorder ? (
              <span className="text-xs px-2 py-1 bg-category-100 text-category-700 dark:bg-category-900 dark:text-category-200 rounded flex items-center gap-1">
                <CalendarClock className="w-3 h-3" />
                {t('indie.preorder')}
              </span>
            ) : isAvailable ? (
              <span className="text-xs px-2 py-1 bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200 rounded flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                {t('indie.available')}
              </span>
            ) : (
              <span className="text-xs px-2 py-1 bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200 rounded flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {t('indie.waitlist')}
              </span>
            )}
            {ebook.demand_level && ebook.demand_level !== 'none' && (
              <span className={clsx(
                'text-xs px-2 py-1 rounded flex items-center gap-1',
                ebook.demand_level === 'card_available'
                  ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200'
                  : ebook.demand_level === 'high'
                    ? 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200'
                    : 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-800 dark:text-lsc-cream/70'
              )}>
                {ebook.demand_level === 'card_available' ? (
                  <ShoppingCart className="w-3 h-3" />
                ) : (
                  <TrendingUp className="w-3 h-3" />
                )}
                {ebook.demand_level === 'card_available'
                  ? t('indie.cardAvailable')
                  : ebook.demand_level === 'high'
                    ? t('indie.highDemand')
                    : t('indie.growingInterest')}
              </span>
            )}
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            <span className="flex items-center gap-1">
              <Star aria-hidden="true" className={clsx('w-3 h-3', ebook.average_rating ? 'text-lsc-gold dark:text-status-warning-400 fill-lsc-gold dark:fill-status-warning-400' : 'text-lsc-dark/30 dark:text-lsc-cream/60')} />
              {ebook.average_rating
                ? <>{ebook.average_rating.toFixed(1)} ({ebook.rating_count})</>
                : <span className="text-lsc-dark/70 dark:text-lsc-cream/50">{t('indie.noRatings')}</span>
              }
            </span>
            {!settings.noFOMO && ebook.total_borrows > 0 && (
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                {ebook.total_borrows} {ebook.total_borrows === 1 ? t('indie.reader') : t('indie.readers')}
              </span>
            )}
            {ebook.is_preorder && ebook.preorder_release_date ? (
              <span className="flex items-center gap-1">
                <CalendarClock className="w-3 h-3" />
                {t('indieCatalog.expectedDate', { date: parseDate(ebook.preorder_release_date)?.toLocaleDateString() ?? '-' })}
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {t('indieCatalog.borrowDurationDays', { count: ebook.borrow_duration_days })}
              </span>
            )}
          </div>

          {/* Description */}
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={ebook.description}>
            {ebook.description}
          </p>

          {/* Actions */}
          <div className="mt-3 flex items-center gap-2">
            <Link
              to={`/indie/book/${generateSlug(ebook.title, ebook.id)}`}
              className="text-sm text-lsc-rose underline hover:text-lsc-rose/80"
              aria-label={t('indieCatalog.viewDetailsForTitle', { title: ebook.title })}
              onMouseEnter={() => {
                const slug = generateSlug(ebook.title, ebook.id)
                queryClient.prefetchQuery({
                  queryKey: ['indie-book', slug],
                  queryFn: () => getPublicBookDetail(slug),
                  staleTime: 5 * 60 * 1000,
                })
              }}
            >
              {t('indie.viewDetails')}
            </Link>
            <ShareButton
              resourceType="book"
              resourceId={ebook.id}
              title={ebook.title}
              variant="compact"
              platforms={['copy_link', 'email', 'whatsapp']}
              {...(ebook.author_pen_name ? { author: ebook.author_pen_name } : {})}
              {...(ebook.cover_url ? { imageUrl: ebook.cover_url } : {})}
            />
            <button
              onClick={() => setShowPreview(true)}
              className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose flex items-center gap-1"
              aria-label={t('indieCatalog.readSampleOfTitle', { title: ebook.title })}
            >
              <BookOpen className="w-3 h-3" />
              {t('indie.preview')}
            </button>
            {user && <BookmarkButton ebookId={ebook.id} title={ebook.title} />}
            {user && (
              <>
                {ebook.is_preorder ? (
                  <button
                    onClick={() => onPlaceHold(ebook.id)}
                    disabled={isBorrowing}
                    aria-label={t('indieCatalog.placeHoldOnTitle', { title: ebook.title })}
                    className="ml-auto px-3 py-1.5 text-sm bg-category-600 text-white rounded-lg hover:bg-category-700 disabled:opacity-50 flex items-center gap-1"
                  >
                    {isBorrowing ? (
                      <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                    ) : (
                      <Bell className="w-3 h-3" />
                    )}
                    {t('indie.placeHold')}
                  </button>
                ) : isAvailable ? (
                  <button
                    onClick={() => onBorrow(ebook.id)}
                    disabled={isBorrowing}
                    aria-label={t('indieCatalog.borrowTitle', { title: ebook.title })}
                    className="ml-auto px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-1"
                  >
                    {isBorrowing ? (
                      <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                    ) : (
                      <BookMarked className="w-3 h-3" />
                    )}
                    {t('indie.borrow')}
                  </button>
                ) : (
                  <div className="ml-auto flex items-center gap-2">
                    <button
                      onClick={() => onJoinWaitlist(ebook.id)}
                      disabled={isBorrowing}
                      aria-label={t('indieCatalog.joinWaitlistForTitle', { title: ebook.title })}
                      className="px-3 py-1.5 text-sm border border-lsc-rose text-lsc-rose rounded-lg hover:bg-lsc-rose/10 disabled:opacity-50"
                    >
                      {t('indie.joinWaitlist')}
                    </button>
                    <Link
                      to={`/indie/book/${generateSlug(ebook.title, ebook.id)}`}
                      aria-label={t('indieCatalog.buyOptionsForTitle', { title: ebook.title })}
                      className="px-3 py-1.5 text-sm border border-lsc-blue text-lsc-blue dark:border-lsc-blue-light dark:text-lsc-blue-light rounded-lg hover:bg-lsc-blue/10 dark:hover:bg-lsc-blue-light/10 flex items-center gap-1"
                    >
                      <ShoppingCart className="w-3 h-3" />
                      {t('indie.buy')}
                    </Link>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      {showPreview && <BookPreviewModal ebookId={ebook.id} onClose={() => setShowPreview(false)} />}
    </div>
  )
}

export default function IndieCatalogPage(): React.ReactElement {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { quietMode } = useNeurodivergentUX()
  usePageTitle(t('indieCatalog.pageTitle', 'Indie eBooks'), t('indieCatalog.pageDescription', 'Browse and borrow indie ebooks from local authors.'))
  const { settings } = useAccessibility()
  const [searchParams, setSearchParams] = useSearchParams()

  // URL-synced filter state (shareable, back-button friendly)
  const submittedQuery = searchParams.get('q') || ''
  const selectedGenre = searchParams.get('genre') || ''
  const selectedRating = (searchParams.get('rating') || '') as ContentRating | ''
  const selectedSort = searchParams.get('sort') || 'newest'
  const availableOnly = searchParams.get('avail') === '1'
  const page = Number(searchParams.get('page')) || 1
  const [searchQuery, setSearchQuery] = useState(submittedQuery)
  const [showFilters, setShowFilters] = useState(!!selectedGenre || !!selectedRating)
  const [showStickySearch, setShowStickySearch] = useState(false)
  const [stickySearchTop, setStickySearchTop] = useState(0)
  const [showCWPrefs, setShowCWPrefs] = useState(false)
  const heroRef = useRef<HTMLDivElement>(null)
  const browseRef = useRef<HTMLDivElement>(null)

  // Show sticky search bar when hero scrolls out of view
  useEffect(() => {
    if (!heroRef.current) return
    const observer = new IntersectionObserver(
      ([entry]) => setShowStickySearch(!entry?.isIntersecting),
      { threshold: 0 }
    )
    observer.observe(heroRef.current)
    return () => observer.disconnect()
  }, [])

  // The site header is sticky too; pin the search pill directly below it
  useEffect(() => {
    if (!showStickySearch) return
    const measure = () => {
      const header = document.querySelector('header')
      setStickySearchTop(header ? Math.max(0, header.getBoundingClientRect().bottom) : 0)
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [showStickySearch])

  const scrollToBrowse = useCallback(() => {
    browseRef.current?.scrollIntoView({ behavior: settings.reduceMotion ? "auto" : "smooth", block: "start" })
  }, [settings.reduceMotion])

  const { data: discoveryData, isLoading: discoveryLoading } = useQuery({
    queryKey: ['indie-discovery'],
    queryFn: getDiscoveryPage,
    staleTime: 10 * 60 * 1000,
  })
  const featuredBook = discoveryData?.featured?.[0]
  // Live genre taxonomy from the API; fall back to the hardcoded list while loading
  const apiGenres = discoveryData?.popular_genres
  const hasApiGenres = !!apiGenres && apiGenres.length > 0
  const genreOptions = hasApiGenres
    ? apiGenres.map((g) => ({ label: `${formatGenre(g.name)} (${g.count})`, value: g.name }))
    : getGenres(t)
  const genreChips = hasApiGenres
    ? [
        { label: t('indieCatalog.genreChipAll', 'All'), value: '' },
        ...[...apiGenres]
          .sort((a, b) => b.count - a.count)
          .slice(0, 8)
          .map((g) => ({ label: `${formatGenre(g.name)} (${g.count})`, value: g.name })),
      ]
    : getGenreChips(t)
  const staffPicks = discoveryData?.staff_picks || []
  const newArrivals = discoveryData?.new_arrivals || []

  const { data: preorderData } = useQuery({
    queryKey: ["indie-preorders"],
    queryFn: getPreorderEbooks,
    staleTime: 10 * 60 * 1000,
  })

  const { data: justAvailable } = useQuery({
    queryKey: ['indie-just-available'],
    queryFn: () => getJustAvailableEbooks(8, 7),
    staleTime: 5 * 60 * 1000,
  })

  const { data: upcomingEvents } = useQuery({
    queryKey: ['indie-upcoming-events'],
    queryFn: () => getUpcomingIndieEvents(5),
    staleTime: 5 * 60 * 1000,
  })

  const { data: publicLists } = useQuery({
    queryKey: ['indie-public-lists'],
    queryFn: () => getPublicReadingLists(6),
    staleTime: 5 * 60 * 1000,
  })

  const { data: contentPrefs } = useQuery({
    queryKey: ['indie-content-prefs'],
    queryFn: getContentPreferences,
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
  })

  const { data: featuredAuthor } = useQuery({
    queryKey: ["indie-featured-author"],
    queryFn: getFeaturedAuthor,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  const hiddenWarningsKey = [...(contentPrefs?.hidden_warnings || [])].sort().join('|')

  const { data, isLoading, error } = useQuery({
    queryKey: ['indie-catalog', submittedQuery, selectedGenre, selectedRating, selectedSort, page, hiddenWarningsKey],
    queryFn: () => {
      const params: Parameters<typeof browseIndieCatalog>[0] = { page, per_page: 20 }
      if (submittedQuery) params.q = submittedQuery
      if (selectedGenre) params.genre = selectedGenre
      if (selectedRating) params.content_rating = selectedRating
      if (selectedSort) params.sort = selectedSort
      if (contentPrefs?.hidden_warnings && contentPrefs.hidden_warnings.length > 0) {
        params.exclude_warnings = contentPrefs.hidden_warnings
      }
      return browseIndieCatalog(params)
    },
    staleTime: 2 * 60 * 1000,
    placeholderData: keepPreviousData,
  })

  const borrowMutation = useMutation({
    mutationFn: borrowEbook,
    onSuccess: (data) => {
      toast.success(t('toast.indieCatalog.successfullyBorrowedEbooktitle', { ebooktitle: data.ebook_title }))
      queryClient.invalidateQueries({ queryKey: ['indie-catalog'] })
      queryClient.invalidateQueries({ queryKey: ['active-borrows'] })
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : t('toast.indie.failedToBorrowEbook'))
    },
  })

  const waitlistMutation = useMutation({
    mutationFn: joinWaitlist,
    onSuccess: (data) => {
      toast.success(t('toast.indieCatalog.addedToWaitlistForEbooktitle', { ebooktitle: data.ebook_title, position: data.position }))
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : t('toast.indie.failedToJoinWaitlist'))
    },
  })

  const preorderHoldMutation = useMutation({
    mutationFn: (ebookId: number) => placePreorderHold(ebookId),
    onSuccess: (data) => {
      toast.success(t('toast.indieCatalog.message', { message: data.message }))
      queryClient.invalidateQueries({ queryKey: ['indie-preorders'] })
      queryClient.invalidateQueries({ queryKey: ['indie-catalog'] })
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : t('toast.holdFailed'))
    },
  })

  const updateParams = (updates: Record<string, string>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      for (const [k, v] of Object.entries(updates)) {
        if (v) next.set(k, v)
        else next.delete(k)
      }
      return next
    }, { replace: true })
  }

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault()
    updateParams({ q: searchQuery, page: '' })
    scrollToBrowse()
  }

  const handleClearFilters = () => {
    updateParams({ genre: '', rating: '', page: '' })
  }

  const hasFilters = selectedGenre || selectedRating

  return (
    
    <div className="space-y-8">
      {/* Sticky Search -- appears when scrolling past hero */}
      <div
        style={{ top: stickySearchTop }}
        aria-hidden={!showStickySearch}
        className={clsx(
          'fixed left-0 right-0 z-40 transition-transform duration-300 bg-lsc-white/95 dark:bg-earth-900/95 backdrop-blur-sm shadow-md',
          showStickySearch ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0 pointer-events-none'
        )}
      >
        <form
          onSubmit={submitSearch}
          className="max-w-2xl mx-auto px-4 py-2.5 flex gap-2"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('indieCatalog.searchIndieEbooksEllipsis', 'Search indie ebooks...')}
              aria-label={t('indieCatalog.searchIndieEbooksLabel', 'Search indie ebooks')}
              tabIndex={showStickySearch ? 0 : -1}
              className="w-full pl-9 pr-4 py-2 rounded-full border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
            />
          </div>
          <button
            type="submit"
            tabIndex={showStickySearch ? 0 : -1}
            className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-full hover:bg-lsc-rose/90"
          >
            {t('indieCatalog.searchBtn', 'Search')}
          </button>
        </form>
      </div>

      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Heart className="w-6 h-6 text-lsc-rose" />
          <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('indieCatalog.indieAuthorsIndependentVoices', 'Indie Authors, Independent Voices')}
          </h1>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          {t('indieCatalog.independentlyPublishedEbooksAvailableToBorrow', 'Independently published eBooks available to borrow for free through the library. Real authors, real stories. No waitlists on most titles.')}
        </p>
        {discoveryData && (discoveryData.total_books > 0 || discoveryData.total_authors > 0) && (
          <p className="mt-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60" aria-label={t('indieCatalog.catalogSize', 'Catalog size')}>
            {discoveryData.total_books > 0 && (
              <span>{t('indieCatalog.titleCount', { count: discoveryData.total_books })}</span>
            )}
            {discoveryData.total_books > 0 && discoveryData.total_authors > 0 && <span> &middot; </span>}
            {discoveryData.total_authors > 0 && (
              <span>{t('indieCatalog.authorCount', { count: discoveryData.total_authors })}</span>
            )}
            {' '}&middot;{' '}
            <a
              href={getRssFeedUrl()}
              className="inline-flex items-center gap-1 underline hover:text-lsc-rose"
            >
              <Rss className="w-3 h-3" aria-hidden="true" />
              {t('indieCatalog.rssFeedOfNewIndie', 'RSS feed of new indie titles')}
            </a>
          </p>
        )}
        {!user && (
          <p className="mt-2 text-sm text-lsc-rose">
            <Link to="/login" className="underline">{t('indieCatalog.signIn', 'Sign in')}</Link> {t('indieCatalog.toBorrowItsFreeAlwaysHas', "to borrow - it's free, always has been")}
          </p>
        )}
        <div className="mt-3 flex items-center justify-center gap-4 text-sm flex-wrap">
          {user && (
            <>
              <Link to="/indie/my-borrows" className="text-lsc-rose underline hover:text-lsc-rose/80">
                {t('indieCatalog.myBorrows', 'My Borrows')}
              </Link>
              <Link to="/indie/saved" className="text-lsc-rose underline hover:text-lsc-rose/80 flex items-center gap-1">
                <Bookmark className="w-3.5 h-3.5" />
                {t('indieCatalog.mySavedBooks', 'My Saved Books')}
              </Link>
            </>
          )}
          <Link to="/indie/author/browse" className="text-lsc-rose underline hover:text-lsc-rose/80 flex items-center gap-1">
            <Users className="w-3.5 h-3.5" />
            {t('indieCatalog.browseAuthors', 'Browse authors')}
          </Link>
        </div>
      </div>

      {/* Quick Search -- compact entry point below header */}
      <div ref={heroRef} className="max-w-xl mx-auto">
        <form
          onSubmit={submitSearch}
          className="relative"
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50" aria-hidden="true" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('indieCatalog.searchByTitleAuthorOrGenre', 'Search by title, author, or genre...')}
            aria-label={t('indieCatalog.quickSearchIndieEbooks', 'Quick search indie ebooks')}
            className="w-full pl-9 pr-20 py-2.5 rounded-full border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/40 dark:placeholder:text-lsc-cream/40 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          />
          <button
            type="submit"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 px-4 py-1.5 text-sm bg-lsc-rose text-white rounded-full hover:bg-lsc-rose/90"
          >
            {t('indieCatalog.searchBtn', 'Search')}
          </button>
        </form>
      </div>

      {/* How indie works -- explainer strip */}
      <section aria-labelledby="why-indie-heading" className="max-w-4xl mx-auto mt-2 mb-10">
        <h2 id="why-indie-heading" className="text-center text-xs font-semibold uppercase tracking-wide text-lsc-rose mb-4">
          {t('indieCatalog.howIndieWorks', 'How indie works')}
        </h2>
        <ul className="grid gap-4 sm:grid-cols-3 list-none p-0 m-0">
          <li className="rounded-xl bg-lsc-cream/60 dark:bg-earth-800 p-4 text-center">
            <Heart aria-hidden="true" className="w-6 h-6 mx-auto mb-2 text-lsc-rose" />
            <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('indieCatalog.authorsGetPaid', 'Authors get paid')}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('indieCatalog.whenWeBuyAnIndie', "When we buy an indie author's book, a fair share goes straight to them.")}</p>
          </li>
          <li className="rounded-xl bg-lsc-cream/60 dark:bg-earth-800 p-4 text-center">
            <BookMarked aria-hidden="true" className="w-6 h-6 mx-auto mb-2 text-lsc-rose" />
            <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('indieCatalog.weOwnOurCopy', 'We own our copy')}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('indieCatalog.itsOursToLendForGood', "It's ours to lend for good, not a license that expires when a contract ends.")}</p>
          </li>
          <li className="rounded-xl bg-lsc-cream/60 dark:bg-earth-800 p-4 text-center">
            <CheckCircle aria-hidden="true" className="w-6 h-6 mx-auto mb-2 text-lsc-rose" />
            <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('indieCatalog.youBorrowFree', 'You borrow free')}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('indieCatalog.noFeesNoWaitlistOnMost', 'No fees, no waitlist on most titles. Borrow it and start reading.')}</p>
          </li>
        </ul>
      </section>

      {/* Continue reading -- logged-in only, hidden in Quiet Mode */}
      {!quietMode && user && <ContinueReadingRail />}

      {/* Discovery sections -- hidden in Quiet Mode */}
      {!quietMode && (
        discoveryLoading ? (
          <div className="space-y-8 animate-pulse">
            {/* Hero skeleton */}
            <div className="h-64 rounded-xl bg-lsc-cream dark:bg-earth-800" />
            {/* Staff picks skeleton */}
            <div>
              <div className="h-6 w-32 rounded bg-lsc-cream dark:bg-earth-800 mb-4" />
              <div className="flex gap-4 overflow-hidden">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="w-[200px] flex-shrink-0 rounded-xl bg-lsc-cream dark:bg-earth-800 h-72" />
                ))}
              </div>
            </div>
            {/* New this week skeleton */}
            <div>
              <div className="h-6 w-36 rounded bg-lsc-cream dark:bg-earth-800 mb-4" />
              <div className="flex gap-4 overflow-hidden">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="w-[180px] flex-shrink-0 rounded-xl bg-lsc-cream dark:bg-earth-800 h-64" />
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Featured Book Hero */}
            {featuredBook && (
              <FeaturedBookHero
                book={featuredBook}
                onBookClick={(slug) => navigate(`/indie/book/${slug}`)}
              />
            )}

            {/* Staff Picks */}
            <StaffPicksSection
              books={staffPicks}
              onBookClick={(slug) => navigate(`/indie/book/${slug}`)}
            />

            {/* New This Week */}
            <NewThisWeekSection
              books={newArrivals}
              onBookClick={(slug) => navigate(`/indie/book/${slug}`)}
            />

            {/* Just Became Available -- shows only when there are recent returns */}
            {justAvailable && justAvailable.length > 0 && (
              <JustAvailableSection books={justAvailable} />
            )}

            {/* Upcoming author events -- shows when indie authors have events */}
            {upcomingEvents && upcomingEvents.length > 0 && (
              <UpcomingEventsRail events={upcomingEvents} />
            )}

            {/* Public patron-made reading lists */}
            {publicLists && publicLists.length > 0 && (
              <PublicListsRail lists={publicLists} />
            )}
          </>
        )
      )}

      {/* Author Spotlight -- hidden in Quiet Mode */}
      {!quietMode && featuredAuthor && (
        <AuthorSpotlight author={featuredAuthor} />
      )}

      {/* Coming Soon / Preorders -- hidden in Quiet Mode */}
      {!quietMode && preorderData && preorderData.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <CalendarClock className="w-5 h-5 text-category-600 dark:text-category-400" />
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('indieCatalog.comingSoon', 'Coming Soon')}
            </h2>
            <span className="text-xs px-2 py-0.5 bg-category-100 text-category-700 dark:bg-category-900 dark:text-category-200 rounded-full">
              {t('indieCatalog.placeAHoldNow', 'Place a hold now')}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {preorderData.map((preorder) => (
              <div
                key={preorder.ebook_id}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 hover:shadow-md transition-shadow border border-category-100 dark:border-category-900/30"
              >
                <div className="flex gap-3">
                  <div className="w-16 h-24 bg-lsc-cream dark:bg-lsc-brown rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
                    {preorder.cover_url ? (
                      <img
                        src={preorder.cover_url}
                        alt={t('indieCatalog.coverOfTitle', { title: preorder.title })}
                        className="w-full h-full object-cover"
                        loading="lazy"
                        decoding="async"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none'
                        }}
                      />
                    ) : (
                      <BookOpen className="w-6 h-6 text-category-400/50" aria-hidden="true" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream truncate" title={preorder.title}>
                      {preorder.title}
                    </h3>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {t('indieCatalog.byAuthor', { author: preorder.author_pen_name })}
                    </p>
                    {preorder.release_date && (
                      <p className="text-xs text-category-600 dark:text-category-400 mt-1 flex items-center gap-1">
                        <CalendarClock className="w-3 h-3" />
                        {parseDate(preorder.release_date)?.toLocaleDateString() ?? '-'}
                      </p>
                    )}
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 flex items-center gap-1">
                      <Users className="w-3 h-3" aria-hidden="true" />
                      {t('indieCatalog.holdCount', { count: preorder.hold_count })}
                    </p>
                  </div>
                </div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={preorder.description}>
                  {preorder.description}
                </p>
                {user ? (
                  <button
                    onClick={() => preorderHoldMutation.mutate(preorder.ebook_id)}
                    disabled={preorderHoldMutation.isPending}
                    className="mt-3 w-full px-3 py-1.5 text-sm bg-category-600 text-white rounded-lg hover:bg-category-700 disabled:opacity-50 flex items-center justify-center gap-1"
                  >
                    {preorderHoldMutation.isPending ? (
                      <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                    ) : (
                      <Bell className="w-3 h-3" />
                    )}
                    {t('indie.placeHold')}
                  </button>
                ) : (
                  <Link
                    to={`/login?next=${encodeURIComponent('/indie')}`}
                    className="mt-3 w-full px-3 py-1.5 text-sm border border-category-600 text-category-700 dark:text-category-200 rounded-lg hover:bg-category-50 dark:hover:bg-category-900/30 flex items-center justify-center gap-1"
                    aria-label={t('indieCatalog.signInToPlaceAHoldOnTitle', { title: preorder.title })}
                  >
                    <Bell className="w-3 h-3" />
                    {t('indieCatalog.signInToPlaceAHold', 'Sign in to place a hold')}
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search */}
      <div ref={browseRef} />
      <form onSubmit={submitSearch} role="search" aria-label={t('aria.indieCatalog.searchIndieEbooks')} className="max-w-2xl mx-auto">
        <div className="flex gap-2 flex-wrap sm:flex-nowrap">
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('placeholder.indieCatalog.searchIndieEbooks')}
              aria-label={t('aria.indieCatalog.searchIndieEbooks')}
              className="w-full pl-10 pr-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <button
            type="submit"
            className="px-3 sm:px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 shrink-0"
          >
            {t('indieCatalog.searchBtn', 'Search')}
          </button>
          {user && (
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowCWPrefs(!showCWPrefs)}
                aria-label={t('indieCatalog.contentWarningPreferences', 'Content warning preferences')}
                className="px-3 py-3 rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-800 flex items-center gap-1"
              >
                <Settings className="w-5 h-5" />
                {(contentPrefs?.hidden_warnings?.length || 0) > 0 && (
                  <span className="text-xs bg-lsc-rose text-white px-1.5 rounded-full">
                    {contentPrefs?.hidden_warnings?.length}
                  </span>
                )}
              </button>
              {showCWPrefs && (
                <div className="absolute right-0 top-full mt-2 z-50">
                  <ContentPreferencesPanel onClose={() => setShowCWPrefs(false)} />
                </div>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            aria-expanded={showFilters}
            aria-label={showFilters ? t('indieCatalog.hideFilters', 'Hide filters') : t('indieCatalog.showFilters', 'Show filters')}
            className={clsx(
              'px-4 py-3 rounded-xl border flex items-center gap-2',
              showFilters
                ? 'bg-lsc-rose text-white border-lsc-rose'
                : 'border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream'
            )}
          >
            <Filter className="w-5 h-5" />
            {hasFilters && (
              <span className="bg-lsc-white dark:bg-earth-800 text-lsc-rose text-xs px-1.5 rounded-full">
                {(selectedGenre ? 1 : 0) + (selectedRating ? 1 : 0)}
              </span>
            )}
          </button>
        </div>
      </form>


      {/* Genre Quick Filters */}
      <div className="flex gap-2 overflow-x-auto pb-2 max-w-2xl mx-auto scrollbar-thin" role="group" aria-label={t('indieCatalog.filterByGenre', 'Filter by genre')}>
        {genreChips.map((chip) => (
          <button
            key={chip.label}
            onClick={() => updateParams({ genre: chip.value, page: '' })}
            className={clsx(
              'px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors',
              selectedGenre === chip.value
                ? 'bg-lsc-rose text-white'
                : (genreTint(chip.value) || 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/20')
            )}
            aria-pressed={selectedGenre === chip.value}
          >
            {chip.label}
          </button>
        ))}
        <button
          onClick={() => updateParams({ avail: availableOnly ? '' : '1' })}
          className={clsx(
            'px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-1',
            availableOnly
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/20'
          )}
          aria-pressed={availableOnly}
        >
          <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" />
          {t('indieCatalog.availableNow', 'Available now')}
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="max-w-2xl mx-auto bg-lsc-cream dark:bg-earth-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('indieCatalog.filters', 'Filters')}</h3>
            {hasFilters && (
              <button
                onClick={handleClearFilters}
                className="text-sm text-lsc-rose hover:underline flex items-center gap-1"
              >
                <X className="w-4 h-4" /> {t('indieCatalog.clear', 'Clear')}
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-lsc-dark dark:text-lsc-cream">
                {t('indieCatalog.genreLabel', 'Genre')}
              </label>
              <select
                value={selectedGenre}
                onChange={(e) => updateParams({ genre: e.target.value, page: '' })}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
              >
                <option value="">{t('indieCatalog.allGenres', 'All Genres')}</option>
                {genreOptions.map((genre) => (
                  <option key={genre.value} value={genre.value}>{genre.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2 text-lsc-dark dark:text-lsc-cream">
                {t('indieCatalog.contentRatingLabel', 'Content Rating')}
              </label>
              <select
                value={selectedRating}
                onChange={(e) => updateParams({ rating: e.target.value, page: '' })}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
              >
                <option value="">{t('indieCatalog.allRatings', 'All Ratings')}</option>
                <option value="e">{t('indieCatalog.ratingAllAgesE', 'All Ages (E)')}</option>
                <option value="pg">{t('indieCatalog.ratingParentalGuidancePg', 'Parental Guidance (PG)')}</option>
                <option value="pg13">{t('indieCatalog.ratingTeenPg13', 'Teen (PG-13)')}</option>
                <option value="r">{t('indieCatalog.ratingMatureR', 'Mature (R)')}</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      )}

      {error && (
        <div className="text-center py-8">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-status-danger-500" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            {t('indieCatalog.unableToLoadEbooks', 'Unable to load eBooks right now.')}
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('indieCatalog.pleaseRefreshThePage', 'Please refresh the page or try again in a few minutes.')}
          </p>
        </div>
      )}

      {data && (() => {
        // No availability param on the list endpoint; filter the current page client-side
        const visibleItems = availableOnly
          ? data.items.filter((e) => e.available_copies > 0)
          : data.items
        return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="sr-only">{t('indieCatalog.browseEbooks', 'Browse eBooks')}</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70" aria-live="polite">
              {data.total === 0
                ? t('indieCatalog.noEbooksFound', 'No eBooks found')
                : t('indieCatalog.showingCountOfTotal', { count: visibleItems.length, total: data.total })}
              {availableOnly && (
                <span className="ml-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">{t('indieCatalog.availableNowOnly', 'Available now only')}</span>
              )}
              {(contentPrefs?.hidden_warnings?.length || 0) > 0 && (
                <span className="ml-2 text-xs text-status-warning-600 dark:text-status-warning-400">{t('indieCatalog.filteringActive', 'Filtering active')}</span>
              )}
            </p>
            <select
              value={selectedSort}
              onChange={(e) => updateParams({ sort: e.target.value, page: '' })}
              aria-label={t('indieCatalog.sortBooksBy', 'Sort books by')}
              className="px-3 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            >
              <option value="newest">{t('indieCatalog.sortNewest', 'Newest')}</option>
              <option value="popular">{t('indieCatalog.sortMostPopular', 'Most Popular')}</option>
              <option value="rating">{t('indieCatalog.sortHighestRated', 'Highest Rated')}</option>
              <option value="title">{t('indieCatalog.sortTitleAz', 'Title A-Z')}</option>
            </select>
          </div>

          {visibleItems.length > 0 ? (
            <div role="list" className="grid gap-4 lg:grid-cols-2">
              {visibleItems.map((ebook) => (
                <div role="listitem" key={ebook.id}>
                  <EbookCard
                    ebook={ebook}
                    onBorrow={(id) => borrowMutation.mutate(id)}
                    onJoinWaitlist={(id) => waitlistMutation.mutate(id)}
                    onPlaceHold={(id) => preorderHoldMutation.mutate(id)}
                    isBorrowing={
                      (borrowMutation.isPending && borrowMutation.variables === ebook.id) ||
                      (waitlistMutation.isPending && waitlistMutation.variables === ebook.id) ||
                      (preorderHoldMutation.isPending && preorderHoldMutation.variables === ebook.id)
                    }
                    flaggedWarnings={contentPrefs?.flagged_warnings || []}
                    hiddenWarnings={contentPrefs?.hidden_warnings || []}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <BookOpen className="w-16 h-16 mx-auto mb-4 text-lsc-dark/30 dark:text-lsc-cream/60" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('indieCatalog.noIndieEbooksFound', 'No indie eBooks found. Try adjusting your filters.')}
              </p>
            </div>
          )}

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => updateParams({ page: String(Math.max(1, page - 1)) })}
                disabled={page === 1}
                className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50"
              >
                {t('indieCatalog.previous', 'Previous')}
              </button>
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('indieCatalog.pageOfTotal', { page, total: data.pages })}
              </span>
              <button
                onClick={() => updateParams({ page: String(Math.min(data.pages, page + 1)) })}
                disabled={page === data.pages}
                className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50"
              >
                {t('indieCatalog.next', 'Next')}
              </button>
            </div>
          )}
        </div>
        )
      })()}
    </div>
  
  )
}
