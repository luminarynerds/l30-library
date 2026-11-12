/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Cross-hub command palette (Cmd+K / Ctrl+K).
 *
 * Searches across every NavigationHub item plus a small set of static
 * "extras" (frequent staff actions whose pages don't live in any hub).
 * Hub items come from buildHubRegistry() so a single source of truth
 * powers the palette no matter which hub a feature lives in.
 *
 * Accessibility:
 *  - role="dialog" + aria-modal + aria-labelledby on the panel
 *  - role="combobox" + aria-expanded + aria-controls + aria-activedescendant
 *    on the search input
 *  - role="listbox" on results, role="option" + aria-selected on each row
 *  - Focus trapped inside the dialog (focus-trap-react) and returned on close
 *  - Escape closes; ArrowUp/Down moves selection; Enter activates
 */
import { useState, useEffect, useRef, useCallback, useId, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, CornerDownLeft, X, Mic, MicOff } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { useOrganizationFeatures, type OrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useTranslation } from '@/i18n'
import { usePersistedState } from '@/hooks/usePersistedState'
import FocusTrap from 'focus-trap-react'
import { buildHubRegistry, scoreHubEntry, type HubItemEntry, type UserRole } from '../navigation/hubRegistry'

interface StaticCommand {
  id: string
  label: string
  description?: string
  url: string
  keywords?: string[]
  featureFlag?: keyof OrganizationFeatures
}

// Static commands for pages NOT represented in the hub registry.
// (Hub-covered entries are derived from buildHubRegistry; do not duplicate them here.)
const STATIC_COMMANDS: StaticCommand[] = [
  // Circulation extras
  { id: 'nav-fines', label: 'Fines', description: 'Manage patron fines and fees', url: '/staff/fines', keywords: ['fees', 'overdue', 'payment'] },
  { id: 'nav-book-drop-fast', label: 'Book Drop Fast Process', description: 'Rapid book drop processing queue', url: '/staff/book-drop/fast-process', keywords: ['fast', 'quick', 'return'] },
  // Cataloging extras
  { id: 'nav-manga-cataloging', label: 'Manga Cataloging', description: 'Catalog manga titles', url: '/staff/manga-cataloging', keywords: ['manga', 'comics', 'graphic novel'] },
  { id: 'nav-comic-cataloging', label: 'Comic Cataloging', description: 'Catalog comic books and graphic novels', url: '/staff/comic-cataloging', keywords: ['comics', 'graphic novel', 'manga'] },
  { id: 'nav-linked-data', label: 'Linked Data', description: 'Manage linked data and metadata', url: '/staff/linked-data', keywords: ['rdf', 'metadata', 'marc', 'bibframe'] },
  { id: 'nav-sparql', label: 'SPARQL Query', description: 'Run SPARQL queries against catalog data', url: '/staff/sparql', keywords: ['sparql', 'query', 'rdf', 'linked data'] },
  { id: 'nav-reading-review', label: 'Reading Review', description: 'Staff reading reviews and recommendations', url: '/staff/reading-review', keywords: ['review', 'reading', 'recommend'] },
  // Inventory & weeding extras
  { id: 'nav-inventory-scan', label: 'Inventory Scan', description: 'Scan items for inventory audit', url: '/staff/inventory/scan', keywords: ['scan', 'barcode', 'audit'] },
  { id: 'nav-inventory-management', label: 'Inventory Management', description: 'Full inventory management dashboard', url: '/staff/inventory-management' },
  { id: 'nav-lost-damaged', label: 'Lost & Damaged', description: 'Manage lost items', url: '/staff/lost-damaged' },
  { id: 'nav-reports-lost-damaged', label: 'Lost & Damaged Report', description: 'Reports on lost and damaged items', url: '/staff/reports/lost-damaged', keywords: ['report', 'lost', 'damaged'] },
  // Acquisitions
  { id: 'nav-selection-list', label: 'Selection List', description: 'Collection development selection list', url: '/staff/selection-list', keywords: ['selection', 'wishlist', 'order', 'collection development'] },
  { id: 'nav-purchase-requests', label: 'Purchase Requests', description: 'Patron and staff purchase requests', url: '/staff/purchase-requests', keywords: ['request', 'suggest', 'purchase'] },
  { id: 'nav-selectors', label: 'Selectors', description: 'Manage collection selectors and assignments', url: '/staff/selectors', keywords: ['selector', 'subject specialist', 'collection'] },
  { id: 'nav-funds', label: 'Funds', description: 'Manage budget funds for acquisitions', url: '/staff/funds', keywords: ['budget', 'fund', 'money'] },
  { id: 'nav-vendors', label: 'Vendors', description: 'Manage vendor accounts and contacts', url: '/staff/vendors', keywords: ['vendor', 'supplier', 'distributor'] },
  { id: 'nav-donations', label: 'Donations', description: 'Manage donated materials', url: '/staff/donations', keywords: ['donate', 'gift', 'donation'] },
  // Patron extras
  { id: 'nav-card-applications', label: 'Card Applications', description: 'Review and process new library card applications', url: '/staff/card-applications', keywords: ['new card', 'application', 'registration', 'signup'] },
  { id: 'nav-patron-segmentation', label: 'Patron Segmentation', description: 'Segment patrons for outreach and analytics', url: '/staff/patron-segmentation', keywords: ['segment', 'group', 'demographics'] },
  { id: 'nav-cohorts', label: 'Cohorts', description: 'Manage patron cohorts and groups', url: '/staff/cohorts', keywords: ['group', 'cohort'] },
  { id: 'nav-home-delivery-deliveries', label: 'Home Delivery — Deliveries', description: 'Track active home deliveries', url: '/staff/home-delivery/deliveries', keywords: ['delivery', 'homebound', 'route'], featureFlag: 'home_delivery_enabled' },
  { id: 'nav-home-delivery-volunteers', label: 'Home Delivery — Volunteers', description: 'Manage home delivery volunteers', url: '/staff/home-delivery/volunteers', keywords: ['volunteer', 'delivery', 'homebound'], featureFlag: 'home_delivery_enabled' },
  { id: 'nav-home-delivery-reports', label: 'Home Delivery — Reports', description: 'Home delivery program reports', url: '/staff/home-delivery/reports', keywords: ['delivery', 'report', 'homebound'], featureFlag: 'home_delivery_enabled' },
  // Reports & analytics
  { id: 'nav-reports', label: 'Circulation Reports', description: 'View reports', url: '/staff/reports' },
  { id: 'nav-reports-unified', label: 'Unified Reports', description: 'All reports in one place', url: '/staff/reports/unified', keywords: ['report', 'unified', 'all'] },
  { id: 'nav-analytics', label: 'Analytics', description: 'System analytics', url: '/staff/analytics' },
  { id: 'nav-usage-statistics', label: 'Usage Statistics', description: 'Library usage and patron statistics', url: '/staff/usage-statistics', keywords: ['statistics', 'usage', 'metrics'] },
  { id: 'nav-reports-rooms', label: 'Room Booking Reports', description: 'Reports on room reservations', url: '/staff/reports/rooms', keywords: ['room', 'report', 'booking'], featureFlag: 'meeting_rooms_enabled' },
  { id: 'nav-attendance', label: 'Attendance', description: 'Track program and event attendance', url: '/staff/attendance', keywords: ['attendance', 'headcount', 'program'] },
  // Outreach
  { id: 'nav-outreach', label: 'Outreach', description: 'Community outreach programs and tracking', url: '/staff/outreach', keywords: ['outreach', 'community', 'partnership'] },
  // Workflows / shift ops
  { id: 'nav-workflows', label: 'Workflows', description: 'Workflow automation', url: '/staff/workflows' },
  { id: 'nav-end-of-day', label: 'End of Day', description: 'End of day procedures', url: '/staff/end-of-day' },
  { id: 'nav-end-of-shift', label: 'End of Shift', description: 'End of shift checklist and handoff', url: '/staff/end-of-shift', keywords: ['shift', 'end', 'handoff', 'checklist'] },
  { id: 'nav-positivity', label: 'Positivity Hub', description: 'Track praise and wins', url: '/staff/positivity', keywords: ['praise', 'gratitude', 'win of the day', 'compliment'] },
  { id: 'nav-certifications', label: 'Certifications', description: 'Staff certifications and credentials', url: '/staff/certifications', keywords: ['certification', 'credential', 'badge', 'training'], featureFlag: 'training_modules_enabled' },
  { id: 'nav-pto', label: 'PTO', description: 'Paid time off tracking', url: '/staff/pto', keywords: ['pto', 'vacation', 'time off', 'leave'], featureFlag: 'staff_scheduling_enabled' },
  { id: 'nav-knowledge-base', label: 'Knowledge Base', description: 'Staff knowledge base and documentation', url: '/staff/knowledge-base', keywords: ['knowledge', 'help', 'documentation', 'faq', 'wiki'] },
  { id: 'nav-directory', label: 'Staff Directory', description: 'Staff contact directory', url: '/staff/directory', keywords: ['directory', 'contact', 'staff', 'phone'] },
  // Safety
  { id: 'nav-medical-emergency', label: 'Medical Emergency', description: 'Medical emergency procedures and contacts', url: '/staff/medical-emergency', keywords: ['medical', 'emergency', 'first aid', 'safety'] },
  // Content
  { id: 'nav-homepage', label: 'Homepage Management', description: 'Manage the public-facing homepage content', url: '/staff/homepage', keywords: ['homepage', 'content', 'featured', 'carousel'] },
  { id: 'nav-content-flags', label: 'Content Flags', description: 'Review flagged content', url: '/staff/content-flags', keywords: ['flag', 'review', 'moderation', 'content'] },
  { id: 'nav-review-responses', label: 'Review Responses', description: 'Respond to patron reviews', url: '/staff/review-responses', keywords: ['review', 'response', 'reply', 'patron'] },
  { id: 'nav-event-reviews', label: 'Event Reviews', description: 'Moderate patron event reviews', url: '/staff/event-reviews', keywords: ['event', 'review', 'rating', 'moderation', 'hide'] },
  { id: 'nav-book-challenges', label: 'Book Challenges', description: 'Manage book challenge requests', url: '/staff/book-challenges', keywords: ['challenge', 'ban', 'reconsideration', 'intellectual freedom'], featureFlag: 'banned_books_tracking_enabled' },
  { id: 'nav-audiobooks-review', label: 'Audiobook Review', description: 'Review and curate audiobook titles', url: '/staff/audiobooks/review', keywords: ['audiobook', 'review', 'audio', 'listen'] },
  { id: 'nav-reference-chat', label: 'Reference Chat', description: 'Virtual reference chat with patrons', url: '/staff/reference-chat', keywords: ['reference', 'chat', 'virtual', 'patron'] },
  { id: 'nav-amas-public', label: 'AMAs (Public)', description: 'Browse live author Q&A sessions', url: '/amas', keywords: ['ama', 'ask', 'author', 'qa', 'live'], featureFlag: 'ama_enabled' },
  // Equipment & tech
  { id: 'nav-rfid', label: 'RFID Management', description: 'RFID operations', url: '/staff/rfid' },
  { id: 'nav-sip2', label: 'SIP2 Terminal', description: 'SIP2 management', url: '/staff/sip2' },
  { id: 'nav-streaming', label: 'Streaming', description: 'Manage streaming media services', url: '/staff/streaming', keywords: ['streaming', 'video', 'media', 'palace'], featureFlag: 'streaming_enabled' },
  { id: 'nav-equipment', label: 'Equipment', description: 'Manage library equipment checkout', url: '/staff/equipment', keywords: ['equipment', 'device', 'checkout', 'laptop', 'hotspot'], featureFlag: 'tech_services_enabled' },
  { id: 'nav-print', label: 'Print Management', description: 'Manage print jobs and printers', url: '/staff/print', keywords: ['print', 'printer', 'queue'] },
  // Marketing
  { id: 'nav-marketing', label: 'Marketing', description: 'Marketing campaigns and materials', url: '/staff/marketing', keywords: ['marketing', 'campaign', 'promotion'] },
  { id: 'nav-marketing-hub', label: 'Marketing Hub', description: 'Centralized marketing hub', url: '/staff/marketing-hub', keywords: ['marketing', 'hub', 'communications'] },
  // Compliance
  { id: 'nav-audit-logs', label: 'Audit Logs', description: 'System audit logs and activity history', url: '/staff/audit-logs', keywords: ['audit', 'log', 'history', 'activity'] },
  { id: 'nav-audit-reversal', label: 'Audit Reversal', description: 'Reverse and correct audit entries', url: '/staff/audit-reversal', keywords: ['audit', 'reversal', 'correct', 'undo'] },
  { id: 'nav-board-audit-log', label: 'Board Audit Log', description: 'Tamper-resistant governance audit trail with CSV/JSON export', url: '/staff/admin/board/audit-log', keywords: ['board', 'audit', 'governance', 'compliance'], featureFlag: 'board_features_enabled' },
  // Releases
  { id: 'nav-releases', label: 'Releases', description: 'View system release notes and changelog', url: '/staff/releases', keywords: ['release', 'changelog', 'update', 'version'] },
  // Admin extras (root + per-area not covered by Settings Hub categories)
  { id: 'nav-admin', label: 'Admin Dashboard', description: 'System administration', url: '/staff/admin' },
  { id: 'nav-admin-dashboard', label: 'Admin — Dashboard', description: 'Admin overview dashboard', url: '/staff/admin/dashboard', keywords: ['admin', 'dashboard', 'overview'] },
]

interface PaletteRow {
  id: string
  label: string
  description?: string
  url: string
  hubLabel?: string
  categoryTitle?: string
  /** synthetic corpus for static-only keywords */
  keywords?: string[]
}

const STAFF_ROLES: ReadonlyArray<UserRole> = [
  'staff',
  'admin',
  'super_admin',
  'director',
  'legal',
  'bookmobile',
  'homebond',
]

function scoreStatic(query: string, cmd: StaticCommand): number {
  const q = query.trim().toLowerCase()
  if (!q) return 0
  const label = cmd.label.toLowerCase()
  const desc = (cmd.description ?? '').toLowerCase()
  const kw = (cmd.keywords ?? []).join(' ').toLowerCase()
  const corpus = `${label} ${desc} ${kw}`
  const tokens = q.split(/\s+/).filter(Boolean)
  let total = 0
  for (const tok of tokens) {
    if (!corpus.includes(tok)) return 0
    let s = tok.length
    const wordStart = new RegExp(`(^|\\s)${tok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`)
    if (wordStart.test(corpus)) s += 5
    if (label.includes(tok)) s += 10
    if (label === tok || label.startsWith(tok + ' ')) s += 25
    total += s
  }
  return total
}

const checkSpeechSupport = (): boolean => {
  if (typeof window === 'undefined') return false
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition)
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps): React.ReactElement | null {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const speechSupported = checkSpeechSupport()
  const headingId = useId()
  const listboxId = useId()
  const optionIdBase = useId()

  const isStaffUser = Boolean(user && STAFF_ROLES.includes(user.role))

  // Build the unified, role+flag-filtered universe of rows.
  const allRows = useMemo<PaletteRow[]>(() => {
    if (!user) return []
    const hubRows: PaletteRow[] = buildHubRegistry({
      isFeatureEnabled,
      role: user.role,
    }).map((entry: HubItemEntry) => ({
      id: `${entry.hubSlug}:${entry.categoryId}:${entry.itemPath}`,
      label: entry.itemLabel,
      ...(entry.itemDescription !== undefined ? { description: entry.itemDescription } : {}),
      url: entry.itemPath,
      hubLabel: entry.hubLabel,
      categoryTitle: entry.categoryTitle,
    }))
    const hubUrls = new Set(hubRows.map((r) => r.url))
    const staticRows: PaletteRow[] = STATIC_COMMANDS
      .filter((cmd) => !cmd.featureFlag || isFeatureEnabled(cmd.featureFlag))
      .filter((cmd) => !hubUrls.has(cmd.url))
      .map((cmd) => ({
        id: cmd.id,
        label: cmd.label,
        ...(cmd.description !== undefined ? { description: cmd.description } : {}),
        url: cmd.url,
        ...(cmd.keywords !== undefined ? { keywords: cmd.keywords } : {}),
      }))
    return [...hubRows, ...staticRows]
  }, [user, isFeatureEnabled])

  // Recent commands -- persisted via usePersistedState
  const [recentCommandIds, setRecentCommandIds] = usePersistedState<string[]>('lsc-command-palette-recent', [])

  const saveRecentCommand = useCallback((commandId: string) => {
    setRecentCommandIds((prev) => [commandId, ...prev.filter((id) => id !== commandId)].slice(0, 5))
  }, [setRecentCommandIds])

  // Filter + score
  const filteredRows = useMemo<PaletteRow[]>(() => {
    const q = query.trim()
    if (!q) {
      const recentRows = recentCommandIds
        .map((id) => allRows.find((r) => r.id === id))
        .filter(Boolean) as PaletteRow[]
      return recentRows.length > 0 ? recentRows : allRows.slice(0, 8)
    }
    const scored: Array<{ row: PaletteRow; score: number }> = []
    for (const row of allRows) {
      const score = row.hubLabel
        ? scoreHubEntry(q, {
            hubSlug: '',
            hubLabel: row.hubLabel,
            categoryId: '',
            categoryTitle: row.categoryTitle ?? '',
            itemLabel: row.label,
            ...(row.description !== undefined ? { itemDescription: row.description } : {}),
            itemPath: row.url,
          })
        : scoreStatic(q, {
            id: row.id,
            label: row.label,
            ...(row.description !== undefined ? { description: row.description } : {}),
            url: row.url,
            ...(row.keywords !== undefined ? { keywords: row.keywords } : {}),
          })
      if (score > 0) scored.push({ row, score })
    }
    scored.sort((a, b) => b.score - a.score)
    return scored.slice(0, 8).map((s) => s.row)
  }, [query, allRows, recentCommandIds])

  // Reset selection on query change
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset highlighted row to top when the query (and thus filteredRows) changes
    setSelectedIndex(0)
  }, [query])

  // Reset state + focus on open
  useEffect(() => {
    if (isOpen) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset palette state on isOpen transition; paired with focus timer below
      setQuery('')
      setSelectedIndex(0)
      const timer = setTimeout(() => inputRef.current?.focus(), 50)
      return () => clearTimeout(timer)
    }
    recognitionRef.current?.stop()
    return undefined
  }, [isOpen])

  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'en-US'

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(recognition as any).onstart = () => setIsListening(true)

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join('')
      setQuery(transcript)
    }

    recognition.onerror = () => setIsListening(false)
    recognition.onend = () => setIsListening(false)

    recognitionRef.current = recognition
    recognition.start()
  }

  const stopListening = () => {
    recognitionRef.current?.stop()
    setIsListening(false)
  }

  const toggleVoice = () => {
    if (isListening) stopListening()
    else startListening()
  }

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) => Math.min(prev + 1, filteredRows.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => Math.max(prev - 1, 0))
        break
      case 'Enter': {
        e.preventDefault()
        const row = filteredRows[selectedIndex]
        if (row) {
          saveRecentCommand(row.id)
          navigate(row.url)
          onClose()
        }
        break
      }
      case 'Escape':
        e.preventDefault()
        onClose()
        break
    }
  }, [filteredRows, selectedIndex, navigate, onClose, saveRecentCommand])

  // Scroll selected option into view
  useEffect(() => {
    const list = listRef.current
    if (!list) return
    const items = list.querySelectorAll('[data-command-item]')
    items[selectedIndex]?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  if (!isOpen || !isStaffUser) return null

  const activeOptionId = filteredRows.length > 0 ? `${optionIdBase}-${selectedIndex}` : undefined

  return (
    <FocusTrap
      active={isOpen}
      focusTrapOptions={{
        escapeDeactivates: false,
        allowOutsideClick: true,
        returnFocusOnDeactivate: true,
        fallbackFocus: () => document.body,
      }}
    >
      <div>
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/50 z-[100] motion-safe:animate-fade-in"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* Palette */}
        <div
          className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-xl z-[101] motion-safe:animate-scale-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby={headingId}
        >
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
            <h2 id={headingId} className="sr-only">
              {t('aria.commandPalette.commandPalette', 'Command palette')}
            </h2>

            {/* Search input */}
            <div className="flex items-center gap-3 px-4 border-b border-lsc-border dark:border-earth-700">
              <Search className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0" aria-hidden="true" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('commandPalette.placeholder', 'Search hubs, settings, or actions...')}
                aria-label={t('commandPalette.placeholder', 'Search hubs, settings, or actions...')}
                role="combobox"
                aria-expanded={isOpen}
                aria-controls={listboxId}
                aria-activedescendant={activeOptionId}
                aria-autocomplete="list"
                className="flex-1 py-4 bg-transparent text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none text-base"
                autoComplete="off"
                spellCheck={false}
              />
              {speechSupported && (
                <button
                  type="button"
                  onClick={toggleVoice}
                  className={`p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors ${
                    isListening ? 'text-status-danger-600 motion-safe:animate-pulse' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                  }`}
                  aria-label={isListening
                    ? t('commandPalette.stopListening', 'Stop listening')
                    : t('commandPalette.voiceSearch', 'Voice search')}
                >
                  {isListening ? <MicOff className="w-4 h-4" aria-hidden="true" /> : <Mic className="w-4 h-4" aria-hidden="true" />}
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                aria-label={t('aria.commandPalette.closeCommandPalette', 'Close command palette')}
              >
                <X className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
              </button>
            </div>

            {/* Results listbox */}
            <div
              ref={listRef}
              id={listboxId}
              className="max-h-[360px] overflow-y-auto py-2"
              role="listbox"
              aria-label={t('aria.commandPalette.commandResults', 'Command results')}
            >
              {filteredRows.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('commandPalette.noResults', 'No results for "{{query}}"').replace('{{query}}', query)}
                  </p>
                </div>
              ) : (
                <>
                  {!query.trim() && (
                    <div className="px-4 py-1.5">
                      <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                        {recentCommandIds.length > 0
                          ? t('commandPalette.recent', 'Recent')
                          : t('commandPalette.quickAccess', 'Quick access')}
                      </span>
                    </div>
                  )}
                  {filteredRows.map((row, index) => {
                    const isSelected = index === selectedIndex
                    return (
                      <button
                        key={row.id}
                        id={`${optionIdBase}-${index}`}
                        data-command-item
                        role="option"
                        aria-selected={isSelected}
                        onClick={() => {
                          saveRecentCommand(row.id)
                          navigate(row.url)
                          onClose()
                        }}
                        onMouseEnter={() => setSelectedIndex(index)}
                        className={`w-full flex flex-col items-start gap-0.5 px-4 py-2.5 text-left transition-colors ${
                          isSelected
                            ? 'bg-lsc-rose/10 dark:bg-lsc-rose/20'
                            : 'hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50'
                        }`}
                      >
                        {row.hubLabel && (
                          <span className="text-[10px] uppercase tracking-wider text-lsc-dark/60 dark:text-lsc-cream/50 font-medium">
                            {row.hubLabel}
                            {row.categoryTitle ? ` · ${row.categoryTitle}` : ''}
                          </span>
                        )}
                        <div className="flex items-center justify-between w-full gap-3">
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-semibold truncate ${
                              isSelected ? 'text-lsc-rose' : 'text-lsc-dark dark:text-lsc-cream'
                            }`} title={row.label}>
                              {row.label}
                            </p>
                            {row.description && (
                              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={row.description}>
                                {row.description}
                              </p>
                            )}
                          </div>
                          {isSelected && (
                            <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0">
                              <CornerDownLeft className="w-3 h-3" aria-hidden="true" />
                              <span>{t('commandPalette.enterHint', 'Enter')}</span>
                            </div>
                          )}
                        </div>
                      </button>
                    )
                  })}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2.5 border-t border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-900/50">
              <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-lsc-white dark:bg-earth-700 rounded border border-lsc-border dark:border-earth-700 font-mono text-xs">↑↓</kbd>
                  {t('commandPalette.footerNavigate', 'Navigate')}
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-lsc-white dark:bg-earth-700 rounded border border-lsc-border dark:border-earth-700 font-mono text-xs">↵</kbd>
                  {t('commandPalette.footerOpen', 'Open')}
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-lsc-white dark:bg-earth-700 rounded border border-lsc-border dark:border-earth-700 font-mono text-xs">Esc</kbd>
                  {t('commandPalette.footerClose', 'Close')}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}
