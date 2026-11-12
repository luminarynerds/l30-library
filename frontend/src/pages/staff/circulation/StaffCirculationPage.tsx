/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useCallback } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"
import { AdminShell } from "@/components/shells/AdminShell"
import { getPatronCheckouts } from "@/api/api"
import { Book, Keyboard, LogOut, LogIn, RefreshCw, Bookmark, Monitor } from "lucide-react"
import toast from "react-hot-toast"
import { DestructiveActionDialog } from "@/components/dialogs/DestructiveActionDialog"
import { usePatronKeyboardShortcuts } from "@/hooks/usePatronKeyboardShortcuts"
import { useKeyboardPreferences } from "@/hooks/useKeyboardPreferences"
import KeyboardShortcutsHelpModal from "@/components/staff/KeyboardShortcutsHelpModal"
import ProblemResolutionModal from "@/components/staff/ProblemResolutionModal"
import { OverrideHoldModal } from "@/components/staff/OverrideHoldModal"
import { useTranslation } from "@/i18n"
import { useJourneyTracker } from "@/hooks/useJourneyTracker"
import { useState } from "react"

import { usePatronSearch } from "./hooks/usePatronSearch"
import { useCheckout } from "./hooks/useCheckout"
import { useCheckin } from "./hooks/useCheckin"
import { useRenewal } from "./hooks/useRenewal"
import { PatronSearchSection } from "./components/PatronSearchSection"
import { PatronContextStrip } from "./components/PatronContextStrip"
import { QuickCheckoutSection } from "./components/QuickCheckoutSection"
import { QuickCheckinSection } from "./components/QuickCheckinSection"
import { HoldTrapCard } from "./components/HoldTrapCard"
import { CurrentCheckoutsList } from "./components/CurrentCheckoutsList"
import { CheckoutSlip } from "./components/CheckoutSlip"
import { ActivityFeed, type ActivityEntry } from "./components/ActivityFeed"
import { QuickMessagePanel } from "./components/QuickMessagePanel"
import { useOrganizationFeatures } from "@/contexts/OrganizationFeaturesContext"
import { useCirculationBroadcast } from "./hooks/useCirculationBroadcast"

