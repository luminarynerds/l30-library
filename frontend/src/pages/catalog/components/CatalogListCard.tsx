/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { useState, useId, useCallback, memo } from 'react'
import { createPortal } from 'react-dom'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  Headphones,
  Film,
  Disc,
  Newspaper,
  Gamepad2,
  Smartphone,
  Package,
  Volume2,
  VolumeX,
  CircleCheck,
  Clock,
  Users,
  Truck,
  PackageSearch,
  AlertTriangle,
  Shield,
  MapPin,
  Award,
} from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { type CatalogItem } from '@/api/api'
import { getCatalogItem } from '@/api/domains/catalog/catalog-api'
import { getSourceLabel } from '@/api/domains/catalog/unified-search-api'
import { clsx } from '@/utils/helpers'
import PlaceholderCover from './PlaceholderCover'
import {
  statusColor,
  statusLabel,
  statusLabelI18n,
  statusIcon,
  FORMAT_LABELS,
  catalogItemLink,
  coverProxyUrl,
  catalogSignInPath,
} from '@/pages/catalog/utils/catalogHelpers'
import { getMoodTags } from '@/pages/catalog/utils/catalogItemUtils'
import { resolveAvailabilityChip } from '@/pages/catalog/utils/availabilityChip'
import MoodTag from '@/pages/catalog/components/MoodTag'
import { SHELF_BORDER_COLORS, SHELF_STATUS_LABELS } from '@/hooks/useShelfStatusMap'
import type { ItemAvailabilityInfo } from '@/hooks/useAvailabilityMap'
import ShelfBookmark from '@/components/shelf/ShelfBookmark'
import { AddToListDropdown } from '@/components/reading-lists/AddToListDropdown'
import { LexileBadge } from '@/components/LexileBadge'
import { PlaceHoldModal } from './PlaceHoldModal'
import { useAuth } from '@/contexts/AuthContext'
import type { ShelfStatus } from '@/api/domains/content/reading-status-api'

// Statuses where Place Hold is meaningless. PlaceHoldModal's 422 handler
// catches the server-side business-rule case if anything slips through.
const NON_HOLDABLE_STATUSES = new Set(['withdrawn', 'lost', 'damaged'])

// Re-export for backwards compat (other files may import from here)
export { statusColor, statusLabel, FORMAT_LABELS }

const STATUS_ICON_MAP: Record<string, typeof Clock> = {
  CircleCheck, Clock, Users, Truck, PackageSearch,
}

function StatusIndicator({ status, className, tone }: { status: string; className?: string; tone?: 'green' | 'amber' | 'blue' }) {
  const iconName = statusIcon(status)
  const Icon = STATUS_ICON_MAP[iconName] || Clock
  // Honor an explicit tone (from the resolved availability chip) so the icon
  // color never disagrees with the chip text -- e.g. a multi-copy title that
  // is "checked_out" at the title level but has copies on the shelf shows the
  // green chip AND a green icon.
  const color = tone ?? statusColor(status)
  const colorClass = {
    green: 'text-status-success-600 dark:text-status-success-400',
    amber: 'text-status-warning-500 dark:text-status-warning-400',
    blue: 'text-status-info-500 dark:text-status-info-400',
  }[color]
  return <Icon className={clsx('w-4 h-4 flex-shrink-0', colorClass, className)} aria-hidden="true" />
}

