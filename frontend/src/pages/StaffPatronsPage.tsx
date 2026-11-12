/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import { useBulkSelection, type BulkAction, SendNotificationModal } from "../components/staff"
import BulkMessageModal from "../components/staff/BulkMessageModal"
import type { BulkOperationResult } from "../components/staff"
import { PatronStatisticsDashboard, PatronFinesTab, PatronHistoryTab } from "../components/staff/patrons"
import { CardScanModal } from "../components/staff/patrons/CardScanModal"
import AddPatronModal from "../components/staff/AddPatronModal"
import { PatronPagination } from "./staff-patrons/PatronPagination"
import { sendPatronMessage } from "../api/domains/patron/patron-communication-api"
import { getPatronStatistics, returnItem, cancelHold } from "../api/api"
import { getPatronActivity, type PatronActivityListResponse, type PatronActivityType, getPatronCheckouts, getPatronHolds, staffCheckoutHold, staffRenewCheckout } from "../api/staff-api"
import type { CardStatusFilter, PatronAdvancedFilters, Patron } from "@/api/staff-api/patrons"
import type { ExpiringCardBand } from "../components/staff/patrons/PatronStatisticsDashboard"

const VALID_CARD_STATUS: ReadonlySet<CardStatusFilter> = new Set([
  "any",
  "active",
  "expiring_30d",
  "expiring_90d",
  "expired",
])

function parseCardStatusParam(raw: string | null): CardStatusFilter | undefined {
  if (!raw) return undefined
  return VALID_CARD_STATUS.has(raw as CardStatusFilter) && raw !== "any"
    ? (raw as CardStatusFilter)
    : undefined
}
import { Barcode, Bell, RefreshCw, Loader2, CreditCard, Calendar, Copy, Shield, UserPlus } from "lucide-react"
import toast from "react-hot-toast"
import { filterPatronsByAlertStatus } from "./staff/patrons/utils/patronFilters"

// Import all hooks
import {
  usePatronSearch,
  usePatronDetail,
  usePatronMerge,
  usePatronDeletion,
  useLibraryCardPrinting,
  useEstateManagement,
  usePatronAccountSettings,
  useBulkOperations,
} from "./staff/patrons/hooks"

// Import all components
import {
  PatronSearchPanel,
  PatronFilterPresetsRow,
  PatronListTable,
  PatronProfileTab,
  PatronCheckoutsTab,
  PatronHoldsTab,
  PatronCommunicationTab,
  PatronPIIAccessTab,
  PatronMergeDialogs,
  LibraryCardPrintModal,
  EstateManagementPanel,
  DeletionManagementPanel,
  PatronAccountSettingsModal,
} from "./staff/patrons/components"
import { usePatronFilterPresets, type PresetFilters } from "./staff/patrons/hooks/usePatronFilterPresets"
import { BulkWaiveReasonModal } from "../components/staff/patrons/BulkWaiveReasonModal"
import { PatronEmptyState } from "./staff/patrons/components/PatronEmptyState"
import { PatronRecentNotesStrip } from "./staff/patrons/components/PatronRecentNotesStrip"
import { recordRecentPatron } from "./staff/patrons/utils/recentPatrons"
import { expirySeverity } from "./staff/patrons/utils/patronChipSeverity"
import { useTranslation } from '@/i18n'

