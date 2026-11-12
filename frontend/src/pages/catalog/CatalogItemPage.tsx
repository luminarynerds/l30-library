/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent } from 'react'
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, AlertTriangle, Keyboard, BookMarked, Loader2, Volume2, VolumeX, CircleCheck, BookOpen, Star, ChevronDown, Library, Shield } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { fetchApi } from '@/api/fetchApi'

import { useReadingStatus } from '@/hooks/useReadingStatus'
import { useReviews } from '@/hooks/useReviews'
import type { ShelfStatus } from '@/api/domains/content/reading-status-api'

import { useItemDetail } from './hooks/useItemDetail'
import { useItemActions } from './hooks/useItemActions'
import { useRelatedFormats } from './hooks/useRelatedFormats'
import { useSeriesReadingOrder } from './hooks/useSeriesReadingOrder'
import { useItemRecommendations } from './hooks/useItemRecommendations'
import { useHoldPosition } from './hooks/useHoldPosition'
import { getStatusConfig, formatItemType, getReadingTimeEstimate, getComplexityRating, getPatronMoodLabels } from './utils/catalogItemUtils'
import { catalogSignInPath } from './utils/catalogHelpers'
import { MoodIcon } from './utils/catalogLandingConfig'
import { HoldQueueInfo } from './components/HoldQueueInfo'
import { ItemHeader } from './components/ItemHeader'
import { FormatTabs } from './components/FormatTabs'
import { ItemActions } from './components/ItemActions'
import { ItemReviews } from './components/ItemReviews'
import { PlaceHoldModal } from './components/PlaceHoldModal'
import { WayfindingModal } from './components/WayfindingModal'
import { BranchAvailability } from './components/BranchAvailability'
import StreamingAvailability from '@/components/StreamingAvailability'
import { t } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useJourneyTracker } from '@/hooks/useJourneyTracker'
import { useRecentlyViewed } from './hooks/useRecentlyViewed'
import { searchCatalog } from '@/api'
import type { CatalogItem } from '@/api'
import { RelatedItems } from './components/RelatedItems'
import { SeriesReadingOrder } from './components/SeriesReadingOrder'
import { ReadAlikes } from './components/ReadAlikes'
import { ReadingTimeline } from './components/ReadingTimeline'
import { NotifyWhenAvailable } from './components/NotifyWhenAvailable'
import { IndieEbookAvailability } from './components/IndieEbookAvailability'
import { ShelfNotes } from './components/ShelfNotes'
import { useChallengeNotice } from './hooks/useChallengeNotice'
import PageContainer from '@/components/layout/PageContainer'

// Text-to-Speech utilities
function speakText(text: string, onEnd?: () => void): void {
  if (!('speechSynthesis' in window)) return

  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.rate = 0.9
  utterance.pitch = 1
  if (onEnd) utterance.onend = onEnd
  window.speechSynthesis.speak(utterance)
}

function stopSpeaking(): void {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
}

