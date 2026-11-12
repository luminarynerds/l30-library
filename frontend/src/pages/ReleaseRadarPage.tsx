/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useMemo } from "react"
import { useAuth } from "../contexts/AuthContext"
import { Loader2, Calendar, BookOpen, Heart, Bell, Search, User, Baby, X, Plus, ChevronLeft, ChevronRight } from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation, getCurrentLocale } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useBranding } from '@/contexts/BrandingContext'
import { fetchApi } from '@/api/fetchApi'
import PageContainer from '@/components/layout/PageContainer'

const PAGE_SIZE = 10

type SortOption = "date_asc" | "date_desc" | "author_name"
type MoodFilter = "all" | "cozy" | "page_turner" | "funny"

interface Author {
  id: string
  name: string
  image_url: string | null
  follower_count: number
}

interface Book {
  id: string
  title: string
  subtitle: string | null
  release_date: string | null
  is_date_exact: boolean
  isbn_13: string | null
  age_rating: string
  cover_url: string | null
  publisher: string | null
  status: string
  mood?: MoodFilter
}

interface ReleaseFeedItem {
  book: Book
  author: Author
  days_until_release: number | null
  is_followed: boolean
}

interface FollowedAuthor {
  follow_id: number
  author: Author
  profile_type: string
  notify_on_release: boolean
}

interface AuthorSearchResult {
  id: string | null
  name: string
  source: string
  source_id?: string
  follower_count: number
  image_url: string | null
}

// Wraps the shared fetchApi (which attaches the JWT and base URL) and preserves
// the existing call-site signature. The token arg is intentionally unused but
// kept so the !token short-circuits in callers stay meaningful.
async function apiFetch<T>(_token: string, endpoint: string, options: RequestInit = {}): Promise<T> {
  try {
    return await fetchApi("/releases" + endpoint, options) as T
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'message' in err) {
      throw new Error(String((err as { message: unknown }).message))
    }
    throw err instanceof Error ? err : new Error(String(err))
  }
}

const formatDate = (d: string | null, isExact: boolean): string => {
  if (!d) return "Coming Soon"
  const date = new Date(d)
  if (!isExact) {
    const month = date.toLocaleDateString(getCurrentLocale(), { month: "long" })
    return `Coming ${month} ${date.getFullYear()}`
  }
  return date.toLocaleDateString(getCurrentLocale(), { weekday: "short", month: "short", day: "numeric", year: "numeric" })
}

const getDaysLabel = (days: number | null): string => {
  if (days === null) return ""
  if (days < 0) return "Released"
  if (days === 0) return "Today!"
  if (days === 1) return "Tomorrow"
  if (days <= 7) return `${days} days`
  if (days <= 30) return `${Math.ceil(days / 7)} weeks`
  return `${Math.ceil(days / 30)} months`
}

const getAgeIcon = (rating: string) => {
  if (rating === "child") return <Baby aria-hidden="true" className="w-4 h-4 text-status-success-600" />
  if (rating === "teen") return <User aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
  return null
}

