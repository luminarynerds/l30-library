/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useId, useCallback, memo } from 'react'
import { createPortal } from 'react-dom'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { CircleCheck, Clock, Users, Truck, PackageSearch, Shield } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { type CatalogItem, getCatalogItem } from '@/api/api'
import { getSourceLabel } from '@/api/domains/catalog/unified-search-api'
import { clsx } from '@/utils/helpers'
import PlaceholderCover from './PlaceholderCover'
import { FORMAT_ICONS } from './CatalogListCard'
import {
  statusColor,
  statusIcon,
  catalogItemLink,
  coverProxyUrl,
  FORMAT_LABELS,
  catalogSignInPath,
} from '../utils/catalogHelpers'
import { getMoodTags } from '../utils/catalogItemUtils'
import { resolveAvailabilityChip } from '../utils/availabilityChip'
import MoodTag from './MoodTag'
import { SHELF_TOP_BORDER_COLORS, SHELF_STATUS_LABELS } from '@/hooks/useShelfStatusMap'
import type { ItemAvailabilityInfo } from '@/hooks/useAvailabilityMap'
import ShelfBookmark from '@/components/shelf/ShelfBookmark'
import { PlaceHoldModal } from './PlaceHoldModal'
import { useAuth } from '@/contexts/AuthContext'
import type { ShelfStatus } from '@/api/domains/content/reading-status-api'

const NON_HOLDABLE_STATUSES = new Set(['withdrawn', 'lost', 'damaged'])

// ---------------------------------------------------------------------------
// CatalogGridCard
// ---------------------------------------------------------------------------

const STATUS_ICON_MAP: Record<string, typeof Clock> = {
  CircleCheck, Clock, Users, Truck, PackageSearch,
}

function StatusIndicator({ status, className }: { status: string; className?: string }) {
  const iconName = statusIcon(status)
  const Icon = STATUS_ICON_MAP[iconName] || Clock
  const color = statusColor(status)
  const colorClass = {
    green: 'text-status-success-600 dark:text-status-success-400',
    amber: 'text-status-warning-500 dark:text-status-warning-400',
    blue: 'text-status-info-500 dark:text-status-info-400',
  }[color]
  return <Icon className={clsx('w-4 h-4 flex-shrink-0', colorClass, className)} aria-hidden="true" />
}

/** Background colors for source badges (mirrors CatalogListCard). */
const SOURCE_BADGE_COLORS: Record<string, string> = {
  local: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/40 dark:text-status-info-300',
  indie: 'bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300',
}

interface CatalogGridCardProps {
  item: CatalogItem
  /** Content source identifier (e.g. 'local', 'indie'). */
  source?: string | undefined
  /** User's shelf status for this item, if any. */
  shelfStatus?: string | undefined
  /** Batched copy-level availability for this item (local items only). */
  copyAvailability?: ItemAvailabilityInfo | undefined
  hasChallengeOrBan?: boolean | undefined
}

