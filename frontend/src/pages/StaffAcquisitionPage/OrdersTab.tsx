/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useRef, useState } from "react"
import {
  Plus, Edit2, FileDown, Mail, CheckCircle, XCircle, Send, Truck, Package, Save,
  Search, Clock, FileText, ArrowRight, ChevronUp, ChevronDown, X,
} from "lucide-react"
import toast from "react-hot-toast"
import EditPurchaseOrderModal from "../../components/acquisition/EditPurchaseOrderModal"
import RejectPOModal from "../../components/acquisition/RejectPOModal"
import ReceiveItemsModal from "../../components/acquisition/ReceiveItemsModal"
import EDIBadge from "../../components/acquisition/edi/EDIBadge"
import { StatusBadge as SharedStatusBadge } from "@/components/ui/StatusBadge"
import { groupTransactionsByPO } from "../../components/acquisition/edi/ediStatus"
import { getEDITransactions, type EDITransaction } from "@/api/domains/admin/edi-api"
import { useTranslation, getCurrentLocale } from "@/i18n"
import { type Fund, type Vendor, type PurchaseOrder, type PurchaseOrderDetail, apiFetch, formatMoney, API_BASE } from "./types"
import { getAccessToken } from "@/utils/tokenStore"

interface OrdersTabProps {
  token: string
  funds: Fund[]
  vendors: Vendor[]
  orders: PurchaseOrder[]
  user: { role: string } | null
  loadData: () => void
  onSaveAsTemplate: (poId: number) => void
}

type SortKey = "po_number" | "vendor_name" | "created_at" | "status" | "total_amount"
type SortDir = "asc" | "desc"

const PAGE_SIZE = 25

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "pending_approval", label: "Pending Approval" },
  { value: "approved", label: "Approved" },
  { value: "submitted", label: "Submitted" },
  { value: "ordered", label: "Ordered" },
  { value: "shipped", label: "Shipped" },
  { value: "partially_received", label: "Partially Received" },
  { value: "received", label: "Received" },
  { value: "cancelled", label: "Cancelled" },
]

// Badge config — reuses pipelineStageConfig palette from AcquisitionDashboard
// for the shared statuses (draft, pending_approval, approved, submitted, received)
// and extends with sensible tokens for the rest.
const STATUS_BADGE: Record<string, { label: string; classes: string; Icon: typeof Clock }> = {
  draft: {
    label: "Draft",
    classes: "bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-100",
    Icon: FileText,
  },
  pending_approval: {
    label: "Pending Approval",
    classes: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-200",
    Icon: Clock,
  },
  approved: {
    label: "Approved",
    classes: "bg-lsc-rose/15 text-lsc-rose dark:bg-lsc-rose/25 dark:text-lsc-rose-light",
    Icon: CheckCircle,
  },
  submitted: {
    label: "Submitted",
    classes: "bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-200",
    Icon: ArrowRight,
  },
  ordered: {
    label: "Ordered",
    classes: "bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-200",
    Icon: Send,
  },
  shipped: {
    label: "Shipped",
    classes: "bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-200",
    Icon: Truck,
  },
  partially_received: {
    label: "Partially Received",
    classes: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-200",
    Icon: Package,
  },
  received: {
    label: "Received",
    classes: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-200",
    Icon: CheckCircle,
  },
  cancelled: {
    label: "Cancelled",
    classes: "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-200",
    Icon: XCircle,
  },
}