// Format icons (JSX — must live in a .tsx file, not the .ts helpers)
export const FORMAT_ICONS: Record<string, React.ReactNode> = {
  book: <BookOpen className="w-4 h-4" aria-hidden="true" />,
  audiobook: <Headphones className="w-4 h-4" aria-hidden="true" />,
  ebook: <Smartphone className="w-4 h-4" aria-hidden="true" />,
  dvd: <Film className="w-4 h-4" aria-hidden="true" />,
  bluray: <Film className="w-4 h-4" aria-hidden="true" />,
  cd: <Disc className="w-4 h-4" aria-hidden="true" />,
  vinyl: <Disc className="w-4 h-4" aria-hidden="true" />,
  magazine: <Newspaper className="w-4 h-4" aria-hidden="true" />,
  game: <Gamepad2 className="w-4 h-4" aria-hidden="true" />,
  equipment: <Package className="w-4 h-4" aria-hidden="true" />,
  kit: <Package className="w-4 h-4" aria-hidden="true" />,
  other: <Package className="w-4 h-4" aria-hidden="true" />,
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/** Background colors for source badges. */
const SOURCE_BADGE_COLORS: Record<string, string> = {
  local: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/40 dark:text-status-info-300',
  indie: 'bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300',
}

interface CatalogListCardProps {
  item: CatalogItem
  /** Content source identifier (e.g. 'local', 'indie'). */
  source?: string | undefined
  simplifiedView: boolean
  quietMode: boolean
  showImages: boolean
  isSpeaking: boolean
  onSpeak: (text: string) => void
  onStopSpeak: () => void
  /** User's shelf status for this item, if any. */
  shelfStatus?: string | undefined
  /** Batched copy-level availability for this item (local items only). */
  copyAvailability?: ItemAvailabilityInfo | undefined
  hasChallengeOrBan?: boolean | undefined
}

export default memo(function CatalogListCard({
  item,
  source,
  simplifiedView,
  quietMode,
  showImages,
  isSpeaking,
  onSpeak,
  onStopSpeak,
  shelfStatus,
  copyAvailability,
  hasChallengeOrBan,
}: CatalogListCardProps): React.ReactElement {
  const { t } = useTranslation()
  const [imageError, setImageError] = useState(false)
  const [showHoldModal, setShowHoldModal] = useState(false)
  const { user } = useAuth()
  const navigate = useNavigate()
  const isHoldable = !NON_HOLDABLE_STATUSES.has(item.status)
  const canPlaceHold = !!user && isHoldable
  const moods = getMoodTags(item.id, item.subjects ?? null)

  // Prefetch item detail on hover/focus so the navigation feels instant.
  // queryKey matches useItemDetail; staleTime=5min avoids re-fetch on rapid
  // re-hover. react-query dedupes concurrent in-flight requests.
  const queryClient = useQueryClient()
  const prefetchItem = useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: ['catalog-item', item.id],
      queryFn: () => getCatalogItem(item.id),
      staleTime: 5 * 60 * 1000,
    })
  }, [queryClient, item.id])
  // ids for aria-labelledby — keeps the accessible link name narrow
  // (title + status, plus author when present) so SR users still discover
  // moods/location/content-notes via normal child traversal. See spec
  // 2026-05-16-l30-catalog-card-improvements-design.md.
  const titleId = useId()
  const authorId = useId()
  const statusId = useId()

  const formatLabel = FORMAT_LABELS[item.item_type] || item.item_type
  // Backend cover-proxy: see CatalogGridCard for the privacy rationale. The
  // proxy returns 404 when no cover exists, which the onError handler
  // promotes to the generative thumbnail.
  const primaryImage = item.images?.find((img) => img.is_primary) ?? item.images?.[0]
  const hasAnyCover = Boolean(primaryImage?.image_url || item.cover_url)
  const coverSrc = hasAnyCover ? coverProxyUrl(item.id) : null
  const hasCover = coverSrc && !imageError
  // One resolved availability chip (shared with the grid card) so both views
  // speak the same grammar -- the copy count IS the chip, never a contradictory
  // "Checked Out · 1 of 2 available" pairing. The full chip label is the
  // accessible name; quiet mode shows just the plain status word visually
  // (copy counts are secondary metadata it suppresses, like moods/description).
  const chip = resolveAvailabilityChip(item.status, copyAvailability, t)
  const statusText = chip.label
  const visibleStatusText = quietMode ? statusLabelI18n(item.status) : chip.label

  const shelfBorderClass = shelfStatus
    ? SHELF_BORDER_COLORS[shelfStatus as ShelfStatus] || 'border-l-transparent'
    : 'border-l-transparent'
  const shelfLabel = shelfStatus ? SHELF_STATUS_LABELS[shelfStatus as ShelfStatus] : undefined

  const speakableText = [
    item.title,
    item.author ? `, by ${item.author}` : '',
    `. ${formatLabel}`,
    item.is_large_print ? ', Large Print edition' : '',
    `. ${item.status === 'available' ? 'Available now' : `Currently ${item.status.replace(/_/g, ' ')}`}`,
    item.description ? `. ${item.description}` : '',
  ].join('')

  return (
    // Overlay-link pattern: the card is a plain positioned container; the
    // title <Link> stretches over it via an ::after overlay. Other interactive
    // children (series link, buttons, dropdown) are siblings of the anchor,
    // lifted above the overlay with z-index — never nested inside it.
    <div
      className={clsx(
        'relative block bg-lsc-white dark:bg-earth-800 rounded-xl p-5 hover:bg-earth-50 dark:hover:bg-earth-700/40 motion-safe:transition-colors',
        'border-l-[3px]',
        shelfBorderClass,
      )}
    >
      {/* Visually-hidden status text used for the link's accessible name.
          The visible status text in the body remains for sighted users. */}
      <span id={statusId} className="sr-only">
        {statusText}
        {shelfLabel ? `, ${shelfLabel}` : ''}
      </span>
      <div className="flex flex-wrap sm:flex-nowrap gap-[18px] items-start">
        {/* Cover image - 80x120, hidden in simplified view or when images disabled */}
        {!simplifiedView && showImages && (
          <div className="relative w-20 min-w-[80px] h-[120px] rounded-lg flex-shrink-0 overflow-hidden shadow-sm">
            {hasCover ? (
              <img
                src={coverSrc!}
                alt=""
                aria-hidden="true"
                className="w-full h-full object-cover"
                loading="lazy"
                onError={() => setImageError(true)}
            onLoad={(e) => { const img = e.currentTarget; if (img.naturalWidth <= 1 && img.naturalHeight <= 1) setImageError(true) }}
              />
            ) : (
              <PlaceholderCover itemId={item.id} title={item.title} author={item.author} itemType={item.item_type} size="sm" hasBookmarkOverlay />
            )}
            {/* The Add-to-List dropdown was removed from this cover overlay
                because the menu was clipped by the cover's overflow-hidden
                container; the action-row variant below is always rendered
                in its place. */}
            <div className="absolute top-1 left-1 z-[1] flex items-center gap-1">
              <ShelfBookmark catalogItemId={item.id} />
            </div>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 min-w-0">
          <h3 className="font-serif text-[17px] font-bold text-lsc-dark dark:text-lsc-cream leading-tight">
            {/* The card's single navigation link. The ::after overlay stretches
                its hit area over the whole card (nearest positioned ancestor =
                the card container). Focus ring is drawn on the overlay so the
                whole card shows the indicator, matching the old behavior. */}
            <Link
              to={catalogItemLink(item.id, item.title, source)}
              state={{ fromCatalog: true }}
              aria-labelledby={[titleId, item.author ? authorId : '', statusId].filter(Boolean).join(' ')}
              onMouseEnter={prefetchItem}
              onFocus={prefetchItem}
              className="focus:outline-none after:content-[''] after:absolute after:inset-0 after:rounded-xl focus:after:ring-2 focus:after:ring-lsc-rose focus:after:ring-offset-2 dark:focus:after:ring-offset-lsc-dark"
            >
              <span id={titleId}>{item.title}</span>
            </Link>
          </h3>
          <p id={authorId} className="text-[13px] font-bold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            {item.author || '\u2014'}
          </p>

          {item.series_name && (
            <p className="text-[12px] text-lsc-dark/65 dark:text-lsc-cream/65 mb-2 italic">
              <Link
                to={`/catalog?series_facets=${encodeURIComponent(item.series_name)}`}
                aria-label={`View all in series: ${item.series_name}`}
                className="relative z-[1] underline underline-offset-2 hover:text-lsc-rose focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm"
              >
                {item.series_name}{item.series_number ? `, #${item.series_number}` : ''}
              </Link>
            </p>
          )}

          {/* Description - hidden in quiet mode */}
          {!quietMode && item.description && (
            <p className="text-[13px] text-lsc-dark/75 dark:text-lsc-cream/75 line-clamp-2 mb-3" title={item.description}>
              {item.description}
            </p>
          )}

          {/* Traffic-light format + status row */}
          <div className="flex flex-wrap gap-x-4 gap-y-[6px] pt-[10px] border-t border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-[6px] text-sm text-lsc-dark/80 dark:text-lsc-cream/80 font-semibold">
              {FORMAT_ICONS[item.item_type] || FORMAT_ICONS.other}
              <span>
                {formatLabel}
                {item.is_large_print ? ' (LP)' : ''}
              </span>
              <StatusIndicator status={item.status} tone={chip.tone} />
              {/* Status text is always rendered so status is not color-only.
                  WCAG 1.4.1 Use of Color. The chip label already folds in the
                  copy count ("1 of 2 available"), so there is no separate
                  count span to contradict it. */}
              <span
                className={clsx(
                  'font-medium',
                  quietMode
                    ? 'text-xs text-lsc-dark/70 dark:text-lsc-cream/70'
                    : 'text-sm text-lsc-dark/80 dark:text-lsc-cream/80',
                )}
              >
                {visibleStatusText}
              </span>
            </div>
            {source && source !== 'local' && (
              <span
                className={clsx(
                  'inline-flex items-center px-2 py-[2px] rounded-lg text-xs font-semibold',
                  SOURCE_BADGE_COLORS[source] || 'bg-lsc-cream text-lsc-dark dark:bg-earth-800/40 dark:text-lsc-cream/70',
                )}
              >
                {getSourceLabel(source)}
              </span>
            )}
            {hasChallengeOrBan && (
              <span className="inline-flex items-center gap-1 px-2 py-[2px] rounded-lg text-xs font-semibold bg-category-50 text-category-700 dark:bg-category-900/30 dark:text-category-300">
                <Shield className="w-3 h-3" aria-hidden="true" />
                Challenged
              </span>
            )}
            {item.staff_pick && (
              <span
                className="inline-flex items-center gap-1 px-2 py-[2px] rounded-lg text-xs font-semibold bg-category-50 text-category-700 dark:bg-category-900/30 dark:text-category-300"
                title={t('catalog.card.staffPick', 'Staff Pick')}
                aria-label={t('catalog.card.staffPickAria', 'Staff pick')}
              >
                <Award className="w-3 h-3" aria-hidden="true" />
                {t('catalog.card.staffPick', 'Staff Pick')}
              </span>
            )}
          </div>

          {/* Mood tags - hidden in quiet mode. Clickable: each pill browses
              that mood (/catalog/mood/{slug}) via the shared MoodTag. */}
          {!quietMode && moods.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {moods.map(mood => (
                <MoodTag key={mood} mood={mood} size="md" />
              ))}
            </div>
          )}

          {item.lexile_measure && (
            <div className="mt-1.5">
              <LexileBadge measure={item.lexile_measure} compact />
            </div>
          )}

          {/* Content notes indicator */}
          {!quietMode && item.content_notes && (
            <div className="flex items-center gap-1 mt-1.5 text-xs text-status-warning-600 dark:text-status-warning-400">
              <AlertTriangle className="w-3 h-3" aria-hidden="true" />
              <span>Content notes available</span>
            </div>
          )}

          {/* Shelf location */}
          {!quietMode && (item.call_number || item.location) && (
            <div className="flex items-center gap-1 mt-1.5 text-xs text-earth-600 dark:text-earth-400">
              <MapPin className="w-3 h-3 flex-shrink-0" aria-hidden="true" />
              <span>{[item.call_number, item.location].filter(Boolean).join(" \u2022 ")}</span>
            </div>
          )}
        </div>

        {/* Action buttons - hidden in quiet mode and simplified view */}
        {!quietMode && !simplifiedView && (
          <div className="relative z-[1] flex items-center gap-1 flex-shrink-0 self-start mt-[2px] w-full sm:w-auto justify-end sm:justify-start">
            <AddToListDropdown catalogItemId={item.id} />
            <button
              className="w-9 h-9 min-w-[36px] flex items-center justify-center rounded-lg text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose hover:bg-lsc-rose/10 transition-colors"
              onClick={() => {
                if (isSpeaking) {
                  onStopSpeak()
                } else {
                  onSpeak(speakableText)
                }
              }}
              aria-label={isSpeaking ? 'Stop reading aloud' : 'Read item description aloud'}
              title={isSpeaking ? 'Stop reading aloud' : 'Read aloud'}
            >
              {isSpeaking ? (
                <VolumeX className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Volume2 className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
            {canPlaceHold && (
              <button
                type="button"
                className="h-9 px-3 min-w-[36px] flex items-center justify-center rounded-lg text-xs font-semibold border border-lsc-rose text-lsc-rose hover:bg-lsc-rose hover:text-lsc-white transition-colors"
                onClick={() => setShowHoldModal(true)}
                aria-label={t('catalog.card.placeHoldFor', 'Place hold on this item')}
                title={t('catalog.card.placeHold', 'Place hold')}
              >
                {t('catalog.card.placeHold', 'Place hold')}
              </button>
            )}
            {!user && isHoldable && (
              <button
                type="button"
                className="h-9 px-3 min-w-[36px] flex items-center justify-center rounded-lg text-xs font-semibold border border-lsc-rose text-lsc-rose hover:bg-lsc-rose hover:text-lsc-white transition-colors"
                onClick={() => {
                  // Sign-in-and-return: LoginPage honors location.state.from,
                  // and /catalog/{id}?action=hold re-opens the hold modal.
                  const { pathname, state } = catalogSignInPath(item.id, { action: 'hold', title: item.title })
                  navigate(pathname, { state })
                }}
                aria-label={t('catalog.card.signInToPlaceHold', 'Sign in to place hold')}
                title={t('catalog.card.signInToPlaceHold', 'Sign in to place hold')}
              >
                {t('catalog.card.signInToPlaceHold', 'Sign in to place hold')}
              </button>
            )}
          </div>
        )}
      </div>
      {showHoldModal && createPortal(
        // Portal to document.body so the dialog escapes the card's stacking
        // context. The card is no longer an anchor, so clicks inside the
        // modal cannot trigger a navigation — no stopPropagation needed.
        <PlaceHoldModal
          item={item}
          onClose={() => setShowHoldModal(false)}
          onSuccess={() => setShowHoldModal(false)}
        />,
        document.body,
      )}
    </div>
  )
})
