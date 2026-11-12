/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import * as Sentry from "@/lib/sentry-lazy"
import toast from 'react-hot-toast'
import {
  Loader2,
  BookOpen,
  Phone,
  MapPin,
  ExternalLink,
  Printer,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Heart,
  Brain,
  Apple,
  Home,
  Scale,
  Baby,
  Copy,
  Check,
  ClipboardList,
} from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import {
  getResourceGuide,
  verifyResourceGuideItem,
  type ResourceGuideSection,
  type ResourceGuideItem,
} from '@/api/parent-onboarding-api'
import { useTranslation, useLanguage } from '@/i18n'
import { useState, useMemo, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AdminShell } from '../components/shells/AdminShell'
import { HandoutToolbar } from './parent-resources/HandoutToolbar'
import { LanguageChip } from './parent-resources/LanguageChip'
import { LanguageFilter } from './parent-resources/LanguageFilter'
import { HandoutCoverSheet } from './parent-resources/HandoutCoverSheet'
import {
  FlagOutOfDateModal,
  VerifiedBadge,
  useStaffPredicate,
} from './parent-resources/Verification'
import './parent-resources/print.css'

/** Frontend-side fallback for parent_resource_stale_after_months. The
 * authoritative value lives in backend config and is reflected in the
 * `item.stale` boolean; this fallback is only used to render the
 * "(over N months ago)" suffix when item.stale=true. */
const FALLBACK_STALE_MONTHS = 6

const SECTION_ICONS: Record<string, React.ReactNode> = {
  health: <Heart className="w-5 h-5 text-status-danger-500" />,
  education: <BookOpen className="w-5 h-5 text-status-info-500" />,
  mental_health: <Brain className="w-5 h-5 text-status-info-500" />,
  nutrition: <Apple className="w-5 h-5 text-status-success-500" />,
  housing: <Home className="w-5 h-5 text-status-warning-500" />,
  legal: <Scale className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />,
  childcare: <Baby className="w-5 h-5 text-lsc-rose" />,
}

const KNOWN_SECTION_ICONS = new Set(Object.keys(SECTION_ICONS))

function formatPhone(raw: string): string {
  const digits = raw.replace(/\D/g, '')
  if (digits.length === 10) {
    return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`
  }
  return raw
}

function renderSectionIcon(icon: string | null | undefined): React.ReactNode {
  const key = icon ?? ''
  if (key && !KNOWN_SECTION_ICONS.has(key)) {
    // Surface taxonomy drift: backend introduces a section.icon value we
    // do not have a glyph for. Logged once per render path; the UI still
    // falls back to the generic BookOpen so the page never breaks.
    Sentry.addBreadcrumb({
      category: 'i18n',
      level: 'info',
      message: 'ParentResourcesPage: unknown section.icon',
      data: { icon: key },
    })
  }
  return SECTION_ICONS[key] ?? <BookOpen className="w-5 h-5 text-lsc-rose" />
}

function AddressRow({
  address,
  copyLabel,
  copiedLabel,
  openInMapsLabel,
}: {
  address: string
  copyLabel: string
  copiedLabel: string
  openInMapsLabel: string
}) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(address)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      Sentry.captureException(err)
    }
  }

  return (
    <span className="flex items-center gap-1">
      <a
        href={`https://maps.google.com/?q=${encodeURIComponent(address)}`}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={openInMapsLabel}
        className="flex items-center gap-1 hover:text-lsc-rose transition-colors"
      >
        <MapPin className="w-3.5 h-3.5" />
        {address}
      </a>
      <button
        type="button"
        onClick={handleCopy}
        aria-label={copied ? copiedLabel : copyLabel}
        className="ml-1 inline-flex items-center justify-center p-1 rounded hover:text-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 transition-colors print:hidden"
      >
        {copied ? (
          <Check className="w-3.5 h-3.5" aria-hidden="true" />
        ) : (
          <Copy className="w-3.5 h-3.5" aria-hidden="true" />
        )}
      </button>
    </span>
  )
}

