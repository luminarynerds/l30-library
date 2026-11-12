/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  AlertTriangle, Loader2,
  Wrench, BarChart3,
  RefreshCw, FileX, HelpCircle, ClipboardList
} from "lucide-react"
import toast from "react-hot-toast"
import { Modal } from "../components/ui/Modal"
import {
  // Lost items
  listLostItems, processFoundItem, writeOffLostItem, autoConvertOverdueToLost,
  type LostItemRecord,
  // Damaged items
  listDamagedItems, sendToMending, completeRepair,
  type DamagedItemRecord,
  // Mending queue
  listMendingQueue, type MendingQueueEntry,
  // Claims
  listClaims, resolveClaim,
  type ClaimsReturnedDispute,
  // Reports
  getFinancialSummary, getChargesByType, getInventorySummary,
  getPatronRiskReportLostDamaged, getMonthlyTrend,
  // Bulk operations
  bulkWriteOffLostItems, bulkAssignMending,
} from "../api/staff-api"
import { formatCurrency } from "../utils/format-utils"
import {
  LostItemsTab,
  DamagedItemsTab,
  ClaimsReturnedTab,
  MendingQueueTab,
  ReportsTab,
  BulkOperationsTab,
} from "../components/staff-lost-damaged"
import { useTranslation} from '@/i18n'

type TabId = "lost" | "damaged" | "claims" | "mending" | "reports" | "bulk"

