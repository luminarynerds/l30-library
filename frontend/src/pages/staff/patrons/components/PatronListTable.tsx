/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react"
 
import { useVirtualizer } from "@tanstack/react-virtual"
import {
  Users,
  Loader2,
  User,
  Ban,
  BookOpen,
  Bookmark,
  CheckSquare,
  Square,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
} from "lucide-react"
import type { Patron } from "../../../../api/api"
import type { PatronDetail } from "../types"
import { BulkOperationsPanel, type BulkAction, type BulkOperationResult } from "../../../../components/staff"
import type { PatronSortField, SortDirection } from "@/api/staff-api/patrons"
import { useTranslation, formatCurrency } from '@/i18n'

interface PatronListTableProps {
  patrons: Patron[]
  totalPatrons: number
  filteredPatrons: Patron[]
  selectedPatron: PatronDetail | null
  isSearching: boolean
  isBulkMode: boolean
  onBulkModeToggle: () => void
  bulkSelectedIds: number[]
  onSelectPatron: (patron: Patron) => void
  onBulkSelectionToggle: (id: number, index: number, allIds: number[], shiftKey: boolean) => void
  isBulkSelected: (id: number) => boolean
  bulkActions: BulkAction[]
  bulkOperationResult: BulkOperationResult | null
  onBulkResultDismiss: () => void
  onBulkSelectedIdsChange: (ids: number[]) => void
  clearBulkSelection: () => void
  activeAlertFilter: "none" | "overdue" | "fines" | "inactive"
  onClearAlertFilter: () => void
  sortBy?: PatronSortField
  sortDirection?: SortDirection
  onSortChange?: (field: PatronSortField) => void
}

const SORT_OPTION_FIELDS: PatronSortField[] = ["name", "member_date", "fines_balance", "checkout_count"]

const SORT_FIELD_I18N_KEY: Record<PatronSortField, string> = {
  name: "name",
  member_date: "memberDate",
  fines_balance: "finesBalance",
  checkout_count: "checkoutCount",
}

function PatronRowSummary({ patron }: { patron: Patron }): React.ReactElement {
  const { t, language } = useTranslation()
  const name = `${patron.first_name} ${patron.last_name}`
  const email = patron.email ?? patron.email_masked ?? ""
  const checkouts = t('aria.patronListTable.checkoutsCount', '{{count}} checkouts').replace('{{count}}', String(patron.current_checkouts || 0))
  const holds = t('aria.patronListTable.holdsCount', '{{count}} holds').replace('{{count}}', String(patron.current_holds || 0))
  return (
    <span className="sr-only">
      {name}, {email}, {checkouts}, {holds}
      {(patron.fines_balance ?? 0) > 0 && `, ${t('aria.patronListTable.finesOwed', '{{amount}} owed').replace('{{amount}}', formatCurrency(patron.fines_balance ?? 0, language, 'USD'))}`}
      {!patron.is_active && `, ${t('aria.patronListTable.inactiveStatus', 'inactive')}`}
    </span>
  )
}

function SortIcon({ field, activeField, direction }: { field: PatronSortField; activeField?: PatronSortField; direction?: SortDirection }) {
  if (field !== activeField) return <ArrowUpDown className="w-3.5 h-3.5 opacity-40" aria-hidden="true" />
  if (direction === "asc") return <ArrowUp className="w-3.5 h-3.5" aria-hidden="true" />
  return <ArrowDown className="w-3.5 h-3.5" aria-hidden="true" />
}

