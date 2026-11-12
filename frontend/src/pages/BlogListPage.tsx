/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// frontend/src/pages/BlogListPage.tsx
import { useState, useEffect, useRef, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link, useSearchParams } from "react-router-dom"
import { Search, Tag as TagIcon, ChevronLeft, ChevronRight, Newspaper, User, Clock } from "lucide-react"
import { getBlogPosts, getBlogTags } from "@/services/blog-api"
import BlogCard from "@/components/BlogCard"
import { usePageMeta } from "@/hooks/usePageMeta"
import { useBranding } from '@/contexts/BrandingContext'
import { useTranslation } from '@/i18n/I18nContext'

export default function BlogListPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTag = searchParams.get("tag") || undefined
  const searchQuery = searchParams.get("q") || ""
  const page = parseInt(searchParams.get("page") || "1", 10)

  const [searchInput, setSearchInput] = useState(searchQuery)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  usePageMeta({
    title: "Field Notes",
    description: `Practical insights on library technology, vendor strategy, and digital literacy from the ${branding.library_short_name} team.`,
    canonicalPath: "/blog",
  })

  const { data: postsData, isLoading } = useQuery({
    queryKey: ["blog", "posts", { tag: activeTag, q: searchQuery, page }],
    queryFn: () => getBlogPosts({ tag: activeTag, q: searchQuery || undefined, page, per_page: 12 }),
  })

  const { data: tags } = useQuery({
    queryKey: ["blog", "tags"],
    queryFn: getBlogTags,
  })

  // RSS feed auto-discovery — main feed plus per-tag feed when filtering by tag.
  useEffect(() => {
    const links: HTMLLinkElement[] = []
    const makeLink = (href: string, title: string) => {
      const el = document.createElement("link")
      el.rel = "alternate"
      el.type = "application/atom+xml"
      el.title = title
      el.href = href
      document.head.appendChild(el)
      links.push(el)
    }
    makeLink("/api/v1/blog/feed", `${branding.library_short_name} Blog`)
    if (activeTag) {
      makeLink(
        `/api/v1/blog/feed/tag/${activeTag}`,
        `${branding.library_short_name} Blog — #${activeTag}`,
      )
    }
    return () => {
      for (const el of links) {
        document.head.removeChild(el)
      }
    }
  }, [activeTag, branding.library_short_name])

  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchInput(value)
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        const params = new URLSearchParams(searchParams)
        if (value.trim()) {
          params.set("q", value.trim())
        } else {
          params.delete("q")
        }
        params.delete("page")
        setSearchParams(params)
      }, 300)
    },
    [searchParams, setSearchParams]
  )

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const handleTagClick = (slug: string) => {
    const params = new URLSearchParams(searchParams)
    if (activeTag === slug) {
      params.delete("tag")
    } else {
      params.set("tag", slug)
    }
    params.delete("page")
    setSearchParams(params)
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set("page", newPage.toString())
    setSearchParams(params)
  }

  const totalPages = postsData ? Math.ceil(postsData.total / postsData.per_page) : 0
  const showFeatured = page === 1 && !activeTag && !searchQuery
  const posts = postsData?.items ?? []
  const featuredPost = showFeatured ? posts[0] : null
  const gridPosts = showFeatured ? posts.slice(1) : posts

  return (
    <div className="bg-cream-100 dark:bg-transparent -mx-4 sm:-mx-6 px-4 sm:px-6 py-8 rounded-xl min-h-screen">
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="space-y-2 border-b-2 border-lsc-dark dark:border-lsc-cream pb-4">
        <p className="text-xs font-bold tracking-[0.18em] uppercase text-lsc-rose mb-1.5">THE <span className="normal-case">L30</span> BLOG</p>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-serif font-bold tracking-tight text-lsc-dark dark:text-lsc-cream">
          {t('blog.pageTitle')}
        </h1>
        <p className="text-base md:text-lg text-lsc-dark/70 dark:text-lsc-cream/80 max-w-xl">
          {t('blog.pageSubtitle')}
        </p>
      </div>

      {/* Search -- live debounced */}
      <div className="max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70" aria-hidden="true" />
          <input
            type="search"
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder={t('blog.searchPlaceholder')}
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            aria-label="Search blog posts"
          />
        </div>
      </div>

      {/* Tags */}
      {tags && tags.length > 0 && (
        <div className="flex flex-wrap gap-2 justify-start" role="group" aria-label="Filter posts by topic">
          {tags.map((tag) => (
            <button
              key={tag.id}
              onClick={() => handleTagClick(tag.slug)}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-full border transition-colors ${
                activeTag === tag.slug
                  ? "bg-lsc-rose text-white border-lsc-rose"
                  : "border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose/40"
              }`}
              aria-pressed={activeTag === tag.slug}
            >
              <TagIcon className="w-3 h-3" aria-hidden="true" />
              {tag.name}
              {tag.post_count != null && (
                <span className="text-xs">({tag.post_count})</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 motion-safe:animate-pulse h-48" />
          ))}
        </div>
      )}

      {/* Posts -- asymmetric editorial layout */}
      {posts.length > 0 && (
        <div className="space-y-8">
          {/* Featured post -- only on first page with no filters */}
          {featuredPost && (
            <article
              className="group motion-safe:animate-slide-up-fade motion-safe:opacity-0"
              key={`featured-${searchQuery}-${activeTag}-${page}`}
            >
              <Link to={`/blog/${featuredPost.slug}`} className="block no-underline">
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 border-l-4 border-l-lsc-rose overflow-hidden hover:shadow-lg transition-shadow [&_img]:mix-blend-multiply [&_img]:dark:mix-blend-normal">
                  <div className={`aspect-[16/9] md:aspect-[5/2] overflow-hidden bg-cream-100 dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700`}>
                    {featuredPost.featured_image ? (
                      <img src={featuredPost.featured_image} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-lsc-cream via-lsc-cream/80 to-sage-100 dark:from-earth-700 dark:via-earth-700 dark:to-earth-800">
                        <Newspaper className="w-12 h-12 text-lsc-rose/40 dark:text-lsc-rose/30" aria-hidden="true" />
                        {featuredPost.tags?.[0] && (
                          <span className="text-xs font-semibold text-lsc-dark/60 dark:text-lsc-cream/40 uppercase tracking-wider">{featuredPost.tags[0].name}</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="p-4 sm:p-6">
                    <span className="text-xs font-medium text-lsc-rose uppercase tracking-wider mb-2">Featured</span>
                    <h2 className="font-serif text-2xl sm:text-3xl font-bold text-lsc-dark dark:text-lsc-cream mb-3 group-hover:text-lsc-rose transition-colors">
                      {featuredPost.title}
                    </h2>
                    {featuredPost.tldr && (
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm line-clamp-3 mb-4">{featuredPost.tldr}</p>
                    )}
                    <div className="flex flex-wrap items-center gap-3 text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                      <span className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5" aria-hidden="true" />
                        {featuredPost.author_name}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                        {featuredPost.read_time_minutes} min read
                      </span>
                    </div>
                    {featuredPost.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {featuredPost.tags.map((tag) => (
                          <span key={tag.id} className="px-2 py-0.5 text-xs rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            </article>
          )}

          {/* Remaining posts in 2-column grid */}
          {gridPosts.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {gridPosts.map((post, idx) => (
                <div
                  key={`${searchQuery}-${activeTag}-${page}-${post.id}`}
                  className="motion-safe:animate-slide-up-fade motion-safe:opacity-0"
                  style={{ animationDelay: `${(featuredPost ? idx + 1 : idx) * 60}ms` }}
                >
                  <BlogCard post={post} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {postsData && postsData.items.length === 0 && (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
          <p>{t('blog.noPosts')}</p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <nav className="flex flex-wrap items-center justify-center gap-3 sm:gap-4" aria-label="Blog pagination">
          <button
            onClick={() => handlePageChange(page - 1)}
            disabled={page <= 1}
            className="flex items-center gap-1 px-3 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 disabled:opacity-40 hover:border-lsc-rose/40 transition-colors"
            aria-label="Previous page"
          >
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
            {t('blog.previous')}
          </button>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            {t('blog.pageOf', { page, totalPages })}
          </span>
          <button
            onClick={() => handlePageChange(page + 1)}
            disabled={page >= totalPages}
            className="flex items-center gap-1 px-3 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 disabled:opacity-40 hover:border-lsc-rose/40 transition-colors"
            aria-label="Next page"
          >
            {t('blog.next')}
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </nav>
      )}
    </div>
    </div>
  )
}