export default function StaffPatronsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // Seed advanced filters from URL on first mount so deep-links like
  // ?cardStatus=expired land you on the filtered view immediately.
  const initialAdvancedFiltersRef = useRef<PatronAdvancedFilters>({
    ...(parseCardStatusParam(searchParams.get("cardStatus")) && {
      cardStatus: parseCardStatusParam(searchParams.get("cardStatus")),
    }),
  })

  // Card scan modal state
  const [isCardScanOpen, setIsCardScanOpen] = useState(false)

  // Add patron modal state
  const [isAddPatronOpen, setIsAddPatronOpen] = useState(false)

  // Send notification modal state
  const [isNotificationModalOpen, setIsNotificationModalOpen] = useState(false)

  // Bulk message modal state. The modal-driven action awaits a promise that
  // resolves when the modal's Send button fires its API call -- mirrors the
  // promise-resolver pattern in BulkPatronOperations.tsx for waive-fines.
  const [isBulkMessageOpen, setIsBulkMessageOpen] = useState(false)
  const [bulkMessageIds, setBulkMessageIds] = useState<number[]>([])
  const bulkMessageResolverRef = useRef<((result: BulkOperationResult) => void) | null>(null)

  // Detail tabs
  const [activeTab, setActiveTab] = useState<"profile" | "checkouts" | "holds" | "fines" | "history" | "communication" | "pii-access">(
    "profile"
  )

  // Statistics state
  const { data: patronStats = null, isLoading: statsLoading } = useQuery({
    queryKey: ['patron-statistics'],
    queryFn: () => getPatronStatistics(token!),
    enabled: !!token,
  })
  const [activeAlertFilter, setActiveAlertFilter] = useState<"none" | "overdue" | "fines" | "inactive">("none")
  const [isDashboardExpanded, setIsDashboardExpanded] = useState(true)

  // History tab state
  const [activityData, setActivityData] = useState<PatronActivityListResponse | null>(null)
  const [activityLoading, setActivityLoading] = useState(false)
  const [activityPage, setActivityPage] = useState(1)
  const [activityTypeFilter, setActivityTypeFilter] = useState<PatronActivityType | "">("")

  // Bulk operations state
  const [isBulkMode, setIsBulkMode] = useState(false)
  const [bulkOperationResult, setBulkOperationResult] = useState<{ success: boolean; successCount: number; failureCount: number; message: string; failedIds?: number[] } | null>(null)
  const {
    selectedIds: bulkSelectedIds,
    setSelectedIds: setBulkSelectedIds,
    toggleSelectionWithRange: toggleBulkSelectionWithRange,
    isSelected: isBulkSelected,
    clearSelection: clearBulkSelection,
  } = useBulkSelection()

  // Use custom hooks
  const {
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter,
    patrons,
    totalPatrons,
    currentPage,
    perPage,
    totalPages,
    setCurrentPage,
    setPerPage,
    isSearching,
    handleSearch,
    performSearch,
    sortBy,
    sortDirection,
    updateSort,
    updatePatronInList,
    advancedFilters,
    activeFilterCount,
    setAdvancedFilters,
    clearAdvancedFilters,
  } = usePatronSearch(token, isAuthenticated, initialAdvancedFiltersRef.current)

  // Keep ?cardStatus= URL param in sync with the active filter so the view is
  // shareable / refreshable. Empty value removes the param.
  useEffect(() => {
    const next = new URLSearchParams(searchParams)
    const current = advancedFilters.cardStatus
    if (current && current !== "any") {
      if (next.get("cardStatus") !== current) {
        next.set("cardStatus", current)
        setSearchParams(next, { replace: true })
      }
    } else if (next.has("cardStatus")) {
      next.delete("cardStatus")
      setSearchParams(next, { replace: true })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [advancedFilters.cardStatus])

  const handleExpiringCardsClick = useCallback((band: ExpiringCardBand) => {
    setAdvancedFilters({ ...advancedFilters, cardStatus: band })
    setCurrentPage(1)
  }, [advancedFilters, setAdvancedFilters, setCurrentPage])

  // Debounced search callback - triggers search when debounced query changes
  const handleDebouncedSearch = useCallback((_query: string) => {
    if (currentPage !== 1) {
      setCurrentPage(1)
      return
    }

    performSearch({ page: 1 })
  }, [currentPage, setCurrentPage, performSearch])

  // Saved-views (FilterPreset) row — localStorage-only, per-user.
  const presets = usePatronFilterPresets(user?.id)
  const handleApplyPreset = useCallback((id: string, filters: PresetFilters) => {
    const { statusFilter: nextStatus, ...rest } = filters
    clearAdvancedFilters()
    setAdvancedFilters(rest)
    setStatusFilter(nextStatus ?? "all")
    setCurrentPage(1)
    presets.applyPreset(id, filters)
  }, [clearAdvancedFilters, setAdvancedFilters, setStatusFilter, setCurrentPage, presets])
  const handleClearActivePreset = useCallback(() => {
    clearAdvancedFilters()
    setStatusFilter("all")
    setCurrentPage(1)
    presets.clearActivePreset()
  }, [clearAdvancedFilters, setStatusFilter, setCurrentPage, presets])

  const {
    selectedPatron,
    setSelectedPatron,
    familyData,
    selectPatron,
    refreshPatron,
    isRefreshing,
  } = usePatronDetail(token)

  // Record the active patron in sessionStorage so the empty state can offer
  // a quick re-open dropdown. Effect-driven so it covers selectPatron(),
  // selectRecent flows, and any future setSelectedPatron paths.
  useEffect(() => {
    if (!selectedPatron) return
    recordRecentPatron(user?.id, {
      id: selectedPatron.id,
      displayName: `${selectedPatron.first_name ?? ""} ${selectedPatron.last_name ?? ""}`.trim() || selectedPatron.email || `Patron #${selectedPatron.id}`,
    })
  }, [selectedPatron, user?.id])

  // Cross-component request to jump to a specific note in the Communication
  // tab. Recent-notes strip sets it; the tab clears it after scrolling.
  const [scrollToNoteId, setScrollToNoteId] = useState<number | null>(null)
  const handleOpenNoteInTab = useCallback((noteId: number) => {
    setScrollToNoteId(noteId)
    setActiveTab("communication")
  }, [])
  // Bump every successful note save so the Communication tab refetches if mounted.
  const [notesRefreshNonce, setNotesRefreshNonce] = useState(0)

  // Load activity data when history tab is active
  useEffect(() => {
    if (!token || !selectedPatron || activeTab !== "history") return
    setActivityLoading(true)
    getPatronActivity(token, selectedPatron.id, {
      ...(activityTypeFilter && { activityType: activityTypeFilter }),
      page: activityPage,
      perPage: 10,
    })
      .then(setActivityData)
      .catch((err) => { setActivityData(null); toast.error(err instanceof Error ? err.message : 'Failed to load activity data') })
      .finally(() => setActivityLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedPatron?.id, activeTab, activityPage, activityTypeFilter])

  const [bulkWaiveModalOpen, setBulkWaiveModalOpen] = useState(false)
  const bulkWaivePendingRef = useRef<{ ids: number[]; resolve: (r: BulkOperationResult) => void } | null>(null)

  const { handleBulkBlock, handleBulkUnblock, handleBulkWaiveFines, handleBulkExport, handleBulkMessage } = useBulkOperations({
    token,
    onOperationComplete: () => {
      handleSearch({ preventDefault: () => {} } as React.FormEvent)
    },
  })

  const {
    showDuplicatesModal,
    setShowDuplicatesModal,
    duplicates,
    isLoadingDuplicates,
    selectedDuplicate,
    showMergePreviewModal,
    mergePreview,
    isLoadingMergePreview,
    isMerging,
    mergeOptions,
    setShowMergePreviewModal,
    setMergeOptions,
    handleSelectDuplicateForMerge,
    handleExecuteMerge,
  } = usePatronMerge()

  const {
    showCardPreviewModal,
    setShowCardPreviewModal,
  } = useLibraryCardPrinting()

  const {
    showEstatePanel,
  } = useEstateManagement()

  const {
    showDeletionSection,
    handleInitiateDeletion,
  } = usePatronDeletion()

  const {
    showSettingsPanel,
    setShowSettingsPanel,
  } = usePatronAccountSettings()

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('staffPatrons.staffAccessRequired'))
      navigate("/account")
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated, user, navigate])

  // Refresh holds for the currently selected patron without resetting the view
  const refreshHolds = useCallback(async () => {
    if (!token || !selectedPatron) return
    try {
      const holds = await getPatronHolds(token, selectedPatron.id)
      setSelectedPatron(prev => prev ? { ...prev, holds } : prev)
    } catch {
      // Silently fail -- the stale data is still visible
    }
  }, [token, selectedPatron, setSelectedPatron])

  // Hold action callbacks
  const handleCancelHold = useCallback(async (holdId: number) => {
    if (!token) return
    await cancelHold(token, holdId, "Cancelled by staff")
    toast.success("Hold cancelled")
    await refreshHolds()
  }, [token, refreshHolds])


  // Refetch checkouts for the selected patron and update state
  const refreshCheckouts = useCallback(async () => {
    if (!token || !selectedPatron) return
    try {
      const checkouts = await getPatronCheckouts(token, selectedPatron.id)
      setSelectedPatron(prev => prev ? { ...prev, checkouts } : prev)
    } catch {
      // silent - the action toast already informed the user
    }
  }, [token, selectedPatron, setSelectedPatron])

  const handleCheckoutHold = useCallback(async (holdId: number) => {
    if (!token || !selectedPatron) return
    try {
      await staffCheckoutHold(token, holdId)
      toast.success("Hold checked out")
      await refreshHolds()
      await refreshCheckouts()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Hold checkout failed")
    }
  }, [token, selectedPatron, refreshHolds, refreshCheckouts])

  // Inline circulation handlers
  const handleRenew = useCallback(async (checkoutId: number) => {
    if (!token) return
    try {
      await staffRenewCheckout(token, checkoutId)
      toast.success("Item renewed")
      await refreshCheckouts()
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Renewal failed"
      // Renewal cap is the only block staff can override here. The hold-queue
      // block ("someone else is waiting") is intentionally not overridable.
      if (/maximum number of/i.test(msg)) {
        if (window.confirm(`${msg}\n\nOverride and renew anyway? (Staff override, recorded in the audit log.)`)) {
          try {
            await staffRenewCheckout(token, checkoutId, true)
            toast.success("Item renewed (staff override)")
            await refreshCheckouts()
            return
          } catch (err2) {
            toast.error(err2 instanceof Error ? err2.message : "Override renewal failed")
            throw err2
          }
        }
        return
      }
      toast.error(msg)
      throw err
    }
  }, [token, refreshCheckouts])

  const handleCheckIn = useCallback(async (checkoutId: number) => {
    if (!token) return
    try {
      await returnItem(token, checkoutId)
      toast.success("Item checked in")
      await refreshCheckouts()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Check-in failed")
      throw err
    }
  }, [token, refreshCheckouts])

  // Filter patrons based on alert filter
  const filteredPatrons = filterPatronsByAlertStatus(patrons, patronStats, activeAlertFilter)

  // Bulk actions configuration
  const bulkActions: BulkAction[] = [
    {
      id: "block",
      label: t('staffPatrons.bulk.blockSelected'),
      variant: "danger",
      onExecute: async (ids: number[]) => await handleBulkBlock(ids),
    },
    {
      id: "unblock",
      label: t('staffPatrons.bulk.unblockSelected'),
      variant: "default",
      onExecute: async (ids: number[]) => await handleBulkUnblock(ids),
    },
    {
      id: "waive_fines",
      label: t('staffPatrons.bulk.waiveFines'),
      variant: "warning",
      onExecute: (ids: number[]) =>
        new Promise<BulkOperationResult>((resolve) => {
          bulkWaivePendingRef.current = { ids, resolve }
          setBulkWaiveModalOpen(true)
        }),
    },
    {
      id: "export",
      label: t('staffPatrons.bulk.exportSelected'),
      variant: "default",
      onExecute: async (ids: number[]) => await handleBulkExport(ids),
    },
    {
      id: "message",
      label: t('staffPatrons.bulk.messageSelected'),
      variant: "default",
      onExecute: (ids: number[]) => new Promise<BulkOperationResult>((resolve) => {
        setBulkMessageIds(ids)
        bulkMessageResolverRef.current = resolve
        setIsBulkMessageOpen(true)
      }),
    },
  ]

  const closeBulkMessage = (result?: BulkOperationResult) => {
    setIsBulkMessageOpen(false)
    if (bulkMessageResolverRef.current) {
      bulkMessageResolverRef.current(result ?? { success: true, successCount: 0, failureCount: 0, message: "Cancelled" })
      bulkMessageResolverRef.current = null
    }
    setBulkMessageIds([])
  }

  const handleAlertClick = (filter: "none" | "overdue" | "fines" | "inactive") => {
    setActiveAlertFilter(filter)
    setCurrentPage(1)
  }

  // Alert-card row actions: open the patron record, or open it and pop the
  // notification composer prefilled (staff reviews + sends; no silent send).
  const handleOpenPatronFromAlert = useCallback((patronId: number) => {
    void selectPatron({ id: patronId } as Patron)
  }, [selectPatron])

  const handleRemindPatronFromAlert = useCallback(async (patronId: number) => {
    await selectPatron({ id: patronId } as Patron)
    setIsNotificationModalOpen(true)
  }, [selectPatron])

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString()
  }

  return (
    <AdminShell title="Patron Management">
          <div className="flex items-center justify-between">
            <div>

              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffPatrons.searchAndManageLibraryPatrons')}</p>
            </div>
            <div className="flex items-center gap-2">
              {selectedPatron && (
                <button
                  onClick={() => setIsNotificationModalOpen(true)}
                  className="flex items-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/50 dark:hover:bg-earth-800 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium transition-colors"
                >
                  <Bell className="w-5 h-5" />
                  {t('staffPatrons.sendNotification')}
                </button>
              )}
              <button
                onClick={() => setIsAddPatronOpen(true)}
                className="flex items-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/50 dark:hover:bg-earth-800 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium transition-colors"
              >
                <UserPlus className="w-5 h-5" />
                {t('staffPatrons.registerPatron')}
              </button>
              <button
                onClick={() => setIsCardScanOpen(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
              >
                <Barcode className="w-5 h-5" />
                {t('staffPatrons.scanCard')}
              </button>
            </div>
          </div>

          {/* Statistics Dashboard */}
          <PatronStatisticsDashboard
            statistics={patronStats}
            isLoading={statsLoading}
            isDashboardExpanded={isDashboardExpanded}
            onExpandChange={setIsDashboardExpanded}
            activeAlertFilter={activeAlertFilter}
            onAlertFilterChange={setActiveAlertFilter}
            onAlertClick={handleAlertClick}
            onOpenPatron={handleOpenPatronFromAlert}
            onRemindPatron={handleRemindPatronFromAlert}
            onExpiringCardsClick={handleExpiringCardsClick}
            formatDate={formatDate}
          />

          {/* Saved-view presets */}
          <PatronFilterPresetsRow
            userPresets={presets.userPresets}
            activePresetId={presets.activePresetId}
            currentFilters={advancedFilters}
            currentStatusFilter={statusFilter}
            onApply={handleApplyPreset}
            onClearActive={handleClearActivePreset}
            onSavePreset={presets.saveCurrentAsPreset}
            onDeleteUserPreset={presets.deleteUserPreset}
          />

          {/* Search Panel */}
          <PatronSearchPanel
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            onSearch={handleSearch}
            isSearching={isSearching}
            onPageChange={setCurrentPage}
            onDebouncedSearch={handleDebouncedSearch}
            advancedFilters={advancedFilters}
            onAdvancedFiltersChange={setAdvancedFilters}
            onClearAdvancedFilters={clearAdvancedFilters}
            activeFilterCount={activeFilterCount}
          />

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Patron List */}
            <div className="xl:col-span-1 space-y-4">
              <PatronListTable
                patrons={patrons}
                totalPatrons={totalPatrons}
                filteredPatrons={filteredPatrons}
                selectedPatron={selectedPatron}
                isSearching={isSearching}
                isBulkMode={isBulkMode}
                onBulkModeToggle={() => setIsBulkMode(!isBulkMode)}
                bulkSelectedIds={bulkSelectedIds}
                onSelectPatron={selectPatron}
                onBulkSelectionToggle={toggleBulkSelectionWithRange}
                isBulkSelected={isBulkSelected}
                bulkActions={bulkActions}
                bulkOperationResult={bulkOperationResult}
                onBulkResultDismiss={() => setBulkOperationResult(null)}
                onBulkSelectedIdsChange={setBulkSelectedIds}
                clearBulkSelection={clearBulkSelection}
                activeAlertFilter={activeAlertFilter}
                onClearAlertFilter={() => setActiveAlertFilter("none")}
                sortBy={sortBy}
                sortDirection={sortDirection}
                onSortChange={updateSort}
              />
              <PatronPagination
                currentPage={currentPage}
                totalPages={totalPages}
                totalItems={totalPatrons}
                perPage={perPage}
                onPrevious={() => setCurrentPage(Math.max(1, currentPage - 1))}
                onNext={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                onPageChange={setCurrentPage}
                onPerPageChange={setPerPage}
              />
            </div>

            {/* Patron Detail */}
            <div className="xl:col-span-2">
              {selectedPatron ? (
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
                  <div className="p-6 border-b border-lsc-border dark:border-earth-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                          {selectedPatron.first_name} {selectedPatron.last_name}
                        </h2>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{selectedPatron.email}</p>
                        {/* Secondary meta: member-since + last-login as a definition
                            list so screen readers expose term/description pairs. */}
                        <dl className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                          <div className="flex items-center gap-1">
                            <dt className="sr-only">{t("staffPatrons.meta.memberSince", "Member since")}</dt>
                            <dd>{t("staffPatrons.meta.memberSinceLabel", "Member since")} {new Date(selectedPatron.created_at).toLocaleDateString()}</dd>
                          </div>
                          <span aria-hidden="true">.</span>
                          <div className="flex items-center gap-1">
                            <dt className="sr-only">{t("staffPatrons.meta.lastLogin", "Last login")}</dt>
                            <dd>
                              {t("staffPatrons.meta.lastLoginLabel", "Last login")} {selectedPatron.last_login
                                ? (() => {
                                    const diff = Date.now() - new Date(selectedPatron.last_login).getTime()
                                    const minutes = Math.floor(diff / 60000)
                                    const hours = Math.floor(diff / 3600000)
                                    const days = Math.floor(diff / 86400000)
                                    if (minutes < 1) return t("staffPatrons.meta.activeNow", "active now")
                                    if (minutes < 60) return `${minutes}m ago`
                                    if (hours < 24) return `${hours}h ago`
                                    if (days < 30) return `${days}d ago`
                                    return `${Math.floor(days / 30)}mo ago`
                                  })()
                                : t("staffPatrons.meta.neverLoggedIn", "never")}
                            </dd>
                          </div>
                          {/* Card expiry: shown here only when NOT urgent.
                              Warning/expired bubbles up to the chip row above. */}
                          {selectedPatron.card_expires_at && expirySeverity(selectedPatron.card_expires_at) === "default" && (
                            <>
                              <span aria-hidden="true">.</span>
                              <div className="flex items-center gap-1">
                                <dt className="sr-only">{t("staffPatrons.meta.cardExpires", "Card expires")}</dt>
                                <dd>{t("staffPatrons.meta.cardExpiresLabel", "Card expires")} {new Date(selectedPatron.card_expires_at).toLocaleDateString()}</dd>
                              </div>
                            </>
                          )}
                        </dl>
                      </div>
                      <button
                        onClick={refreshPatron}
                        disabled={isRefreshing}
                        className="p-2 rounded-lg border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/50 dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 transition-colors disabled:opacity-50"
                        title="Refresh patron data"
                      >
                        {isRefreshing ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-5 h-5" />
                        )}
                      </button>
                    </div>

                    {/* Priority chip row: status + (urgent-only) expiry are
                        color-bearing; card number + card type stay as chips
                        but in muted/secondary styling. */}
                    <div className="flex flex-wrap items-center gap-2 mt-3">
                      {/* Status badge -- always color-bearing */}
                      {selectedPatron.patron_status && (
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                          {
                            active: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300",
                            suspended: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300",
                            blocked: "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300",
                            deceased: "bg-earth-100 text-earth-600 dark:bg-earth-800/50 dark:text-earth-400",
                          }[selectedPatron.patron_status] || ""
                        }`}>
                          <Shield className="w-3 h-3" />
                          {selectedPatron.patron_status.charAt(0).toUpperCase() + selectedPatron.patron_status.slice(1)}
                        </span>
                      )}

                      {/* Card expiry -- color-bearing ONLY when expired or .30d
                          out. Calm-state expiry moves to the meta <dl> above. */}
                      {selectedPatron.card_expires_at && (() => {
                        const severity = expirySeverity(selectedPatron.card_expires_at)
                        if (severity === "default") return null
                        const expiryDate = new Date(selectedPatron.card_expires_at!)
                        return (
                          <span
                            data-testid="expiry-chip"
                            data-severity={severity}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                              severity === "error"
                                ? "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300"
                                : "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300"
                            }`}
                          >
                            <Calendar className="w-3 h-3" />
                            {severity === "error" ? t("staffPatrons.chip.expired", "Expired") : `${t("staffPatrons.chip.expSoon", "Exp")} ${expiryDate.toLocaleDateString()}`}
                          </span>
                        )
                      })()}

                      {/* Library card number -- muted, not color-bearing */}
                      {selectedPatron.library_card && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                          <CreditCard className="w-3 h-3" />
                          <span className="font-mono">{selectedPatron.library_card}</span>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(selectedPatron.library_card!)
                              toast.success(t("staffPatrons.cardCopied", "Card number copied"))
                            }}
                            className="ml-0.5 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
                            aria-label="Copy card number"
                            title="Copy card number"
                          >
                            <Copy className="w-3 h-3" />
                          </button>
                        </span>
                      )}

                      {/* Card type -- muted; was previously colored. */}
                      {selectedPatron.card_type && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                          {selectedPatron.card_type.charAt(0).toUpperCase() + selectedPatron.card_type.slice(1)}
                        </span>
                      )}
                    </div>

                    {/* Recent notes strip -- the most-consulted patron data,
                        promoted from the 6th sub-tab to a sticky position. */}
                    {token && (
                      <PatronRecentNotesStrip
                        token={token}
                        patronId={selectedPatron.id}
                        userId={user?.id}
                        onOpenNote={handleOpenNoteInTab}
                        onNoteCreated={() => setNotesRefreshNonce((n) => n + 1)}
                      />
                    )}

                    {/* Tab Navigation */}
                    <div className="flex gap-2 mt-6 border-b border-lsc-border dark:border-earth-700">
                      {[
                        { id: "profile", label: t('staffPatrons.tabs.profile') },
                        { id: "checkouts", label: t('staffPatrons.tabs.checkouts') },
                        { id: "holds", label: t('staffPatrons.tabs.holds') },
                        { id: "fines", label: t('staffPatrons.tabs.fines') },
                        { id: "history", label: t('staffPatrons.tabs.history') },
                        { id: "communication", label: t('staffPatrons.tabs.communication') },
                        ...((user?.role === "super_admin" || user?.role === "director" || user?.role === "legal")
                          ? [{ id: "pii-access", label: t('staffPatrons.tabs.piiAccess') }]
                          : []),
                      ].map((tab) => (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id as typeof activeTab)}
                          className={`px-4 py-2 font-medium transition-colors ${
                            activeTab === tab.id
                              ? "text-lsc-rose dark:text-lsc-rose-light border-b-2 border-lsc-rose dark:border-lsc-rose-light"
                              : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                          }`}
                        >
                          {tab.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Tab Content */}
                  <div className="p-6">
                    {activeTab === "profile" && (
                      <PatronProfileTab
                        patron={selectedPatron}
                        isLoadingFamily={false}
                        familyData={familyData}
                        onPatronUpdated={(updatedPatron) => {
                          setSelectedPatron(updatedPatron)
                          updatePatronInList(updatedPatron.id, {
                            first_name: updatedPatron.first_name,
                            last_name: updatedPatron.last_name,
                            phone: updatedPatron.phone,
                            address: updatedPatron.address,
                          })
                        }}
                      />
                    )}

                    {activeTab === "checkouts" && (
                      <PatronCheckoutsTab
                        checkouts={selectedPatron.checkouts || []}
                        onRenew={handleRenew}
                        onCheckIn={handleCheckIn}
                      />
                    )}

                    {activeTab === "holds" && (
                      <PatronHoldsTab
                        holds={selectedPatron.holds || []}
                        onCancelHold={handleCancelHold}
                        onCheckoutHold={handleCheckoutHold}
                      />
                    )}

                    {activeTab === "fines" && <PatronFinesTab selectedPatron={selectedPatron} />}

                    {activeTab === "history" && (
                      <PatronHistoryTab
                        activityData={activityData}
                        isLoading={activityLoading}
                        currentPage={activityPage}
                        perPage={10}
                        activityTypeFilter={activityTypeFilter}
                        onPageChange={setActivityPage}
                        onActivityTypeFilterChange={setActivityTypeFilter}
                      />
                    )}

                    {activeTab === "communication" && (
                      <PatronCommunicationTab
                        patronId={selectedPatron.id}
                        scrollToNoteId={scrollToNoteId}
                        onScrollComplete={() => setScrollToNoteId(null)}
                        refreshNonce={notesRefreshNonce}
                      />
                    )}

                    {activeTab === "pii-access" && (
                      <PatronPIIAccessTab patronId={selectedPatron.id} />
                    )}
                  </div>

                  {/* Estate Management Panel */}
                  {showEstatePanel && (
                    <div className="p-6 border-t border-lsc-border dark:border-earth-700">
                      <EstateManagementPanel
                        patronId={selectedPatron.id}
                        isDeceased={!!selectedPatron.date_of_death}
                        {...(selectedPatron.date_of_death !== undefined && { dateOfDeath: selectedPatron.date_of_death })}
                        {...(selectedPatron.estate_contact_name !== undefined && { estateContactName: selectedPatron.estate_contact_name })}
                        {...(selectedPatron.estate_followup_required !== undefined && { estateFollowupRequired: selectedPatron.estate_followup_required })}
                      />
                    </div>
                  )}

                  {/* Deletion Management Panel */}
                  {showDeletionSection && (
                    <div className="p-6 border-t border-lsc-border dark:border-earth-700">
                      <DeletionManagementPanel
                        patronId={selectedPatron.id}
                        onInitiateDeletion={() => handleInitiateDeletion(selectedPatron.id, true)}
                      />
                    </div>
                  )}
                </div>
              ) : (
                <PatronEmptyState
                  userId={user?.id}
                  headline={t("staffPatrons.selectAPatronToView")}
                  onScanCard={() => setIsCardScanOpen(true)}
                  onRegisterPatron={() => setIsAddPatronOpen(true)}
                  onSelectRecent={(patronId) => {
                    // selectPatron only reads .id; usePatronDetail re-fetches
                    // the full record. A minimal stub avoids a second roundtrip.
                    void selectPatron({ id: patronId } as Patron)
                  }}
                />
              )}
            </div>

      {/* Modals */}
      <CardScanModal
        isOpen={isCardScanOpen}
        onClose={() => setIsCardScanOpen(false)}
      />

      <AddPatronModal
        isOpen={isAddPatronOpen}
        onClose={() => setIsAddPatronOpen(false)}
        onSuccess={() => {
          setIsAddPatronOpen(false)
          performSearch({ page: 1 })
        }}
      />

      <PatronMergeDialogs
        showDuplicatesModal={showDuplicatesModal}
        onClose={() => setShowDuplicatesModal(false)}
        duplicates={duplicates}
        isLoadingDuplicates={isLoadingDuplicates}
        selectedDuplicate={selectedDuplicate}
        showMergePreviewModal={showMergePreviewModal}
        mergePreview={mergePreview}
        isLoadingMergePreview={isLoadingMergePreview}
        isMerging={isMerging}
        mergeOptions={mergeOptions}
        onSelectDuplicate={(dup) => token && handleSelectDuplicateForMerge(token, dup)}
        onExecuteMerge={() => {
          if (token && mergePreview) {
            handleExecuteMerge(token, mergePreview.primary_patron.id, mergePreview.secondary_patron.id)
          }
        }}
        onCloseMergePreview={() => setShowMergePreviewModal(false)}
        onSetMergeOptions={setMergeOptions}
      />

      <BulkWaiveReasonModal
        isOpen={bulkWaiveModalOpen}
        patronCount={bulkWaivePendingRef.current?.ids.length ?? 0}
        onCancel={() => {
          bulkWaivePendingRef.current?.resolve({
            success: true,
            successCount: 0,
            failureCount: 0,
            message: t('staffPatrons.bulk.waiveCancelled'),
          })
          bulkWaivePendingRef.current = null
          setBulkWaiveModalOpen(false)
        }}
        onSubmit={async (reason) => {
          const pending = bulkWaivePendingRef.current
          if (!pending) return
          setBulkWaiveModalOpen(false)
          const result = await handleBulkWaiveFines(pending.ids, reason)
          pending.resolve(result)
          bulkWaivePendingRef.current = null
        }}
      />
      <LibraryCardPrintModal
        isOpen={showCardPreviewModal}
        onClose={() => setShowCardPreviewModal(false)}
        patronName={selectedPatron ? `${selectedPatron.first_name} ${selectedPatron.last_name}` : ""}
        {...(selectedPatron && { libraryCardNumber: selectedPatron.library_card })}
      />

      <PatronAccountSettingsModal
        isOpen={showSettingsPanel}
        onClose={() => setShowSettingsPanel(false)}
        patronId={selectedPatron?.id || 0}
        {...(selectedPatron && { patronName: `${selectedPatron.first_name} ${selectedPatron.last_name}` })}
      />

      <SendNotificationModal
        isOpen={isNotificationModalOpen}
        patron={selectedPatron}
        onClose={() => setIsNotificationModalOpen(false)}
        onSend={async (patron, data) => {
          if (!token) throw new Error("Not authenticated")
          await sendPatronMessage(token, patron.id, {
            message_type: "custom",
            channel: data.type,
            subject: data.subject || data.message.substring(0, 100),
            body: data.message,
          })
        }}
      />

      <BulkMessageModal
        isOpen={isBulkMessageOpen}
        onClose={() => closeBulkMessage()}
        recipientCount={bulkMessageIds.length}
        onSend={async ({ subject, body, channels }) => {
          const response = await handleBulkMessage({
            patron_ids: bulkMessageIds,
            subject,
            body,
            channels,
          })
          if (bulkMessageResolverRef.current) {
            bulkMessageResolverRef.current({
              success: response.failed === 0,
              successCount: response.sent,
              failureCount: response.failed + response.capped,
              message: `${response.sent} sent, ${response.capped} capped, ${response.failed} failed`,
            })
            bulkMessageResolverRef.current = null
          }
          return response
        }}
      />
      </div>
    </AdminShell>
  )
}
