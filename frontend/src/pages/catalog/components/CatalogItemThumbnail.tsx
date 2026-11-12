/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import {
  BookOpen,
  Headphones,
  Film,
  Disc3,
  Gamepad2,
  Newspaper,
  Smartphone,
  Package,
  Library,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface CatalogItemThumbnailProps {
  title: string
  author?: string | null
  itemType?: string
  subjects?: string | null
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

interface ThemeMatch {
  icon: LucideIcon
  from: string
  to: string
}

const ITEM_TYPE_ICONS: Record<string, LucideIcon> = {
  book: BookOpen,
  ebook: Smartphone,
  audiobook: Headphones,
  dvd: Film,
  bluray: Film,
  cd: Disc3,
  vinyl: Disc3,
  magazine: Newspaper,
  game: Gamepad2,
  equipment: Package,
  kit: Package,
  other: Library,
}

const THEME_KEYWORDS: [string[], { from: string; to: string }][] = [
  [['mystery', 'detective', 'crime', 'thriller', 'suspense'], { from: 'from-earth-700', to: 'to-earth-900' }],
  [['romance', 'love', 'heart', 'wedding', 'kiss'], { from: 'from-lsc-rose', to: 'to-earth-800' }],
  [['science', 'space', 'cosmos', 'physics', 'quantum'], { from: 'from-forest-600', to: 'to-forest-900' }],
  [['history', 'war', 'ancient', 'empire', 'civil'], { from: 'from-earth-600', to: 'to-earth-800' }],
  [['cooking', 'recipe', 'food', 'kitchen', 'baking'], { from: 'from-sage-600', to: 'to-sage-800' }],
  [['children', 'kids', 'baby', 'toddler', 'young'], { from: 'from-lsc-rose', to: 'to-sage-700' }],
  [['fantasy', 'magic', 'dragon', 'wizard', 'quest'], { from: 'from-forest-600', to: 'to-earth-800' }],
  [['horror', 'ghost', 'dark', 'haunted', 'zombie'], { from: 'from-earth-800', to: 'to-lsc-dark' }],
  [['nature', 'garden', 'animal', 'wildlife', 'plant'], { from: 'from-forest-600', to: 'to-forest-900' }],
  [['music', 'song', 'band', 'guitar', 'piano'], { from: 'from-lsc-rose', to: 'to-lsc-600' }],
  [['technology', 'computer', 'digital', 'program', 'code'], { from: 'from-earth-700', to: 'to-forest-900' }],
  [['art', 'painting', 'drawing', 'creative'], { from: 'from-lsc-rose', to: 'to-earth-700' }],
  [['health', 'wellness', 'fitness', 'exercise', 'yoga'], { from: 'from-sage-600', to: 'to-forest-900' }],
  [['travel', 'adventure', 'journey', 'explore'], { from: 'from-forest-600', to: 'to-sage-800' }],
  [['business', 'finance', 'money', 'market'], { from: 'from-earth-700', to: 'to-earth-900' }],
]

const FALLBACK_GRADIENTS: { from: string; to: string }[] = [
  { from: 'from-earth-600', to: 'to-earth-800' },
  { from: 'from-forest-600', to: 'to-forest-900' },
  { from: 'from-lsc-rose', to: 'to-earth-800' },
  { from: 'from-sage-600', to: 'to-sage-800' },
]

function getTheme(title: string, itemType?: string, subjects?: string | null): ThemeMatch {
  const icon = ITEM_TYPE_ICONS[itemType || ''] ?? ITEM_TYPE_ICONS['other']!
  const lower = `${title} ${subjects || ''}`.toLowerCase()

  for (const [keywords, gradient] of THEME_KEYWORDS) {
    if (keywords.some((k) => lower.includes(k))) {
      return { icon, ...gradient }
    }
  }

  // Deterministic fallback based on title hash
  const hash = [...title].reduce((h, c) => ((h << 5) - h + c.charCodeAt(0)) | 0, 0)
  const fallback = FALLBACK_GRADIENTS[Math.abs(hash) % FALLBACK_GRADIENTS.length]!
  return { icon, ...fallback }
}

const SIZES = {
  sm: { container: 'h-[120px]', icon: 'w-4 h-4', pad: 'p-2', title: 'text-[11px] line-clamp-3', author: 'text-[10px]' },
  md: { container: 'h-full', icon: 'w-6 h-6', pad: 'p-3', title: 'text-sm line-clamp-4', author: 'text-xs' },
  lg: { container: 'h-full', icon: 'w-8 h-8', pad: 'p-4', title: 'text-base line-clamp-4', author: 'text-sm' },
}

export default function CatalogItemThumbnail({
  title,
  author,
  itemType,
  subjects,
  size = 'md',
  className = '',
}: CatalogItemThumbnailProps) {
  const theme = getTheme(title, itemType, subjects)
  const Icon = theme.icon
  const s = SIZES[size]

  return (
    <div
      className={`${s.container} ${className} bg-gradient-to-br ${theme.from} ${theme.to} relative overflow-hidden`}
    >
      {/* Pattern overlay */}
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 80%, white 1px, transparent 1px), radial-gradient(circle at 80% 20%, white 1px, transparent 1px)',
          backgroundSize: '30px 30px',
        }}
      />
      {/* Text-based placeholder: title + author so the tile reads like a
          cover instead of an anonymous glyph. aria-hidden because the
          surrounding card already conveys title/author to assistive tech. */}
      <div aria-hidden="true" className={`relative z-10 h-full flex flex-col ${s.pad}`}>
        <Icon className={`${s.icon} text-white/90 drop-shadow-md flex-shrink-0`} />
        <span className={`mt-auto font-serif font-bold text-white drop-shadow-sm leading-snug break-words ${s.title}`}>
          {title}
        </span>
        {author && (
          <span className={`${s.author} text-white/80 drop-shadow-sm truncate flex-shrink-0`}>{author}</span>
        )}
      </div>
    </div>
  )
}

