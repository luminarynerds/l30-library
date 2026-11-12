/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2 } from "lucide-react"
import { DestructiveActionDialog } from "@/components/dialogs/DestructiveActionDialog"
import { AdminShell } from "@/components/shells/AdminShell"
import { useHoldShelf } from "./hooks/useHoldShelf"
import { HoldShelfHeader } from "./components/HoldShelfHeader"
import { ViewModeTabs } from "./components/ViewModeTabs"
import { CapacityWarning } from "./components/CapacityWarning"
import { StatsBar } from "./components/StatsBar"
import { LocationFilter } from "./components/LocationFilter"
import { SearchBar } from "./components/SearchBar"
import { ExpiringHoldsView } from "./components/ExpiringHoldsView"
import { ExpiredHoldsSectionView } from "./components/ExpiredHoldsView"
import { PullListView } from "./components/PullListView"
import { EmptyState } from "./components/EmptyState"

export default function StaffHoldShelfPage(): React.ReactElement {
  const {
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
    onWayCount,
    noShowCount,
    setPendingNotPickedUp,
    setPendingRequeue,
    setSearchQuery,
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
  } = useHoldShelf()

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  const displayList = filteredPullList || pullList

  return (
    <AdminShell title="Smart Hold Shelf">
        <div className="p-8">
          <HoldShelfHeader
            batchAssigning={batchAssigning}
            onBatchAssign={handleBatchAssignSlots}
          />

          <ViewModeTabs
            viewMode={viewMode}
            onViewModeChange={handleViewModeChange}
            expiredCount={expiredHolds.length}
          />

          {capacityStatus && (
            <CapacityWarning capacityStatus={capacityStatus} />
          )}

          {viewMode === "pull-list" && pullList && (
            <>
              <StatsBar
                pullList={pullList}
                onWayCount={onWayCount}
                noShowCount={noShowCount}
              />
              <SearchBar value={searchQuery} onChange={setSearchQuery} />
              <LocationFilter
                pullList={pullList}
                selectedLocation={selectedLocation}
                onLocationSelect={handleLocationSelect}
              />
            </>
          )}

          {/* Main Content */}
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
          ) : viewMode === "expiring" && expiringHolds ? (
            <ExpiringHoldsView
              expiringHolds={expiringHolds}
              processingHoldId={processingHoldId}
              onRequeue={handleRequeue}
              onMarkNotPickedUp={handleMarkNotPickedUp}
            />
          ) : viewMode === "expired" ? (
            expiredHolds.length > 0 ? (
              <ExpiredHoldsSectionView
                expiredHolds={expiredHolds}
                processingHoldId={processingHoldId}
                onRequeue={handleRequeue}
                onMarkNotPickedUp={handleMarkNotPickedUp}
              />
            ) : (
              <EmptyState />
            )
          ) : displayList ? (
            <>
              <PullListView
                pullList={displayList}
                processingHoldId={processingHoldId}
                onPrintSlip={handlePrintSlip}
                onPrintLabels={handlePrintLabels}
                onRequeue={handleRequeue}
                onMarkNotPickedUp={handleMarkNotPickedUp}
                onUpdateShelfSlot={handleUpdateShelfSlot}
                onFulfillHold={handleFulfillHold}
                onTogglePatronOnWay={handleTogglePatronOnWay}
              />
              {/* Show expired holds at bottom of pull list view too */}
              {expiredHolds.length > 0 && (
                <ExpiredHoldsSectionView
                  expiredHolds={expiredHolds}
                  processingHoldId={processingHoldId}
                  onRequeue={handleRequeue}
                  onMarkNotPickedUp={handleMarkNotPickedUp}
                />
              )}
            </>
          ) : (
            <EmptyState />
          )}
      </div>

      {/* Confirmation: Mark Not Picked Up */}
      <DestructiveActionDialog
        isOpen={pendingNotPickedUp !== null}
        title="Mark as Not Picked Up"
        message="This hold will be marked as not picked up. The item will be returned to the shelf and the next patron in the queue will be notified."
        onConfirm={() => {
          if (pendingNotPickedUp !== null) {
            handleMarkNotPickedUp(pendingNotPickedUp)
            setPendingNotPickedUp(null)
          }
        }}
        onCancel={() => setPendingNotPickedUp(null)}
      />

      {/* Confirmation: Re-queue Hold */}
      <DestructiveActionDialog
        isOpen={pendingRequeue !== null}
        title="Re-queue Hold"
        message="This will move the hold to the end of the queue. The patron will need to wait for the item again."
        onConfirm={() => {
          if (pendingRequeue !== null) {
            handleRequeue(pendingRequeue)
            setPendingRequeue(null)
          }
        }}
        onCancel={() => setPendingRequeue(null)}
      />

    </AdminShell>
  )
}