// eslint-disable-next-line complexity
export default function StaffLostDamagedPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<TabId>("lost")

  // Filter states
  const [lostStatusFilter, setLostStatusFilter] = useState<string>("")
  const [lostTypeFilter, setLostTypeFilter] = useState<string>("")
  const [damagedStatusFilter, setDamagedStatusFilter] = useState<string>("")
  const [claimStatusFilter, setClaimStatusFilter] = useState<string>("")
  const [_searchQuery, _setSearchQuery] = useState("")

  // Selection states for bulk operations
  const [selectedLostItems, setSelectedLostItems] = useState<number[]>([])
  const [selectedMendingItems, setSelectedMendingItems] = useState<number[]>([])
  const [lastSelectedLostIndex, setLastSelectedLostIndex] = useState<number | null>(null)
  const [lastSelectedMendingIndex, setLastSelectedMendingIndex] = useState<number | null>(null)

  // Modal states
  const [showFoundModal, setShowFoundModal] = useState(false)
  const [showWriteOffModal, setShowWriteOffModal] = useState(false)
  const [showMendingModal, setShowMendingModal] = useState(false)
  const [showResolveClaimModal, setShowResolveClaimModal] = useState(false)
  const [showAutoConvertModal, setShowAutoConvertModal] = useState(false)
  const [showBulkWriteOffModal, setShowBulkWriteOffModal] = useState(false)
  const [showBulkAssignModal, setShowBulkAssignModal] = useState(false)

  // Selected items for actions
  const [selectedLostItem, setSelectedLostItem] = useState<LostItemRecord | null>(null)
  const [selectedDamagedItem, setSelectedDamagedItem] = useState<DamagedItemRecord | null>(null)
  const [selectedClaim, setSelectedClaim] = useState<ClaimsReturnedDispute | null>(null)
  const [_selectedMendingEntry, _setSelectedMendingEntry] = useState<MendingQueueEntry | null>(null)

  // Form states
  const [foundCondition, setFoundCondition] = useState("good")
  const [resolutionNotes, setResolutionNotes] = useState("")
  const [writeOffNotes, setWriteOffNotes] = useState("")
  const [autoConvertDays, setAutoConvertDays] = useState(60)
  const [autoConvertDryRun, setAutoConvertDryRun] = useState(true)
  const [claimApproved, setClaimApproved] = useState(true)
  const [claimResolutionReason, setClaimResolutionReason] = useState("")
  const [bulkAssignStaffId, setBulkAssignStaffId] = useState("")
  const [bulkPriority, setBulkPriority] = useState(3)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, user, navigate, t])

  // Lost items query
  const { data: lostItemsData, isLoading: lostLoading, refetch: refetchLost } = useQuery({
    queryKey: ["staff-lost-items", lostStatusFilter, lostTypeFilter],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, limit: 50, offset: 0 }
      return await listLostItems(token, {
        ...(lostStatusFilter && { status: lostStatusFilter }),
        ...(lostTypeFilter && { lost_type: lostTypeFilter }),
        limit: 50,
      })
    },
    enabled: !!token && activeTab === "lost",
  })

  // Damaged items query
  const { data: damagedItemsData, isLoading: damagedLoading, refetch: refetchDamaged } = useQuery({
    queryKey: ["staff-damaged-items", damagedStatusFilter],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, limit: 50, offset: 0 }
      return await listDamagedItems(token, {
        ...(damagedStatusFilter && { status: damagedStatusFilter }),
        limit: 50,
      })
    },
    enabled: !!token && activeTab === "damaged",
  })

  // Mending queue query
  const { data: mendingData, isLoading: mendingLoading, refetch: refetchMending } = useQuery({
    queryKey: ["staff-mending-queue"],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, limit: 50, offset: 0 }
      return await listMendingQueue(token, { limit: 50 })
    },
    enabled: !!token && activeTab === "mending",
  })

  // Claims query
  const { data: claimsData, isLoading: claimsLoading, refetch: refetchClaims } = useQuery({
    queryKey: ["staff-claims", claimStatusFilter],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, limit: 50, offset: 0 }
      return await listClaims(token, {
        ...(claimStatusFilter && { status: claimStatusFilter }),
        limit: 50,
      })
    },
    enabled: !!token && activeTab === "claims",
  })

  // Reports queries
  const { data: financialSummary, isLoading: financialLoading } = useQuery({
    queryKey: ["staff-lost-damaged-financial"],
    queryFn: async () => {
      if (!token) return null
      return await getFinancialSummary(token)
    },
    enabled: !!token && activeTab === "reports",
  })

  const { data: inventorySummary, isLoading: inventoryLoading } = useQuery({
    queryKey: ["staff-lost-damaged-inventory"],
    queryFn: async () => {
      if (!token) return null
      return await getInventorySummary(token)
    },
    enabled: !!token && activeTab === "reports",
  })

  const { data: chargesByType } = useQuery({
    queryKey: ["staff-lost-damaged-charges-type"],
    queryFn: async () => {
      if (!token) return null
      return await getChargesByType(token)
    },
    enabled: !!token && activeTab === "reports",
  })

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { data: _monthlyTrend } = useQuery({
    queryKey: ["staff-lost-damaged-trend"],
    queryFn: async () => {
      if (!token) return []
      return await getMonthlyTrend(token, 6)
    },
    enabled: !!token && activeTab === "reports",
  })

  const { data: patronRiskData } = useQuery({
    queryKey: ["staff-lost-damaged-patron-risk"],
    queryFn: async () => {
      if (!token) return []
      return await getPatronRiskReportLostDamaged(token, { min_incidents: 2, limit: 10 })
    },
    enabled: !!token && activeTab === "reports",
  })

  // Mutations
  const processFoundMutation = useMutation({
    mutationFn: async (data: { lost_record_id: number; found_condition: string; resolution_notes?: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await processFoundItem(token, data)
    },
    onSuccess: (result) => {
      toast.success(result.message || t('toast.staffLostDamaged.itemMarkedAsFound'))
      queryClient.invalidateQueries({ queryKey: ["staff-lost-items"] })
      setShowFoundModal(false)
      setSelectedLostItem(null)
      setResolutionNotes("")
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const writeOffMutation = useMutation({
    mutationFn: async ({ recordId, notes }: { recordId: number; notes?: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await writeOffLostItem(token, recordId, notes)
    },
    onSuccess: (result) => {
      toast.success(result.message || t('toast.staffLostDamaged.itemWrittenOff'))
      queryClient.invalidateQueries({ queryKey: ["staff-lost-items"] })
      setShowWriteOffModal(false)
      setSelectedLostItem(null)
      setWriteOffNotes("")
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const autoConvertMutation = useMutation({
    mutationFn: async (data: { threshold_days: number; dry_run: boolean }) => {
      if (!token) throw new Error("Not authenticated")
      return await autoConvertOverdueToLost(token, data)
    },
    onSuccess: (result) => {
      if (result.dry_run) {
        toast.success(t('toast.staffLostDamaged.previewProcessedcountItemsWouldBe', { processedcount: result.processed_count }))
      } else {
        toast.success(t('toast.staffLostDamaged.convertedProcessedcountItemsToLost', { processedcount: result.processed_count }))
        queryClient.invalidateQueries({ queryKey: ["staff-lost-items"] })
      }
      setShowAutoConvertModal(false)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const sendToMendingMutation = useMutation({
    mutationFn: async (data: { damage_record_id: number; priority?: number; repair_instructions?: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await sendToMending(token, data)
    },
    onSuccess: (result) => {
      toast.success(result.message || t('toast.staffLostDamaged.itemSentToMending'))
      queryClient.invalidateQueries({ queryKey: ["staff-damaged-items"] })
      queryClient.invalidateQueries({ queryKey: ["staff-mending-queue"] })
      setShowMendingModal(false)
      setSelectedDamagedItem(null)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const completeRepairMutation = useMutation({
    mutationFn: async (data: { mending_entry_id: number; new_condition: string; completion_notes?: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await completeRepair(token, data)
    },
    onSuccess: (result) => {
      toast.success(result.message || t('toast.staffLostDamaged.repairCompleted'))
      queryClient.invalidateQueries({ queryKey: ["staff-mending-queue"] })
      queryClient.invalidateQueries({ queryKey: ["staff-damaged-items"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const resolveClaimMutation = useMutation({
    mutationFn: async (data: { dispute_id: number; approved: boolean; resolution_reason: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await resolveClaim(token, data)
    },
    onSuccess: (result) => {
      toast.success(result.message || t('toast.staffLostDamaged.claimResolved'))
      queryClient.invalidateQueries({ queryKey: ["staff-claims"] })
      setShowResolveClaimModal(false)
      setSelectedClaim(null)
      setClaimResolutionReason("")
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const bulkWriteOffMutation = useMutation({
    mutationFn: async (data: { lost_record_ids: number[]; notes?: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await bulkWriteOffLostItems(token, data)
    },
    onSuccess: (result) => {
      toast.success(t('toast.staffLostDamaged.wroteOffSuccesscountItemsFailurecount', { successcount: result.success_count, failurecount: result.failure_count }))
      queryClient.invalidateQueries({ queryKey: ["staff-lost-items"] })
      setShowBulkWriteOffModal(false)
      setSelectedLostItems([])
      setLastSelectedLostIndex(null)
      setWriteOffNotes("")
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const bulkAssignMutation = useMutation({
    mutationFn: async (data: { mending_entry_ids: number[]; assigned_to_id: number; priority?: number }) => {
      if (!token) throw new Error("Not authenticated")
      return await bulkAssignMending(token, data)
    },
    onSuccess: (result) => {
      toast.success(t('toast.staffLostDamaged.assignedSuccesscountItemsFailurecountFailed', { successcount: result.success_count, failurecount: result.failure_count }))
      queryClient.invalidateQueries({ queryKey: ["staff-mending-queue"] })
      setShowBulkAssignModal(false)
      setSelectedMendingItems([])
      setLastSelectedMendingIndex(null)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: "lost", label: "Lost Items", icon: <FileX className="w-4 h-4" /> },
    { id: "damaged", label: "Damaged Items", icon: <AlertTriangle className="w-4 h-4" /> },
    { id: "claims", label: "Claims Returned", icon: <HelpCircle className="w-4 h-4" /> },
    { id: "mending", label: "Mending Queue", icon: <Wrench className="w-4 h-4" /> },
    { id: "reports", label: "Reports", icon: <BarChart3 className="w-4 h-4" /> },
    { id: "bulk", label: "Bulk Operations", icon: <ClipboardList className="w-4 h-4" /> },
  ]

  const handleRefresh = () => {
    if (activeTab === "lost") refetchLost()
    else if (activeTab === "damaged") refetchDamaged()
    else if (activeTab === "mending") refetchMending()
    else if (activeTab === "claims") refetchClaims()
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === "patron") return <></>

  return (
    <AdminShell title="Lost & Damaged Items">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
                <AlertTriangle className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
              </div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Lost & Damaged Items
              </h1>
            </div>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b border-lsc-border dark:border-earth-700">
            <nav className="flex gap-4 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 pb-3 px-1 border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? "border-lsc-rose text-lsc-rose dark:text-lsc-rose-light"
                      : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                  }`}
                >
                  {tab.icon}
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          {activeTab === "lost" && (
            <LostItemsTab
              lostItemsData={lostItemsData}
              lostLoading={lostLoading}
              lostStatusFilter={lostStatusFilter}
              setLostStatusFilter={setLostStatusFilter}
              lostTypeFilter={lostTypeFilter}
              setLostTypeFilter={setLostTypeFilter}
              setShowAutoConvertModal={setShowAutoConvertModal}
              setSelectedLostItem={setSelectedLostItem}
              setShowFoundModal={setShowFoundModal}
              setShowWriteOffModal={setShowWriteOffModal}
            />
          )}

          {activeTab === "damaged" && (
            <DamagedItemsTab
              damagedItemsData={damagedItemsData}
              damagedLoading={damagedLoading}
              damagedStatusFilter={damagedStatusFilter}
              setDamagedStatusFilter={setDamagedStatusFilter}
              setSelectedDamagedItem={setSelectedDamagedItem}
              setShowMendingModal={setShowMendingModal}
            />
          )}

          {activeTab === "claims" && (
            <ClaimsReturnedTab
              claimsData={claimsData}
              claimsLoading={claimsLoading}
              claimStatusFilter={claimStatusFilter}
              setClaimStatusFilter={setClaimStatusFilter}
              setSelectedClaim={setSelectedClaim}
              setShowResolveClaimModal={setShowResolveClaimModal}
            />
          )}

          {activeTab === "mending" && (
            <MendingQueueTab
              mendingData={mendingData}
              mendingLoading={mendingLoading}
              completeRepairMutation={completeRepairMutation}
            />
          )}

          {activeTab === "reports" && (
            <ReportsTab
              financialSummary={financialSummary}
              financialLoading={financialLoading}
              inventorySummary={inventorySummary}
              inventoryLoading={inventoryLoading}
              chargesByType={chargesByType}
              patronRiskData={patronRiskData}
            />
          )}

          {activeTab === "bulk" && (
            <BulkOperationsTab
              setShowBulkWriteOffModal={setShowBulkWriteOffModal}
              setShowBulkAssignModal={setShowBulkAssignModal}
              setShowAutoConvertModal={setShowAutoConvertModal}
            />
          )}

          {/* Modals */}
          {/* Found Item Modal */}
          {showFoundModal && selectedLostItem && (
            <Modal isOpen onClose={() => { setShowFoundModal(false); setSelectedLostItem(null) }} title={t('staffLostDamaged.markItemAsFound')} size="md">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Item: <strong>{selectedLostItem.item_title || `Item #${selectedLostItem.item_copy_id}`}</strong>
                </p>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="found-item-condition" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Condition</label>
                    <select
                      id="found-item-condition"
                      value={foundCondition}
                      onChange={(e) => setFoundCondition(e.target.value)}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    >
                      <option value="excellent">Excellent</option>
                      <option value="good">Good</option>
                      <option value="fair">Fair</option>
                      <option value="poor">Poor</option>
                      <option value="damaged">Damaged</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="found-item-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Notes (optional)</label>
                    <textarea
                      id="found-item-notes"
                      value={resolutionNotes}
                      onChange={(e) => setResolutionNotes(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      placeholder={t('staffLostDamaged.whereWasItFoundAny')}
                    />
                  </div>
                </div>
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => { setShowFoundModal(false); setSelectedLostItem(null) }}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => processFoundMutation.mutate({
                      lost_record_id: selectedLostItem.id,
                      found_condition: foundCondition,
                      ...(resolutionNotes && { resolution_notes: resolutionNotes }),
                    })}
                    disabled={processFoundMutation.isPending}
                    className="flex-1 px-4 py-2 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg disabled:opacity-50"
                  >
                    {processFoundMutation.isPending ? "Processing..." : "Mark Found"}
                  </button>
                </div>
            </Modal>
          )}

          {/* Write Off Modal */}
          {showWriteOffModal && selectedLostItem && (
            <Modal isOpen onClose={() => { setShowWriteOffModal(false); setSelectedLostItem(null) }} title={t('staffLostDamaged.writeOffLostItem')} size="md">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Item: <strong>{selectedLostItem.item_title || `Item #${selectedLostItem.item_copy_id}`}</strong>
                </p>
                <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-3 mb-4">
                  <p className="text-sm text-status-danger-700 dark:text-status-danger-400">
                    This action is permanent. The item will be removed from inventory.
                  </p>
                </div>
                <div>
                  <label htmlFor="write-off-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Notes (optional)</label>
                  <textarea
                    id="write-off-notes"
                    value={writeOffNotes}
                    onChange={(e) => setWriteOffNotes(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    placeholder={t('placeholder.staffLostDamaged.reasonForWriteoff')}
                  />
                </div>
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => { setShowWriteOffModal(false); setSelectedLostItem(null) }}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => writeOffMutation.mutate({
                      recordId: selectedLostItem.id,
                      ...(writeOffNotes && { notes: writeOffNotes }),
                    })}
                    disabled={writeOffMutation.isPending}
                    className="flex-1 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-lg disabled:opacity-50"
                  >
                    {writeOffMutation.isPending ? "Processing..." : "Write Off"}
                  </button>
                </div>
            </Modal>
          )}

          {/* Send to Mending Modal */}
          {showMendingModal && selectedDamagedItem && (
            <Modal isOpen onClose={() => { setShowMendingModal(false); setSelectedDamagedItem(null) }} title={t('staffLostDamaged.sendToMendingQueue')} size="md">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Item: <strong>{selectedDamagedItem.item_title || `Item #${selectedDamagedItem.item_copy_id}`}</strong>
                </p>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="mending-priority" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Priority (1-5)</label>
                    <select
                      id="mending-priority"
                      value={bulkPriority}
                      onChange={(e) => setBulkPriority(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    >
                      <option value={1}>1 - Low</option>
                      <option value={2}>2 - Below Normal</option>
                      <option value={3}>3 - Normal</option>
                      <option value={4}>4 - High</option>
                      <option value={5}>5 - Urgent</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => { setShowMendingModal(false); setSelectedDamagedItem(null) }}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => sendToMendingMutation.mutate({
                      damage_record_id: selectedDamagedItem.id,
                      priority: bulkPriority,
                    })}
                    disabled={sendToMendingMutation.isPending}
                    className="flex-1 px-4 py-2 bg-category-600 hover:bg-category-700 text-white rounded-lg disabled:opacity-50"
                  >
                    {sendToMendingMutation.isPending ? "Processing..." : "Send to Mending"}
                  </button>
                </div>
            </Modal>
          )}

          {/* Resolve Claim Modal */}
          {showResolveClaimModal && selectedClaim && (
            <Modal isOpen onClose={() => { setShowResolveClaimModal(false); setSelectedClaim(null) }} title="Resolve Claim" size="md">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Item: <strong>{selectedClaim.item_title || `Item #${selectedClaim.item_copy_id}`}</strong><br />
                  Patron: <strong>{selectedClaim.patron_name}</strong>
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Resolution</label>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          checked={claimApproved}
                          onChange={() => setClaimApproved(true)}
                          className="text-status-success-600"
                        />
                        <span className="text-sm text-lsc-dark dark:text-lsc-cream">Approve</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          checked={!claimApproved}
                          onChange={() => setClaimApproved(false)}
                          className="text-status-danger-600"
                        />
                        <span className="text-sm text-lsc-dark dark:text-lsc-cream">Deny</span>
                      </label>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="resolve-claim-reason" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Reason</label>
                    <textarea
                      id="resolve-claim-reason"
                      value={claimResolutionReason}
                      onChange={(e) => setClaimResolutionReason(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      placeholder={t('staffLostDamaged.explainTheResolutionDecision')}
                      required
                    />
                  </div>
                </div>
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => { setShowResolveClaimModal(false); setSelectedClaim(null) }}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => resolveClaimMutation.mutate({
                      dispute_id: selectedClaim.id,
                      approved: claimApproved,
                      resolution_reason: claimResolutionReason,
                    })}
                    disabled={resolveClaimMutation.isPending || !claimResolutionReason.trim()}
                    className={`flex-1 px-4 py-2 ${claimApproved ? "bg-status-success-600 hover:bg-status-success-700" : "bg-status-danger-600 hover:bg-status-danger-700"} text-white rounded-lg disabled:opacity-50`}
                  >
                    {resolveClaimMutation.isPending ? "Processing..." : claimApproved ? "Approve Claim" : "Deny Claim"}
                  </button>
                </div>
            </Modal>
          )}

          {/* Auto-Convert Modal */}
          {showAutoConvertModal && (
            <Modal isOpen onClose={() => setShowAutoConvertModal(false)} title="Auto-Convert Overdue Items" size="md">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Automatically mark items as lost if they have been overdue for a specified number of days.
                </p>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="auto-convert-threshold" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Days Overdue Threshold</label>
                    <input
                      id="auto-convert-threshold"
                      type="number"
                      value={autoConvertDays}
                      onChange={(e) => setAutoConvertDays(parseInt(e.target.value) || 60)}
                      min={14}
                      max={365}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={autoConvertDryRun}
                      onChange={(e) => setAutoConvertDryRun(e.target.checked)}
                      className="rounded text-lsc-rose"
                    />
                    <span className="text-sm text-lsc-dark dark:text-lsc-cream">{t('staffLostDamaged.previewOnlyDryRun')}</span>
                  </label>
                  {!autoConvertDryRun && (
                    <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-3">
                      <p className="text-sm text-status-warning-700 dark:text-status-warning-400">
                        Warning: This will mark items as lost and charge patrons.
                      </p>
                    </div>
                  )}
                </div>
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setShowAutoConvertModal(false)}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => autoConvertMutation.mutate({
                      threshold_days: autoConvertDays,
                      dry_run: autoConvertDryRun,
                    })}
                    disabled={autoConvertMutation.isPending}
                    className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg disabled:opacity-50"
                  >
                    {autoConvertMutation.isPending ? "Processing..." : autoConvertDryRun ? "Preview" : "Convert"}
                  </button>
                </div>
            </Modal>
          )}

          {/* Bulk Write-Off Modal */}
          {showBulkWriteOffModal && (
            <Modal isOpen onClose={() => { setShowBulkWriteOffModal(false); setSelectedLostItems([]); setLastSelectedLostIndex(null) }} title={t('staffLostDamaged.bulkWriteOffLostItems')} size="lg">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Select items to write off from the lost items list, then use this modal to process them.
                </p>
                {lostItemsData?.items && lostItemsData.items.filter(i => i.status !== "found" && i.status !== "written_off").length > 0 ? (
                  <>
                    <div className="max-h-60 overflow-y-auto border border-lsc-border dark:border-earth-700 rounded-lg mb-4">
                      {(() => {
                        const eligibleItems = lostItemsData.items.filter(i => i.status !== "found" && i.status !== "written_off")
                        const allIds = eligibleItems.map(i => i.id)
                        return eligibleItems.map((item, index) => (
                        <label key={item.id} className="flex items-center gap-3 p-3 border-b border-lsc-border dark:border-earth-700 last:border-b-0 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedLostItems.includes(item.id)}
                            onChange={(e) => {
                              const shiftKey = e.nativeEvent instanceof MouseEvent && e.nativeEvent.shiftKey
                              if (shiftKey && lastSelectedLostIndex !== null && lastSelectedLostIndex !== index) {
                                const start = Math.min(lastSelectedLostIndex, index)
                                const end = Math.max(lastSelectedLostIndex, index)
                                const rangeIds = allIds.slice(start, end + 1)
                                setSelectedLostItems(prev => Array.from(new Set([...prev, ...rangeIds])))
                              } else if (e.target.checked) {
                                setSelectedLostItems([...selectedLostItems, item.id])
                              } else {
                                setSelectedLostItems(selectedLostItems.filter(id => id !== item.id))
                              }
                              setLastSelectedLostIndex(index)
                            }}
                            className="rounded text-lsc-rose"
                            title={t('staffLostDamaged.holdShiftToSelectRange')}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.item_title || `Item #${item.item_copy_id}`}>{item.item_title || `Item #${item.item_copy_id}`}</p>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{formatCurrency(item.replacement_cost)}</p>
                          </div>
                        </label>
                      ))})()}
                    </div>
                    <div>
                      <label htmlFor="bulk-write-off-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Notes (optional)</label>
                      <textarea
                        id="bulk-write-off-notes"
                        value={writeOffNotes}
                        onChange={(e) => setWriteOffNotes(e.target.value)}
                        rows={2}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                        placeholder={t('staffLostDamaged.reasonForBulkWriteOff')}
                      />
                    </div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                      {selectedLostItems.length} items selected
                    </p>
                  </>
                ) : (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffLostDamaged.noEligibleItemsToWrite')}</p>
                )}
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => { setShowBulkWriteOffModal(false); setSelectedLostItems([]); setLastSelectedLostIndex(null) }}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => bulkWriteOffMutation.mutate({
                      lost_record_ids: selectedLostItems,
                      ...(writeOffNotes && { notes: writeOffNotes }),
                    })}
                    disabled={bulkWriteOffMutation.isPending || selectedLostItems.length === 0}
                    className="flex-1 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-lg disabled:opacity-50"
                  >
                    {bulkWriteOffMutation.isPending ? "Processing..." : `Write Off ${selectedLostItems.length} Items`}
                  </button>
                </div>
            </Modal>
          )}

          {/* Bulk Assign Modal */}
          {showBulkAssignModal && (
            <Modal isOpen onClose={() => { setShowBulkAssignModal(false); setSelectedMendingItems([]); setLastSelectedMendingIndex(null) }} title={t('staffLostDamaged.bulkAssignMendingQueue')} size="lg">
                {mendingData?.items && mendingData.items.filter(i => !i.is_completed).length > 0 ? (
                  <>
                    <div className="max-h-60 overflow-y-auto border border-lsc-border dark:border-earth-700 rounded-lg mb-4">
                      {(() => {
                        const eligibleItems = mendingData.items.filter(i => !i.is_completed)
                        const allIds = eligibleItems.map(i => i.id)
                        return eligibleItems.map((entry, index) => (
                        <label key={entry.id} className="flex items-center gap-3 p-3 border-b border-lsc-border dark:border-earth-700 last:border-b-0 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedMendingItems.includes(entry.id)}
                            onChange={(e) => {
                              const shiftKey = e.nativeEvent instanceof MouseEvent && e.nativeEvent.shiftKey
                              if (shiftKey && lastSelectedMendingIndex !== null && lastSelectedMendingIndex !== index) {
                                const start = Math.min(lastSelectedMendingIndex, index)
                                const end = Math.max(lastSelectedMendingIndex, index)
                                const rangeIds = allIds.slice(start, end + 1)
                                setSelectedMendingItems(prev => Array.from(new Set([...prev, ...rangeIds])))
                              } else if (e.target.checked) {
                                setSelectedMendingItems([...selectedMendingItems, entry.id])
                              } else {
                                setSelectedMendingItems(selectedMendingItems.filter(id => id !== entry.id))
                              }
                              setLastSelectedMendingIndex(index)
                            }}
                            className="rounded text-lsc-rose"
                            title={t('staffLostDamaged.holdShiftToSelectRange2')}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={entry.item_title || `Item #${entry.item_copy_id}`}>{entry.item_title || `Item #${entry.item_copy_id}`}</p>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Priority: P{entry.priority}</p>
                          </div>
                        </label>
                      ))
                      })()}
                    </div>
                    <div className="space-y-4">
                      <div>
                        <label htmlFor="bulk-assign-staff-id" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('staffLostDamaged.assignToStaffId')}</label>
                        <input
                          id="bulk-assign-staff-id"
                          type="number"
                          value={bulkAssignStaffId}
                          onChange={(e) => setBulkAssignStaffId(e.target.value)}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                          placeholder={t('staffLostDamaged.enterStaffMemberId')}
                        />
                      </div>
                      <div>
                        <label htmlFor="bulk-assign-priority-override" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Priority Override (optional)</label>
                        <select
                          id="bulk-assign-priority-override"
                          value={bulkPriority}
                          onChange={(e) => setBulkPriority(parseInt(e.target.value))}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                        >
                          <option value={0}>Keep current</option>
                          <option value={1}>1 - Low</option>
                          <option value={2}>2 - Below Normal</option>
                          <option value={3}>3 - Normal</option>
                          <option value={4}>4 - High</option>
                          <option value={5}>5 - Urgent</option>
                        </select>
                      </div>
                    </div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                      {selectedMendingItems.length} items selected
                    </p>
                  </>
                ) : (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffLostDamaged.noPendingItemsInMending')}</p>
                )}
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => { setShowBulkAssignModal(false); setSelectedMendingItems([]); setLastSelectedMendingIndex(null) }}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => bulkAssignMutation.mutate({
                      mending_entry_ids: selectedMendingItems,
                      assigned_to_id: parseInt(bulkAssignStaffId),
                      ...(bulkPriority > 0 && { priority: bulkPriority }),
                    })}
                    disabled={bulkAssignMutation.isPending || selectedMendingItems.length === 0 || !bulkAssignStaffId}
                    className="flex-1 px-4 py-2 bg-category-600 hover:bg-category-700 text-white rounded-lg disabled:opacity-50"
                  >
                    {bulkAssignMutation.isPending ? "Processing..." : `Assign ${selectedMendingItems.length} Items`}
                  </button>
                </div>
            </Modal>
          )}
    </AdminShell>
  )
}