interface CatalogCoverProps extends CatalogItemThumbnailProps {
  coverUrl: string | null | undefined
  alt: string
  imgClassName?: string
  loading?: 'lazy' | 'eager'
  /**
   * When set, the rendered `<img>` uses the backend cover-proxy
   * (`/api/v1/catalog/covers/{itemId}`) instead of `coverUrl` directly.
   * This keeps patron browsing private (no `Referer` to third-party CDNs)
   * and gives us a single revalidation point if an upstream goes away.
   *
   * `coverUrl` is still used to decide whether there is *any* cover to
   * render at all -- pass `null`/`undefined` to fall back to the
   * generative thumbnail without making a wasted request.
   */
  itemId?: number
}

export function CatalogCover({
  coverUrl,
  alt,
  title,
  author,
  itemType,
  subjects,
  size = 'md',
  className = '',
  imgClassName = 'w-full h-full object-cover',
  loading = 'lazy',
  itemId,
}: CatalogCoverProps) {
  const renderedSrc = itemId !== undefined && coverUrl
    ? `/api/v1/catalog/covers/${itemId}`
    : coverUrl
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const failed = failedUrl !== null && failedUrl === renderedSrc

  if (!renderedSrc || failed) {
    return (
      <CatalogItemThumbnail
        title={title}
        {...(author !== undefined && { author })}
        {...(itemType !== undefined && { itemType })}
        {...(subjects !== undefined && { subjects })}
        size={size}
        className={className}
      />
    )
  }

  return (
    <img
      src={renderedSrc}
      alt={alt}
      // The surrounding card/link already conveys title + author + format,
      // so the cover is decorative for assistive tech. Keeping `alt` as a
      // prop preserves the option to opt out for contexts where the image
      // IS the primary identifier (e.g. an image-gallery zoom view).
      aria-hidden={alt === '' ? 'true' : undefined}
      loading={loading}
      onError={() => setFailedUrl(renderedSrc)}
      className={`${imgClassName} ${className}`.trim()}
    />
  )
}
