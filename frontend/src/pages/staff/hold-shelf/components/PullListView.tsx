/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import {
  PrinterIcon,
  Clock,
  Navigation,
  UserX,
  QrCode,
  ScanLine,
  RotateCcw,
  Trash2,
  Loader2,
  CheckCircle,
  Check,
  X,
} from "lucide-react"
import { useTranslation } from "@/i18n"
import { getUrgencyColor, getUrgencyLabel } from "../constants"
import type { PullListItem, PullListResponse } from "../types"

interface PullListViewProps {
  pullList: PullListResponse
  processingHoldId: number | null
  onPrintSlip: (holdId: number) => void
  onPrintLabels: (items: PullListItem[]) => void
  onRequeue: (holdId: number) => void
  onMarkNotPickedUp: (holdId: number) => void
  onUpdateShelfSlot: (holdId: number, slot: string | null) => void
  onFulfillHold: (holdId: number) => void
  onTogglePatronOnWay: (holdId: number) => void
}

function InlineSlotEditor({
  holdId,
  currentSlot,
  onSave,
  disabled,
}: {
  holdId: number
  currentSlot: string | null
  onSave: (holdId: number, slot: string | null) => void
  disabled: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(currentSlot || "")

  if (!editing) {
    return (
      <button
        onClick={() => { setValue(currentSlot || ""); setEditing(true) }}
        disabled={disabled}
        className="group"
        title="Click to edit shelf slot"
        aria-label={currentSlot ? `Edit shelf slot ${currentSlot}` : "Add shelf slot"}
      >
        {currentSlot ? (
          <span className="inline-block bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-200 px-2 py-1 rounded font-mono font-bold text-sm group-hover:ring-2 group-hover:ring-status-success-400 transition-all">
            {currentSlot}
          </span>
        ) : (
          <span className="text-earth-600 dark:text-earth-200 text-sm hover:text-lsc-rose transition-colors">
            + slot
          </span>
        )}
      </button>
    )
  }

  const handleSave = () => {
    onSave(holdId, value.trim() || null)
    setEditing(false)
  }

  const handleCancel = () => {
    setValue(currentSlot || "")
    setEditing(false)
  }

  return (
    <div className="flex items-center gap-1">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value.toUpperCase())}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSave()
          if (e.key === "Escape") handleCancel()
        }}
        placeholder="A-03"
        aria-label="Shelf slot"
        autoFocus
        className="w-16 px-1.5 py-0.5 text-sm font-mono border border-lsc-border dark:border-earth-600 rounded bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:outline-none"
      />
      <button onClick={handleSave} className="text-status-success-600 hover:text-status-success-700" title="Save" aria-label="Save shelf slot">
        <Check className="h-3.5 w-3.5" />
      </button>
      <button onClick={handleCancel} className="text-status-danger-500 hover:text-status-danger-600" title="Cancel" aria-label="Cancel editing shelf slot">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

