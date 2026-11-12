/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Star } from "lucide-react"
import { useTranslation } from "@/i18n"
import { ProgressBar } from "./ProgressBar"

interface DeliveryReport {
  period: string
  total_deliveries: number
  completed_deliveries: number
  failed_deliveries: number
  total_items_delivered: number
  average_rating?: number
}

interface DeliveryAnalytics {
  total_deliveries: number
  success_rate?: number
  total_items_delivered: number
  average_rating?: number
  deliveries_by_status: Record<string, number>
}

interface Props {
  analyticsStart: string
  analyticsEnd: string
  setAnalyticsStart: (v: string) => void
  setAnalyticsEnd: (v: string) => void
  deliveryAnalytics: DeliveryAnalytics | undefined
  deliveryReports: DeliveryReport[] | undefined
  deliveryReportsLoading: boolean
}

export function DeliveriesTab({
  analyticsStart,
  analyticsEnd,
  setAnalyticsStart,
  setAnalyticsEnd,
  deliveryAnalytics,
  deliveryReports,
  deliveryReportsLoading,
}: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      {deliveryAnalytics && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Delivery Analytics</h3>
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={analyticsStart}
                onChange={(e) => setAnalyticsStart(e.target.value)}
                className="px-2 py-1 bg-lsc-cream dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded text-xs text-lsc-dark dark:text-lsc-cream"
              />
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">to</span>
              <input
                type="date"
                value={analyticsEnd}
                onChange={(e) => setAnalyticsEnd(e.target.value)}
                className="px-2 py-1 bg-lsc-cream dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded text-xs text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{deliveryAnalytics.total_deliveries}</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Total</p>
            </div>
            <div className="text-center p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
              <p className="text-2xl font-bold text-status-success-700 dark:text-status-success-400">{deliveryAnalytics.success_rate?.toFixed(0)}%</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Success Rate</p>
            </div>
            <div className="text-center p-3 bg-earth-50 dark:bg-earth-800/20 rounded-lg">
              <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{deliveryAnalytics.total_items_delivered}</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Items Delivered</p>
            </div>
            <div className="text-center p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
              <p className="text-2xl font-bold text-status-warning-700 dark:text-status-warning-400">
                {deliveryAnalytics.average_rating?.toFixed(1) ?? 'N/A'}
              </p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Avg Rating</p>
            </div>
          </div>

          {Object.keys(deliveryAnalytics.deliveries_by_status).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">By Status</h4>
              <div className="space-y-1.5">
                {Object.entries(deliveryAnalytics.deliveries_by_status).map(([status, count]) => (
                  <div key={status} className="flex items-center gap-2 text-sm">
                    <span className="w-28 text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{status.replace(/_/g, ' ')}</span>
                    <div className="flex-1 bg-lsc-border dark:bg-earth-700 rounded h-2">
                      <div
                        className="bg-lsc-rose h-2 rounded"
                        style={{ width: `${deliveryAnalytics.total_deliveries > 0 ? (count / deliveryAnalytics.total_deliveries) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-lsc-dark/70 dark:text-lsc-cream/70">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Monthly Delivery History</h3>
        </div>
        {deliveryReportsLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : deliveryReports && deliveryReports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Period</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Total</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Completed</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Failed</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Items</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Avg Rating</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Success</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {deliveryReports.map((report) => (
                  <tr key={report.period} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                    <td className="px-4 py-2 font-medium text-lsc-dark dark:text-lsc-cream">{report.period}</td>
                    <td className="px-4 py-2 text-lsc-dark/80 dark:text-lsc-cream/80">{report.total_deliveries}</td>
                    <td className="px-4 py-2 text-status-success-600 dark:text-status-success-400">{report.completed_deliveries}</td>
                    <td className="px-4 py-2 text-status-danger-600 dark:text-status-danger-400">{report.failed_deliveries}</td>
                    <td className="px-4 py-2 text-lsc-dark/80 dark:text-lsc-cream/80">{report.total_items_delivered}</td>
                    <td className="px-4 py-2">
                      {report.average_rating ? (
                        <span className="flex items-center gap-1">
                          <Star className="w-3.5 h-3.5 text-status-warning-500" />
                          {report.average_rating.toFixed(1)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-2">
                      <ProgressBar value={report.completed_deliveries} max={report.total_deliveries} color="bg-status-success-500" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-6 text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryReports.noDeliveryReportData')}</div>
        )}
      </div>
    </div>
  )
}