export default memo(function CatalogGridCard({ item, source, shelfStatus, copyAvailability, hasChallengeOrBan }: CatalogGridCardProps) {
  const { t } = useTranslation()
  const [imageError, setImageError] = useState(false)
  const [showHoldModal, setShowHoldModal] = useState(false)
  const { user } = useAuth()
  const navigate = useNavigate()
  const isHoldable = !NON_HOLDABLE_STATUSES.has(item.status)
  const canPlaceHold = !!user && isHoldable
  const moods = getMoodTags(item.id, item.subjects ?? null)

  // Prefetch item detail on hover/focus. See CatalogListCard for rationale.
  const queryClient = useQueryClient()
  const prefetchItem = useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: ['catalog-item', item.id],
      queryFn: () => getCatalogItem(item.id),
      staleTime: 5 * 60 * 1000,
    })
  }, [queryClient, item.id])
  // The backend cover-proxy resolves the actual source (uploaded image or
  // remote ``cover_url``) server-side and serves it from our origin, so we
  // do not leak ``Referer`` to third-party CDNs. The proxy 404s cleanly when
  // there is nothing to serve, which the ``onError`` handler turns into the
  // generative thumbnail below.
  const primaryImage = item.images?.find((img) => img.is_primary) ?? item.images?.[0]
  const hasAnyCover = Boolean(primaryImage?.image_url || item.cover_url)
  const coverSrc = hasAnyCover ? coverProxyUrl(item.id) : null
  const hasCover = coverSrc && !imageError
  // One resolved availability chip (shared with the list card) so the grid and
  // list views speak the same grammar and never pair "checked out" with the
  // word "available".
  const chip = resolveAvailabilityChip(item.status, copyAvailability, t)
  const color = chip.tone

  const shelfBorderClass = shelfStatus
    ? SHELF_TOP_BORDER_COLORS[shelfStatus as ShelfStatus] || ''
    : ''
  const shelfLabel = shelfStatus ? SHELF_STATUS_LABELS[shelfStatus as ShelfStatus] : undefined

  // ids for aria-labelledby. See spec 2026-05-16-l30-catalog-card-improvements-design.md
  // for the WCAG rationale (2.5.3 / 4.1.2 / 1.3.1).
  const titleId = useId()
  const authorId = useId()
  const statusId = useId()

  return (
    // Overlay-link pattern: the card is a plain positioned container; the
    // title <Link> stretches over it via an ::after overlay. Interactive
    // children (shelf bookmark, hold/sign-in buttons) are siblings of the
    // anchor, lifted above the overlay with z-index — never nested inside it.
    <div
      className={clsx(
        'group relative block rounded-xl motion-safe:transition-[transform,box-shadow] motion-safe:duration-150 motion-safe:ease-[cubic-bezier(0.23,1,0.32,1)]',
        'hover:shadow-lg motion-safe:[@media(hover:hover)_and_(pointer:fine)]:hover:-translate-y-0.5',
        shelfStatus && 'border-t-[3px]',
        shelfBorderClass,
      )}
    >
      {/* Visually-hidden status text used for the link's accessible name. */}
      <span id={statusId} className="sr-only">
        {chip.label}
        {shelfLabel ? `, ${shelfLabel}` : ''}
      </span>
      {/* Cover image with frosted-glass status badge */}
      <div className="relative w-full aspect-[2/3] rounded-xl overflow-hidden bg-lsc-border dark:bg-earth-700 shadow-sm mb-2">
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
          <PlaceholderCover itemId={item.id} title={item.title} author={item.author} itemType={item.item_type} size="md" hasBookmarkOverlay />
        )}

        {/* Frosted glass status badge — opacity bumped to /95 and amber darkened
            so white text holds WCAG AA contrast over varied cover images. */}
        <span
          className={clsx(
            'absolute bottom-2 left-2 flex items-center gap-1 px-2 py-[3px]',
            'rounded-lg text-xs font-bold text-white backdrop-blur-sm',
            // Solid backgrounds (no /95) so contrast vs. arbitrary cover art
            // is deterministic — WCAG 1.4.3 Contrast (Minimum, AA).
            color === 'green' && 'bg-status-success-900',
            color === 'amber' && 'bg-status-warning-900',
            color === 'blue' && 'bg-status-info-900',
          )}
        >
          <StatusIndicator status={item.status} className="w-3.5 h-3.5 !text-white" />
          {chip.label}
        </span>

        {/* Source badge for non-local items */}
        {source && source !== 'local' && (
          <span
            className={clsx(
              'absolute top-2 right-2 px-2 py-[2px] rounded-lg text-[10px] font-bold backdrop-blur-sm',
              SOURCE_BADGE_COLORS[source] || 'bg-lsc-cream text-lsc-dark dark:bg-earth-800/40 dark:text-lsc-cream/70',
            )}
          >
            {getSourceLabel(source)}
          </span>
        )}

        {/* Challenge badge - top-right when no source badge */}
        {hasChallengeOrBan && !(source && source !== 'local') && (
          <span className="absolute top-2 right-2 px-2 py-[2px] rounded-lg text-[10px] font-bold backdrop-blur-sm bg-category-100 text-category-800 dark:bg-category-900/60 dark:text-category-200">
            <Shield className="w-3 h-3 inline mr-0.5" aria-hidden="true" />
            {t('catalog.card.challenged')}
          </span>
        )}

        {/* Shelf bookmark - top-left. The Add-to-List dropdown was removed
            from the cover overlay because the dropdown menu was clipped by
            the cover's overflow-hidden container. Adding to a list lives on
            the item detail page. */}
        <div className="absolute top-2 left-2 z-[1] flex items-center gap-1">
          <ShelfBookmark catalogItemId={item.id} />
        </div>
      </div>

      {/* Title & author */}
      <h3 className="font-serif text-lg text-lsc-dark dark:text-lsc-cream leading-[1.15] mb-1 line-clamp-2" title={item.title}>
        {/* The card's single navigation link. The ::after overlay stretches its
            hit area over the whole card (nearest positioned ancestor = the card
            container). Focus ring is drawn on the overlay so the whole card
            shows the indicator, matching the old behavior. */}
        <Link
          to={catalogItemLink(item.id, item.title, source)}
          state={{ fromCatalog: true }}
          onMouseEnter={prefetchItem}
          onFocus={prefetchItem}
          className="focus:outline-none after:content-[''] after:absolute after:inset-0 after:rounded-xl focus:after:ring-2 focus:after:ring-lsc-rose focus:after:ring-offset-2 dark:focus:after:ring-offset-lsc-dark"
          aria-labelledby={`${titleId} ${statusId}`}
        >
          <span id={titleId}>{item.title}</span>
        </Link>
      </h3>
      {item.author && (
        <p id={authorId} className="text-sm text-earth-600 dark:text-lsc-cream/70 mb-1.5 truncate" title={item.author}>
          {item.author}
        </p>
      )}
      {/* One quiet meta line: format + large-print flag. Staff-pick, Lexile,
          call number and location live on the item detail page so the browse
          grid stays scannable. */}
      <div className="flex items-center gap-1 text-xs text-earth-600 dark:text-lsc-cream/55 truncate" aria-hidden="true">
        {FORMAT_ICONS[item.item_type] || FORMAT_ICONS.other}
        <span>{FORMAT_LABELS[item.item_type] || item.item_type}</span>
        {item.is_large_print && <span className="ml-0.5 text-xs font-semibold text-status-warning-600 dark:text-status-warning-400">{t('catalog.card.largePrintShort', 'LP')}</span>}
      </div>
      {/* First mood as a clickable tag (kept OUT of the aria-hidden meta line
          above so the filter link stays in the a11y tree). */}
      {moods.length > 0 && (
        <div className="mt-1">
          <MoodTag mood={moods[0]!} size="sm" />
        </div>
      )}
      {item.location && (
        <p className="text-xs text-earth-600 dark:text-lsc-cream/40 truncate mt-0.5" aria-hidden="true">
          {item.location}
        </p>
      )}
      {canPlaceHold && (
        <button
          type="button"
          className="relative z-[1] mt-2 w-full h-9 px-3 flex items-center justify-center rounded-lg text-xs font-semibold border border-lsc-rose text-lsc-rose hover:bg-lsc-rose hover:text-lsc-white motion-safe:transition-opacity opacity-100 [@media(hover:hover)]:opacity-0 group-hover:!opacity-100 group-focus-within:!opacity-100"
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
          className="relative z-[1] mt-2 w-full h-9 px-3 flex items-center justify-center rounded-lg text-xs font-semibold border border-lsc-rose text-lsc-rose hover:bg-lsc-rose hover:text-lsc-white motion-safe:transition-opacity opacity-100 [@media(hover:hover)]:opacity-0 group-hover:!opacity-100 group-focus-within:!opacity-100"
          onClick={() => {
            // Sign-in-and-return: LoginPage honors location.state.from, and
            // /catalog/{id}?action=hold re-opens the hold modal after auth.
            const { pathname, state } = catalogSignInPath(item.id, { action: 'hold', title: item.title })
            navigate(pathname, { state })
          }}
          aria-label={t('catalog.card.signInToPlaceHold', 'Sign in to place hold')}
          title={t('catalog.card.signInToPlaceHold', 'Sign in to place hold')}
        >
          {t('catalog.card.signInToPlaceHold', 'Sign in to place hold')}
        </button>
      )}
      {showHoldModal && createPortal(
        // Portal out of the card: the card container applies a `transform` on
        // hover, which would make it the containing block for the modal's
        // `position: fixed` backdrop (squashing the dialog into the card).
        // The card is no longer an anchor, so clicks inside the modal cannot
        // trigger a navigation — no stopPropagation needed.
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
