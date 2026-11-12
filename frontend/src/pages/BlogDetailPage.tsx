/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState, useRef, useMemo, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  ArrowLeft, ArrowUp, Calendar, Clock, User, ChevronLeft, ChevronRight,
  Link2, Share2, Mail, Focus,
} from "lucide-react"
import DOMPurify from "dompurify"
import { getBlogPost, getBlogSeries } from "@/services/blog-api"
import RelatedPosts from "@/components/RelatedPosts"
import { usePageMeta } from "@/hooks/usePageMeta"
import { useBranding } from '@/contexts/BrandingContext'
import { useTranslation } from '@/i18n/I18nContext'
import { getCurrentLocale } from '@/i18n'

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/g, "")
}

function absoluteImageUrl(path: string | null | undefined, origin: string): string | undefined {
  if (!path) return undefined
  if (/^https?:\/\//i.test(path)) return path
  if (!origin) return path
  return `${origin}${path.startsWith("/") ? "" : "/"}${path}`
}

function safeJsonLd(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c")
}

function displayRole(authorName: string, authorRole: string | null | undefined): string | null {
  if (!authorRole) return null
  const name = authorName.toLowerCase().trimEnd()
  const role = authorRole.toLowerCase().trim()
  if (name.endsWith(`, ${role}`) || name.endsWith(` ${role}`) || name === role) return null
  return authorRole
}

export default function BlogDetailPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const { slug } = useParams<{ slug: string }>()
  const [readProgress, setReadProgress] = useState(0)
  const [showBackToTop, setShowBackToTop] = useState(false)
  const articleRef = useRef<HTMLElement>(null)
  const [copied, setCopied] = useState(false)
  const [focusMode, setFocusMode] = useState(false)

  const { data: post, isLoading, error } = useQuery({
    queryKey: ["blog", "post", slug],
    queryFn: () => getBlogPost(slug!),
    enabled: !!slug,
  })

  const { data: seriesPosts } = useQuery({
    queryKey: ["blog", "series", post?.series_name],
    queryFn: () => getBlogSeries(post!.series_name!),
    enabled: !!post?.series_name,
  })

  const minutesLeft = post?.read_time_minutes
    ? Math.max(0, Math.ceil(post.read_time_minutes * (1 - readProgress / 100)))
    : 0

  // SEO meta
  const ogImage = absoluteImageUrl(post?.featured_image, branding.domain)
  usePageMeta({
    title: post?.title,
    description: post?.meta_description || post?.tldr || undefined,
    canonicalPath: post ? `/blog/${post.slug}` : undefined,
    ogType: "article",
    ogImage,
  })

  // RSS feed auto-discovery
  useEffect(() => {
    const link = document.createElement("link")
    link.rel = "alternate"
    link.type = "application/atom+xml"
    link.title = `${branding.library_short_name} Blog`
    link.href = "/api/v1/blog/feed"
    document.head.appendChild(link)
    return () => {
      document.head.removeChild(link)
    }
  }, [])

  // Reading progress bar
  useEffect(() => {
    const handleScroll = () => {
      if (!articleRef.current) return
      const el = articleRef.current
      const rect = el.getBoundingClientRect()
      const totalHeight = el.scrollHeight
      const scrolled = Math.max(0, -rect.top)
      const viewable = totalHeight - window.innerHeight
      if (viewable <= 0) {
        setShowBackToTop(window.scrollY > 400)
        setReadProgress(100)
        return
      }
      setReadProgress(Math.min(100, Math.max(0, (scrolled / viewable) * 100)))
      setShowBackToTop(window.scrollY > 400)
    }
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [post])

  // Lazy load images in article body
  useEffect(() => {
    if (!articleRef.current) return
    const images = articleRef.current.querySelectorAll("img:not([loading])")
    images.forEach((img) => img.setAttribute("loading", "lazy"))
  }, [post])

  // Extract headings for TOC. Slugified ids let users deep-link to a section
  // by URL fragment (e.g. /blog/foo#why-it-matters) and survive page reflows.
  const headings = useMemo(() => {
    if (!post?.body) return []
    const parser = new DOMParser()
    const doc = parser.parseFromString(post.body, "text/html")
    const nodes = doc.querySelectorAll("h2, h3")
    const seen = new Map<string, number>()
    return Array.from(nodes).map((node) => {
      const text = node.textContent || ""
      const base = slugify(text) || "section"
      const count = seen.get(base) || 0
      seen.set(base, count + 1)
      const id = count === 0 ? base : `${base}-${count + 1}`
      const level = node.tagName === "H2" ? 2 : 3
      return { id, text, level }
    })
  }, [post?.body])

  // Word count derived from sanitized body text for Article JSON-LD.
  // Plain (non-memoized) since it runs only on data updates and produces a number.
  const wordCount = ((): number => {
    if (!post?.body) return 0
    const parser = new DOMParser()
    const doc = parser.parseFromString(post.body, "text/html")
    const text = (doc.body.textContent || "").trim()
    if (!text) return 0
    return text.split(/\s+/).filter(Boolean).length
  })()

  // Inject IDs into rendered headings
  useEffect(() => {
    if (!articleRef.current || headings.length === 0) return
    const nodes = articleRef.current.querySelectorAll(".prose h2, .prose h3")
    nodes.forEach((node, i) => {
      if (headings[i]) {
        ;(node as HTMLElement).id = headings[i].id
      }
    })
  }, [headings, post])


  // Focus mode: Escape to exit
  useEffect(() => {
    if (!focusMode) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFocusMode(false)
    }
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [focusMode])
  const shareUrl = typeof window !== "undefined" ? window.location.href : ""
  const shareTitle = post?.title || ""

  const handleCopyLink = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback
    }
  }, [shareUrl])

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto motion-safe:animate-pulse space-y-4">
        <div className="h-8 bg-lsc-cream dark:bg-earth-800 rounded w-3/4" />
        <div className="h-4 bg-lsc-cream dark:bg-earth-800 rounded w-1/2" />
        <div className="h-64 bg-lsc-cream dark:bg-earth-800 rounded" />
      </div>
    )
  }

  if (error || !post) {
    return (
      <div className="max-w-3xl mx-auto text-center py-12">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/60">{t('blog.postNotFound')}</p>
        <Link to="/blog" className="text-lsc-rose hover:underline mt-2 inline-block">
          Back to blog
        </Link>
      </div>
    )
  }

  const publishedDate = post.published_at
    ? new Date(post.published_at).toLocaleDateString(getCurrentLocale(), {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null

  const currentIndex = seriesPosts?.findIndex((p) => p.slug === post.slug) ?? -1
  const prevPost = currentIndex > 0 ? seriesPosts?.[currentIndex - 1] : null
  const nextPost = currentIndex >= 0 && seriesPosts ? seriesPosts[currentIndex + 1] : null

  const sanitizedBody = DOMPurify.sanitize(post.body, {
    ADD_ATTR: ["data-callout-type"],
  })

  // JSON-LD structured data for Article + breadcrumb trail.
  const canonicalUrl = `${branding.domain}/blog/${post.slug}`
  const articleImage = absoluteImageUrl(post.featured_image, branding.domain)
  const logoUrl = absoluteImageUrl("/og-image.png", branding.domain)

  const articleLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    datePublished: post.published_at || undefined,
    dateModified: post.updated_at || post.published_at || undefined,
    author: {
      "@type": "Person",
      name: post.author_name,
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": canonicalUrl,
    },
    publisher: {
      "@type": "Organization",
      name: branding.library_name,
      logo: logoUrl
        ? { "@type": "ImageObject", url: logoUrl }
        : undefined,
    },
  }
  if (articleImage) {
    articleLd.image = [articleImage]
  }
  if (post.tags && post.tags.length > 0) {
    articleLd.articleSection = post.tags.map((t) => t.name)
  }
  if (wordCount > 0) {
    articleLd.wordCount = wordCount
  }

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: `${branding.domain}/`,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Blog",
        item: `${branding.domain}/blog`,
      },
      {
        "@type": "ListItem",
        position: 3,
        name: post.title,
        item: canonicalUrl,
      },
    ],
  }

  return (
    <div className={focusMode ? "blog-focus-active" : ""}>
      {/* JSON-LD structured data for SEO. Injected inline (no helmet); script
          tags in body are valid per Google's structured data guidance. */}
      <script
        type="application/ld+json"
        data-testid="blog-article-ld"
        dangerouslySetInnerHTML={{ __html: safeJsonLd(articleLd) }}
      />
      <script
        type="application/ld+json"
        data-testid="blog-breadcrumb-ld"
        dangerouslySetInnerHTML={{ __html: safeJsonLd(breadcrumbLd) }}
      />
      {/* Reading progress bar */}
      <div
        className="fixed top-0 left-0 h-1 bg-lsc-rose z-50 transition-[width] duration-150"
        style={{ width: `${readProgress}%` }}
        role="progressbar"
        aria-valuenow={Math.round(readProgress)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Reading progress"
      />

      <article ref={articleRef} className="max-w-3xl mx-auto space-y-8">
        {/* Back link */}
        <Link
          to="/blog"
          className="inline-flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose transition-colors"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Back to blog
        </Link>

        {/* Featured image */}
        {post.featured_image && (
          <div className="rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700">
            <img
              src={post.featured_image}
              alt={`Featured image for ${post.title}`}
              loading="lazy"
              className="w-full h-auto max-h-96 object-cover"
            />
          </div>
        )}

        {/* Header */}
        <header className="space-y-4">
          <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream leading-tight">
            {post.title}
          </h1>

          <div className="flex flex-wrap items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            <span className="flex items-center gap-1.5">
              <User className="w-4 h-4" aria-hidden="true" />
              {post.author_name}
              {(() => { const r = displayRole(post.author_name, post.author_role); return r ? `, ${r}` : null })()}
            </span>
            {publishedDate && (
              <span className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4" aria-hidden="true" />
                <time dateTime={post.published_at!}>{publishedDate}</time>
              </span>
            )}
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" aria-hidden="true" />
              {minutesLeft > 0 ? `${minutesLeft} min left` : 'Almost done'}
            </span>
            <button
              onClick={() => setFocusMode(f => !f)}
              className="flex items-center gap-1.5 text-xs text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-rose transition-colors rounded-lg px-2 py-1 hover:bg-lsc-cream/50 dark:hover:bg-earth-800"
              aria-label={focusMode ? "Exit focus mode" : "Enter focus mode"}
              aria-pressed={focusMode}
            >
              <Focus className="w-3.5 h-3.5" />
              {focusMode ? "Exit Focus" : "Focus"}
            </button>
          </div>

          {/* Tags */}
          {post.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {post.tags.map((tag) => (
                <Link
                  key={tag.id}
                  to={`/blog?tag=${tag.slug}`}
                  className="px-2.5 py-1 text-xs rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-rose/10 transition-colors"
                >
                  {tag.name}
                </Link>
              ))}
            </div>
          )}

          {/* Series indicator */}
          {post.series_name && (
            <div className="px-4 py-3 bg-lsc-cream dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 text-sm">
              Part of the series: <strong>{post.series_name}</strong>
              {post.series_order != null && ` (Part ${post.series_order})`}
            </div>
          )}
        </header>

        {/* Sticky reading progress bar */}
        <div
          className="sticky top-0 z-10 bg-lsc-cream dark:bg-lsc-dark border-b border-lsc-border dark:border-earth-700 px-4 py-2 -mx-4 flex items-center justify-between text-sm text-lsc-dark/60 dark:text-lsc-cream/60"
          data-print-hide
        >
          <span className="font-serif text-xs truncate max-w-[60%]">{post.title}</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            {minutesLeft > 0 ? `${minutesLeft} min left` : 'Finished'}
          </span>
        </div>

        {/* Share buttons */}
        <div className="flex flex-wrap items-center gap-2" data-print-hide>
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mr-1">Share:</span>
          <button
            onClick={handleCopyLink}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose/40 transition-colors"
            aria-label="Copy link"
          >
            <Link2 className="w-3.5 h-3.5" aria-hidden="true" />
            {copied ? "Copied!" : "Copy link"}
          </button>
          <a
            href={`https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareTitle)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose/40 transition-colors"
            aria-label="Share on X"
          >
            <Share2 className="w-3.5 h-3.5" aria-hidden="true" />
            X
          </a>
          <a
            href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose/40 transition-colors"
            aria-label="Share on Facebook"
          >
            <Share2 className="w-3.5 h-3.5" aria-hidden="true" />
            Facebook
          </a>
          <a
            href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose/40 transition-colors"
            aria-label="Share on LinkedIn"
          >
            <Share2 className="w-3.5 h-3.5" aria-hidden="true" />
            LinkedIn
          </a>
          <a
            href={`mailto:?subject=${encodeURIComponent(shareTitle)}&body=${encodeURIComponent(shareUrl)}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose/40 transition-colors"
            aria-label="Share via email"
          >
            <Mail className="w-3.5 h-3.5" aria-hidden="true" />
            Email
          </a>
        </div>

        {/* TL;DR */}
        {post.tldr && (
          <aside className="px-5 py-4 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl border-l-2 border-lsc-rose">
            <p className="text-sm font-medium text-lsc-dark/80 dark:text-lsc-cream/80 mb-1">
              Quick version
            </p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{post.tldr}</p>
          </aside>
        )}

        {/* Table of Contents */}
        {headings.length >= 3 && (
          <nav className="px-5 py-4 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl border border-lsc-border dark:border-earth-700" aria-label="Table of contents">
            <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">In this post</p>
            <ul className="space-y-1">
              {headings.map((h) => (
                <li key={h.id} className={h.level === 3 ? "ml-4" : ""}>
                  <a
                    href={`#${h.id}`}
                    className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
                  >
                    {h.text}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        )}

        {/* Body */}
        <div
          className="prose prose-lg leading-relaxed dark:prose-invert max-w-none
            prose-headings:font-serif prose-headings:tracking-tight prose-headings:text-lsc-dark dark:prose-headings:text-lsc-cream
            prose-p:text-lsc-dark/80 dark:prose-p:text-lsc-cream/80
            prose-a:text-lsc-rose hover:prose-a:underline
            prose-blockquote:border-lsc-rose prose-blockquote:text-lsc-dark/70 dark:prose-blockquote:text-lsc-cream/70
            prose-code:bg-lsc-cream dark:prose-code:bg-earth-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded"
          dangerouslySetInnerHTML={{ __html: sanitizedBody }}
        />
        <style>{`
          .prose .callout,
          .prose div[data-callout-type] {
            border-left: 4px solid;
            border-radius: 0.5rem;
            padding: 0.75rem 1rem;
            margin: 0.75rem 0;
          }
          .prose .callout[data-callout-type="info"],
          .prose div[data-callout-type="info"] {
            border-color: #3b82f6;
            background: rgba(59, 130, 246, 0.08);
          }
          .prose .callout[data-callout-type="tip"],
          .prose div[data-callout-type="tip"] {
            border-color: #22c55e;
            background: rgba(34, 197, 94, 0.08);
          }
          .prose .callout[data-callout-type="warning"],
          .prose div[data-callout-type="warning"] {
            border-color: #f59e0b;
            background: rgba(245, 158, 11, 0.08);
          }
          .prose .callout[data-callout-type="important"],
          .prose div[data-callout-type="important"] {
            border-color: #ef4444;
            background: rgba(239, 68, 68, 0.08);
          }
          @media print {
            [role="progressbar"],
            nav[aria-label="Series navigation"],
            [data-print-hide] {
              display: none !important;
            }
            article {
              max-width: 100% !important;
            }
            .prose {
              font-size: 12pt !important;
              line-height: 1.6 !important;
            }
            .prose a {
              text-decoration: underline !important;
              color: inherit !important;
            }
            .prose a::after {
              content: " (" attr(href) ")" !important;
              font-size: 0.8em !important;
              color: #666 !important;
            }
            .callout, div[data-callout-type] {
              background: none !important;
              border: 1px solid #ccc !important;
              border-left: 4px solid !important;
            }
          }
          /* Focus mode */
          .blog-focus-active > *:not(article) {
            opacity: 0.08;
            pointer-events: none;
            transition: opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1);
          }
          .blog-focus-active article {
            max-width: 65ch;
            margin-inline: auto;
          }
          .blog-focus-active article > *:not(.prose):not(style) {
            opacity: 0.15;
            pointer-events: none;
            transition: opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1);
          }
          .blog-focus-active article > header .flex {
            opacity: 1;
            pointer-events: auto;
          }
          .blog-focus-active article > .prose {
            opacity: 1;
            transition: opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1);
          }
          @media (prefers-reduced-motion: reduce) {
            .blog-focus-active > *,
            .blog-focus-active article > * {
              transition: none;
            }
          }
        `}</style>

        {/* Author bio card */}
        <div className="flex items-start gap-4 p-5 rounded-xl bg-lsc-cream/50 dark:bg-earth-800 border border-lsc-border dark:border-earth-700">
          <div className="w-14 h-14 rounded-full bg-lsc-rose/20 flex items-center justify-center flex-shrink-0">
            <User className="w-7 h-7 text-lsc-rose" />
          </div>
          <div>
            <p className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{post.author_name}</p>
            {(() => { const r = displayRole(post.author_name, post.author_role); return r ? <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{r}</p> : null })()}
          </div>
        </div>

        {/* Series navigation */}
        {(prevPost || nextPost) && (
          <nav className="flex items-stretch gap-4 pt-6 border-t border-lsc-border dark:border-earth-700" aria-label="Series navigation">
            {prevPost ? (
              <Link
                to={`/blog/${prevPost.slug}`}
                className="flex-1 flex items-center gap-2 p-4 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose/40 transition-colors"
              >
                <ChevronLeft className="w-5 h-5 shrink-0 text-lsc-dark/70" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">Previous in series</p>
                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">{prevPost.title}</p>
                </div>
              </Link>
            ) : (
              <div className="flex-1" />
            )}
            {nextPost ? (
              <Link
                to={`/blog/${nextPost.slug}`}
                className="flex-1 flex items-center justify-end gap-2 p-4 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose/40 transition-colors text-right"
              >
                <div className="min-w-0">
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">Next in series</p>
                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">{nextPost.title}</p>
                </div>
                <ChevronRight className="w-5 h-5 shrink-0 text-lsc-dark/70" aria-hidden="true" />
              </Link>
            ) : (
              <div className="flex-1" />
            )}
          </nav>
        )}

        {/* Related posts */}
        <RelatedPosts slug={post.slug} />
      </article>

      {showBackToTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="fixed bottom-6 right-6 p-3 rounded-full bg-lsc-rose text-white shadow-lg hover:bg-lsc-rose/90 transition-opacity z-40"
          aria-label="Back to top"
        >
          <ArrowUp className="w-5 h-5" />
        </button>
      )}
    </div>
  )
}
