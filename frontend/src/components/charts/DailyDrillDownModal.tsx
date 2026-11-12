/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react"
import { X, Loader2, BookOpen, RotateCcw, User } from "lucide-react"
import { fetchApi } from '@/api/fetchApi'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CheckoutDetail {
  checkout_id: number
  item_title: string
  item_author: string
  patron_name: string
  checked_out_at: string
}

interface ReturnDetail {
  checkout_id: number
  item_title: string
  item_author: string
  patron_name: string
  returned_at: string
}

interface DailyDrillDownData {
  date: string
  checkouts: CheckoutDetail[]
  returns: ReturnDetail[]
  patron_count: number
}

interface DailyDrillDownModalProps {
  isOpen: boolean
  onClose: () => void
  date: string
  token: string | null
}

export default function DailyDrillDownModal({
  isOpen,
  onClose,
  date,
  token,
}: DailyDrillDownModalProps): React.ReactElement | null {
  const [data, setData] = useState<DailyDrillDownData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !token || !date) return

    const fetchDailyDetails = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const result = await fetchApi(`/reports/circulation/daily-details?date=${date}`)
        setData(result)
      } catch (_err) {
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
        const msg = _err instanceof Error ? _err.message : (_err as { message?: string })?.message
        setError(msg || "Failed to load data")
      } finally {
        setIsLoading(false)
      }
    }

    fetchDailyDetails()
  }, [isOpen, date, token])

  if (!isOpen) return null

  const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString()
  const formatTime = (dateStr: string) =>
    new Date(dateStr).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })

  return (
     
    <ModalBackdrop onClose={onClose} title="Daily Activity Details">
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
          <div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Daily Activity Details
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {formatDate(date)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
            aria-label={t('aria.addRoleModal.closeModal')}
          >
            <X className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 min-h-0 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-64 text-status-danger-600 dark:text-status-danger-400">
              <p className="text-lg font-medium">Error loading data</p>
              <p className="text-sm mt-2">{error}</p>
            </div>
          ) : data ? (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <BookOpen className="w-5 h-5 text-lsc-rose" />
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Checkouts
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {data.checkouts.length}
                  </p>
                </div>
                <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <RotateCcw className="w-5 h-5 text-lsc-rose" />
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Returns
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {data.returns.length}
                  </p>
                </div>
                <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <User className="w-5 h-5 text-lsc-rose" />
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Active Patrons
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {data.patron_count}
                  </p>
                </div>
              </div>

              {/* Checkouts List */}
              <div>
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-lsc-rose" />
                  Items Checked Out
                </h3>
                {data.checkouts.length > 0 ? (
                  <div className="space-y-2">
                    {data.checkouts.map((checkout) => (
                      <div
                        key={checkout.checkout_id}
                        className="bg-lsc-cream dark:bg-earth-700 rounded-lg p-4 flex items-start justify-between gap-4"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={checkout.item_title}>
                            {checkout.item_title}
                          </p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            by {checkout.item_author}
                          </p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            Patron: {checkout.patron_name}
                          </p>
                        </div>
                        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                          {formatTime(checkout.checked_out_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">
                    No checkouts on this day
                  </p>
                )}
              </div>

              {/* Returns List */}
              <div>
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                  <RotateCcw className="w-5 h-5 text-lsc-rose" />
                  Items Returned
                </h3>
                {data.returns.length > 0 ? (
                  <div className="space-y-2">
                    {data.returns.map((returnItem) => (
                      <div
                        key={returnItem.checkout_id}
                        className="bg-lsc-cream dark:bg-earth-700 rounded-lg p-4 flex items-start justify-between gap-4"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={returnItem.item_title}>
                            {returnItem.item_title}
                          </p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            by {returnItem.item_author}
                          </p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            Patron: {returnItem.patron_name}
                          </p>
                        </div>
                        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                          {formatTime(returnItem.returned_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">
                    No returns on this day
                  </p>
                )}
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-t border-lsc-border dark:border-earth-700 p-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}