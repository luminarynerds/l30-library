/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { CheckCircle, Users, ArrowRight, XCircle } from "lucide-react"
import { CheckInResult, getResultStatusLabel } from "@/api/book-drop-api"

interface BookDropItemsPanelProps {
  results: CheckInResult[]
  title?: string
  showHeader?: boolean
}

export const BookDropItemsPanel: React.FC<BookDropItemsPanelProps> = ({
  results,
  title = "Recent Check-ins",
  showHeader = true,
}) => {
  if (results.length === 0) {
    return null
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
      {showHeader && (
        <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {title}
          </h3>
        </div>
      )}
      <div className="divide-y divide-lsc-border dark:divide-earth-700">
        {results.map((result, idx) => (
          <div
            key={result.id || idx}
            className={`p-4 flex items-center justify-between ${
              result.status === "exception" || result.status === "not_found"
                ? "bg-status-danger-50/50 dark:bg-status-danger-900/10"
                : result.status === "hold_triggered"
                ? "bg-earth-50/50 dark:bg-earth-800/10"
                : result.status === "transit"
                ? "bg-category-50/50 dark:bg-category-900/10"
                : ""
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`p-1.5 rounded-full ${
                  result.status === "success"
                    ? "bg-status-success-100 dark:bg-status-success-900/30"
                    : result.status === "hold_triggered"
                    ? "bg-earth-100 dark:bg-earth-800/30"
                    : result.status === "transit"
                    ? "bg-category-100 dark:bg-category-900/30"
                    : "bg-status-danger-100 dark:bg-status-danger-900/30"
                }`}
              >
                {result.status === "success" ? (
                  <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
                ) : result.status === "hold_triggered" ? (
                  <Users className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                ) : result.status === "transit" ? (
                  <ArrowRight className="w-4 h-4 text-category-600 dark:text-category-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" />
                )}
              </div>
              <div>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {result.item_title || result.barcode}
                </p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {result.barcode}
                  {result.item_author && ` by ${result.item_author}`}
                </p>
              </div>
            </div>
            <div className="text-right">
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  result.status === "success"
                    ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400"
                    : result.status === "hold_triggered"
                    ? "bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light"
                    : result.status === "transit"
                    ? "bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-400"
                    : "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400"
                }`}
              >
                {getResultStatusLabel(result.status)}
              </span>
              {result.hold_patron_name && (
                <p className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-1">
                  Hold for: {result.hold_patron_name}
                </p>
              )}
              {result.destination_branch && (
                <p className="text-xs text-category-600 dark:text-category-400 mt-1">
                  To: {result.destination_branch}
                </p>
              )}
              {result.exception_message && (
                <p className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-1">
                  {result.exception_message}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
