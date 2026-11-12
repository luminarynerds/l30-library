/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  getItemCopyLifecycle,
  getCatalogItemLifecycle,
  searchItemsForLifecycle,
  createLifecycleEvent,
  createBatchLifecycleEvents,
  filterEventsByStage,
  getLifecycleAlerts,
  LifecycleTimeline,
  LifecycleEventType,
  LifecycleStage,
  LifecycleEventCreate,
  LifecycleSearchResult,
  LifecycleAlert,
} from "../api/lifecycle-api"
import { Loader2, Plus, Filter, History } from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation } from '@/i18n'
import { LifecycleSearchPanel } from "../components/lifecycle/LifecycleSearchPanel"
import { LifecycleFiltersPanel } from "../components/lifecycle/LifecycleFiltersPanel"
import { LifecycleViewModeTabs, type LifecycleViewMode } from "../components/lifecycle/LifecycleViewModeTabs"
import { LifecycleCopiesSelector } from "../components/lifecycle/LifecycleCopiesSelector"
import { LifecycleTimelineView } from "../components/lifecycle/LifecycleTimelineView"
import { LifecycleStagesView } from "../components/lifecycle/LifecycleStagesView"
import { LifecycleStatsView } from "../components/lifecycle/LifecycleStatsView"
import { LifecycleBulkView, type BulkQueueItem } from "../components/lifecycle/LifecycleBulkView"
import { LifecycleAddEventModal } from "../components/lifecycle/LifecycleAddEventModal"

type SearchType = "keyword" | "copy" | "item" | "scan"

