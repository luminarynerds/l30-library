/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { memo } from 'react'
import { FORMAT_LABELS } from '@/pages/catalog/utils/catalogHelpers'

// ---------------------------------------------------------------------------
// PlaceholderCover
//
// Informative text-based cover for catalog items that have no cover image.
// Open-Library style: the real title + author rendered as live text (so it is
// selectable and exposed to assistive tech) over a deterministic colored
// background derived from a hash of the item id/title. Replaces the previous
// dark glyph-only tile, which made ~half the grid read as "broken".
//
// Palette is L30's brand family (rose / plum / sage / gold / forest / earth)
// -- never MetisLib's teal/indigo. Each pairing is a solid background + a
// text color chosen for WCAG AA contrast against it.
// ---------------------------------------------------------------------------

interface PlaceholderCoverProps {
  itemId: number
  title: string
  author?: string | null
  itemType?: string | null
  /** Visual size. `sm` matches the 80x120 list thumbnail; `md` fills the grid card. */
  size?: 'sm' | 'md'
  className?: string
  /** When true, reserves left-padding on the title so the absolute-positioned
   *  ShelfBookmark (top-left, ~36px wide) does not clip the first characters. */
  hasBookmarkOverlay?: boolean
}

/** Brand-family background/text pairings (rose / plum / sage / gold / earth --
 *  L30's family, never MetisLib teal/indigo). All backgrounds are deep enough
 *  that the paired text color clears WCAG AA. Tokens are verified against the
 *  tailwind theme: `lsc-rose`, `category-*` (the plum/purple ramp), `forest-*`
 *  (the green/sage ramp), `earth-*`, and the single `lsc-gold`. */
const PALETTE: { bg: string; text: string; accent: string }[] = [
  { bg: 'bg-lsc-rose', text: 'text-white', accent: 'text-white/90' },
  { bg: 'bg-category-700', text: 'text-white', accent: 'text-white/90' },
  { bg: 'bg-category-800', text: 'text-white', accent: 'text-white/90' },
  { bg: 'bg-forest-800', text: 'text-white', accent: 'text-white/90' },
  { bg: 'bg-earth-700', text: 'text-white', accent: 'text-white/90' },
  { bg: 'bg-lsc-gold', text: 'text-earth-900', accent: 'text-earth-900/90' },
]

/** Stable 32-bit string hash (same algorithm CatalogItemThumbnail uses). */
function hashString(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

const SIZES = {
  sm: { title: 'text-[13px] leading-tight', author: 'text-[10px]', pad: 'p-2', format: 'text-[9px]' },
  md: { title: 'text-base leading-snug', author: 'text-xs', pad: 'p-4', format: 'text-[10px]' },
} as const

// ShelfBookmark renders as w-9 (36px) at top-2/left-2 (8px offset). These
// nudges push the title text right so it clears the button on both sizes.
const BOOKMARK_TITLE_NUDGE = { sm: 'pl-8', md: 'pl-9' } as const

export default memo(function PlaceholderCover({
  itemId,
  title,
  author,
  itemType,
  size = 'md',
  className = '',
  hasBookmarkOverlay = false,
}: PlaceholderCoverProps) {
  // Deterministic color from a stable key so the same item always renders the
  // same cover across sessions and surfaces. Falls back to the title when the
  // id is missing (indie items can arrive with id 0).
  const key = itemId > 0 ? String(itemId) : title
  const palette = PALETTE[hashString(key) % PALETTE.length]!
  const s = SIZES[size]
  const formatLabel = itemType ? FORMAT_LABELS[itemType] || itemType : null
  const titlePl = hasBookmarkOverlay ? BOOKMARK_TITLE_NUDGE[size] : 'pl-1'

  return (
    <div
      className={`${className} w-full h-full ${palette.bg} ${s.pad} flex flex-col justify-between relative overflow-hidden`}
      // The surrounding card/link already names the item for assistive tech,
      // so the cover text is decorative duplication here -- hide it from the
      // a11y tree to avoid a double-announce, while keeping it real, selectable
      // on-screen text (not baked into an image) for sighted low-vision users.
      aria-hidden="true"
    >
      {/* Spine accent bar -- subtle "this is a cover" affordance */}
      <span className="absolute top-0 left-0 h-full w-1.5 bg-black/15" />
      <p className={`font-serif font-bold ${palette.text} ${s.title} line-clamp-4 ${titlePl}`}>
        {title}
      </p>
      <div className="pl-1">
        {author && (
          <p className={`${palette.accent} ${s.author} line-clamp-2 mb-1`}>{author}</p>
        )}
        {formatLabel && (
          <p className={`${palette.accent} ${s.format} uppercase tracking-wide font-semibold`}>
            {formatLabel}
          </p>
        )}
      </div>
    </div>
  )
})
