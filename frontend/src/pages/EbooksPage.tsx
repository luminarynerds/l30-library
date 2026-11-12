/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * MetisLib eBooks Page — L30 Design
 * Dark glass aesthetic with horizontal scroll sections
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  BookOpen,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  TrendingUp,
  Globe,
  Feather,
  ArrowRight,
  Filter,
  Star,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import {
  browseMetisLibEbooks,
  getMetisLibPopular,
  getMetisLibFeatured,
  type MetisLibEbook,
} from '@/api/domains/catalog/metislib-api'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import PageContainer from '@/components/layout/PageContainer'

function EbookCard({ ebook, size = 'normal' }: { ebook: MetisLibEbook; size?: 'normal' | 'large' }): React.ReactElement {
  const [coverFailed, setCoverFailed] = useState(false)
  const isLarge = size === 'large'

  return (
    <Link
      to={ebook.entry_type === 'indie_ebook' ? `/ebooks/${ebook.id}?entry_type=indie_ebook` : `/ebooks/${ebook.id}`}
      className={clsx(
        'flex-shrink-0 rounded-xl overflow-hidden group relative',
        'bg-gradient-to-b from-white/5 to-white/[0.02] dark:from-white/10 dark:to-white/[0.03]',
        'border border-lsc-white/10 dark:border-white/5',
        'backdrop-blur-sm hover:border-white/20 dark:hover:border-white/15 transition-all duration-300',
        'hover:shadow-lg hover:shadow-black/20 hover:-translate-y-1',
        isLarge ? 'w-48 md:w-56' : 'w-36 md:w-44'
      )}
    >
      <div className={clsx('overflow-hidden', isLarge ? 'aspect-[2/3]' : 'aspect-[2/3]')}>
        {ebook.cover_url && !coverFailed ? (
          <img
            src={ebook.cover_url}
            alt={`Cover of ${ebook.title}`}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
            loading="lazy"
            onError={() => setCoverFailed(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-lsc-rose/20 to-category-500/20">
            <BookOpen className="w-10 h-10 text-white/30" />
          </div>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream/90 line-clamp-2 leading-tight" title={ebook.title}>
          {ebook.title}
        </h3>
        <p className="text-xs text-earth-600 dark:text-lsc-cream/50 mt-1 truncate" title={ebook.author_name}>
          {ebook.author_name}
        </p>
        <div className="flex items-center gap-1.5 mt-2">
          {ebook.source_type === 'open_access' ? (
            <Globe className="w-3 h-3 text-earth-600" />
          ) : (
            <Feather className="w-3 h-3 text-category-400" />
          )}
          <span className="text-[10px] text-earth-600 dark:text-lsc-cream/40 uppercase tracking-wider">
            {ebook.format}
          </span>
        </div>
      </div>
    </Link>
  )
}

function HorizontalScroll({ children, title, icon: Icon, subtitle, viewAllHref }: {
  children: React.ReactNode
  title: string
  icon: React.ElementType
  subtitle?: string
  viewAllHref?: string
}): React.ReactElement {
  return (
    <section className="mb-10">
      <div className="flex items-center justify-between mb-4 px-1">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-lsc-rose/20 to-lsc-rose/5 dark:from-lsc-rose/30 dark:to-lsc-rose/10">
            <Icon className="w-5 h-5 text-lsc-rose" />
          </div>
          <div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{title}</h2>
            {subtitle && <p className="text-xs text-earth-600 dark:text-lsc-cream/40">{subtitle}</p>}
          </div>
        </div>
        {viewAllHref && (
          <Link to={viewAllHref} className="flex items-center gap-1 text-sm text-lsc-rose hover:underline">
            View all <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        )}
      </div>
      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-earth-300 dark:scrollbar-thumb-earth-600 scrollbar-track-transparent -mx-4 px-4">
        {children}
      </div>
    </section>
  )
}

export default function EbooksPage(): React.ReactElement {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [page, setPage] = useState(1)
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null)
  const [sourceType, setSourceType] = useState<'open_access' | 'indie' | undefined>(undefined)
  const [sortBy, setSortBy] = useState<string>('default')

  const handleSearch = (value: string) => {
    setSearchQuery(value)
    if (debounceTimer) clearTimeout(debounceTimer)
    setDebounceTimer(setTimeout(() => {
      setDebouncedQuery(value)
      setPage(1)
    }, 400))
  }

  const handleSourceType = (value: 'open_access' | 'indie' | undefined) => {
    setSourceType(value)
    setPage(1)
  }

  const { data: popular } = useQuery({
    queryKey: ['metislib-popular'],
    queryFn: () => getMetisLibPopular(12),
  })

  const { data: featured } = useQuery({
    queryKey: ['metislib-featured'],
    queryFn: () => getMetisLibFeatured(),
  })

  const { data: catalog, isLoading } = useQuery({
    queryKey: ['metislib-ebooks', debouncedQuery, page, sourceType],
    queryFn: () => browseMetisLibEbooks(clean({
      q: debouncedQuery || undefined,
      source_type: sourceType,
      page,
      per_page: 24,
    })),
  })

  const sortedItems = (() => {
    if (!catalog?.items) return []
    if (sortBy === 'title_asc') return [...catalog.items].sort((a, b) => a.title.localeCompare(b.title))
    if (sortBy === 'title_desc') return [...catalog.items].sort((a, b) => b.title.localeCompare(a.title))
    return catalog.items
  })()

  const totalPages = catalog?.pages ?? 1

  return (
    <PageContainer className="py-8">
      {/* Hero Header */}
      <div className="mb-10 text-center">
        <h1 className="font-serif text-4xl md:text-5xl font-bold text-lsc-dark dark:text-lsc-cream mb-3">
          Digital Library
        </h1>
        <p className="text-earth-600 dark:text-lsc-cream/50 max-w-lg mx-auto text-lg">
          Public domain classics and indie works. Free to read.
        </p>
      </div>

      {/* Search */}
      <div className="max-w-2xl mx-auto mb-10">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-earth-600 dark:text-lsc-cream/30" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder={t('placeholder.ebooks.searchTitlesAuthors')}
            className={clsx(
              'w-full pl-12 pr-4 py-3.5 rounded-xl text-lg',
              'bg-lsc-white/80 dark:bg-lsc-white/5 backdrop-blur-sm',
              'border border-lsc-border dark:border-lsc-white/10',
              'text-lsc-dark dark:text-lsc-cream placeholder-earth-400 dark:placeholder-white/30',
              'focus:ring-2 focus:ring-lsc-rose/50 focus:border-lsc-rose outline-none',
              'transition-all duration-200'
            )}
          />
        </div>
      </div>

      {/* Filter Bar */}
      <div className="max-w-2xl mx-auto mb-10 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-earth-600 dark:text-lsc-cream/40 flex-shrink-0" />
          {([
            { label: 'All', value: undefined },
            { label: 'Public Domain', value: 'open_access' as const },
            { label: 'Indie', value: 'indie' as const },
          ]).map((opt) => (
            <button
              key={opt.label}
              onClick={() => handleSourceType(opt.value)}
              aria-pressed={sourceType === opt.value}
              className={clsx(
                'px-3.5 py-1.5 rounded-full text-sm font-medium transition-all duration-200',
                sourceType === opt.value
                  ? 'bg-lsc-rose/20 border border-lsc-rose text-lsc-rose-dark dark:text-lsc-cream'
                  : 'bg-lsc-white/5 border border-lsc-white/10 text-earth-600 dark:text-lsc-cream/50 hover:bg-lsc-white/10 hover:border-white/20'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          aria-label={t('ebooks.sortBy', 'Sort eBooks by')}
          className={clsx(
            'px-3 py-1.5 rounded-xl text-sm',
            'bg-lsc-white/5 border border-lsc-white/10',
            'text-earth-600 dark:text-lsc-cream/60',
            'focus:ring-2 focus:ring-lsc-rose/50 focus:border-lsc-rose outline-none',
            'transition-all duration-200 cursor-pointer'
          )}
        >
          <option value="default">Default</option>
          <option value="title_asc">Title A-Z</option>
          <option value="title_desc">Title Z-A</option>
        </select>
      </div>

      {/* Featured Section */}
      {!debouncedQuery && !sourceType && featured && featured.items && featured.items.length > 0 && (
        <HorizontalScroll title="Featured" icon={Star} subtitle="Editor's picks">
          {featured.items.map((ebook) => (
            <EbookCard key={`feat-${ebook.id}`} ebook={ebook} size="large" />
          ))}
        </HorizontalScroll>
      )}

      {/* Popular Section */}
      {!debouncedQuery && !sourceType && popular && popular.items && popular.items.length > 0 && (
        <HorizontalScroll title="Trending Now" icon={TrendingUp} subtitle={t('ebooks.mostAccessedThisMonth')}>
          {popular.items.map((ebook) => (
            <EbookCard key={`pop-${ebook.id}`} ebook={ebook} size="large" />
          ))}
        </HorizontalScroll>
      )}

      {/* Browse / Search Results */}
      <section>
        <div className="flex items-center gap-3 mb-4 px-1">
          <div className="p-2 rounded-xl bg-gradient-to-br from-lsc-rose/20 to-lsc-rose/5 dark:from-lsc-rose/30 dark:to-lsc-rose/10">
            <Sparkles className="w-5 h-5 text-lsc-rose" />
          </div>
          <div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              {debouncedQuery ? `Results for "${debouncedQuery}"` : sourceType === 'open_access' ? 'Public Domain eBooks' : sourceType === 'indie' ? 'Indie eBooks' : 'All eBooks'}
            </h2>
            {catalog && (
              <p className="text-xs text-earth-600 dark:text-lsc-cream/40">
                {catalog.total} title{catalog.total !== 1 ? 's' : ''}
              </p>
            )}
          </div>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-20" role="status" aria-live="polite">
            <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" aria-hidden="true" />
            <span className="sr-only">{t('common.loading', 'Loading…')}</span>
          </div>
        )}

        {sortedItems.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {sortedItems.map((ebook) => (
              <EbookCard key={`cat-${ebook.entry_type}-${ebook.id}`} ebook={ebook} />
            ))}
          </div>
        )}

        {catalog && sortedItems.length === 0 && (
          <div className="text-center py-20">
            <BookOpen className="w-12 h-12 text-earth-300 dark:text-lsc-cream/10 mx-auto mb-4" />
            <h3 className="font-serif text-lg text-lsc-dark dark:text-lsc-cream/80 mb-1">No results</h3>
            <p className="text-earth-600 dark:text-lsc-cream/40">{t('ebooks.tryADifferentSearchTerm')}</p>
          </div>
        )}

        {/* Pagination */}
        {catalog && totalPages > 1 && (
          <div className="flex items-center justify-center gap-4 mt-8">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="flex items-center gap-1 px-4 py-2 rounded-xl bg-lsc-white/5 dark:bg-lsc-white/5 border border-lsc-white/10 text-earth-600 dark:text-lsc-cream/60 hover:bg-lsc-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
              Prev
            </button>
            <span className="text-sm text-earth-600 dark:text-lsc-cream/40 tabular-nums">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="flex items-center gap-1 px-4 py-2 rounded-xl bg-lsc-white/5 dark:bg-lsc-white/5 border border-lsc-white/10 text-earth-600 dark:text-lsc-cream/60 hover:bg-lsc-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </section>
    </PageContainer>
  )
}