export function PatronListTable({
  totalPatrons,
  filteredPatrons,
  selectedPatron,
  isSearching,
  isBulkMode,
  onBulkModeToggle,
  bulkSelectedIds,
  onSelectPatron,
  onBulkSelectionToggle,
  isBulkSelected,
  bulkActions,
  bulkOperationResult,
  onBulkResultDismiss,
  onBulkSelectedIdsChange,
  clearBulkSelection,
  activeAlertFilter,
  onClearAlertFilter,
  sortBy,
  sortDirection,
  onSortChange,
}: PatronListTableProps) {
  const { t, language } = useTranslation()
  const fmt = (amount: number): string => formatCurrency(amount, language, 'USD')
  const patronListRef = useRef<HTMLDivElement>(null)

  const SORT_OPTIONS: { field: PatronSortField; label: string }[] = SORT_OPTION_FIELDS.map(field => ({
    field,
    label: t(`patronListTable.sort.${SORT_FIELD_I18N_KEY[field]}`),
  }))

  // Virtualization for large patron lists
   
   
  const shouldVirtualizePatrons = filteredPatrons.length > 50
  // eslint-disable-next-line react-hooks/incompatible-library
  const patronVirtualizer = useVirtualizer({
    count: filteredPatrons.length,
    getScrollElement: () => patronListRef.current,
    estimateSize: () => 76,
    overscan: 5,
    enabled: shouldVirtualizePatrons,
  })

  const allPatronIds = filteredPatrons.map((p) => p.id)
  const pagePatronIds = filteredPatrons.slice(0, 10).map((p) => p.id)

  // Roving tabindex: only one row's select button is in the tab order at a time.
  // Arrow keys move within the list; Tab leaves the list. This avoids forcing
  // keyboard users to tab through every row before reaching the detail pane.
  const [activeIndex, setActiveIndex] = useState(0)

  // Clamp activeIndex when the filtered list shrinks.
  useEffect(() => {
    if (activeIndex > 0 && activeIndex >= filteredPatrons.length) {
      setActiveIndex(Math.max(0, filteredPatrons.length - 1))
    }
  }, [filteredPatrons.length, activeIndex])

  const focusRow = useCallback((index: number) => {
    const container = patronListRef.current
    if (!container) return
    const target = container.querySelector<HTMLButtonElement>(
      `[data-patron-row="${index}"]`
    )
    if (target) target.focus()
  }, [])

  const handleListKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (filteredPatrons.length === 0) return
      const last = filteredPatrons.length - 1
      let next = activeIndex
      switch (e.key) {
        case "ArrowDown":
          next = Math.min(last, activeIndex + 1)
          break
        case "ArrowUp":
          next = Math.max(0, activeIndex - 1)
          break
        case "Home":
          next = 0
          break
        case "End":
          next = last
          break
        default:
          return
      }
      e.preventDefault()
      if (next === activeIndex) {
        // Re-focus the current row (covers focus loss after re-render).
        focusRow(next)
        return
      }
      setActiveIndex(next)
      // For the virtualized branch, scroll the target into the rendered window
      // before focusing. The DOM node may not exist yet, so retry on the next
      // frame after the virtualizer renders it.
      if (shouldVirtualizePatrons) {
        patronVirtualizer.scrollToIndex(next, { align: "auto" })
      }
      requestAnimationFrame(() => focusRow(next))
    },
    [activeIndex, filteredPatrons.length, focusRow, patronVirtualizer, shouldVirtualizePatrons]
  )

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
      <div className="p-4 border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('patronListTable.patrons')}</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                onBulkModeToggle()
                if (isBulkMode) {
                  clearBulkSelection()
                  onBulkResultDismiss()
                }
              }}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                isBulkMode
                  ? "bg-lsc-rose text-white"
                  : "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-lsc-brown/80"
              }`}
            >
              {isBulkMode ? t('patronListTable.exitBulk') : t('patronListTable.bulkMode')}
            </button>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {activeAlertFilter !== "none" ? (
                <span className="flex items-center gap-1">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      activeAlertFilter === "overdue"
                        ? "bg-status-danger-500"
                        : activeAlertFilter === "fines"
                        ? "bg-status-warning-500"
                        : "bg-earth-500"
                    }`}
                  />
                  {t('patronListTable.countFiltered', { count: filteredPatrons.length })}
                </span>
              ) : (
                <>{t('patronListTable.countTotal', { count: totalPatrons })}</>
              )}
            </span>
          </div>
        </div>

        {/* Bulk Operations Panel */}
        {isBulkMode && (
          <div className="mt-4">
            <BulkOperationsPanel
              selectedIds={bulkSelectedIds}
              totalItems={filteredPatrons.length}
              actions={bulkActions}
              onSelectionChange={onBulkSelectedIdsChange}
              allItemIds={allPatronIds}
              pageItemIds={pagePatronIds}
              itemLabel="patrons"
              {...(bulkOperationResult && { lastResult: bulkOperationResult })}
              onResultDismiss={onBulkResultDismiss}
              compact
            />
          </div>
        )}

        {/* Sort Bar */}
        {onSortChange && (
          <div className="mt-3 flex items-center gap-1 flex-wrap">
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mr-1">{t('patronListTable.sort.label')}</span>
            {SORT_OPTIONS.map(({ field, label }) => {
              const isActive = sortBy === field
              const directionLabel = isActive
                ? sortDirection === "asc"
                  ? t('patronListTable.sort.ascending')
                  : t('patronListTable.sort.descending')
                : ''
              return (
                <button
                  key={field}
                  onClick={() => onSortChange(field)}
                  className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg transition-colors ${
                    isActive
                      ? "bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light font-medium"
                      : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50"
                  }`}
                  aria-pressed={isActive}
                  aria-label={
                    isActive
                      ? t('patronListTable.sort.ariaLabelActive', { label, direction: directionLabel })
                      : t('patronListTable.sort.ariaLabelInactive', { label })
                  }
                >
                  {label}
                  <SortIcon field={field} {...(sortBy ? { activeField: sortBy } : {})} {...(sortDirection ? { direction: sortDirection } : {})} />
                </button>
              )
            })}
          </div>
        )}
      </div>

      {isSearching && filteredPatrons.length === 0 ? (
        <div className="p-8 flex items-center justify-center">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
        </div>
      ) : filteredPatrons.length === 0 ? (
        <div className="p-8 text-center">
          <Users aria-hidden="true" className="w-12 h-12 text-lsc-border dark:text-lsc-cream/70 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {activeAlertFilter !== "none" ? t('patronListTable.noMatchingAtRiskPatrons') : t('patronListTable.noPatronsFound')}
          </p>
          {activeAlertFilter !== "none" && (
            <button
              onClick={onClearAlertFilter}
              className="mt-2 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              {t('patronListTable.clearFilter')}
            </button>
          )}
        </div>
      ) : shouldVirtualizePatrons ? (
        /* Virtualized patron list for large datasets */
        <div
          ref={patronListRef}
          className="h-[400px] overflow-auto"
          role="list"
          aria-label={t('patronListTable.patronList')}
          onKeyDown={handleListKeyDown}
        >
          <div
            style={{
              height: `${patronVirtualizer.getTotalSize()}px`,
              width: "100%",
              position: "relative",
            }}
          >
            {patronVirtualizer.getVirtualItems().map((virtualRow) => {
              const patron = filteredPatrons[virtualRow.index]
              const index = virtualRow.index
              if (!patron) return null
              return (
                <div
                  key={patron.id}
                  role="listitem"
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                  className={`w-full flex items-center gap-3 p-4 text-left transition-colors border-b border-lsc-border dark:border-earth-700 ${
                    selectedPatron?.id === patron.id
                      ? "bg-lsc-cream dark:bg-lsc-brown/30"
                      : isBulkSelected(patron.id)
                      ? "bg-lsc-rose/10 dark:bg-lsc-rose/20"
                      : "hover:bg-lsc-cream dark:hover:bg-lsc-brown/50"
                  }`}
                >
                  {isBulkMode && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onBulkSelectionToggle(patron.id, index, allPatronIds, e.shiftKey)
                      }}
                      className="flex-shrink-0 p-1 rounded hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors"
                      aria-label={
                        isBulkSelected(patron.id)
                          ? t('patronListTable.deselectPatron')
                          : t('patronListTable.selectPatronShift')
                      }
                    >
                      {isBulkSelected(patron.id) ? (
                        <CheckSquare
                          className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light"
                          aria-hidden="true"
                        />
                      ) : (
                        <Square className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
                      )}
                    </button>
                  )}
                  <button
                    onClick={() => !isBulkMode && onSelectPatron(patron)}
                    className="flex-1 flex items-center gap-3 min-w-0"
                    disabled={isBulkMode}
                    data-patron-row={index}
                    tabIndex={index === activeIndex ? 0 : -1}
                    onFocus={() => {
                      if (index !== activeIndex) setActiveIndex(index)
                    }}
                  >
                    <PatronRowSummary patron={patron} />
                    <div
                      aria-hidden="true"
                      className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                        patron.is_active ? "bg-lsc-cream dark:bg-lsc-brown/30" : "bg-status-danger-100 dark:bg-status-danger-900/30"
                      }`}
                    >
                      <User
                        className={`w-5 h-5 ${
                          patron.is_active
                            ? "text-lsc-rose dark:text-lsc-rose-light"
                            : "text-status-danger-600 dark:text-status-danger-400"
                        }`}
                      />
                    </div>
                    <div aria-hidden="true" className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={`${patron.first_name} ${patron.last_name}`}>
                          {patron.first_name} {patron.last_name}
                        </p>
                        {!patron.is_active && (
                          <Ban
                            aria-hidden="true"
                            className="w-4 h-4 text-status-danger-500 dark:text-status-danger-400 flex-shrink-0"
                          />
                        )}
                      </div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={patron.email ?? patron.email_masked ?? undefined}>{patron.email ?? patron.email_masked ?? ""}</p>
                    </div>
                    <div aria-hidden="true" className="text-right flex-shrink-0">
                      <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        <span className="flex items-center gap-1">
                          <BookOpen aria-hidden="true" className="w-3.5 h-3.5" />
                          {patron.current_checkouts || 0}
                        </span>
                        <span className="flex items-center gap-1">
                          <Bookmark aria-hidden="true" className="w-3.5 h-3.5" />
                          {patron.current_holds || 0}
                        </span>
                      </div>
                      {(patron.fines_balance ?? 0) > 0 && (
                        <span className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light">
                          {fmt(patron.fines_balance ?? 0)}
                        </span>
                      )}
                    </div>
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        /* Standard patron list for small datasets */
        <div
          ref={patronListRef}
          className="divide-y divide-lsc-border dark:divide-earth-700"
          role="list"
          aria-label={t('patronListTable.patronList')}
          onKeyDown={handleListKeyDown}
        >
          {filteredPatrons.map((patron, index) => (
            <div
              key={patron.id}
              role="listitem"
              className={`w-full flex items-center gap-3 p-4 text-left transition-colors ${
                selectedPatron?.id === patron.id
                  ? "bg-lsc-cream dark:bg-lsc-brown/30"
                  : isBulkSelected(patron.id)
                  ? "bg-lsc-rose/10 dark:bg-lsc-rose/20"
                  : "hover:bg-lsc-cream dark:hover:bg-lsc-brown/50"
              }`}
            >
              {isBulkMode && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onBulkSelectionToggle(patron.id, index, allPatronIds, e.shiftKey)
                  }}
                  className="flex-shrink-0 p-1 rounded hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors"
                  aria-label={
                    isBulkSelected(patron.id) ? "Deselect patron" : "Select patron. Hold Shift to select range"
                  }
                >
                  {isBulkSelected(patron.id) ? (
                    <CheckSquare
                      className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light"
                      aria-hidden="true"
                    />
                  ) : (
                    <Square className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
                  )}
                </button>
              )}

              <button
                onClick={() => !isBulkMode && onSelectPatron(patron)}
                className="flex-1 flex items-center gap-3 min-w-0"
                disabled={isBulkMode}
                data-patron-row={index}
                tabIndex={index === activeIndex ? 0 : -1}
                onFocus={() => {
                  if (index !== activeIndex) setActiveIndex(index)
                }}
              >
                <PatronRowSummary patron={patron} />
                <div
                  aria-hidden="true"
                  className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                    patron.is_active ? "bg-lsc-cream dark:bg-lsc-brown/30" : "bg-status-danger-100 dark:bg-status-danger-900/30"
                  }`}
                >
                  <User
                    className={`w-5 h-5 ${
                      patron.is_active
                        ? "text-lsc-rose dark:text-lsc-rose-light"
                        : "text-status-danger-600 dark:text-status-danger-400"
                    }`}
                  />
                </div>
                <div aria-hidden="true" className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={`${patron.first_name} ${patron.last_name}`}>
                      {patron.first_name} {patron.last_name}
                    </p>
                    {!patron.is_active && (
                      <Ban aria-hidden="true" className="w-4 h-4 text-status-danger-500 dark:text-status-danger-400 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={patron.email ?? patron.email_masked ?? undefined}>{patron.email ?? patron.email_masked ?? ""}</p>
                </div>
                <div aria-hidden="true" className="text-right flex-shrink-0">
                  <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="flex items-center gap-1">
                      <BookOpen aria-hidden="true" className="w-3.5 h-3.5" />
                      {patron.current_checkouts || 0}
                    </span>
                    <span className="flex items-center gap-1">
                      <Bookmark aria-hidden="true" className="w-3.5 h-3.5" />
                      {patron.current_holds || 0}
                    </span>
                  </div>
                  {(patron.fines_balance ?? 0) > 0 && (
                    <span className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light">
                      {fmt(patron.fines_balance ?? 0)}
                    </span>
                  )}
                </div>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