export default function StaffLifecycleManagementPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [viewMode, setViewMode] = useState<LifecycleViewMode>("search")
  const [isLoading, setIsLoading] = useState(false)

  const [searchType, setSearchType] = useState<SearchType>("keyword")
  const [searchId, setSearchId] = useState("")
  const [searchResults, setSearchResults] = useState<LifecycleSearchResult[]>([])
  const scanInputRef = useRef<HTMLInputElement>(null)

  const [timelines, setTimelines] = useState<LifecycleTimeline[]>([])
  const [selectedTimeline, setSelectedTimeline] = useState<LifecycleTimeline | null>(null)

  const [stageFilter, setStageFilter] = useState<LifecycleStage | "all">("all")
  const [showFilters, setShowFilters] = useState(false)

  const [showAddEventModal, setShowAddEventModal] = useState(false)
  const [newEvent, setNewEvent] = useState<Partial<LifecycleEventCreate>>({})

  const [bulkEventType, setBulkEventType] = useState<LifecycleEventType | "">("")
  const [bulkDescription, setBulkDescription] = useState("")
  const [bulkQueue, setBulkQueue] = useState<BulkQueueItem[]>([])
  const [bulkSubmitting, setBulkSubmitting] = useState(false)
  const bulkScanRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, user, navigate, t])

  const handleSearch = useCallback(async () => {
    if (!token || !searchId.trim()) {
      toast.error(t('toast.staffLifecycleManagement.pleaseEnterASearchTerm'))
      return
    }

    setIsLoading(true)
    setSearchResults([])
    try {
      if (searchType === "keyword") {
        const results = await searchItemsForLifecycle(token, searchId.trim())
        setSearchResults(results)
        if (results.length === 0) {
          toast("No items found")
        }
      } else {
        const id = parseInt(searchId.trim())
        if (isNaN(id)) {
          toast.error(t('toast.staffLifecycleManagement.pleaseEnterAValidNumeric'))
          return
        }
        if (searchType === "copy") {
          const timeline = await getItemCopyLifecycle(token, id)
          setTimelines([timeline])
          setSelectedTimeline(timeline)
        } else {
          const itemTimelines = await getCatalogItemLifecycle(token, id)
          setTimelines(itemTimelines)
          setSelectedTimeline(itemTimelines.length > 0 ? itemTimelines[0]! : null)
        }
        setViewMode("timeline")
      }
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.selectionList.searchFailed'))
      setTimelines([])
      setSelectedTimeline(null)
    } finally {
      setIsLoading(false)
    }
  }, [token, searchId, searchType, t])

  const handleSelectResult = useCallback(async (result: LifecycleSearchResult) => {
    if (!token) return
    setIsLoading(true)
    try {
      const timeline = await getItemCopyLifecycle(token, result.copy_id)
      setTimelines([timeline])
      setSelectedTimeline(timeline)
      setSearchResults([])
      setViewMode("timeline")
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffInventory.failedToLoadLifecycle'))
    } finally {
      setIsLoading(false)
    }
  }, [token, t])

  const handleAddEvent = async () => {
    if (!token || !selectedTimeline || !newEvent.event_type) {
      toast.error(t('staffLifecycleManagement.pleaseFillInTheRequired'))
      return
    }

    try {
      setIsLoading(true)
      await createLifecycleEvent(token, {
        item_copy_id: selectedTimeline.item_copy_id,
        event_type: newEvent.event_type,
        description: newEvent.description || null,
        metadata: newEvent.metadata || {},
      })
      toast.success(t('toast.staffLifecycleManagement.eventAddedSuccessfully'))
      setShowAddEventModal(false)
      setNewEvent({})
      const refreshed = await getItemCopyLifecycle(token, selectedTimeline.item_copy_id)
      setSelectedTimeline(refreshed)
      setTimelines(prev => prev.map(tl => tl.item_copy_id === refreshed.item_copy_id ? refreshed : tl))
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffLifecycleManagement.failedToAddEvent'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleBarcodeScan = useCallback(async (barcode: string) => {
    if (!token || !barcode.trim()) return
    setIsLoading(true)
    try {
      const results = await searchItemsForLifecycle(token, barcode.trim())
      if (results.length === 1) {
        const timeline = await getItemCopyLifecycle(token, results[0]!.copy_id)
        setTimelines([timeline])
        setSelectedTimeline(timeline)
        setSearchResults([])
        setViewMode("timeline")
        toast.success(`Loaded: ${results[0]!.title}`)
      } else if (results.length > 1) {
        setSearchResults(results)
        toast("Multiple items found -- select one from the list")
      } else {
        toast.error("No item found for that barcode")
      }
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Scan lookup failed")
    } finally {
      setIsLoading(false)
      setSearchId("")
      if (scanInputRef.current) scanInputRef.current.focus()
    }
  }, [token])

  const handleBulkScan = useCallback(async (barcode: string) => {
    if (!token || !barcode.trim()) return
    if (bulkQueue.some(q => q.barcode === barcode.trim())) {
      toast.error("Item already in queue")
      return
    }
    try {
      const results = await searchItemsForLifecycle(token, barcode.trim())
      if (results.length === 1) {
        setBulkQueue(prev => [...prev, {
          copy_id: results[0]!.copy_id,
          barcode: results[0]!.barcode,
          title: results[0]!.title,
          author: results[0]!.author,
          status: "queued",
        }])
        toast.success(`Added: ${results[0]!.title}`)
      } else if (results.length > 1) {
        toast.error("Multiple matches -- use keyword search to disambiguate")
      } else {
        toast.error("No item found for that barcode")
      }
    } catch {
      toast.error("Lookup failed")
    }
    if (bulkScanRef.current) {
      bulkScanRef.current.value = ""
      bulkScanRef.current.focus()
    }
  }, [token, bulkQueue])

  const handleBulkSubmit = useCallback(async () => {
    if (!token || !bulkEventType || bulkQueue.length === 0) return
    setBulkSubmitting(true)
    try {
      const resp = await createBatchLifecycleEvents(token, {
        event_type: bulkEventType as LifecycleEventType,
        description: bulkDescription || null,
        items: bulkQueue.map(q => ({ item_copy_id: q.copy_id })),
      })
      setBulkQueue(prev => prev.map((item, i) => {
        const result = resp.results[i]
        return {
          copy_id: item.copy_id,
          barcode: item.barcode,
          title: item.title,
          author: item.author,
          status: result?.status === "success" ? "success" as const : "error" as const,
          ...(result?.message ? { message: result.message } : {}),
        }
      }))
      toast.success(`${resp.total_success} events created, ${resp.total_errors} errors`)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Batch submission failed")
    } finally {
      setBulkSubmitting(false)
    }
  }, [token, bulkEventType, bulkDescription, bulkQueue])

  const handleSearchTypeChange = useCallback((type: SearchType) => {
    setSearchType(type)
    setSearchResults([])
    setSearchId("")
  }, [])

  const handleClearQueue = useCallback(() => {
    setBulkQueue([])
    if (bulkScanRef.current) bulkScanRef.current.focus()
  }, [])

  const handleRemoveQueueItem = useCallback((index: number) => {
    setBulkQueue(prev => prev.filter((_, j) => j !== index))
  }, [])

  const handleJumpToTimelineForStage = useCallback((stage: LifecycleStage) => {
    setStageFilter(stage)
    setViewMode("timeline")
  }, [])

  const alerts = useMemo<LifecycleAlert[]>(() => {
    if (!selectedTimeline) return []
    return getLifecycleAlerts(selectedTimeline)
  }, [selectedTimeline])

  const filteredEvents = useMemo(() => {
    if (!selectedTimeline) return []
    if (stageFilter === "all") return selectedTimeline.events
    return filterEventsByStage(selectedTimeline.events, stageFilter)
  }, [selectedTimeline, stageFilter])

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === "patron") {
    return <></>
  }

  return (
    <AdminShell title="Lifecycle Management" subtitle="Track and manage items through their complete lifecycle">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-end gap-4">
        <div className="flex items-center gap-3">
          {selectedTimeline && (
            <button
              onClick={() => setShowAddEventModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Event
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-colors ${
              showFilters
                ? "bg-lsc-rose text-white"
                : "text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20"
            }`}
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>
      </div>

      <LifecycleSearchPanel
        searchType={searchType}
        searchId={searchId}
        isLoading={isLoading}
        scanInputRef={scanInputRef}
        searchResults={searchResults}
        onSearchTypeChange={handleSearchTypeChange}
        onSearchIdChange={setSearchId}
        onSearch={handleSearch}
        onBarcodeScan={handleBarcodeScan}
        onSelectResult={handleSelectResult}
      />

      {showFilters && (
        <LifecycleFiltersPanel stageFilter={stageFilter} onStageFilterChange={setStageFilter} />
      )}

      {timelines.length > 0 && (
        <LifecycleViewModeTabs viewMode={viewMode} onChange={setViewMode} />
      )}

      {timelines.length > 1 && (
        <LifecycleCopiesSelector
          timelines={timelines}
          selectedTimeline={selectedTimeline}
          onSelect={setSelectedTimeline}
        />
      )}

      {isLoading ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-12 shadow-sm">
          <div className="flex items-center justify-center">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
          </div>
        </div>
      ) : viewMode === "search" || !selectedTimeline ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-12 shadow-sm">
          <div className="text-center">
            <History className="w-16 h-16 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20 mb-4" />
            <h3 className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              Search for an Item
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/80 max-w-md mx-auto">
              Enter an item copy ID or catalog item ID above to view the complete lifecycle history and manage lifecycle events.
            </p>
          </div>
        </div>
      ) : viewMode === "timeline" ? (
        <LifecycleTimelineView
          timeline={selectedTimeline}
          alerts={alerts}
          filteredEvents={filteredEvents}
          isLoading={isLoading}
        />
      ) : viewMode === "stages" ? (
        <LifecycleStagesView
          timeline={selectedTimeline}
          alerts={alerts}
          onJumpToTimelineForStage={handleJumpToTimelineForStage}
        />
      ) : viewMode === "stats" ? (
        <LifecycleStatsView
          timeline={selectedTimeline}
          alerts={alerts}
          onViewAllEvents={() => setViewMode("timeline")}
        />
      ) : viewMode === "bulk" ? (
        <LifecycleBulkView
          bulkEventType={bulkEventType}
          bulkDescription={bulkDescription}
          bulkQueue={bulkQueue}
          bulkSubmitting={bulkSubmitting}
          bulkScanRef={bulkScanRef}
          onBulkEventTypeChange={setBulkEventType}
          onBulkDescriptionChange={setBulkDescription}
          onBulkScan={handleBulkScan}
          onBulkSubmit={handleBulkSubmit}
          onClearQueue={handleClearQueue}
          onRemoveQueueItem={handleRemoveQueueItem}
        />
      ) : null}

      {showAddEventModal && selectedTimeline && (
        <LifecycleAddEventModal
          timeline={selectedTimeline}
          draft={newEvent}
          isLoading={isLoading}
          onChange={setNewEvent}
          onClose={() => { setShowAddEventModal(false); setNewEvent({}) }}
          onSubmit={handleAddEvent}
        />
      )}
    </AdminShell>
  )
}
