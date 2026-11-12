/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom"
import { Calendar, Clock, Newspaper, User } from "lucide-react"
import type { BlogPostListItem } from "@/services/blog-api"
import { useTranslation } from "@/i18n/I18nContext"
import { getCurrentLocale } from '@/i18n'

interface BlogCardProps {
  post: BlogPostListItem
  variant?: "default" | "compact"
}

export default function BlogCard({ post, variant = "default" }: BlogCardProps): React.ReactElement {
  const { t } = useTranslation()
  const publishedDate = post.published_at
    ? new Date(post.published_at).toLocaleDateString(getCurrentLocale(), {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null

  if (variant === "compact") {
    return (
      <article className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden hover:border-lsc-rose/40 transition-colors h-full">
        <Link to={`/blog/${post.slug}`} className="flex gap-3 p-3 h-full">
          <div className="w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-lsc-cream dark:bg-earth-700">
            {post.featured_image ? (
              <img src={post.featured_image} alt="" loading="lazy" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-lsc-cream to-sage-100 dark:from-earth-700 dark:to-earth-800">
                <Newspaper className="w-6 h-6 text-lsc-rose/40" aria-hidden="true" />
              </div>
            )}
          </div>
          <div className="flex-1 min-w-0 space-y-1.5">
            <h3 className="text-sm font-serif font-semibold text-lsc-dark dark:text-lsc-cream leading-snug line-clamp-2">
              {post.title}
            </h3>
            <div className="flex items-center gap-2 text-xs text-lsc-dark/80 dark:text-lsc-cream/50">
              <span>{post.author_name}</span>
              <span className="text-earth-300 dark:text-earth-600">&middot;</span>
              <span>{post.read_time_minutes} min</span>
            </div>
          </div>
        </Link>
      </article>
    )
  }

  return (
    <article className="relative overflow-hidden bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 shadow-[0_1px_2px_rgba(43,35,48,.05),0_12px_24px_-14px_rgba(43,35,48,.30)] hover:shadow-[0_4px_10px_rgba(43,35,48,.10),0_20px_36px_-12px_rgba(43,35,48,.34)] hover:-translate-y-[3px] transition-all before:absolute before:left-0 before:inset-y-0 before:w-1 before:bg-lsc-rose before:content-['']">
      <Link to={`/blog/${post.slug}`} className="block">
        <div className="aspect-[16/10] overflow-hidden bg-lsc-cream dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700">
          {post.featured_image ? (
            <img
              src={post.featured_image}
              alt={t('blog.card.coverAlt', { title: post.title })}
              loading="lazy"
              className="w-full h-full object-cover mix-blend-multiply p-[6%] dark:mix-blend-normal dark:p-0"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-lsc-cream via-lsc-cream/80 to-sage-100 dark:from-earth-700 dark:via-earth-700 dark:to-earth-800">
              <Newspaper className="w-10 h-10 text-lsc-rose/40 dark:text-lsc-rose/30" aria-hidden="true" />
              {post.tags?.[0] && (
                <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/30 uppercase tracking-wider">
                  {post.tags[0].name}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="p-4 space-y-3">
          <h3 className="text-base font-serif font-semibold text-lsc-dark dark:text-lsc-cream leading-snug">
            {post.title}
          </h3>

          {post.tldr && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2">
              {post.tldr}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
            <span className="flex items-center gap-1">
              <User className="w-3.5 h-3.5" aria-hidden="true" />
              {post.author_name}
            </span>
            {publishedDate && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
                {publishedDate}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" aria-hidden="true" />
              {t('blog.card.minReadSuffix', { minutes: post.read_time_minutes })}
            </span>
          </div>

          {post.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {post.tags.map((tag) => (
                <span
                  key={tag.id}
                  className="px-2 py-0.5 text-xs rounded-full bg-lsc-rose/10 text-lsc-rose border border-lsc-rose/20 font-semibold dark:bg-earth-700 dark:text-lsc-cream/70 dark:border-transparent"
                >
                  {tag.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </Link>
    </article>
  )
}