export default function StaffCirculationPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get("tab") || "all"
  const setActiveTab = (tab: string) => {
    if (tab === "all") { setSearchParams({}) } else { setSearchParams({ tab }) }
  }
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false)
  // Session-scoped activity log; cleared on patron switch via handleClearPatron.
  const [activityEntries, setActivityEntries] = useState<ActivityEntry[]>([])
  const appendActivity = useCallback((entry: Omit<ActivityEntry, "id" | "timestamp">) => {
    setActivityEntries((prev) => [
      ...prev,
      { ...entry, id: `${Date.now()}-${prev.length}`, timestamp: new Date() },
    ])
  }, [])

  // Refs for keyboard navigation
  const searchInputRef = useRef<HTMLInputElement>(null)
  const checkoutInputRef = useRef<HTMLInputElement>(null)
  const checkinInputRef = useRef<HTMLInputElement>(null)

  // Initialize hooks
  const search = usePatronSearch(token)
  const checkout = useCheckout(token)
  const checkin = useCheckin(token, { inputRef: checkinInputRef })
  const renewal = useRenewal(token)
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { broadcastCheckout, broadcastCheckin, broadcastClear } = useCirculationBroadcast()
  const slipEnabled = isFeatureEnabled('circulation_print_slip_enabled')
  // Default ON: flag absent or context still loading → still render the card.
  const holdTrapCardEnabled = isFeatureEnabled("circulation_hold_trap_card_enabled")
  // Default OFF — header link + popout route both gate on this flag.
  const customerDisplayEnabled = isFeatureEnabled('customer_display_enabled')
  const { trackStage } = useJourneyTracker({ journeyType: 'staff_checkin' })

  // Wire up selectPatron to load checkouts and auto-focus
  // Journey tracking: checkin_started
  useEffect(() => { trackStage("checkin_started") }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectPatron = useCallback((patron: Parameters<typeof search.selectPatron>[0]) => {
    trackStage('patron_identified')
    search.selectPatron(patron, () => {
      if (patron.is_active) {
        setTimeout(() => checkoutInputRef.current?.focus(), 100)
      }
    })
    if (token) {
      renewal.refreshCheckouts(patron.id)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // Wire up clearPatron to also clear checkouts
  const handleClearPatron = useCallback(() => {
    search.clearPatron()
    renewal.setPatronCheckouts([])
    broadcastClear()
    setActivityEntries([])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Wire up checkout to refresh checkouts on complete
  const handleCheckoutRefresh = useCallback(async (patronId: number) => {
    if (!token) return
    trackStage('items_scanned')
    const last = checkout.lastCheckout
    if (last) {
      appendActivity({
        type: "checkout",
        title: last.item_title || t('staffCirculation.itemFallback'),
        patronName: search.selectedPatron
          ? `${search.selectedPatron.first_name} ${search.selectedPatron.last_name}`
          : undefined,
      })
    }
    const checkouts = await getPatronCheckouts(token, patronId)
    renewal.setPatronCheckouts(checkouts)
    if (search.selectedPatron) {
      broadcastCheckout(search.selectedPatron, checkouts, null)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, checkout.lastCheckout, search.selectedPatron, appendActivity])

  // Wire up checkin to refresh checkouts if patron selected
  const handleCheckinComplete = useCallback(async () => {
    trackStage('checkin_completed')
    const last = checkin.lastCheckinResult
    if (last) {
      appendActivity({
        type: "checkin",
        title: last.itemTitle || t('staffCirculation.itemFallback'),
      })
    }
    if (search.selectedPatron && token) {
      const checkouts = await getPatronCheckouts(token, search.selectedPatron.id)
      renewal.setPatronCheckouts(checkouts)
      broadcastCheckin(search.selectedPatron, checkouts, null)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, search.selectedPatron, checkin.lastCheckinResult, appendActivity])

  // Warn before leaving with active patron session
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (search.selectedPatron) {
        e.preventDefault()
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [search.selectedPatron])

  // Autofocus based on active tab
  useEffect(() => {
    if (!authLoading && isAuthenticated && user && user.role !== "patron") {
      const timer = setTimeout(() => {
        if (activeTab === "checkin") { checkinInputRef.current?.focus() }
        else if (activeTab === "renew") { searchInputRef.current?.focus() }
        else { searchInputRef.current?.focus() }
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [authLoading, isAuthenticated, user, activeTab])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (!authLoading && (!user || user.role === "patron")) { toast.error(t('staffCirculation.staffAccessRequired')); navigate("/account") } }, [authLoading, isAuthenticated, user, navigate])

  // Keyboard shortcut handlers
  const handleFocusSearch = useCallback(() => {
    searchInputRef.current?.focus()
  }, [])

  const handleQuickCheckout = useCallback(() => {
    if (search.selectedPatron && search.selectedPatron.is_active) {
      checkoutInputRef.current?.focus()
    }
  }, [search.selectedPatron])

  const handleQuickCheckin = useCallback(() => {
    checkinInputRef.current?.focus()
  }, [])

  const handleRenewAllWithLog = useCallback(async () => {
    const before = renewal.patronCheckouts.length
    await renewal.handleRenewAll(search.selectedPatron)
    if (before > 0) {
      appendActivity({
        type: "renewal",
        title: t('staffCirculation.renewAllEntryTitle', { count: before }),
        patronName: search.selectedPatron
          ? `${search.selectedPatron.first_name} ${search.selectedPatron.last_name}`
          : undefined,
      })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.selectedPatron, renewal.patronCheckouts.length, appendActivity])

  const handleRenewAllShortcut = handleRenewAllWithLog

  const handlePrintReceipt = useCallback(() => {
    if (!search.selectedPatron) {
      toast.error(t('staffCirculation.pleaseSelectAPatronFirst2'))
      return
    }
    window.print()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.selectedPatron])

  // Keyboard preferences
  const { bindings } = useKeyboardPreferences(user?.id)

  // Integrate keyboard shortcuts
  usePatronKeyboardShortcuts({
    onFocusSearch: handleFocusSearch,
    onEscape: search.handleEscape,
    onNavigateUp: search.handleNavigateUp,
    onNavigateDown: search.handleNavigateDown,
    onEnter: search.handleEnter,
    onEdit: () => {},
    onBlockToggle: () => {},
    onAddNote: () => {},
    onShowHelp: () => setShowShortcutsHelp(true),
    onQuickCheckout: handleQuickCheckout,
    onQuickCheckin: handleQuickCheckin,
    onRenewAll: handleRenewAllShortcut,
    onPrintReceipt: handlePrintReceipt,
    enabled: !showShortcutsHelp,
    bindings,
  })

  return (
    <AdminShell
      title={t('staffCirculation.circulationDesk')}
      actions={
        <div className="flex items-center gap-2">
          {customerDisplayEnabled && (
            <a
              href="/staff/circulation/display"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg transition-colors"
              aria-label={t('staffCirculation.openPatronDisplay')}
            >
              <Monitor className="w-4 h-4" aria-hidden="true" />
              <span>{t('staffCirculation.patronDisplay')}</span>
            </a>
          )}
          <button
            onClick={() => setShowShortcutsHelp(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg transition-colors"
            aria-label={t('aria.staffCirculation.showKeyboardShortcuts')}
          >
            <Keyboard className="w-4 h-4" aria-hidden="true" />
            <span>{t('staffCirculation.shortcuts')}</span>
            <kbd className="hidden md:inline-block px-1.5 py-0.5 text-xs font-mono bg-lsc-cream dark:bg-lsc-brown rounded">?</kbd>
          </button>
        </div>
      }
    >

          {/* Tab Bar */}
          <div className="flex gap-1 bg-lsc-cream/50 dark:bg-earth-800/50 p-1 rounded-xl mb-4 overflow-x-auto">
            {[
              { id: "all", label: t('staffCirculation.tabAll'), icon: Book },
              { id: "checkout", label: t('staffCirculation.tabCheckOut'), icon: LogOut },
              { id: "checkin", label: t('staffCirculation.tabCheckIn'), icon: LogIn },
              { id: "renew", label: t('staffCirculation.tabRenew'), icon: RefreshCw },
              { id: "holds", label: t('staffCirculation.tabHolds'), icon: Bookmark },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  if (tab.id === "holds") { navigate("/staff/holds/shelf") }
                  else { setActiveTab(tab.id) }
                }}
                aria-current={activeTab === tab.id ? "true" : undefined}
                aria-label={tab.label}
                className={`flex items-center gap-2 px-3 md:px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? "bg-lsc-white dark:bg-earth-800 text-lsc-rose shadow-sm"
                    : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-white/50 dark:hover:bg-earth-800/30"
                }`}
              >
                <tab.icon className="w-4 h-4" aria-hidden="true" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>

          <div className={`grid gap-4 md:gap-6 ${activeTab === "all" ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1 max-w-2xl"}`}>
            {(activeTab === "all" || activeTab === "checkout" || activeTab === "renew") && <div className="space-y-4 md:space-y-6">
              <PatronSearchSection
                patronQuery={search.patronQuery}
                setPatronQuery={search.setPatronQuery}
                searchResults={search.searchResults}
                selectedResultIndex={search.selectedResultIndex}
                isSearching={search.isSearching}
                recentPatrons={search.recentPatrons}
                handlePatronSearch={search.handlePatronSearch}
                selectPatron={handleSelectPatron}
                handleNavigateUp={search.handleNavigateUp}
                handleNavigateDown={search.handleNavigateDown}
                searchInputRef={searchInputRef}
              />

              {search.selectedPatron && (
                <>
                  <PatronContextStrip
                    patronId={search.selectedPatron.id}
                    patronName={`${search.selectedPatron.first_name || ''} ${search.selectedPatron.last_name || ''}`.trim() || t('staffCirculation.thisPatronFallback')}
                    onTileClick={(section) => {
                      if (section === "holds") {
                        navigate("/staff/holds/shelf")
                      } else if (section === "checkouts") {
                        if (activeTab !== "all") setActiveTab("checkin")
                        requestAnimationFrame(() => {
                          document.getElementById("circulation-checkouts-section")?.scrollIntoView({ block: "nearest", behavior: "smooth" })
                        })
                      }
                    }}
                  />
                  <QuickCheckoutSection
                    selectedPatron={search.selectedPatron}
                    itemBarcode={checkout.itemBarcode}
                    setItemBarcode={checkout.setItemBarcode}
                    isCheckingOut={checkout.isCheckingOut}
                    checkoutSuccess={checkout.checkoutSuccess}
                    handleCheckout={(e) => checkout.handleCheckout(e, search.selectedPatron!.id, handleCheckoutRefresh)}
                    clearPatron={handleClearPatron}
                    checkoutInputRef={checkoutInputRef}
                    checkoutError={checkout.checkoutError}
                    onDismissError={checkout.clearCheckoutError}
                    onShowErrorDetails={checkout.openProblemModal}
                  />
                  {slipEnabled && checkout.lastCheckout &&
                    checkout.lastCheckout.user_id === search.selectedPatron.id && (
                    <CheckoutSlip
                      checkout={checkout.lastCheckout}
                      patron={search.selectedPatron}
                      token={token}
                    />
                  )}
                </>
              )}
            </div>}

            {(activeTab === "all" || activeTab === "checkin") && <div className="space-y-4 md:space-y-6">
              <QuickCheckinSection
                checkinBarcode={checkin.checkinBarcode}
                setCheckinBarcode={checkin.setCheckinBarcode}
                isCheckingIn={checkin.isCheckingIn}
                checkinSuccess={checkin.checkinSuccess}
                handleCheckin={(e) => checkin.handleCheckin(e, handleCheckinComplete)}
                checkinInputRef={checkinInputRef}
              />

              {holdTrapCardEnabled && checkin.lastNextHold && (
                <HoldTrapCard
                  nextHold={checkin.lastNextHold}
                  onDismiss={checkin.dismissNextHold}
                />
              )}

              {search.selectedPatron && (
                <div id="circulation-checkouts-section">
                  <CurrentCheckoutsList
                    selectedPatron={search.selectedPatron}
                    patronCheckouts={renewal.patronCheckouts}
                    loadingCheckouts={renewal.loadingCheckouts}
                    isRenewingAll={renewal.isRenewingAll}
                    onRenewAllClick={() => renewal.setShowRenewConfirm(true)}
                  />
                </div>
              )}

              {search.selectedPatron && (
                <details
                  open
                  data-testid="activity-feed-details"
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden"
                >
                  <summary className="cursor-pointer px-4 py-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream select-none">
                    {t('staffCirculation.sessionActivity')}
                  </summary>
                  <div className="px-1 pb-1">
                    <ActivityFeed entries={activityEntries} />
                  </div>
                </details>
              )}

              {search.selectedPatron && token && (
                <details
                  data-testid="quick-message-details"
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden"
                >
                  <summary className="cursor-pointer px-4 py-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream select-none">
                    {t('staffCirculation.quickMessage.heading')}
                  </summary>
                  <div className="px-1 pb-1">
                    <QuickMessagePanel patron={search.selectedPatron} token={token} />
                  </div>
                </details>
              )}
            </div>}
          </div>
      {/* Keyboard Shortcuts Help Modal */}
      <KeyboardShortcutsHelpModal
        isOpen={showShortcutsHelp}
        onClose={() => setShowShortcutsHelp(false)}
      />

      {/* Problem Resolution Modal */}
      {/* Renew All Confirmation */}
      <DestructiveActionDialog
        isOpen={renewal.showRenewConfirm}
        title={t('staffCirculation.renewAllItemsTitle')}
        message={t('staffCirculation.renewAllItemsConfirm', { name: `${search.selectedPatron?.first_name || ''} ${search.selectedPatron?.last_name || ''}`.trim() || t('staffCirculation.thisPatronFallback') })}
        onConfirm={() => {
          renewal.setShowRenewConfirm(false)
          handleRenewAllWithLog()
        }}
        onCancel={() => renewal.setShowRenewConfirm(false)}
      />

      {checkout.problemModal && search.selectedPatron && (
        <ProblemResolutionModal
          problem={checkout.problemModal}
          patronId={search.selectedPatron.id}
          onClose={checkout.clearProblemModal}
          onActionExecuted={() => {
            if (search.selectedPatron && token) {
              getPatronCheckouts(token, search.selectedPatron.id).then(renewal.setPatronCheckouts)
            }
          }}
          onRetryCheckout={() => checkout.handleRetryCheckout(search.selectedPatron!.id, handleCheckoutRefresh)}
        />
      )}

      {checkout.holdOverride && search.selectedPatron && (
        <OverrideHoldModal
          holdOverride={checkout.holdOverride}
          walkInPatronName={`${search.selectedPatron.first_name} ${search.selectedPatron.last_name}`}
          isSubmitting={checkout.isCheckingOut}
          onConfirm={(disposition) =>
            checkout.handleOverrideCheckout(search.selectedPatron!.id, disposition, handleCheckoutRefresh)
          }
          onCancel={checkout.clearHoldOverride}
        />
      )}
    </AdminShell>
  )
}