// eslint-disable-next-line complexity
export default function CatalogItemPage(): React.ReactElement {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const canGoBack = location.state?.fromCatalog === true
  const { user, token } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const {
    simplifiedView,
    quietMode,
    noFOMO,
    reduceMotion,
    showImages,
    announceToScreenReader,
  } = useUnifiedAccessibility()

  // Item loading
  const { item, isLoading, error, refetch } = useItemDetail(id ? Number(id) : undefined)
  usePageTitle(item?.title ?? t('catalogItem.loading', 'Item details'))
  const { trackStage } = useJourneyTracker({ journeyType: "search_to_hold" })
  const { add: addRecentlyViewed } = useRecentlyViewed()

  // Track item_selected when item data loads, and remember the visit locally
  // so the catalog landing strip can surface "Pick up where you left off".
  useEffect(() => {
    if (item) {
      trackStage("item_selected")
      addRecentlyViewed(item.id)
    }
  }, [item?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Item actions (favorites, lists, holds)
  const itemActions = useItemActions(token, item)

  // Deeplink: /catalog/{id}?action=hold opens the place-hold modal once the
  // item has loaded. Used by Discover's primary-action button so the card
  // doesn't have to duplicate the modal's branch/pickup logic.
  useEffect(() => {
    if (!item) return
    // Auth guard: PlaceHoldModal needs a token, and the sign-in-and-return
    // flow lands logged-out users on this URL before they authenticate.
    if (!user || !token) return
    const params = new URLSearchParams(location.search)
    if (params.get('action') === 'hold') {
      itemActions.setShowHoldModal(true)
      // Consume the param so later re-runs (e.g. token refresh giving `token`
      // a new identity) don't re-open the modal unprompted.
      params.delete('action')
      navigate({ search: params.toString() }, { replace: true })
    }
  }, [item?.id, location.search, user, token]) // eslint-disable-line react-hooks/exhaustive-deps

  // Related formats
  const { formats } = useRelatedFormats(item)
  const { items: readAlikes } = useItemRecommendations(item?.id)
  // Series reading-order context (only fetches when item has a parsed position)
  const { series: seriesReadingOrder } = useSeriesReadingOrder(item)

  // Hold position
  const holdPosition = useHoldPosition(item?.id, token)

  // Reading status
  const readingStatus = useReadingStatus(item?.id)

  // Reviews & ratings
  const reviews = useReviews(item?.id)
  // Challenge/ban notice
  const { hasChallengeOrBan } = useChallengeNotice(item?.id, isFeatureEnabled('banned_books_tracking_enabled'))

  // Status history
  const [stateHistory, setStateHistory] = useState<Array<{
    id: number
    old_status: string | null
    new_status: string
    reason: string
    source_type: string
    created_at: string | null
    actor_name?: string
  }>>([])

  useEffect(() => {
    if (!item?.id) {
      setStateHistory([])
      return
    }
    let cancelled = false
    fetchApi(`/catalog/items/${item.id}/state-history`)
      .then(data => { if (!cancelled) setStateHistory(data) })
      .catch(() => { if (!cancelled) setStateHistory([]) })
    return () => { cancelled = true }
  }, [item?.id, token])

  // Related items for withdrawn/restricted items
  const [relatedItems, setRelatedItems] = useState<CatalogItem[]>([])
  const isWithdrawnOrRestricted = item?.status === 'withdrawn' || item?.status === 'restricted'

  useEffect(() => {
    if (!item || !isWithdrawnOrRestricted) {
      setRelatedItems([])
      return
    }
    const subjectTerms = item.subjects?.split(',').map(s => s.trim()).filter(Boolean) ?? []
    const query = subjectTerms.length > 0 ? subjectTerms.slice(0, 3).join(' ') : item.author ?? item.title
    searchCatalog({ query, status: 'available', per_page: 6 })
      .then(result => {
        setRelatedItems(result.items.filter(r => r.id !== item.id).slice(0, 6))
      })
      .catch(() => setRelatedItems([]))
  }, [item?.id, item?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  // Text-to-speech state
  const [isSpeaking, setIsSpeaking] = useState(false)

  // Wayfinding modal
  const [showWayfinding, setShowWayfinding] = useState(false)

  // Shelf dropdown state
  const [showShelfDropdown, setShowShelfDropdown] = useState(false)

  // Star rating hover state
  const [hoverRating, setHoverRating] = useState(0)

  // Sticky action bar
  const [showStickyBar, setShowStickyBar] = useState(false)

  // Dropdown and accessibility refs
  const dropdownRef = useRef<HTMLDivElement>(null)
  const shelfDropdownRef = useRef<HTMLDivElement>(null)
  const formatTabsRef = useRef<HTMLDivElement>(null)
  const addToListButtonRef = useRef<HTMLButtonElement>(null)

  const closeListDropdown = useCallback((restoreFocus: boolean): void => {
    itemActions.setShowListDropdown(false)
    if (restoreFocus) {
      window.setTimeout(() => addToListButtonRef.current?.focus(), 0)
    }
  }, [itemActions])

  // Close dropdown on outside click. The list menu portals to document.body
  // to escape the main card's overflow-hidden, so dropdownRef no longer
  // contains it - hence the explicit lookup by menu id.
  useEffect(() => {
    function handleClickOutside(event: MouseEvent): void {
      const target = event.target as Node
      const inTrigger = dropdownRef.current?.contains(target) ?? false
      const inMenu = document.getElementById('add-to-list-menu')?.contains(target) ?? false
      if (!inTrigger && !inMenu) {
        closeListDropdown(false)
      }
    }
    if (itemActions.showListDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [itemActions.showListDropdown, closeListDropdown])

  // Close shelf dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent): void {
      if (shelfDropdownRef.current && !shelfDropdownRef.current.contains(event.target as Node)) {
        setShowShelfDropdown(false)
      }
    }
    if (showShelfDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showShelfDropdown])

  // Sticky action bar - show when format tabs scroll out of view
  useEffect(() => {
    if (!formatTabsRef.current) return
    const observer = new IntersectionObserver(
      ([entry]) => setShowStickyBar(!entry!.isIntersecting),
      { threshold: 0 }
    )
    observer.observe(formatTabsRef.current)
    return () => observer.disconnect()
  }, [item])

  useEffect(() => {
    if (!itemActions.showListDropdown) return
    // The menu is portaled out of dropdownRef's subtree; look it up by id.
    const firstItem = document.getElementById('add-to-list-menu')
      ?.querySelector<HTMLElement>('[data-list-item]')
    firstItem?.focus()
  }, [itemActions.showListDropdown])

  // Text-to-speech handler
  const handleSpeak = useCallback((): void => {
    if (!item) return

    if (isSpeaking) {
      stopSpeaking()
      setIsSpeaking(false)
      return
    }

    const statusConfig = getStatusConfig(item.status)
    const readingTime = getReadingTimeEstimate(item.page_count, item.item_type)
    const complexity = getComplexityRating(item.page_count, item.item_type)

    const textToSpeak = [
      item.title,
      item.author ? `by ${item.author}` : '',
      formatItemType(item.item_type),
      statusConfig.label,
      statusConfig.description,
      readingTime || '',
      complexity ? complexity.description : '',
      item.description || '',
    ].filter(Boolean).join('. ')

    setIsSpeaking(true)
    speakText(textToSpeak, () => setIsSpeaking(false))
  }, [item, isSpeaking])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      switch (e.key) {
        case 'Escape':
          stopSpeaking()
          setIsSpeaking(false)
          closeListDropdown(true)
          setShowShelfDropdown(false)
          break
        case 'R':
          // Read-aloud shortcut is now Shift+R, not bare ``r``. A
          // single-letter shortcut on a content page traps screen-reader
          // and switch-control users who need to type a literal "r" --
          // exactly the WCAG 2.1.4 (Character Key Shortcuts) trap that
          // HeaderSearch removed from its bare "/" shortcut. The input/
          // textarea guard above doesn't cover contenteditable or speech-
          // input dictation, so a modifier is the safer gate.
          if (e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey && item) {
            e.preventDefault()
            handleSpeak()
          }
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [item, handleSpeak, closeListDropdown])

  // Announce page load to screen reader
  useEffect(() => {
    if (item) {
      announceToScreenReader(`Viewing ${item.title}${item.author ? ` by ${item.author}` : ''}`)
    }
  }, [item, announceToScreenReader])

  // Handle dropdown keyboard navigation
  const handleListMenuKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>): void => {
    if (event.key === 'Escape') {
      event.preventDefault()
      closeListDropdown(true)
      return
    }

    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return

    const items = Array.from(
      // The menu is portaled out of dropdownRef's subtree; look it up by id.
      document.getElementById('add-to-list-menu')
        ?.querySelectorAll<HTMLButtonElement>('[data-list-item]') ?? []
    )
    if (!items.length) return

    const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement)
    let nextIndex = currentIndex

    switch (event.key) {
      case 'ArrowDown':
        nextIndex = currentIndex === -1 ? 0 : Math.min(currentIndex + 1, items.length - 1)
        break
      case 'ArrowUp':
        nextIndex = currentIndex === -1 ? items.length - 1 : Math.max(currentIndex - 1, 0)
        break
      case 'Home':
        nextIndex = 0
        break
      case 'End':
        nextIndex = items.length - 1
        break
      default:
        break
    }

    if (nextIndex !== currentIndex) {
      event.preventDefault()
      items[nextIndex]?.focus()
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]" role="status" aria-label={t('aria.catalogItem.loadingItemDetails')}>
        <div className="flex flex-col items-center gap-3"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" /><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Loading item details...</p></div>
      </div>
    )
  }

  if (error || !item) {
    return (
      <div className="text-center py-12">
        <BookOpen aria-hidden="true" className="w-16 h-16 mx-auto mb-4 text-lsc-dark/70 dark:text-lsc-cream/40" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          We couldn't find this item
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          It may have moved — try searching the catalog.
        </p>
        <Link
          to="/catalog"
          className="inline-flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline"
        >
          <ArrowLeft aria-hidden="true" className="w-4 h-4" />
          Back to Catalog
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <div className="flex items-center justify-between">
        {canGoBack ? (
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline"
          >
            <ArrowLeft aria-hidden="true" className="w-4 h-4" />
            Back to results
          </button>
        ) : (
          <Link
            to="/catalog"
            className="inline-flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline"
          >
            <ArrowLeft aria-hidden="true" className="w-4 h-4" />
            Back to Catalog
          </Link>
        )}

        {/* Keyboard hints */}
        {!quietMode && ['book', 'ebook', 'audiobook', 'magazine'].includes(item.item_type) && (
        <div className="hidden sm:flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <Keyboard className="w-3 h-3" aria-hidden="true" />
          <span>Press <kbd className="px-1 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded">r</kbd> to read aloud</span>
        </div>
        )}
      </div>

      {/* Main content card */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden border border-lsc-border/60 dark:border-earth-700/80">
        {/* Header section */}
        <div className="p-6 md:p-8">
          <ItemHeader
            item={item}
            simplifiedView={simplifiedView}
            showImages={showImages}
          />

          {/* Also available as */}
          {formats.filter(f => !f.isCurrent).length > 0 && (
            <div className="flex items-center gap-2 mt-3">
              <span className="text-xs font-medium text-earth-600 dark:text-earth-400">Also available as:</span>
              {formats.filter(f => !f.isCurrent).map(alt => (
                <Link
                  key={alt.id}
                  to={`/catalog/${alt.id}`}
                  state={{ fromCatalog: true }}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-lsc-cream dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 hover:border-lsc-rose transition-colors"
                >
                  {alt.label}
                  {alt.status === 'available' && <CircleCheck className="w-3 h-3 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />}
                </Link>
              ))}
            </div>
          )}

          {/* Promoted read aloud button — text formats only */}
          {['book', 'ebook', 'audiobook', 'magazine'].includes(item.item_type) && (
          <div className="mt-4">
            <button
              onClick={handleSpeak}
              className={clsx(
                'inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors',
                'border border-lsc-border dark:border-earth-700 hover:border-lsc-rose',
                isSpeaking
                  ? 'bg-lsc-rose/10 text-lsc-rose border-lsc-rose'
                  : 'text-lsc-dark dark:text-lsc-cream'
              )}
              aria-label={isSpeaking ? 'Stop reading aloud' : 'Read this page aloud'}
            >
              {isSpeaking ? <VolumeX className="w-4 h-4" aria-hidden="true" /> : <Volume2 className="w-4 h-4" aria-hidden="true" />}
              {isSpeaking ? 'Stop' : 'Read aloud'}
            </button>
          </div>
          )}
        </div>

        {/* Challenged/banned title notice */}
        {hasChallengeOrBan && (
          <div className="mx-6 md:mx-8 mb-4 px-4 py-3 rounded-lg bg-category-50 dark:bg-category-950/30 border border-category-200 dark:border-category-800/50">
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-category-500 dark:text-category-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-category-800 dark:text-category-200">
                  {t('catalogItem.challengeNotice.message')}
                  {' '}
                  <Link
                    to="/intellectual-freedom"
                    className="font-medium underline underline-offset-2 hover:text-category-600 dark:hover:text-category-300 transition-colors"
                  >
                    {t('catalogItem.challengeNotice.learnMore')}
                  </Link>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Status history - collapsed, only if entries exist */}
        {stateHistory.length > 0 && (
          <div className="px-6 md:px-8 pb-4">
            <details className="group">
              <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream select-none">
                <Shield className="w-4 h-4 text-category-500" aria-hidden="true" />
                Status History
                <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <ul className="mt-3 space-y-2 pl-6">
                {stateHistory.map((event) => (
                  <li key={event.id} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex flex-col gap-0.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {event.created_at ? new Date(event.created_at).toLocaleDateString() : 'Unknown date'}
                      </span>
                      <span>
                        {event.old_status ? (
                          <><span className="font-medium">{event.old_status.replace(/_/g, ' ')}</span>{' → '}</>
                        ) : null}
                        <span className="font-medium">{event.new_status.replace(/_/g, ' ')}</span>
                      </span>
                      {event.actor_name && (
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">by {event.actor_name}</span>
                      )}
                    </div>
                    {event.reason && (
                      <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 leading-relaxed">{event.reason}</p>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          </div>
        )}

        {/* Content notes - collapsed by default, only if present */}
        {item.content_notes && (
          <div className="px-6 md:px-8 pb-4">
            <details className="group">
              <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream select-none">
                <AlertTriangle className="w-4 h-4 text-status-warning-500" aria-hidden="true" />
                Content notes
                <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <div className="mt-2 pl-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                {item.content_notes}
              </div>
            </details>
          </div>
        )}

        {/* Divider */}
        <div className="border-t border-lsc-border dark:border-earth-700" />

        {/* Format tabs + availability */}
        <div className="p-6 md:p-8" ref={formatTabsRef}>
          <FormatTabs
            currentItem={item}
            formats={formats}
            holdPosition={holdPosition}
            onPlaceHold={() => itemActions.setShowHoldModal(true)}
            onOpenWayfinding={() => setShowWayfinding(true)}
            reduceMotion={reduceMotion}
            isLoggedIn={!!user && !!token}
          />
        </div>


        {/* Branch availability */}
        <div className="border-t border-lsc-border dark:border-earth-700" />
        <div className="p-6 md:p-8">
          <BranchAvailability itemId={item.id} />
          <NotifyWhenAvailable itemId={item.id} itemStatus={item.status} />
          <HoldQueueInfo itemId={item.id} status={item.status} />
          <IndieEbookAvailability item={item} noFOMO={noFOMO} />
          <StreamingAvailability catalogItemId={item.id} catalogItemTitle={item.title} />
        </div>
        {/* Reading Status + Rating */}
        {user && token && item && (
          <>
            <div className="border-t border-lsc-border dark:border-earth-700" />
            <div className="p-6 md:p-8">
              <div className="flex flex-wrap items-center gap-4">
                {/* Shelf Status Dropdown */}
                <div className="relative z-30" ref={shelfDropdownRef}>
                  <button
                    onClick={() => setShowShelfDropdown(!showShelfDropdown)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:border-lsc-rose transition-colors"
                    aria-haspopup="listbox"
                    aria-expanded={showShelfDropdown}
                    aria-label={readingStatus.currentStatus ? `Current shelf: ${readingStatus.SHELF_LABELS[readingStatus.currentStatus.status]}. Change shelf` : 'Add to shelf'}
                  >
                    <BookOpen className="w-4 h-4" aria-hidden="true" />
                    {readingStatus.currentStatus
                      ? readingStatus.SHELF_LABELS[readingStatus.currentStatus.status]
                      : 'Add to Shelf'}
                    <ChevronDown className="w-3 h-3" aria-hidden="true" />
                  </button>
                  {showShelfDropdown && (
                    <div
                      className="absolute top-full mt-2 left-0 w-56 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg z-30 py-1"
                      role="listbox"
                      aria-label={t('aria.catalogItem.selectReadingShelf')}
                    >
                      {(Object.entries(readingStatus.SHELF_LABELS) as [ShelfStatus, string][]).map(([value, label]) => (
                        <button
                          key={value}
                          role="option"
                          aria-selected={readingStatus.currentStatus?.status === value}
                          className={clsx(
                            'w-full text-left px-4 py-2 text-sm hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors',
                            readingStatus.currentStatus?.status === value
                              ? 'text-lsc-rose font-semibold'
                              : 'text-lsc-dark dark:text-lsc-cream'
                          )}
                          onClick={() => {
                            readingStatus.handleSetStatus(value)
                            setShowShelfDropdown(false)
                          }}
                          disabled={readingStatus.isUpdating}
                        >
                          {label}
                        </button>
                      ))}
                      {readingStatus.currentStatus && (
                        <>
                          <div className="border-t border-lsc-border dark:border-earth-700 my-1" />
                          <button
                            className="w-full text-left px-4 py-2 text-sm text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors"
                            onClick={() => {
                              readingStatus.handleRemove()
                              setShowShelfDropdown(false)
                            }}
                            disabled={readingStatus.isUpdating}
                          >
                            Remove from shelf
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Star Rating */}
                <div className={clsx("flex items-center gap-2 transition-opacity", reviews.isSubmitting && "opacity-50")}>
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Rate this item:</span>
                  <div
                    className="flex items-center gap-0.5"
                    role="radiogroup"
                    aria-label={t('aria.catalogItem.yourRating')}
                    onMouseLeave={() => setHoverRating(0)}
                  >
                    {[1, 2, 3, 4, 5].map((star) => {
                      const isFilled = hoverRating > 0
                        ? star <= hoverRating
                        : star <= (reviews.userRating ?? 0)
                      return (
                        <button
                          key={star}
                          role="radio"
                          aria-checked={reviews.userRating === star}
                          aria-label={`Rate ${star} star${star !== 1 ? 's' : ''}`}
                          className="p-0.5 transition-transform hover:scale-125 disabled:opacity-50"
                          onClick={() => reviews.handleRate(star)}
                          onMouseEnter={() => setHoverRating(star)}
                          disabled={reviews.isSubmitting}
                        >
                          <Star
                            className={clsx(
                              'w-6 h-6 transition-colors',
                              isFilled
                                ? 'text-lsc-rose fill-lsc-rose'
                                : 'text-earth-500 dark:text-earth-400 hover:text-lsc-rose/40'
                            )}
                            aria-hidden="true"
                          />
                        </button>
                      )
                    })}
                  </div>
                  {reviews.userRating && (
                    <button
                      className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-status-danger-500 dark:hover:text-status-danger-400"
                      onClick={reviews.handleDeleteRating}
                      disabled={reviews.isSubmitting}
                      aria-label={t('aria.catalogItem.removeYourRating')}
                    >
                      Clear
                    </button>
                  )}
                  {reviews.isSubmitting && <span className="text-xs text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-pulse">Saving...</span>}
                  {reviews.reviewsLoadError && !reviews.isSubmitting && (
                    <span className="text-xs text-status-danger-600 dark:text-status-danger-400" role="status">
                      Couldn&apos;t load your rating. Refresh to retry.
                    </span>
                  )}
                </div>

                {/* Aggregate Rating */}
                {reviews.aggregate.rating_count > 0 && (
                  <div className="flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Star className="w-4 h-4 text-lsc-rose fill-lsc-rose" aria-hidden="true" />
                    <span>{reviews.aggregate.average_rating}</span>
                    {!noFOMO && <span>({reviews.aggregate.rating_count} rating{reviews.aggregate.rating_count !== 1 ? 's' : ''})</span>}
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Divider */}
        <div className="border-t border-lsc-border dark:border-earth-700" />

                {/* Personal reading activity timeline */}
        {user && item && <ReadingTimeline itemId={item.id} />}
        {item && <ShelfNotes itemId={item.id} />}

        {/* Secondary actions (favorite, share, lists) */}
        <div className="p-6 md:p-8">
          <ItemActions
            item={item}
            isFavorited={itemActions.isFavorited}
            isLoadingFavorite={itemActions.isLoadingFavorite}
            onToggleFavorite={itemActions.handleToggleFavorite}
            lists={itemActions.lists}
            listsWithItem={itemActions.listsWithItem}
            onAddToList={itemActions.handleAddToList}
            onCreateNewList={itemActions.handleCreateNewList}
            onCreateListSubmit={itemActions.handleCreateListSubmit}
            onCancelCreateList={itemActions.handleCancelCreateList}
            showListDropdown={itemActions.showListDropdown}
            setShowListDropdown={itemActions.setShowListDropdown}
            showCreateListForm={itemActions.showCreateListForm}
            setShowCreateListForm={itemActions.setShowCreateListForm}
            newListName={itemActions.newListName}
            setNewListName={itemActions.setNewListName}
            creatingList={itemActions.creatingList}
            user={user}
            token={token}
            reduceMotion={reduceMotion}
            onListMenuKeyDown={handleListMenuKeyDown}
            dropdownRef={dropdownRef}
            addToListButtonRef={addToListButtonRef}
          />
        </div>
      </div>


      {/* Interlibrary loan prompt for unavailable items */}
      {isFeatureEnabled('ill_enabled') && ['withdrawn', 'lost', 'missing', 'damaged_withdrawn'].includes(item.status) && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 md:p-8 border border-lsc-border/60 dark:border-earth-700/80">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
              <Library className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
                {t('catalogItem.illPrompt.heading')}
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 leading-relaxed">
                {t('catalogItem.illPrompt.body')}
              </p>
              <Link
                to={`/interlibrary-loan?title=${encodeURIComponent(item.title)}${item.author ? `&author=${encodeURIComponent(item.author)}` : ''}${item.isbn ? `&isbn=${encodeURIComponent(item.isbn)}` : ''}`}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
              >
                <Library className="w-4 h-4" aria-hidden="true" />
                {t('catalogItem.illPrompt.requestButton')}
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Related items for withdrawn/restricted items */}
      {isWithdrawnOrRestricted && relatedItems.length > 0 && (
        <div className="space-y-4">
          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4 md:p-6">
            <p className="text-sm text-status-warning-800 dark:text-status-warning-200">
              {item.status === 'withdrawn'
                ? t('catalog.relatedItems.withdrawnMessage')
                : t('catalog.relatedItems.restrictedMessage')}
            </p>
          </div>
          <RelatedItems items={relatedItems} />
        </div>
      )}

      {/* Series reading-order context: position + prev/next adjacent held titles.
          Renders nothing unless the item has a parsed numeric series_position. */}
      <SeriesReadingOrder item={item} series={seriesReadingOrder} />

      {/* Read-alikes: curated + algorithmic recommendations for this item */}
      {!quietMode && <ReadAlikes items={readAlikes} />}

      {/* Similar items section */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 md:p-8">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1 flex items-center gap-2">
          <BookMarked aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          You May Also Like
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-4">Available items are highlighted</p>
        <ItemReviews item={item} />
      </div>

      {/* Mood browse links */}
      {!quietMode && item && (() => {
        const moodLabels = getPatronMoodLabels(item.id, item.subjects)
        if (moodLabels.length === 0) return null
        return (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">More like this:</span>
            {moodLabels.map((m) => (
              <Link
                key={m.slug}
                to={`/catalog/mood/${m.slug}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-full border border-category-200 dark:border-category-800 bg-category-50 dark:bg-category-900/20 text-category-700 dark:text-category-300 hover:border-lsc-rose/50 hover:text-lsc-rose transition-colors"
              >
                <MoodIcon name={
                  m.slug === 'quiet' ? 'CloudSun' :
                  m.slug === 'funny' ? 'Laugh' :
                  m.slug === 'hopeful' ? 'Heart' :
                  m.slug === 'gripping' ? 'Flame' :
                  m.slug === 'surprising' ? 'Sparkles' : 'HandHeart'
                } className="w-3.5 h-3.5" />
                {m.label}
              </Link>
            ))}
          </div>
        )
      })()}

      {/* Staff Reviews */}
      {reviews.staffReviews.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 md:p-8">
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Star aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            Staff Reviews
          </h2>
          <div className="space-y-4">
            {reviews.staffReviews.map((review) => (
              <div key={review.id} className="border-b border-lsc-border dark:border-earth-700 pb-4 last:border-0 last:pb-0">
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex items-center gap-0.5">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star
                        key={s}
                        className={clsx(
                          'w-4 h-4',
                          (review.rating ?? 0) >= s
                            ? 'text-lsc-rose fill-lsc-rose'
                            : 'text-earth-300 dark:text-earth-600'
                        )}
                        aria-hidden="true"
                      />
                    ))}
                  </div>
                  {review.reviewer_name && (
                    <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                      {review.reviewer_name}
                    </span>
                  )}
                </div>
                {review.title && (
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{review.title}</h3>
                )}
                {review.body && (
                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-1">{review.body}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hold modal */}
      {itemActions.showHoldModal && (
        <PlaceHoldModal
          item={item}
          onClose={() => itemActions.setShowHoldModal(false)}
          onSuccess={() => refetch()}
        />
      )}

      {/* Wayfinding modal */}
      <WayfindingModal
        isOpen={showWayfinding}
        onClose={() => setShowWayfinding(false)}
        item={item}
        reduceMotion={reduceMotion}
      />

      {/* Sticky action bar — mobile only */}
      {showStickyBar && item && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-lsc-white/95 dark:bg-earth-800/95 backdrop-blur-sm border-t border-lsc-border dark:border-earth-700 shadow-lg md:hidden">
          <PageContainer className="py-3 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <span className="font-medium text-lsc-dark dark:text-lsc-cream truncate text-sm" title={item.title}>
                {item.title}
              </span>
              <span className={clsx(
                'text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0',
                item.status === 'available'
                  ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200'
                  : 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200'
              )}>
                {item.status === 'available' ? 'Available' : item.status.replace('_', ' ')}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {item.item_type === 'ebook' ? (
                <Link
                  to="/indie"
                  className="px-4 py-2 bg-lsc-rose text-white rounded-xl text-sm font-medium hover:bg-lsc-rose/90 transition-colors"
                >
                  {t('catalog.item.browseEbooksToBorrow', 'Browse eBooks to borrow')}
                </Link>
              ) : (
                <button
                  onClick={() => {
                    if (!user || !token) {
                      const { pathname, state } = catalogSignInPath(item.id, { action: 'hold', title: item.title })
                      navigate(pathname, { state })
                      return
                    }
                    itemActions.setShowHoldModal(true)
                  }}
                  className="px-4 py-2 bg-lsc-rose text-white rounded-xl text-sm font-medium hover:bg-lsc-rose/90 transition-colors"
                >
                  {!user || !token
                    ? t('catalog.item.signInToPlaceHold', 'Sign in to place hold')
                    : item.status === 'available' ? 'Place on Hold' : 'Join Waitlist'}
                </button>
              )}
              <button
                onClick={() => formatTabsRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' })}
                className="px-3 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
                aria-label={t('aria.catalogItem.scrollToItemDetails')}
              >
                View details
              </button>
            </div>
          </PageContainer>
        </div>
      )}
    </div>
  )
}
