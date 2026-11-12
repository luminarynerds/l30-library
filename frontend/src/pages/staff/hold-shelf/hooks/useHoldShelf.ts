/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useMemo, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"
import { fetchApi } from "@/lib/api-client"
import { listBranches } from "@/api/branch-api"
import { useTranslation, getCurrentLocale } from "@/i18n"
import toast from "react-hot-toast"
import type {
  PullListResponse,
  CapacityStatus,
  ExpiringHoldsResponse,
  MarkNotPickedUpResponse,
  PullListItem,
  ViewMode,
  ShelfSlotUpdateResponse,
  FulfillHoldResponse,
  PatronOnWayToggleResponse,
} from "../types"
import { esc } from "../constants"

export function useHoldShelf() {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [pullList, setPullList] = useState<PullListResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)
  const [capacityStatus, setCapacityStatus] = useState<CapacityStatus | null>(null)
  const [processingHoldId, setProcessingHoldId] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>("pull-list")
  const [expiringHolds, setExpiringHolds] = useState<ExpiringHoldsResponse | null>(null)
  const [batchAssigning, setBatchAssigning] = useState(false)
  const [pendingNotPickedUp, setPendingNotPickedUp] = useState<number | null>(null)
  const [pendingRequeue, setPendingRequeue] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  // Cache branch code→id so we only fetch once per session
  const branchCodeMapRef = useRef<Map<string, number> | null>(null)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  const loadPullList = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const url = selectedLocation
        ? `/circulation/holds/pull-list?location=${encodeURIComponent(selectedLocation)}`
        : "/circulation/holds/pull-list"

      const response = await fetchApi(url, {
        headers: { Authorization: `Bearer ${token}` },
      })
      setPullList(response)

      if (selectedLocation) {
        try {
          // Resolve branch code → id. Branches are stable; cache after first fetch.
          if (!branchCodeMapRef.current) {
            const branches = await listBranches({ active_only: true })
            branchCodeMapRef.current = new Map(
              branches.map((b) => [b.code.toUpperCase(), b.id])
            )
          }
          const branchId = branchCodeMapRef.current.get(selectedLocation.toUpperCase())
          if (branchId != null) {
            const capacityResponse = await fetchApi(
              `/circulation/holds/shelf-capacity/${branchId}`,
              { headers: { Authorization: `Bearer ${token}` } }
            )
            setCapacityStatus(capacityResponse)
          } else {
            // Location string didn't match any known branch — hide panel silently
            setCapacityStatus(null)
          }
        } catch {
          setCapacityStatus(null)
        }
      } else {
        setCapacityStatus(null)
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffHoldShelf.failedToLoadPullList'))
    } finally {
      setIsLoading(false)
    }
  }


  useEffect(() => {
    if (isAuthenticated && token && user && user.role !== "patron") {
      loadPullList()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, token, user])

  // --- Filtered items based on search query ---
  const filteredPullList = useMemo(() => {
    if (!pullList || !searchQuery.trim()) return pullList
    const q = searchQuery.toLowerCase()
    const filteredLocations = pullList.locations
      .map((loc) => ({
        ...loc,
        items: loc.items.filter(
          (item) =>
            item.patron_name.toLowerCase().includes(q) ||
            item.item_title.toLowerCase().includes(q)
        ),
        item_count: 0,
      }))
      .map((loc) => ({ ...loc, item_count: loc.items.length }))
      .filter((loc) => loc.items.length > 0)

    return {
      ...pullList,
      locations: filteredLocations,
      total_items: filteredLocations.reduce((sum, loc) => sum + loc.items.length, 0),
    }
  }, [pullList, searchQuery])

  // --- Expired holds: items from pullList where days_until_expiry < 0 ---
  const expiredHolds = useMemo(() => {
    if (!pullList) return []
    const items: PullListItem[] = []
    for (const loc of pullList.locations) {
      for (const item of loc.items) {
        if (item.days_until_expiry !== null && item.days_until_expiry < 0) {
          items.push(item)
        }
      }
    }
    return items
  }, [pullList])

  const loadExpiringHolds = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response = await fetchApi<ExpiringHoldsResponse>(
        "/circulation/holds/expiring?hours=48",
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setExpiringHolds(response)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffHoldShelf.failedToLoadExpiringHolds'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode)
    if (mode === "expiring") {
      loadExpiringHolds()
    } else {
      loadPullList()
    }
  }

  const handleMarkNotPickedUp = async (holdId: number) => {
    if (!token) return
    setProcessingHoldId(holdId)
    try {
      const response = await fetchApi<MarkNotPickedUpResponse>(
        `/circulation/holds/${holdId}/mark-not-picked-up`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      toast.success(t('staffHoldShelf.holdMarkedAsNotPicked'))
      if (response.next_hold_promoted) {
        toast.success(t('toast.staffHoldShelf.queueAdvancedToPatronname', { patronname: response.next_hold?.patron_name }))
      }
      await loadPullList()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffHoldShelf.failedToMarkHold'))
    } finally {
      setProcessingHoldId(null)
    }
  }

  const handleRequeue = async (holdId: number) => {
    if (!token) return
    setProcessingHoldId(holdId)
    try {
      const response = await fetchApi<{ message: string }>(
        `/circulation/holds/${holdId}/requeue`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      toast.success(response.message)
      if (viewMode === "expiring") {
        await loadExpiringHolds()
      } else {
        await loadPullList()
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffHoldShelf.failedToRequeueHold'))
    } finally {
      setProcessingHoldId(null)
    }
  }

  const handleBatchAssignSlots = async () => {
    if (!token) return
    setBatchAssigning(true)
    try {
      const response = await fetchApi<{ assigned_count: number }>(
        "/circulation/holds/batch-assign-slots?branch_id=1",
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      toast.success(t('toast.staffHoldShelf.assignedShelfSlotsToAssignedcount', { assignedcount: response.assigned_count }))
      await loadPullList()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffHoldShelf.failedToBatchAssignSlots'))
    } finally {
      setBatchAssigning(false)
    }
  }

  const handleUpdateShelfSlot = async (holdId: number, shelfSlot: string | null) => {
    if (!token) return
    setProcessingHoldId(holdId)
    try {
      const response = await fetchApi<ShelfSlotUpdateResponse>(
        `/circulation/holds/${holdId}/shelf-slot`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ shelf_slot: shelfSlot || null }),
        }
      )
      toast.success(response.message)
      // Update local state to avoid full reload
      if (pullList) {
        const updated = { ...pullList }
        for (const loc of updated.locations) {
          for (const item of loc.items) {
            if (item.hold_id === holdId) {
              item.shelf_slot = response.shelf_slot
            }
          }
        }
        setPullList({ ...updated })
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to update shelf slot")
    } finally {
      setProcessingHoldId(null)
    }
  }

  const handleFulfillHold = async (holdId: number) => {
    if (!token) return
    setProcessingHoldId(holdId)
    try {
      const response = await fetchApi<FulfillHoldResponse>(
        `/circulation/holds/${holdId}/fulfill`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      toast.success(response.message)
      await loadPullList()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to mark hold as picked up")
    } finally {
      setProcessingHoldId(null)
    }
  }

  const handleTogglePatronOnWay = async (holdId: number) => {
    if (!token) return
    setProcessingHoldId(holdId)
    try {
      const response = await fetchApi<PatronOnWayToggleResponse>(
        `/circulation/holds/${holdId}/patron-on-way`,
        {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      toast.success(response.message)
      // Update local state
      if (pullList) {
        const updated = { ...pullList }
        for (const loc of updated.locations) {
          for (const item of loc.items) {
            if (item.hold_id === holdId) {
              item.patron_on_way = response.patron_on_way
            }
          }
        }
        setPullList({ ...updated })
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to toggle patron on way")
    } finally {
      setProcessingHoldId(null)
    }
  }

  const handlePrintSlip = async (holdId: number) => {
    if (!token) return
    try {
      const slip = await fetchApi<{
        hold_id: number
        item_title: string
        item_author: string | null
        call_number: string | null
        patron_initials: string
        patron_name: string
        shelf_slot: string | null
        expires_at: string | null
        qr_pickup_code: string | null
        barcode: string | null
        pickup_location: string | null
      }>(`/circulation/holds/${holdId}/slip`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      const printWindow = window.open("", "", "width=400,height=600")
      if (printWindow) {
        const expiresFormatted = slip.expires_at
          ? new Date(slip.expires_at).toLocaleDateString(getCurrentLocale(), {
              month: "short",
              day: "numeric",
              year: "numeric",
            })
          : "N/A"

        const qrUrl = ""

        printWindow.document.write(`
          <html>
            <head>
              <title>Hold Shelf Slip</title>
              <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 8px; width: 280px; }
                .slip { border: 2px solid #2C1810; padding: 10px; }
                .initials { font-size: 36pt; font-weight: bold; text-align: center; color: #2C1810; padding: 8px 0; border-bottom: 2px solid #5C4F3D; margin-bottom: 8px; letter-spacing: 4px; }
                .slot { font-size: 20pt; font-weight: bold; color: #2E7D32; text-align: center; padding: 6px; background: #E8F5E9; border-radius: 4px; margin-bottom: 8px; }
                .title { font-weight: bold; font-size: 10pt; word-wrap: break-word; }
                .author { font-size: 9pt; color: #666; }
                .details { font-size: 8pt; color: #888; margin-top: 4px; }
                .patron { font-size: 9pt; margin: 4px 0; }
                .expiry { background: #FFF9E6; border: 1px solid #E89B44; padding: 6px; margin: 8px 0; text-align: center; border-radius: 4px; }
                .expiry-label { font-size: 8pt; color: #666; }
                .expiry-date { font-size: 11pt; font-weight: bold; color: #C41E3A; }
                .qr { text-align: center; margin: 8px 0 4px; padding-top: 8px; border-top: 1px dashed #ccc; }
                .qr img { width: 100px; height: 100px; }
                .qr-label { font-size: 7pt; color: #999; margin-top: 4px; }
                .location { font-size: 8pt; color: #666; text-align: center; margin-top: 4px; }
              </style>
            </head>
            <body>
              <div class="slip">
                <div class="initials">${esc(slip.patron_initials)}</div>
                ${slip.shelf_slot ? `<div class="slot">${esc(slip.shelf_slot)}</div>` : ""}
                <div style="margin: 8px 0; padding: 6px 0; border-bottom: 1px dashed #ccc;">
                  <div class="title">${esc(slip.item_title)}</div>
                  ${slip.item_author ? `<div class="author">${esc(slip.item_author)}</div>` : ""}
                  <div class="details">
                    ${slip.call_number ? `Call#: ${esc(slip.call_number)}` : ""}
                    ${slip.barcode ? ` | ${esc(slip.barcode)}` : ""}
                  </div>
                </div>
                <div class="patron"><strong>${esc(slip.patron_name)}</strong></div>
                <div class="expiry">
                  <div class="expiry-label">PICK UP BY</div>
                  <div class="expiry-date">${esc(expiresFormatted)}</div>
                </div>
                ${
                  qrUrl
                    ? `<div class="qr">
                    <img src="${qrUrl}" alt="Pickup QR" />
                    <div class="qr-label">Scan for self-pickup</div>
                  </div>`
                    : ""
                }
                ${slip.pickup_location ? `<div class="location">${esc(slip.pickup_location)}</div>` : ""}
              </div>
            </body>
          </html>
        `)
        printWindow.document.close()
        printWindow.print()
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffHoldShelf.failedToPrintSlip'))
    }
  }

  const handlePrintLabels = (items: PullListItem[]) => {
    const printWindow = window.open("", "", "width=800,height=600")
    if (printWindow) {
      printWindow.document.write(`
        <html>
          <head>
            <title>Hold Shelf Labels</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 20px; }
              .label {
                display: inline-block;
                border: 1px solid #ccc;
                padding: 10px;
                margin: 5px;
                width: 220px;
                text-align: center;
              }
              .initials {
                font-size: 24px;
                font-weight: bold;
                color: #2563eb;
              }
              .slot {
                font-size: 16px;
                font-weight: bold;
                color: #2E7D32;
                background: #E8F5E9;
                padding: 2px 8px;
                border-radius: 4px;
                display: inline-block;
                margin-top: 4px;
              }
              .title {
                font-size: 11px;
                margin-top: 5px;
                word-wrap: break-word;
              }
              .on-way {
                font-size: 10px;
                color: #1565C0;
                font-weight: bold;
              }
            </style>
          </head>
          <body>
            <h2>Hold Shelf Labels</h2>
            ${items
              .map(
                (item) => `
              <div class="label">
                <div class="initials">${esc(item.patron_initials)}</div>
                ${item.shelf_slot ? `<div class="slot">${esc(item.shelf_slot)}</div>` : ""}
                <div class="title">${esc(item.item_title)}</div>
                ${item.patron_on_way ? '<div class="on-way">ON WAY</div>' : ""}
              </div>
            `
              )
              .join("")}
          </body>
        </html>
      `)
      printWindow.document.close()
      printWindow.print()
    }
  }

  const handleLocationSelect = (location: string | null) => {
    setSelectedLocation(location)
    setPullList(null)
    loadPullList()
  }

  const onWayCount = pullList
    ? pullList.locations.reduce(
        (sum, loc) => sum + loc.items.filter((i) => i.patron_on_way).length,
        0
      )
    : 0

  const noShowCount = pullList
    ? pullList.locations.reduce(
        (sum, loc) => sum + loc.items.filter((i) => i.no_show_count > 0).length,
        0
      )
    : 0

  return {
    // State
    pullList,
    filteredPullList,
    isLoading,
    selectedLocation,
    capacityStatus,
    processingHoldId,
    viewMode,
    expiringHolds,
    expiredHolds,
    batchAssigning,
    pendingNotPickedUp,
    pendingRequeue,
    authLoading,
    searchQuery,

    // Derived
    onWayCount,
    noShowCount,

    // Setters
    setPendingNotPickedUp,
    setPendingRequeue,
    setSearchQuery,

    // Handlers
    handleViewModeChange,
    handleMarkNotPickedUp,
    handleRequeue,
    handleBatchAssignSlots,
    handleUpdateShelfSlot,
    handleFulfillHold,
    handleTogglePatronOnWay,
    handlePrintSlip,
    handlePrintLabels,
    handleLocationSelect,
  }
}
