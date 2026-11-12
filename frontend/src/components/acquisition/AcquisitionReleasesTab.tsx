/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { useTranslation } from "@/i18n"
import AcquisitionErrorBoundary from "./AcquisitionErrorBoundary"
import CreatePOModal from "./releases/CreatePOModal"
import ReleaseDetailDrawer from "./releases/ReleaseDetailDrawer"
import ReleasesSummaryStats from "./releases/ReleasesSummaryStats"
import ReleasesTable from "./releases/ReleasesTable"
import ReleasesToolbar from "./releases/ReleasesToolbar"
import { useReleases } from "./releases/useReleases"
import type { Fund, LibrarianRelease, Vendor } from "./releases/types"

interface Props {
  token: string
  vendors: Vendor[]
  funds: Fund[]
  onCreatePO: (selectedIds: string[], vendorId: number, fundId: number) => Promise<void>
  onSwitchToOrders: () => void
  formatMoney: (n: number) => string
}

export default function AcquisitionReleasesTab({ token, vendors, funds, onCreatePO, onSwitchToOrders, formatMoney }: Props) {
  const { t } = useTranslation()
  const r = useReleases(token)

  const [selectedReleases, setSelectedReleases] = useState<string[]>([])
  const [detailRelease, setDetailRelease] = useState<LibrarianRelease | null>(null)
  const [showPOModal, setShowPOModal] = useState(false)


  useEffect(() => {
    if (!detailRelease) return
    const updated = r.releases.find((rel) => rel.book.id === detailRelease.book.id)
    if (updated && updated !== detailRelease) {
      setDetailRelease(updated)
    }
  }, [r.releases])

  const selectableReleases = r.filteredAndSorted.filter((rel) => rel.library_status === "new")
  const allSelectableSelected =
    selectableReleases.length > 0 && selectableReleases.every((rel) => selectedReleases.includes(rel.book.id))

  const handleSelectAll = () => {
    const pageIds = selectableReleases.map((rel) => rel.book.id)
    if (allSelectableSelected) {
      setSelectedReleases((prev) => prev.filter((id) => !pageIds.includes(id)))
    } else {
      setSelectedReleases((prev) => [...new Set([...prev, ...pageIds])])
    }
  }

  const handleToggleSelect = (id: string, checked: boolean) => {
    setSelectedReleases((prev) => (checked ? [...prev, id] : prev.filter((x) => x !== id)))
  }

  const openPOModal = () => {
    if (selectedReleases.length === 0) {
      toast.error(t('toast.acquisition.selectReleasesFirst'))
      return
    }
    if (vendors.length === 0 || funds.length === 0) {
      toast.error(t('components.acquisition.acquisitionReleasesTab.ensureVendorsAndFundsExist'))
      return
    }
    setShowPOModal(true)
  }

  const handleConfirmPO = async (vendorId: number, fundId: number) => {
    if (vendorId === 0 || fundId === 0) {
      toast.error(t('components.acquisition.acquisitionReleasesTab.selectAVendorAndFund'))
      return
    }
    try {
      await onCreatePO(selectedReleases, vendorId, fundId)
      setSelectedReleases([])
      setShowPOModal(false)
      onSwitchToOrders()
    } catch {
      // Error handled by parent
    }
  }

  const handleAddDetailToPO = () => {
    if (!detailRelease) return
    if (!selectedReleases.includes(detailRelease.book.id)) {
      setSelectedReleases([...selectedReleases, detailRelease.book.id])
    }
    setDetailRelease(null)
    openPOModal()
  }

  return (
    <AcquisitionErrorBoundary fallbackMessage="Failed to load upcoming releases">
    <div className="space-y-6">
      <ReleasesSummaryStats
        total={r.stats.total}
        thisWeek={r.stats.thisWeek}
        thisMonth={r.stats.thisMonth}
        highDemand={r.stats.highDemand}
        newOnly={r.stats.newOnly}
      />

      <ReleasesToolbar
        libraryStatusFilter={r.libraryStatusFilter}
        onLibraryStatusChange={r.setLibraryStatusFilter}
        sourceFilter={r.sourceFilter}
        onSourceChange={r.setSourceFilter}
        ageFilter={r.ageFilter}
        onAgeChange={r.setAgeFilter}
        dateRange={r.dateRange}
        onDateRangeChange={r.setDateRange}
        onRefresh={r.refreshAll}
        isRefreshing={r.isRefreshing}
        selectedCount={selectedReleases.length}
        onCreatePO={openPOModal}
      />

      <ReleasesTable
        releases={r.filteredAndSorted}
        isLoading={r.isLoading}
        selectedReleases={selectedReleases}
        onToggleSelect={handleToggleSelect}
        onSelectAll={handleSelectAll}
        allSelectableSelected={allSelectableSelected}
        onRowClick={setDetailRelease}
        sortField={r.sortField}
        sortDir={r.sortDir}
        onToggleSort={r.toggleSort}
        formatMoney={formatMoney}
        page={r.page}
        perPage={r.perPage}
        total={r.total}
        totalPages={r.totalPages}
        onPageChange={r.setPage}
      />

      {detailRelease && (
        <ReleaseDetailDrawer
          release={detailRelease}
          onClose={() => setDetailRelease(null)}
          onAddToPO={handleAddDetailToPO}
          onFeature={() => r.featureTitle(detailRelease.book.id, !detailRelease.book.is_featured)}
          formatMoney={formatMoney}
        />
      )}

      {showPOModal && (
        <CreatePOModal
          selectedCount={selectedReleases.length}
          vendors={vendors}
          funds={funds}
          onClose={() => setShowPOModal(false)}
          onConfirm={handleConfirmPO}
          formatMoney={formatMoney}
        />
      )}
    </div>
    </AcquisitionErrorBoundary>
  )
}