export default function ReleaseRadarPage(): React.ReactElement {
  const branding = useBranding()
  usePageTitle('Release Radar', `Discover new books, movies, and music coming to ${branding.library_short_name}. Browse upcoming releases and place holds.`)
  const { t } = useTranslation()
  const { token, isLoading: authLoading, isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState<"timeline" | "authors">("timeline")
  const [profileFilter, setProfileFilter] = useState<"parent" | "child">("parent")
  const [isLoading, setIsLoading] = useState(false)
  const [releases, setReleases] = useState<ReleaseFeedItem[]>([])
  const [followedAuthors, setFollowedAuthors] = useState<FollowedAuthor[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<AuthorSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [sortBy, setSortBy] = useState<SortOption>("date_asc")
  const [moodFilter, setMoodFilter] = useState<MoodFilter>("all")
  const [page, setPage] = useState(0)
  const [totalReleases, setTotalReleases] = useState(0)
  const [unfollowConfirm, setUnfollowConfirm] = useState<string | null>(null)

  const followingIds = useMemo(() => new Set(followedAuthors.map((f) => f.author.id)), [followedAuthors])

  const loadReleases = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      params.set("profile", profileFilter)
      params.set("offset", String(page * PAGE_SIZE))
      params.set("limit", String(PAGE_SIZE))
      params.set("sort", sortBy)
      if (moodFilter !== "all") params.set("mood", moodFilter)
      const data = await apiFetch<{ items: ReleaseFeedItem[]; total: number }>(token, "/my-releases?" + params.toString())
      setReleases(data.items)
      setTotalReleases(data.total)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.acquisition.failedToLoadReleases'))
    } finally {
      setIsLoading(false)
    }
  }, [token, profileFilter, page, sortBy, moodFilter, t])

  const loadAuthors = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await apiFetch<{ items: FollowedAuthor[] }>(token, "/authors")
      setFollowedAuthors(data.items)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.releaseRadar.failedToLoadAuthors'))
    } finally {
      setIsLoading(false)
    }
  }, [token, t])

  useEffect(() => {
    if (token && isAuthenticated) {
      if (activeTab === "timeline") {
        loadReleases()
      } else {
        loadAuthors()
      }
    }
  }, [token, isAuthenticated, activeTab, profileFilter, loadReleases, loadAuthors])

  const handleSortChange = (newSort: SortOption) => {
    setSortBy(newSort)
    setPage(0)
  }

  const handleMoodChange = (mood: MoodFilter) => {
    setMoodFilter(mood)
    setPage(0)
  }

  const totalPages = Math.ceil(totalReleases / PAGE_SIZE)

  const handleSearchAuthors = async () => {
    if (!token || !searchQuery.trim()) return
    setIsSearching(true)
    try {
      const data = await apiFetch<{ results: AuthorSearchResult[] }>(token, "/authors/search?q=" + encodeURIComponent(searchQuery))
      setSearchResults(data.results)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.selectionList.searchFailed'))
    } finally {
      setIsSearching(false)
    }
  }

  const handleFollowAuthor = async (author: AuthorSearchResult) => {
    if (!token) return
    try {
      if (author.id) {
        // Local author - follow directly
        await apiFetch(token, `/authors/${author.id}/follow`, { method: "POST", body: JSON.stringify({ profile_type: profileFilter }) })
      } else {
        // External author - create and follow
        await apiFetch(token, `/authors/create-and-follow?name=${encodeURIComponent(author.name)}&google_id=${author.source_id || ""}&profile_type=${profileFilter}`, { method: "POST" })
      }
      toast.success(t('toast.releaseRadar.followingName', { name: author.name }))
      setSearchResults([])
      setSearchQuery("")
      loadAuthors()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.releaseRadar.failedToFollow'))
    }
  }

  const handleUnfollowAuthor = async (authorId: string) => {
    if (!token) return
    try {
      await apiFetch(token, `/authors/${authorId}/follow`, { method: "DELETE" })
      toast.success(t('toast.releaseRadar.unfollowed'))
      loadAuthors()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.releaseRadar.failedToUnfollow'))
    }
  }

  /* Sub-component: Skeleton Loader for Release Cards */
  const ReleaseSkeleton = () => (
    <div className="relative pl-16 pb-8 motion-safe:animate-pulse">
      <div className="absolute left-4 w-5 h-5 rounded-full bg-lsc-cream dark:bg-lsc-brown" />
      <div className="bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl p-4 flex gap-4">
        <div className="w-20 h-28 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-3">
          <div className="h-4 bg-lsc-cream dark:bg-lsc-brown rounded w-3/4" />
          <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded w-1/2" />
          <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded w-2/3" />
          <div className="flex gap-2 pt-2">
            <div className="h-5 bg-lsc-cream dark:bg-lsc-brown rounded-full w-20" />
            <div className="h-5 bg-lsc-cream dark:bg-lsc-brown rounded-full w-24" />
          </div>
        </div>
      </div>
    </div>
  )

  /* Sub-component: Skeleton Loader for Author Cards */
  const AuthorCardSkeleton = () => (
    <div className="bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl p-4 motion-safe:animate-pulse">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-lsc-cream dark:bg-lsc-brown" />
          <div className="space-y-2">
            <div className="h-4 bg-lsc-cream dark:bg-lsc-brown rounded w-24" />
            <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded w-20" />
          </div>
        </div>
        <div className="w-8 h-8 bg-lsc-cream dark:bg-lsc-brown rounded" />
      </div>
    </div>
  )

  /* Sub-component: Mood Filter Bar */
  const MoodFilterBar = () => (
    <div className="flex flex-wrap gap-2 mb-4">
      {(["all", "cozy", "page_turner", "funny"] as const).map((mood) => (
        <button
          key={mood}
          onClick={() => handleMoodChange(mood)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            moodFilter === mood
              ? "bg-lsc-rose text-white"
              : "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/70 dark:hover:bg-lsc-brown/70"
          }`}
        >
          {mood === "all" ? "All Moods" : mood === "cozy" ? "Cozy" : mood === "page_turner" ? "Page-Turner" : "Funny"}
        </button>
      ))}
    </div>
  )

  /* Sub-component: Sort Bar */
  const SortBar = () => (
    <div className="flex flex-wrap gap-2 mb-4 items-center">
      <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Sort by:</label>
      <select
        value={sortBy}
        onChange={(e) => handleSortChange(e.target.value as SortOption)}
        className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm"
      >
        <option value="date_asc">Release Date (Soonest)</option>
        <option value="date_desc">Release Date (Latest)</option>
        <option value="author_name">Author Name (A-Z)</option>
      </select>
    </div>
  )

  /* Sub-component: Enhanced Release Card */
  const ReleaseCard = ({ item }: { item: ReleaseFeedItem }) => {
    const urgency = item.days_until_release !== null && item.days_until_release <= 7
    const urgencyColor = urgency ? "bg-status-danger-500 dark:bg-status-danger-600" : "bg-lsc-rose dark:bg-lsc-rose-light"

    return (
      <div className="relative pl-16 pb-8">
        <div className={`absolute left-4 w-5 h-5 rounded-full border-4 border-white dark:border-lsc-dark ${urgencyColor}`} />
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden hover:shadow-md transition-shadow">
          <div className="p-4 flex gap-4">
            {item.book.cover_url ? (
              <img src={item.book.cover_url} alt={`Cover of ${item.book.title}`} className="w-20 h-28 object-cover rounded-xl shadow-sm flex-shrink-0" />
            ) : (
              <div className="w-20 h-28 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center flex-shrink-0">
                <BookOpen aria-hidden="true" className="w-8 h-8 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </div>
            )}

            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream leading-tight">{item.book.title}</h3>
                  {item.book.subtitle && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.book.subtitle}</p>}
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{item.author.name}</p>
                </div>
                {getAgeIcon(item.book.age_rating)}
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{formatDate(item.book.release_date, item.book.is_date_exact)}</span>
                {item.days_until_release !== null && (
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${urgency ? "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300" : "bg-lsc-cream text-lsc-dark/70 dark:bg-lsc-brown dark:text-lsc-cream/70"}`}>
                    {getDaysLabel(item.days_until_release)}
                  </span>
                )}
                {item.book.publisher && <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{item.book.publisher}</span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  /* Sub-component: Enhanced Author Card with Two-Step Unfollow */
  const AuthorCard = ({ follow }: { follow: FollowedAuthor }) => (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {follow.author.image_url ? (
            <img src={follow.author.image_url} alt={`Photo of ${follow.author.name}`} className="w-12 h-12 rounded-full object-cover" />
          ) : (
            <div className="w-12 h-12 rounded-full bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center">
              <User aria-hidden="true" className="w-6 h-6 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
          )}
          <div>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{follow.author.name}</p>
            <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              <span>{follow.author.follower_count} followers</span>
              {follow.notify_on_release && <Bell aria-hidden="true" className="w-3 h-3" />}
            </div>
          </div>
        </div>
        <button
          onClick={() => setUnfollowConfirm(unfollowConfirm === follow.author.id ? null : follow.author.id)}
          className={`p-2 rounded-xl transition-colors ${unfollowConfirm === follow.author.id ? "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-600" : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400"}`}
          title={unfollowConfirm === follow.author.id ? "Click again to confirm" : "Unfollow"}
        >
          <X aria-hidden="true" className="w-4 h-4" />
        </button>
      </div>
      {unfollowConfirm === follow.author.id && (
        <div className="mt-3 p-2 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg text-sm text-status-danger-700 dark:text-status-danger-300">
          <p className="mb-2">{t('releaseRadar.sureThisCanTBe')}</p>
          <button
            onClick={() => {
              handleUnfollowAuthor(follow.author.id)
              setUnfollowConfirm(null)
            }}
            className="px-3 py-1 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-lg text-xs font-medium"
          >
            Yes, Unfollow
          </button>
        </div>
      )}
    </div>
  )

  /* Sub-component: Search Result Row with Follow Guard */
  const SearchResultRow = ({ author }: { author: AuthorSearchResult }) => {
    const isAlreadyFollowing = author.id && followingIds.has(author.id)

    return (
      <div className="p-3 flex items-center justify-between hover:bg-lsc-cream dark:hover:bg-lsc-brown/30">
        <div className="flex items-center gap-3">
          {author.image_url ? (
            <img src={author.image_url} alt={`Photo of ${author.name}`} className="w-10 h-10 rounded-full object-cover" />
          ) : (
            <div className="w-10 h-10 rounded-full bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center">
              <User aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
          )}
          <div>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{author.name}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{author.source === "local" ? `${author.follower_count} followers` : "From Google Books"}</p>
          </div>
        </div>
        {isAlreadyFollowing ? (
          <span className="text-xs font-medium text-lsc-rose">Already following</span>
        ) : (
          <button
            onClick={() => handleFollowAuthor(author)}
            className="px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm rounded-xl flex items-center gap-1 transition-colors"
          >
            <Plus aria-hidden="true" className="w-3 h-3" />Follow
          </button>
        )}
      </div>
    )
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <PageContainer className="py-12 text-center">
        <Calendar aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-rose mb-4" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Release Radar</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{t('releaseRadar.trackUpcomingBookReleasesFrom')}</p>
        <a href="/login" className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors">
          Sign in to get started
        </a>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Release Radar</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('releaseRadar.trackUpcomingReleasesFromAuthors')}</p>
      </div>

      {/* Profile Toggle & Tab Navigation */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div className="inline-flex rounded-xl bg-lsc-cream dark:bg-lsc-brown p-1">
          <button
            onClick={() => setProfileFilter("parent")}
            className={"px-4 py-2 rounded-xl text-sm font-medium transition-colors " + (profileFilter === "parent" ? "bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream shadow-sm" : "text-lsc-dark/70 dark:text-lsc-cream/70")}
          >
            <User aria-hidden="true" className="w-4 h-4 inline mr-2" />My Books
          </button>
          <button
            onClick={() => setProfileFilter("child")}
            className={"px-4 py-2 rounded-xl text-sm font-medium transition-colors " + (profileFilter === "child" ? "bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream shadow-sm" : "text-lsc-dark/70 dark:text-lsc-cream/70")}
          >
            <Baby aria-hidden="true" className="w-4 h-4 inline mr-2" />Kid's Books
          </button>
        </div>

        <div className="inline-flex rounded-xl border border-lsc-border dark:border-earth-700">
          <button
            onClick={() => setActiveTab("timeline")}
            className={"px-4 py-2 text-sm font-medium border-r border-lsc-border dark:border-earth-700 " + (activeTab === "timeline" ? "bg-lsc-rose text-white" : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown")}
          >
            <Calendar aria-hidden="true" className="w-4 h-4 inline mr-2" />Timeline
          </button>
          <button
            onClick={() => setActiveTab("authors")}
            className={"px-4 py-2 text-sm font-medium " + (activeTab === "authors" ? "bg-lsc-rose text-white" : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown")}
          >
            <Heart aria-hidden="true" className="w-4 h-4 inline mr-2" />Authors
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === "timeline" ? (
        <div className="space-y-4">
          {/* Filter & Sort Bars */}
          {!isLoading && releases.length > 0 && (
            <>
              <MoodFilterBar />
              <SortBar />
            </>
          )}

          {isLoading ? (
            <div className="relative">
              <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-lsc-cream dark:bg-lsc-brown" />
              {Array(PAGE_SIZE)
                .fill(0)
                .map((_, i) => (
                  <ReleaseSkeleton key={i} />
                ))}
            </div>
          ) : releases.length === 0 ? (
            <div className="text-center py-12 bg-lsc-cream dark:bg-earth-800 rounded-xl">
              <BookOpen aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">No upcoming releases</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('releaseRadar.followSomeAuthorsToSee')}</p>
              <button onClick={() => setActiveTab("authors")} className="text-lsc-rose hover:text-lsc-rose-light font-medium">
                Browse authors →
              </button>
            </div>
          ) : (
            <>
              <div className="relative">
                <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-lsc-cream dark:bg-lsc-brown" />
                {releases.map((item) => (
                  <ReleaseCard key={item.book.id} item={item} />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-8 pt-6 border-t border-lsc-border dark:border-earth-700">
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Page {page + 1} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(page - 1)}
                      disabled={page === 0}
                      className="p-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label={t('aria.account.previousPage')}
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => setPage(page + 1)}
                      disabled={page >= totalPages - 1}
                      className="p-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label={t('aria.account.nextPage')}
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Search */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('releaseRadar.findAuthorsToFollow')}</h3>
            <div className="flex gap-2 flex-wrap">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearchAuthors()}
                placeholder={t('releaseRadar.searchByAuthorName')}
                aria-label={t('releaseRadar.searchByAuthorName2')}
                className="flex-1 min-w-[200px] px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              />
              <button
                onClick={handleSearchAuthors}
                disabled={isSearching}
                className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/70 text-white rounded-xl font-medium flex items-center gap-2 transition-colors"
              >
                {isSearching ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search aria-hidden="true" className="w-4 h-4" />}
                Search
              </button>
            </div>

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div className="mt-4 border border-lsc-border dark:border-earth-700 rounded-xl divide-y divide-lsc-border dark:divide-earth-700 max-h-80 overflow-y-auto">
                {searchResults.map((author) => (
                  <SearchResultRow key={author.name + author.source} author={author} />
                ))}
              </div>
            )}
          </div>

          {/* Following List */}
          <div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Authors You Follow ({followedAuthors.length})</h3>
            {isLoading ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {Array(4)
                  .fill(0)
                  .map((_, i) => (
                    <AuthorCardSkeleton key={i} />
                  ))}
              </div>
            ) : followedAuthors.length === 0 ? (
              <div className="text-center py-8 bg-lsc-cream dark:bg-earth-800 rounded-xl">
                <Heart aria-hidden="true" className="w-10 h-10 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('releaseRadar.youHavenTFollowedAny')}</p>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {followedAuthors.map((follow) => (
                  <AuthorCard key={follow.follow_id} follow={follow} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </PageContainer>
  )
}