interface HandoutSelection {
  // For each section id: a Set of selected item ids. A section with an empty
  // Set is "selected, no items" (rendered as section heading only on print).
  // A section absent from the map is fully unselected.
  bySectionId: Map<number, Set<number>>
}

function buildDefaultSelection(sections: ResourceGuideSection[]): HandoutSelection {
  const bySectionId = new Map<number, Set<number>>()
  for (const section of sections) {
    bySectionId.set(section.id, new Set(section.items.map((it) => it.id)))
  }
  return { bySectionId }
}

export default function ParentResourcesPage() {
  const { t } = useTranslation()
  const { language: uiLanguage } = useLanguage()
  const queryClient = useQueryClient()
  const isStaff = useStaffPredicate()
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set())
  const [searchParams, setSearchParams] = useSearchParams()
  const handoutMode = searchParams.get('handout') === 'building'

  // Multilingual filter -- the URL is the source of truth so back-button
  // restores and copy-pasted links land filtered. Empty string = "All
  // languages" (see spec section "Page-level filter").
  const langFilter = (searchParams.get('lang') ?? '').toLowerCase()

  function setLangFilter(code: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (code === '') {
        next.delete('lang')
      } else {
        next.set('lang', code)
      }
      return next
    })
  }

  const [largeType, setLargeType] = useState(false)
  const [qrCodes, setQrCodes] = useState(false)
  const [coverSheet, setCoverSheet] = useState(false)
  const [selection, setSelection] = useState<HandoutSelection>({
    bySectionId: new Map(),
  })

  // Verification-trail state. Held at page scope so the modal can return
  // focus to the trigger button via DOM-level focus management once the
  // dialog unmounts.
  const [flagModalItem, setFlagModalItem] = useState<ResourceGuideItem | null>(null)
  const [verifyBusyItemId, setVerifyBusyItemId] = useState<number | null>(null)

  const {
    data: sections,
    isLoading,
    error,
  } = useQuery<ResourceGuideSection[]>({
    // Cache key includes the active language so each filter state has
    // its own response (backend substitutes title/description per lang).
    queryKey: ['parent-onboarding-resource-guide', langFilter || 'source'],
    queryFn: () => getResourceGuide({ lang: langFilter || undefined }),
  })

  async function handleVerify(item: ResourceGuideItem) {
    if (verifyBusyItemId === item.id) return
    setVerifyBusyItemId(item.id)
    try {
      await verifyResourceGuideItem(item.id)
      // Refetch the guide -- the backend's response is the freshly-verified
      // single item, but we depend on the section list query downstream so
      // an invalidate keeps everything in sync. Optimistic-update micro-opt
      // skipped because verify happens rarely (~once per item per 6 months).
      await queryClient.invalidateQueries({
        queryKey: ['parent-onboarding-resource-guide'],
      })
    } catch (err) {
      Sentry.captureException(err)
      toast.error(t('parentResources.actions.verifyError'))
    } finally {
      setVerifyBusyItemId(null)
    }
  }

  function handleFlagSubmitted() {
    setFlagModalItem(null)
    toast.success(t('parentResources.flagModal.successToast'))
    queryClient.invalidateQueries({
      queryKey: ['parent-onboarding-resource-guide'],
    })
  }

  // Seed selection when sections load OR when handout mode opens. Reseeding on
  // mode-open avoids stale selection from a prior builder session leaking
  // back; spec is explicit that "saved bundles deferred" and cancel clears.
  //
  // The set-state-in-effect lint rule wants to push derived state into render
  // or out into event handlers. Neither applies cleanly here: the selection
  // shape depends on async-fetched `sections`, and we ALSO need to expand
  // every section as a side effect on entering builder mode. Coupling these
  // two state writes in a single mount-time effect is intentional.
  useEffect(() => {
    if (handoutMode && sections && selection.bySectionId.size === 0) {
      setSelection(buildDefaultSelection(sections))
      setExpandedSections(new Set(sections.map((s) => s.id)))
    }
  }, [handoutMode, sections, selection.bySectionId.size])

  if (error) {
    Sentry.captureException(error)
  }

  function toggleSection(sectionId: number) {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(sectionId)) {
        next.delete(sectionId)
      } else {
        next.add(sectionId)
      }
      return next
    })
  }

  function expandAll() {
    if (sections) {
      setExpandedSections(new Set(sections.map((s) => s.id)))
    }
  }

  function enterHandoutMode() {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('handout', 'building')
      return next
    })
    // Selection seeded by the useEffect above once sections are available.
  }

  function exitHandoutMode() {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('handout')
      return next
    })
    setSelection({ bySectionId: new Map() })
    setLargeType(false)
    setQrCodes(false)
    setCoverSheet(false)
  }

  function isSectionFullySelected(section: ResourceGuideSection): boolean {
    const itemIds = selection.bySectionId.get(section.id)
    if (!itemIds || section.items.length === 0) return false
    if (itemIds.size !== section.items.length) return false
    return section.items.every((it) => itemIds.has(it.id))
  }

  function isSectionPartiallySelected(section: ResourceGuideSection): boolean {
    const itemIds = selection.bySectionId.get(section.id)
    if (!itemIds || itemIds.size === 0) return false
    return itemIds.size < section.items.length
  }

  function isItemSelected(sectionId: number, itemId: number): boolean {
    const itemIds = selection.bySectionId.get(sectionId)
    return itemIds?.has(itemId) ?? false
  }

  function toggleSectionSelection(section: ResourceGuideSection) {
    setSelection((prev) => {
      const next = new Map(prev.bySectionId)
      if (isSectionFullySelected(section)) {
        // Fully selected -> uncheck all items in section.
        next.set(section.id, new Set())
      } else {
        // Partially or fully unselected -> select all items in section.
        next.set(section.id, new Set(section.items.map((it) => it.id)))
      }
      return { bySectionId: next }
    })
  }

  function toggleItemSelection(sectionId: number, itemId: number) {
    setSelection((prev) => {
      const next = new Map(prev.bySectionId)
      const existing = new Set(next.get(sectionId) ?? new Set<number>())
      if (existing.has(itemId)) {
        existing.delete(itemId)
      } else {
        existing.add(itemId)
      }
      next.set(sectionId, existing)
      return { bySectionId: next }
    })
  }

  // Sections / items selection counts for the toolbar display.
  const { sectionsSelected, itemsSelected, itemsTotal } = useMemo(() => {
    if (!sections) {
      return { sectionsSelected: 0, itemsSelected: 0, itemsTotal: 0 }
    }
    let sectionsSelectedCount = 0
    let itemsSelectedCount = 0
    let itemsTotalCount = 0
    for (const section of sections) {
      itemsTotalCount += section.items.length
      const picked = selection.bySectionId.get(section.id)
      if (picked && picked.size > 0) {
        sectionsSelectedCount += 1
        itemsSelectedCount += picked.size
      }
    }
    return {
      sectionsSelected: sectionsSelectedCount,
      itemsSelected: itemsSelectedCount,
      itemsTotal: itemsTotalCount,
    }
  }, [sections, selection])

  // Multilingual: union of every code mentioned in any item's `languages`
  // array. This drives both the filter dropdown options and the visible
  // chip rows. De-duplicated lowercase codes; LanguageFilter sorts by
  // autonym before render.
  const availableLanguageCodes = useMemo(() => {
    if (!sections) return [] as string[]
    const seen = new Set<string>()
    for (const section of sections) {
      for (const item of section.items) {
        for (const code of item.languages ?? []) {
          if (code) seen.add(code.toLowerCase())
        }
      }
    }
    return Array.from(seen)
  }, [sections])

  // Counts for the filter status line. visibleCount is the number of
  // items whose `languages` includes the current filter; totalCount is
  // every item on the page (denominator stays stable as the filter
  // changes so the ratio reads sensibly).
  const { visibleItemCount, totalItemCount } = useMemo(() => {
    if (!sections) return { visibleItemCount: 0, totalItemCount: 0 }
    let total = 0
    let visible = 0
    for (const section of sections) {
      for (const item of section.items) {
        total += 1
        if (
          langFilter === '' ||
          (item.languages ?? []).some(
            (c) => c.toLowerCase() === langFilter,
          )
        ) {
          visible += 1
        }
      }
    }
    return { visibleItemCount: visible, totalItemCount: total }
  }, [sections, langFilter])

  // Default behavior: on first page load (no `lang` in URL), if any item
  // on the page carries a translation in the staff's UI language, set
  // the filter to that language so they immediately see the
  // localized variant. Otherwise leave it empty (show everything in
  // English) -- avoids the "empty filter trap" in untranslated
  // environments. Only runs when the URL has NO `lang` at all; staff
  // who explicitly cleared the filter back to "All" stay cleared.
  useEffect(() => {
    if (searchParams.has('lang')) return
    if (!sections || sections.length === 0) return
    const code = uiLanguage.toLowerCase()
    if (code === 'en') return // English is the source-of-truth language.
    const anyItemHasTranslation = sections.some((section) =>
      section.items.some(
        (item) =>
          item.translations && item.translations[code] !== undefined,
      ),
    )
    if (anyItemHasTranslation) {
      setLangFilter(code)
    }
    // Intentionally no exhaustive deps -- this is a one-time effect on
    // first sections-ready render. Re-running on lang changes would
    // fight the user's explicit "All languages" choice.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sections, uiLanguage])

  function handlePreviewPrint() {
    window.print()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (error || !sections) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-status-danger-500 mx-auto mb-2" />
          <p className="text-status-danger-700 dark:text-status-danger-300">{t('parentOnboarding.resources.loadFailed')}</p>
        </div>
      </div>
    )
  }

  return (
    <AdminShell title={t('parentOnboarding.resources.pageTitle')}>
    <div
      className="parent-resources-print-root max-w-4xl mx-auto p-6 space-y-6"
      data-large-type={largeType ? 'true' : 'false'}
      data-testid="parent-resources-print-root"
    >
      {/* Cover sheet renders before everything in print only; toggled via state. */}
      {handoutMode && coverSheet && <HandoutCoverSheet />}

      {/* Header */}
      <div className="text-center space-y-2 print:mb-8">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('parentOnboarding.resources.heading')}
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          {t('parentOnboarding.resources.intro')}
        </p>
        {!handoutMode && (
          <div className="flex items-center justify-center gap-3 print:hidden">
            <button
              onClick={expandAll}
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 transition-colors"
            >
              {t('parentOnboarding.resources.expandAll')}
            </button>
            <span className="text-lsc-dark/30 dark:text-lsc-cream/60">|</span>
            <button
              onClick={() => setExpandedSections(new Set())}
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 transition-colors"
            >
              {t('parentOnboarding.resources.collapseAll')}
            </button>
            <span className="text-lsc-dark/30 dark:text-lsc-cream/60">|</span>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
            >
              <Printer className="w-4 h-4" />
              {t('parentOnboarding.resources.print')}
            </button>
            <span className="text-lsc-dark/30 dark:text-lsc-cream/60">|</span>
            <button
              onClick={enterHandoutMode}
              className="flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
              data-testid="enter-handout-mode"
            >
              <ClipboardList className="w-4 h-4" />
              {t('parentResources.handout.button')}
            </button>
          </div>
        )}
      </div>

      {/* Builder toolbar */}
      {handoutMode && sections && (
        <HandoutToolbar
          sectionsSelected={sectionsSelected}
          sectionsTotal={sections.length}
          itemsSelected={itemsSelected}
          itemsTotal={itemsTotal}
          largeType={largeType}
          qrCodes={qrCodes}
          coverSheet={coverSheet}
          onToggleLargeType={() => setLargeType((v) => !v)}
          onToggleQrCodes={() => setQrCodes((v) => !v)}
          onToggleCoverSheet={() => setCoverSheet((v) => !v)}
          onCancel={exitHandoutMode}
          onPreviewPrint={handlePreviewPrint}
        />
      )}

      {/* Multilingual filter -- hidden in print + handout-build mode so
          the printed packet doesn't carry the staff control. */}
      {!handoutMode && availableLanguageCodes.length > 0 && (
        <div className="print:hidden" data-testid="language-filter-region">
          <LanguageFilter
            availableCodes={availableLanguageCodes}
            selected={langFilter}
            onSelect={setLangFilter}
            visibleCount={visibleItemCount}
            totalCount={totalItemCount}
          />
        </div>
      )}

      {/* Sections */}
      {sections.length === 0 ? (
        <div className="text-center py-12">
          <BookOpen className="w-12 h-12 text-lsc-dark/20 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/60">{t('parentOnboarding.resources.empty')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sections.map((section) => {
            const isExpanded = expandedSections.has(section.id)
            const panelId = `section-panel-${section.id}`
            const headingId = `section-heading-${section.id}`
            const sectionChecked = isSectionFullySelected(section)
            const sectionIndeterminate = isSectionPartiallySelected(section)
            // In print, we want only selected sections (with at least one item)
            // to render. Tailwind has no `print:hidden-if-empty` so we use a
            // data attribute + a `display: none` rule for unselected sections.
            const sectionHasAnyPicked =
              (selection.bySectionId.get(section.id)?.size ?? 0) > 0
            const hideInPrint = handoutMode && !sectionHasAnyPicked
            return (
              <div
                key={section.id}
                data-handout-section
                className={`bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden print:border-none print:shadow-none ${hideInPrint ? 'print:hidden' : ''}`}
              >
                <div className="flex items-center gap-2">
                  {handoutMode && (
                    <label className="pl-5 flex items-center print:hidden">
                      <input
                        type="checkbox"
                        checked={sectionChecked}
                        ref={(el) => {
                          if (el) el.indeterminate = sectionIndeterminate
                        }}
                        onChange={() => toggleSectionSelection(section)}
                        aria-checked={
                          sectionIndeterminate ? 'mixed' : sectionChecked
                        }
                        aria-label={t('parentResources.handout.checkbox.section', {
                          section: section.title,
                        })}
                        className="w-5 h-5 rounded border-lsc-border text-lsc-rose focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1"
                        data-testid={`handout-section-checkbox-${section.id}`}
                      />
                    </label>
                  )}
                  <button
                    type="button"
                    onClick={() => toggleSection(section.id)}
                    aria-expanded={isExpanded}
                    aria-controls={panelId}
                    className="flex-1 flex items-center justify-between p-5 text-left hover:bg-lsc-cream/50 dark:hover:bg-earth-700/30 transition-colors print:hover:bg-transparent"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-lsc-cream dark:bg-earth-700/50 rounded-lg print:bg-transparent">
                        {renderSectionIcon(section.icon)}
                      </div>
                      <div>
                        <h2
                          id={headingId}
                          data-handout-section-heading
                          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
                        >
                          {section.title}
                        </h2>
                        {section.description && (
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                            {section.description}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="print:hidden">
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/50" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/50" />
                      )}
                    </div>
                  </button>
                </div>

                {(isExpanded || handoutMode) && (
                  <div
                    id={panelId}
                    role="region"
                    aria-labelledby={headingId}
                    className="border-t border-lsc-border dark:border-earth-700 print:border-t-0"
                  >
                    {section.items.length === 0 ? (
                      <p className="p-5 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                        {t('parentOnboarding.resources.sectionEmpty')}
                      </p>
                    ) : (() => {
                      // Multilingual: when a `?lang=` filter is active,
                      // hide items that don't list that code in their
                      // `languages` array. If the filter wipes the whole
                      // section out, show the per-section empty state but
                      // KEEP the section header visible (spec: staff still
                      // want to see the structure even when a section has
                      // nothing in the active language).
                      const langMatchingItems = langFilter
                        ? section.items.filter((it) =>
                            (it.languages ?? []).some(
                              (c) => c.toLowerCase() === langFilter,
                            ),
                          )
                        : section.items
                      if (langMatchingItems.length === 0) {
                        return (
                          <p
                            className="p-5 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 italic"
                            data-testid={`section-empty-for-language-${section.id}`}
                          >
                            {t('parentResources.section.emptyForLanguage', {
                              language: langFilter,
                            })}
                          </p>
                        )
                      }
                      return (
                      <div className="divide-y divide-lsc-border dark:divide-earth-700">
                        {langMatchingItems.map((item: ResourceGuideItem) => {
                          const itemPicked = isItemSelected(section.id, item.id)
                          const itemHiddenInPrint =
                            handoutMode && !itemPicked
                          const isItemStale =
                            item.stale ?? item.last_verified_at == null
                          // Stale items get a rose-tinted LEFT border. Color is
                          // never the only stale cue -- the badge text below
                          // carries the same meaning for AT (a11y).
                          const staleBorder =
                            isItemStale && !handoutMode
                              ? 'border-l-4 border-l-lsc-rose'
                              : ''

                          // Multilingual rendering: the backend already
                          // substituted title/description for the active
                          // ?lang= when a translation existed. We use the
                          // `translations` map to decide *display details*:
                          //  - what `lang=` attribute to put on the span
                          //    (drives AT voice switching)
                          //  - whether to show the "(in English)" fallback
                          //    marker so parents know not to expect
                          //    translated copy in this card.
                          const hasTitleTranslation = Boolean(
                            langFilter &&
                              item.translations?.[langFilter]?.title,
                          )
                          const hasDescriptionTranslation = Boolean(
                            langFilter &&
                              item.translations?.[langFilter]?.description,
                          )
                          const itemLangCodes = (item.languages ?? []).filter(
                            (c) => c.length > 0,
                          )
                          const titleLang = hasTitleTranslation
                            ? langFilter
                            : 'en'
                          const descriptionLang = hasDescriptionTranslation
                            ? langFilter
                            : 'en'
                          // Only show the fallback marker when a language
                          // is selected AND we're actually falling back.
                          const showTitleFallback = Boolean(
                            langFilter && !hasTitleTranslation,
                          )
                          return (
                          <div
                            key={item.id}
                            data-handout-item
                            data-stale={isItemStale ? 'true' : 'false'}
                            className={`p-5 flex items-start gap-3 ${itemHiddenInPrint ? 'print:hidden' : ''} ${staleBorder}`}
                          >
                            {handoutMode && (
                              <label className="flex items-center pt-0.5 print:hidden">
                                <input
                                  type="checkbox"
                                  checked={itemPicked}
                                  onChange={() =>
                                    toggleItemSelection(section.id, item.id)
                                  }
                                  aria-label={t('parentResources.handout.checkbox.item', {
                                    item: item.title,
                                  })}
                                  className="w-5 h-5 rounded border-lsc-border text-lsc-rose focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1"
                                  data-testid={`handout-item-checkbox-${item.id}`}
                                />
                              </label>
                            )}
                            <div className="flex-1">
                              <h3
                                data-handout-item-title
                                className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-1"
                              >
                                {/* `lang` attribute drives AT voice
                                    switching (load-bearing a11y for
                                    parents using screen readers). When
                                    falling back to English source copy,
                                    we still mark it as English so the
                                    reader doesn't mispronounce English
                                    in a Spanish voice. */}
                                <span lang={titleLang}>{item.title}</span>
                                {showTitleFallback && (
                                  <span
                                    className="ml-1 text-xs font-normal italic text-lsc-dark/60 dark:text-lsc-cream/60"
                                    data-testid={`translation-fallback-marker-${item.id}`}
                                  >
                                    {t('parentResources.translation.fallback')}
                                  </span>
                                )}
                              </h3>
                              {/* Per-item language chip row. Each chip is
                                  a real <button> with aria-pressed; clicking
                                  toggles the page filter. Hidden in
                                  handout-build mode + in print so the
                                  packet doesn't carry the staff control. */}
                              {!handoutMode && itemLangCodes.length > 0 && (
                                <div
                                  className="flex flex-wrap gap-1 mb-2 print:hidden"
                                  data-testid={`language-chips-${item.id}`}
                                >
                                  {itemLangCodes.map((code) => (
                                    <LanguageChip
                                      key={code}
                                      code={code.toLowerCase()}
                                      active={
                                        langFilter === code.toLowerCase()
                                      }
                                      onSelect={(c) => {
                                        // Clicking the active chip clears
                                        // the filter (UX shortcut for
                                        // "go back to All").
                                        setLangFilter(
                                          langFilter === c ? '' : c,
                                        )
                                      }}
                                    />
                                  ))}
                                </div>
                              )}
                              {item.description && (
                                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                                  <span lang={descriptionLang}>
                                    {item.description}
                                  </span>
                                </p>
                              )}
                              <div
                                data-testid={`contact-row-${item.id}`}
                                className="flex flex-wrap gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 items-center"
                              >
                                {item.phone && (
                                  <a
                                    href={`tel:${item.phone}`}
                                    aria-label={t('parentOnboarding.resources.callPhone', { phone: formatPhone(item.phone) })}
                                    className="flex items-center gap-1 hover:text-lsc-rose transition-colors"
                                  >
                                    <Phone className="w-3.5 h-3.5" aria-hidden="true" />
                                    {formatPhone(item.phone)}
                                  </a>
                                )}
                                {item.address && (
                                  <AddressRow
                                    address={item.address}
                                    copyLabel={t('parentOnboarding.resources.copyAddress', { address: item.address })}
                                    copiedLabel={t('parentOnboarding.resources.copiedAddress')}
                                    openInMapsLabel={t('parentOnboarding.resources.openInMaps', { address: item.address })}
                                  />
                                )}
                                {item.url && (
                                  <>
                                    <a
                                      href={item.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="flex items-center gap-1 hover:text-lsc-rose transition-colors"
                                    >
                                      <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
                                      {t('parentOnboarding.resources.website')}
                                    </a>
                                    {handoutMode && qrCodes && (
                                      <span
                                        data-handout-qr
                                        data-testid={`handout-qr-${item.id}`}
                                        aria-label={t('parentResources.handout.qrAlt', { url: item.url })}
                                        className="hidden print:inline-block"
                                      >
                                        <QRCodeSVG
                                          value={item.url}
                                          size={64}
                                          level="M"
                                        />
                                      </span>
                                    )}
                                  </>
                                )}
                              </div>
                              {item.eligibility && (
                                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-2">
                                  <span className="font-medium">{t('parentOnboarding.resources.eligibility')}:</span> {item.eligibility}
                                </p>
                              )}
                              {item.notes && (
                                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1 italic">
                                  {item.notes}
                                </p>
                              )}
                              {/* Verification trail: hidden in handout/print mode (this
                                  is a staff-internal trust signal, not for parent take-home). */}
                              {!handoutMode && (
                                <VerifiedBadge
                                  item={item}
                                  staleAfterMonths={FALLBACK_STALE_MONTHS}
                                  showVerifyButton={isStaff}
                                  onVerify={() => handleVerify(item)}
                                  onFlag={() => setFlagModalItem(item)}
                                  verifyBusy={verifyBusyItemId === item.id}
                                />
                              )}
                            </div>
                          </div>
                          )
                        })}
                      </div>
                      )
                    })()}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {flagModalItem && (
        <FlagOutOfDateModal
          item={flagModalItem}
          onClose={() => setFlagModalItem(null)}
          onSubmitted={handleFlagSubmitted}
        />
      )}
    </div>
    </AdminShell>
  )
}