function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatCreatedAt(value: string | null | undefined): string {
  if (!value) return "—"
  const d = new Date(value)
  if (isNaN(d.getTime())) return "—"
  return d.toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric", year: "numeric" })
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_BADGE[status]
  if (!cfg) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded bg-earth-100 dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70">
        {titleCase(status)}
      </span>
    )
  }
  const { Icon } = cfg
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded ${cfg.classes}`}>
      <Icon aria-hidden="true" className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

interface SortHeaderProps {
  label: string
  sortKey: SortKey
  current: SortKey
  dir: SortDir
  onSort: (k: SortKey) => void
  align?: "left" | "right"
}

function SortHeader({ label, sortKey, current, dir, onSort, align = "left" }: SortHeaderProps) {
  const active = current === sortKey
  const ariaSort = active ? (dir === "asc" ? "ascending" : "descending") : "none"
  return (
    <th
      scope="col"
      aria-sort={ariaSort}
      className={`px-4 py-3 text-${align} text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase`}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1 uppercase tracking-wider hover:text-lsc-dark dark:hover:text-lsc-cream ${align === "right" ? "justify-end w-full" : ""}`}
        aria-label={`Sort by ${label}${active ? `, currently ${ariaSort}` : ""}`}
      >
        {label}
        {active ? (
          dir === "asc"
            ? <ChevronUp aria-hidden="true" className="w-3 h-3" />
            : <ChevronDown aria-hidden="true" className="w-3 h-3" />
        ) : (
          <span aria-hidden="true" className="w-3 h-3 inline-block opacity-30">
            <ChevronDown className="w-3 h-3" />
          </span>
        )}
      </button>
    </th>
  )
}

