/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Loader2, Inbox, Plus, Play, Edit3, Trash2 } from "lucide-react"
import { BookDrop, BookDropStatus, BOOK_DROP_STATUSES, getBookDropStatusLabel, getBackdateModeLabel } from "@/api/book-drop-api"

interface BookDropListProps {
  bookDrops: BookDrop[]
  isLoading: boolean
  filter: "all" | BookDropStatus
  onFilterChange: (filter: "all" | BookDropStatus) => void
  onProcess: (drop: BookDrop) => void
  onEdit: (drop: BookDrop) => void
  onDelete: (drop: BookDrop) => void
  onAddNew: () => void
}

export const BookDropList: React.FC<BookDropListProps> = ({
  bookDrops,
  isLoading,
  filter,
  onFilterChange,
  onProcess,
  onEdit,
  onDelete,
  onAddNew,
}) => {
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "active":
        return "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400"
      case "inactive":
        return "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
      case "maintenance":
        return "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400"
      case "completed":
        return "bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light"
      default:
        return "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-4">
        <select
          value={filter}
          onChange={(e) => onFilterChange(e.target.value as "all" | BookDropStatus)}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="all">All Statuses</option>
          {BOOK_DROP_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
          </div>
        ) : bookDrops.length === 0 ? (
          <div className="p-8 text-center">
            <Inbox className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              No Book Drops Found
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Add your first book drop location
            </p>
            <button
              onClick={onAddNew}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Book Drop
            </button>
          </div>
        ) : (
          <div className="divide-y divide-lsc-border dark:divide-earth-700">
            {bookDrops.map((drop) => (
              <div
                key={drop.id}
                className="p-4 flex items-center justify-between hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div
                    className={`p-2 rounded-lg ${
                      drop.status === "active"
                        ? "bg-status-success-100 dark:bg-status-success-900/30"
                        : drop.status === "maintenance"
                        ? "bg-status-warning-100 dark:bg-status-warning-900/30"
                        : "bg-earth-100 dark:bg-earth-700"
                    }`}
                  >
                    <Inbox
                      className={`w-5 h-5 ${
                        drop.status === "active"
                          ? "text-status-success-600 dark:text-status-success-400"
                          : drop.status === "maintenance"
                          ? "text-status-warning-600 dark:text-status-warning-400"
                          : "text-lsc-dark/70 dark:text-lsc-cream/70"
                      }`}
                    />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {drop.name}
                      </h3>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getStatusBadgeClass(drop.status)}`}>
                        {getBookDropStatusLabel(drop.status)}
                      </span>
                    </div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Code: {drop.code} | {drop.branch_location}
                      {drop.physical_location && ` - ${drop.physical_location}`}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      Backdating: {getBackdateModeLabel(drop.backdate_mode)}
                      {drop.exempt_overnight_fines && " | Exempt overnight fines"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onProcess(drop)}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-success-600 dark:hover:text-status-success-400 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                    title="Process returns"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onEdit(drop)}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onDelete(drop)}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
