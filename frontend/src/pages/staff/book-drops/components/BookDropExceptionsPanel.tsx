/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Loader2, CheckCircle, AlertTriangle } from "lucide-react"
import { CheckInException, EXCEPTION_TYPES, getExceptionTypeLabel } from "@/api/book-drop-api"
import { getCurrentLocale } from '@/i18n'

interface BookDropExceptionsPanelProps {
  exceptions: CheckInException[]
  isLoading: boolean
  filter: string
  onFilterChange: (filter: string) => void
  onResolve: (exception: CheckInException) => void
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return "N/A"
  return new Date(dateStr).toLocaleString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export const BookDropExceptionsPanel: React.FC<BookDropExceptionsPanelProps> = ({
  exceptions,
  isLoading,
  filter,
  onFilterChange,
  onResolve,
}) => {
  return (
    <>
      <div className="flex flex-wrap items-center gap-4">
        <select
          value={filter}
          onChange={(e) => onFilterChange(e.target.value)}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="all">All Exception Types</option>
          {EXCEPTION_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
          </div>
        ) : exceptions.length === 0 ? (
          <div className="p-8 text-center">
            <CheckCircle className="w-12 h-12 mx-auto text-status-success-500 mb-4" />
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              No Pending Exceptions
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              All check-in exceptions have been resolved
            </p>
          </div>
        ) : (
          <div className="divide-y divide-lsc-border dark:divide-earth-700">
            {exceptions.map((exception) => (
              <div
                key={exception.id}
                className="p-4 flex items-center justify-between hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-lg bg-status-danger-100 dark:bg-status-danger-900/30">
                    <AlertTriangle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
                  </div>
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {exception.barcode}
                    </p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {getExceptionTypeLabel(exception.exception_type)}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {exception.message} | {formatDate(exception.created_at)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => onResolve(exception)}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
                >
                  <CheckCircle className="w-4 h-4" />
                  Resolve
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