export function PullListView({
  pullList,
  processingHoldId,
  onPrintSlip,
  onPrintLabels,
  onRequeue,
  onMarkNotPickedUp,
  onUpdateShelfSlot,
  onFulfillHold,
  onTogglePatronOnWay,
}: PullListViewProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      {pullList.locations.map((locationGroup) => (
        <div
          key={locationGroup.location}
          className="rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden bg-lsc-white dark:bg-earth-800"
        >
          {/* Location Header */}
          <div className="bg-earth-50 dark:bg-earth-900 px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
            <div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {locationGroup.location}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {locationGroup.item_count} items ready for pickup
              </p>
            </div>
            <button
              onClick={() => onPrintLabels(locationGroup.items)}
              className="flex items-center gap-2 px-4 py-2 bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light rounded-lg hover:bg-earth-100 transition-colors"
            >
              <PrinterIcon className="h-4 w-4" />
              Print Labels
            </button>
          </div>

          {/* Items Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <caption className="sr-only">Items ready for pickup at this location</caption>
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900">
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                    Slot
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                    Patron
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                    Item Title
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                    Call #
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                    Expires
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                    Status
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {locationGroup.items.map((item) => (
                  <tr
                    key={item.hold_id}
                    className="border-b border-lsc-border dark:border-earth-700 hover:bg-earth-50 dark:hover:bg-earth-800"
                  >
                    <td className="px-4 py-4">
                      <InlineSlotEditor
                        holdId={item.hold_id}
                        currentSlot={item.shelf_slot}
                        onSave={onUpdateShelfSlot}
                        disabled={processingHoldId === item.hold_id}
                      />
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-earth-100 dark:bg-earth-800/30">
                          <span className="text-sm font-bold text-lsc-rose dark:text-lsc-rose-light">
                            {item.patron_initials}
                          </span>
                        </div>
                        <div className="text-sm">
                          <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {item.patron_name}
                          </div>
                          <div className="text-lsc-dark/70 dark:text-lsc-cream/70">
                            {item.patron_library_card}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                        {item.item_title}
                      </div>
                      {item.item_author && (
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {item.item_author}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {item.call_number || "-"}
                    </td>
                    <td className="px-4 py-4">
                      <div
                        className={`flex items-center gap-1 text-sm font-medium ${getUrgencyColor(item.days_until_expiry)}`}
                      >
                        <Clock className="h-3 w-3" />
                        {getUrgencyLabel(item.days_until_expiry)}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-col gap-1">
                        <button
                          onClick={() => onTogglePatronOnWay(item.hold_id)}
                          disabled={processingHoldId === item.hold_id}
                          className={`inline-flex items-center gap-1 text-xs font-medium rounded px-1.5 py-0.5 transition-colors ${
                            item.patron_on_way
                              ? "bg-status-info-100 dark:bg-status-info-900/30 text-status-info-700 dark:text-status-info-300 hover:bg-status-info-200"
                              : "text-earth-600 dark:text-earth-600 hover:text-status-info-600 hover:bg-status-info-50 dark:hover:bg-status-info-900/20"
                          }`}
                          title={item.patron_on_way ? "Click to clear on-way" : "Mark patron as on way"}
                        >
                          <Navigation className="h-3 w-3" />
                          {item.patron_on_way ? "On Way" : "On Way?"}
                        </button>
                        {item.no_show_count > 0 && (
                          <span className="inline-flex items-center gap-1 text-status-warning-600 text-xs font-medium">
                            <UserX className="h-3 w-3" /> {item.no_show_count} no-show
                            {item.no_show_count > 1 ? "s" : ""}
                          </span>
                        )}
                        {item.qr_pickup_code && (
                          <span className="inline-flex items-center gap-1 text-status-success-600 text-xs">
                            <QrCode className="h-3 w-3" /> QR
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex gap-1">
                        <button
                          onClick={() => onFulfillHold(item.hold_id)}
                          disabled={processingHoldId === item.hold_id}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300 rounded hover:bg-status-success-100 transition-colors disabled:opacity-50"
                          title="Mark as picked up"
                        >
                          {processingHoldId === item.hold_id ? (
                            <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
                          ) : (
                            <CheckCircle className="h-3 w-3" />
                          )}
                          Picked Up
                        </button>
                        <button
                          onClick={() => onPrintSlip(item.hold_id)}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light rounded hover:bg-earth-100 transition-colors"
                          title={t('staffHoldShelf.printShelfSlipWithQr')}
                        >
                          <ScanLine className="h-3 w-3" />
                          Slip
                        </button>
                        <button
                          onClick={() => onRequeue(item.hold_id)}
                          disabled={processingHoldId === item.hold_id}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300 rounded hover:bg-status-warning-100 transition-colors disabled:opacity-50"
                          title={t('staffHoldShelf.reQueueToEndOf2')}
                        >
                          <RotateCcw className="h-3 w-3" />
                        </button>
                        <button
                          onClick={() => onMarkNotPickedUp(item.hold_id)}
                          disabled={processingHoldId === item.hold_id}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded hover:bg-status-danger-100 transition-colors disabled:opacity-50"
                          title={t('staffHoldShelf.markNotPickedUp')}
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}