export default function OrdersTab({ token, funds, vendors, orders, user, loadData, onSaveAsTemplate }: OrdersTabProps) {
  const { t } = useTranslation()
  const [selectedPO, setSelectedPO] = useState<PurchaseOrderDetail | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [showReceiveModal, setShowReceiveModal] = useState(false)
  const [statusFilter, setStatusFilter] = useState("all")

  // Search + debounced search
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  useEffect(() => {
    const id = setTimeout(() => setSearch(searchInput.trim().toLowerCase()), 200)
    return () => clearTimeout(id)
  }, [searchInput])

  // Sort state — default: Date desc
  const [sortKey, setSortKey] = useState<SortKey>("created_at")
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  const handleSort = (k: SortKey) => {
    if (k === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(k)
      setSortDir(k === "created_at" || k === "total_amount" ? "desc" : "asc")
    }
  }

  // Pagination
  const [page, setPage] = useState(1)
  // Reset to page 1 whenever filters/search/sort change
  useEffect(() => { setPage(1) }, [statusFilter, search, sortKey, sortDir])

  // EDI transactions for the visible PO universe — fetched once per loadData.
  // Single network call rather than per-row N+1; capped at the API max page size
  // of 100 (well above anything a small library will ship pre-archive). If a
  // library ever exceeds that, badges show the first 100 and we warn rather than
  // silently 422 (the old per_page=500 exceeded the cap and degraded to no badges).
  const [ediByPO, setEdiByPO] = useState<Map<number, EDITransaction[]>>(() => new Map())
  useEffect(() => {
    if (!token) return
    let cancelled = false
    getEDITransactions({ per_page: 100 })
      .then((res) => {
        if (cancelled) return
        if (res.pages > 1) {
          console.warn(
            `EDI transactions exceed one page (${res.total} total); PO badges reflect the first 100 only.`
          )
        }
        setEdiByPO(groupTransactionsByPO(res.items))
      })
      .catch(() => {
        // Non-fatal — silently degrade to no-badges if the EDI endpoint
        // is unreachable; orders table still works as before.
        if (cancelled) return
        setEdiByPO(new Map())
      })
    return () => {
      cancelled = true
    }
    // Re-fetch when orders change so a freshly-sent EDI order picks up
    // its badge without a hard refresh.
  }, [token, orders])

  // Bulk selection
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  // Clear selection when search term changes (avoids confusion); preserve across filter changes.
  useEffect(() => { setSelectedIds(new Set()) }, [search])
  const [isBulkApproving, setIsBulkApproving] = useState(false)
  const headerCheckboxRef = useRef<HTMLInputElement>(null)

  const filteredOrders = useMemo(() => {
    const filtered = orders.filter((o) => {
      if (statusFilter !== "all" && o.status !== statusFilter) return false
      if (search) {
        const po = (o.po_number || "").toLowerCase()
        const vendor = (o.vendor_name || "").toLowerCase()
        if (!po.includes(search) && !vendor.includes(search)) return false
      }
      return true
    })

    const dirMul = sortDir === "asc" ? 1 : -1
    const sorted = [...filtered].sort((a, b) => {
      const av: string | number = (() => {
        switch (sortKey) {
          case "po_number": return (a.po_number || "").toLowerCase()
          case "vendor_name": return (a.vendor_name || "").toLowerCase()
          case "created_at": return a.created_at ? new Date(a.created_at).getTime() : 0
          case "status": return (a.status || "").toLowerCase()
          case "total_amount": return a.total_amount ?? 0
        }
      })()
      const bv: string | number = (() => {
        switch (sortKey) {
          case "po_number": return (b.po_number || "").toLowerCase()
          case "vendor_name": return (b.vendor_name || "").toLowerCase()
          case "created_at": return b.created_at ? new Date(b.created_at).getTime() : 0
          case "status": return (b.status || "").toLowerCase()
          case "total_amount": return b.total_amount ?? 0
        }
      })()
      if (av < bv) return -1 * dirMul
      if (av > bv) return 1 * dirMul
      return 0
    })
    return sorted
  }, [orders, statusFilter, search, sortKey, sortDir])

  const totalCount = filteredOrders.length
  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const startIdx = (currentPage - 1) * PAGE_SIZE
  const endIdx = Math.min(startIdx + PAGE_SIZE, totalCount)
  const pagedOrders = filteredOrders.slice(startIdx, endIdx)

  // Selection derivations — restricted to the currently-filtered universe so a stale
  // selection from a prior filter doesn't drive master-checkbox / bulk-toolbar state.
  const filteredIdSet = useMemo(() => new Set(filteredOrders.map((o) => o.id)), [filteredOrders])
  const selectedInFilter = useMemo(
    () => filteredOrders.filter((o) => selectedIds.has(o.id)),
    [filteredOrders, selectedIds],
  )
  const allFilteredSelected = filteredOrders.length > 0 && selectedInFilter.length === filteredOrders.length
  const someFilteredSelected = selectedInFilter.length > 0 && !allFilteredSelected

  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = someFilteredSelected
    }
  }, [someFilteredSelected])

  const toggleRow = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAllFiltered = () => {
    setSelectedIds((prev) => {
      if (allFilteredSelected) {
        // Deselect everything in the current filter, preserve out-of-filter selections.
        const next = new Set(prev)
        for (const id of filteredIdSet) next.delete(id)
        return next
      }
      // Select every filtered row (union with any prior selections).
      const next = new Set(prev)
      for (const id of filteredIdSet) next.add(id)
      return next
    })
  }

  const clearSelection = () => setSelectedIds(new Set())

  // All selected rows that still exist in the loaded `orders` list — used for bulk actions.
  const selectedOrders = useMemo(
    () => orders.filter((o) => selectedIds.has(o.id)),
    [orders, selectedIds],
  )
  const allSelectedPending =
    selectedOrders.length > 0 && selectedOrders.every((o) => o.status === "pending_approval")

  const handleCreateNewPO = async () => {
    if (!token) return
    try {
      const newPO = await apiFetch<PurchaseOrder>(token, '/purchase-orders', {
        method: 'POST',
        body: JSON.stringify({
          vendor_id: null,
          fund_id: null,
          notes: ''
        })
      })

      const detail = await apiFetch<PurchaseOrderDetail>(token, `/purchase-orders/${newPO.id}`)
      setSelectedPO(detail)
      setShowEditModal(true)
      toast.success(t('staffAcquisition.newPurchaseOrderCreated'))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToCreateOrder'))
    }
  }

  const handleEditPO = async (po: PurchaseOrder) => {
    if (!token) return
    try {
      const detail = await apiFetch<PurchaseOrderDetail>(token, `/purchase-orders/${po.id}`)
      setSelectedPO(detail)
      setShowEditModal(true)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToEditOrder'))
    }
  }

  const handlePrintPO = async (poId: number) => {
    if (!token) return
    try {
      // Binary download — fetchApi can't handle blob responses, use raw fetch with manual Bearer header
      const authToken = getAccessToken()
      // eslint-disable-next-line no-restricted-syntax -- PO PDF binary download
      const res = await fetch(`${API_BASE}/purchase-orders/${poId}/pdf`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      })
      if (!res.ok) throw new Error("Failed to download PDF")
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `PO_${poId}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
      toast.success(t('toast.ordersTab.pdfDownloaded'))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToDownloadPdf'))
    }
  }

  const handleEmailVendor = async (poId: number) => {
    if (!token) return
    try {
      await apiFetch(token, `/purchase-orders/${poId}/email-vendor`, { method: "POST" })
      toast.success(t('staffAcquisition.poEmailedToVendor'))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToEmailVendor'))
    }
  }

  const handleApprovePO = async (poId: number) => {
    if (!token) return
    try {
      await apiFetch(token, `/purchase-orders/${poId}/approve`, { method: "PATCH" })
      toast.success(t('toast.ordersTab.purchaseOrderApproved'))
      loadData()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToApproveOrder'))
    }
  }

  const handleRejectPO = (po: PurchaseOrder) => {
    const detail: PurchaseOrderDetail = {
      id: po.id,
      po_number: po.po_number,
      vendor_id: null,
      vendor_name: po.vendor_name,
      fund_id: null,
      fund_name: po.fund_name,
      status: po.status,
      total_amount: po.total_amount,
      total_items: 0,
      has_backorders: po.has_backorders,
      notes: null,
      items: [],
      created_by_id: 0
    }
    setSelectedPO(detail)
    setShowRejectModal(true)
  }

  const handleConfirmReject = async (notes: string) => {
    if (!token || !selectedPO) return
    try {
      await apiFetch(token, `/purchase-orders/${selectedPO.id}/reject`, {
        method: "PATCH",
        body: JSON.stringify({ rejection_notes: notes }),
      })
      toast.success(t('toast.ordersTab.purchaseOrderRejected'))
      setShowRejectModal(false)
      setSelectedPO(null)
      loadData()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToRejectOrder'))
    }
  }

  const handleSubmitForApproval = async (poId: number) => {
    if (!token) return
    try {
      await apiFetch(token, `/purchase-orders/${poId}/submit-for-approval`, { method: "PATCH" })
      toast.success(t('staffAcquisition.purchaseOrderSubmittedForApproval'))
      loadData()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToSubmitOrderFor'))
    }
  }

  const handleSubmitToVendor = async (poId: number) => {
    if (!token) return
    try {
      await apiFetch(token, `/purchase-orders/${poId}/submit`, { method: "PATCH" })
      toast.success(t('staffAcquisition.purchaseOrderSubmittedToVendor'))
      loadData()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToSubmitToVendor'))
    }
  }

  const handleOpenReceive = async (po: PurchaseOrder) => {
    if (!token) return
    try {
      const detail = await apiFetch<PurchaseOrderDetail>(token, `/purchase-orders/${po.id}`)
      setSelectedPO(detail)
      setShowReceiveModal(true)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.ordersTab.failedToLoadOrderDetails'))
    }
  }

  const handleBulkApprove = async () => {
    if (!token || selectedOrders.length === 0 || !allSelectedPending) return
    setIsBulkApproving(true)
    let successCount = 0
    let failureCount = 0
    for (const po of selectedOrders) {
      try {
        await apiFetch(token, `/purchase-orders/${po.id}/approve`, { method: "PATCH" })
        successCount += 1
      } catch {
        failureCount += 1
      }
    }
    if (failureCount === 0) {
      toast.success(`Approved ${successCount} purchase order${successCount === 1 ? "" : "s"}`)
    } else if (successCount === 0) {
      toast.error(`Failed to approve ${failureCount} purchase order${failureCount === 1 ? "" : "s"}`)
    } else {
      toast.success(`Approved ${successCount}, failed ${failureCount}`)
    }
    clearSelection()
    setIsBulkApproving(false)
    loadData()
  }

  const handleBulkExportCsv = () => {
    if (selectedOrders.length === 0) return
    const headers = ["PO#", "Vendor", "Fund", "Status", "Date", "Items", "Total"]
    const escape = (v: unknown): string => {
      const s = v === null || v === undefined ? "" : String(v)
      // Quote if contains comma, quote, or newline; double internal quotes.
      if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
      return s
    }
    const rows = selectedOrders.map((o) => [
      o.po_number ?? "",
      o.vendor_name ?? "",
      o.fund_name ?? "",
      o.status ?? "",
      formatCreatedAt(o.created_at),
      o.total_items ?? 0,
      (Number(o.total_amount) || 0).toFixed(2),
    ])
    const csv = [headers, ...rows].map((r) => r.map(escape).join(",")).join("\r\n")
    // Prefix BOM so Excel detects UTF-8 correctly.
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    const today = new Date().toISOString().slice(0, 10)
    a.href = url
    a.download = `purchase-orders-${today}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
    toast.success(`Exported ${selectedOrders.length} purchase order${selectedOrders.length === 1 ? "" : "s"} to CSV`)
  }

  const isAdmin = user?.role === "admin" || user?.role === "super_admin"

  const approveDisabledReason = !allSelectedPending
    ? "Approve only works when every selected order is Pending Approval"
    : undefined

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Purchase Orders</h2>
          <button
            onClick={handleCreateNewPO}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"
          >
            <Plus aria-hidden="true" className="w-4 h-4" />New Order
          </button>
        </div>

        {/* Search bar */}
        <div className="relative max-w-md">
          <Search aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50" />
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search PO# or vendor"
            aria-label="Search purchase orders by PO number or vendor name"
            className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/40 dark:placeholder:text-lsc-cream/40 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        {/* Status filter chips — visible to all staff (admin-only action buttons remain gated below) */}
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter purchase orders by status">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setStatusFilter(f.value)}
              aria-pressed={statusFilter === f.value}
              className={`px-3 py-1.5 rounded-xl text-sm font-medium ${
                statusFilter === f.value
                  ? "bg-lsc-rose text-white"
                  : "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Bulk action toolbar */}
        {selectedIds.size > 0 && (
          <div
            role="region"
            aria-label="Bulk actions for selected purchase orders"
            className="flex flex-wrap items-center gap-3 px-4 py-3 rounded-xl bg-lsc-cream dark:bg-lsc-brown border border-lsc-border dark:border-earth-700"
          >
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream" aria-live="polite">
              {selectedIds.size} selected
            </span>
            <button
              type="button"
              onClick={clearSelection}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-white dark:hover:bg-lsc-dark/30"
            >
              <X aria-hidden="true" className="w-3.5 h-3.5" />
              Clear selection
            </button>
            <div className="flex-1" />
            {isAdmin && (
              <button
                type="button"
                onClick={handleBulkApprove}
                disabled={!allSelectedPending || isBulkApproving}
                title={approveDisabledReason}
                aria-label={
                  approveDisabledReason
                    ? `Approve selected (disabled: ${approveDisabledReason})`
                    : `Approve ${selectedIds.size} selected purchase order${selectedIds.size === 1 ? "" : "s"}`
                }
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-status-success-600 hover:bg-status-success-700 text-white disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <CheckCircle aria-hidden="true" className="w-4 h-4" />
                {isBulkApproving ? "Approving…" : "Approve selected"}
              </button>
            )}
            <button
              type="button"
              onClick={handleBulkExportCsv}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white"
              aria-label={`Export ${selectedIds.size} selected purchase order${selectedIds.size === 1 ? "" : "s"} to CSV`}
            >
              <FileDown aria-hidden="true" className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        )}

        {orders.length === 0 ? (
          <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('staffAcquisition.noPurchaseOrdersYet')}
          </p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
                  <tr>
                    <th scope="col" className="px-4 py-3 text-left w-10">
                      <input
                        ref={headerCheckboxRef}
                        type="checkbox"
                        checked={allFilteredSelected}
                        onChange={toggleAllFiltered}
                        disabled={filteredOrders.length === 0}
                        aria-label={
                          allFilteredSelected
                            ? `Deselect all ${filteredOrders.length} filtered purchase orders`
                            : `Select all ${filteredOrders.length} filtered purchase orders`
                        }
                        className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                      />
                    </th>
                    <SortHeader label="PO #" sortKey="po_number" current={sortKey} dir={sortDir} onSort={handleSort} />
                    <SortHeader label="Vendor" sortKey="vendor_name" current={sortKey} dir={sortDir} onSort={handleSort} />
                    <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Fund</th>
                    <SortHeader label="Date" sortKey="created_at" current={sortKey} dir={sortDir} onSort={handleSort} />
                    <SortHeader label="Status" sortKey="status" current={sortKey} dir={sortDir} onSort={handleSort} />
                    <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Items</th>
                    <SortHeader label="Total" sortKey="total_amount" current={sortKey} dir={sortDir} onSort={handleSort} align="right" />
                    <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {pagedOrders.map((order) => (
                    <tr key={order.id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(order.id)}
                          onChange={() => toggleRow(order.id)}
                          aria-label={`Select order ${order.po_number}`}
                          className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                        />
                      </td>
                      <td className="px-4 py-3 font-mono text-sm text-lsc-dark dark:text-lsc-cream">{order.po_number}</td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{order.vendor_name}</td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{order.fund_name}</td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">{formatCreatedAt(order.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <StatusBadge status={order.status} />
                          {order.has_backorders && (
                            <SharedStatusBadge
                              variant="warning"
                              size="sm"
                              className="focus-within:ring-2"
                            >
                              <span aria-label={t('acquisitionsBackorder.poBadgeAriaLabel', {
                                poNumber: order.po_number,
                                defaultValue: `PO ${order.po_number} has backordered items`,
                              })}>
                                {t('acquisitionsBackorder.poBadge', 'Backordered')}
                              </span>
                            </SharedStatusBadge>
                          )}
                          <EDIBadge
                            poId={order.id}
                            poNumber={order.po_number}
                            transactions={ediByPO.get(order.id) ?? []}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{order.total_items}</td>
                      <td className="px-4 py-3 text-right font-semibold text-lsc-dark dark:text-lsc-cream">{formatMoney(order.total_amount)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {order.status === "draft" && (
                            <button onClick={() => handleEditPO(order)} className="p-1.5 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-dark/20 rounded" title="Edit" aria-label={`Edit order ${order.po_number}`}>
                              <Edit2 aria-hidden="true" className="w-4 h-4" />
                            </button>
                          )}
                          {order.status === "draft" && order.total_items > 0 && (
                            <button onClick={() => handleSubmitForApproval(order.id)} className="p-1.5 text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-50 dark:hover:bg-earth-800/20 rounded" title="Submit for Approval" aria-label={`Submit order ${order.po_number} for approval`}>
                              <Send aria-hidden="true" className="w-4 h-4" />
                            </button>
                          )}
                          <button onClick={() => handlePrintPO(order.id)} className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded" title="Print PDF" aria-label={`Print PDF for order ${order.po_number}`}>
                            <FileDown aria-hidden="true" className="w-4 h-4" />
                          </button>
                          {order.total_items > 0 && (
                            <button onClick={() => onSaveAsTemplate(order.id)} className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded" title="Save as Template" aria-label={`Save order ${order.po_number} as template`}>
                              <Save aria-hidden="true" className="w-4 h-4" />
                            </button>
                          )}
                          {order.status === "approved" && order.vendor_name && (
                            <button onClick={() => handleEmailVendor(order.id)} className="p-1.5 text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-50 dark:hover:bg-earth-800/20 rounded" title="Email to Vendor" aria-label={`Email order ${order.po_number} to vendor`}>
                              <Mail aria-hidden="true" className="w-4 h-4" />
                            </button>
                          )}
                          {order.status === "approved" && order.total_items > 0 && (
                            <button onClick={() => handleSubmitToVendor(order.id)} className="p-1.5 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded" title="Submit to Vendor" aria-label={`Submit order ${order.po_number} to vendor`}>
                              <Truck aria-hidden="true" className="w-4 h-4" />
                            </button>
                          )}
                          {(order.status === "submitted" || order.status === "partially_received") && (
                            <button onClick={() => handleOpenReceive(order)} className="p-1.5 text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/20 rounded" title="Receive Items" aria-label={`Receive items for order ${order.po_number}`}>
                              <Package aria-hidden="true" className="w-4 h-4" />
                            </button>
                          )}
                          {/* Approve/Reject remain admin-only (separate from filter gate above) */}
                          {order.status === "pending_approval" && isAdmin && (
                            <>
                              <button onClick={() => handleApprovePO(order.id)} className="p-1.5 text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/20 rounded" title="Approve" aria-label={`Approve order ${order.po_number}`}>
                                <CheckCircle aria-hidden="true" className="w-4 h-4" />
                              </button>
                              <button onClick={() => handleRejectPO(order)} className="p-1.5 text-status-danger-600 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded" title="Reject" aria-label={`Reject order ${order.po_number}`}>
                                <XCircle aria-hidden="true" className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {pagedOrders.length === 0 && (
                    <tr>
                      <td colSpan={9} className="px-4 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                        No purchase orders match your filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalCount > 0 && (
              <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70" aria-live="polite">
                  Showing {startIdx + 1}-{endIdx} of {totalCount}
                </p>
                {pageCount > 1 && (
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/70"
                      aria-label="Previous page"
                    >
                      Previous
                    </button>
                    {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPage(p)}
                        aria-current={p === currentPage ? "page" : undefined}
                        aria-label={`Page ${p}${p === currentPage ? `, current page` : ""}`}
                        className={`min-w-[2.25rem] px-2 py-1.5 rounded-lg text-sm font-medium ${
                          p === currentPage
                            ? "bg-lsc-rose text-white"
                            : "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/70"
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                      disabled={currentPage === pageCount}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/70"
                      aria-label="Next page"
                    >
                      Next
                    </button>
                  </div>
                )}
              </nav>
            )}
          </>
        )}
      </div>

      {showEditModal && selectedPO && (
        <EditPurchaseOrderModal
          isOpen={showEditModal}
          onClose={() => {
            setShowEditModal(false)
            setSelectedPO(null)
          }}
          purchaseOrder={selectedPO}
          funds={funds}
          vendors={vendors}
          token={token || ""}
          onUpdate={() => {
            loadData()
            setShowEditModal(false)
            setSelectedPO(null)
          }}
        />
      )}

      {showRejectModal && selectedPO && (
        <RejectPOModal
          isOpen={showRejectModal}
          onClose={() => {
            setShowRejectModal(false)
            setSelectedPO(null)
          }}
          onConfirm={handleConfirmReject}
          poNumber={selectedPO.po_number}
        />
      )}

      {showReceiveModal && selectedPO && (
        <ReceiveItemsModal
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          po={selectedPO as any}
          token={token || ""}
          onClose={() => {
            setShowReceiveModal(false)
            setSelectedPO(null)
          }}
          onSuccess={() => {
            setShowReceiveModal(false)
            setSelectedPO(null)
            loadData()
          }}
        />
      )}
    </>
  )
}
