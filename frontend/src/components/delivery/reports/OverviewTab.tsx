/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Truck, Heart, Users, FileText } from "lucide-react"
import { ProgressBar } from "./ProgressBar"

interface Props {
  analyticsStart: string
  analyticsEnd: string
  setAnalyticsStart: (v: string) => void
  setAnalyticsEnd: (v: string) => void
  serviceLoading: boolean
  serviceAnalytics: {
    delivery_analytics: {
      total_deliveries: number
      success_rate?: number
      successful_deliveries: number
      failed_deliveries: number
      total_items_delivered: number
      average_items_per_delivery?: number
      unique_patrons_served: number
    }
    volunteer_analytics: {
      total_active_volunteers: number
      total_hours_logged: number
      average_hours_per_volunteer?: number
      average_deliveries_per_volunteer?: number
      hours_by_activity_type: Record<string, number>
    }
    patron_metrics: {
      active_patrons: number
      paused_patrons: number
      new_enrollments_in_period: number
    }
  } | undefined
  applicationPipeline: {
    by_status: Record<string, number>
    average_processing_days?: number
  } | undefined
}

export function OverviewTab({
  analyticsStart,
  analyticsEnd,
  setAnalyticsStart,
  setAnalyticsEnd,
  serviceLoading,
  serviceAnalytics,
  applicationPipeline,
}: Props) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Period:</label>
        <input
          type="date"
          value={analyticsStart}
          onChange={(e) => setAnalyticsStart(e.target.value)}
          className="px-3 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        />
        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">to</span>
        <input
          type="date"
          value={analyticsEnd}
          onChange={(e) => setAnalyticsEnd(e.target.value)}
          className="px-3 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        />
      </div>

      {serviceLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : serviceAnalytics ? (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Truck className="w-4 h-4 text-lsc-rose" />
              Delivery Metrics
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Deliveries</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.delivery_analytics.total_deliveries}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Success Rate</span>
                <span className="font-medium text-status-success-600 dark:text-status-success-400">{serviceAnalytics.delivery_analytics.success_rate?.toFixed(1)}%</span>
              </div>
              <div className="text-sm">
                <div className="flex justify-between mb-1">
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Successful</span>
                  <span className="text-status-success-600 dark:text-status-success-400">{serviceAnalytics.delivery_analytics.successful_deliveries}</span>
                </div>
                <ProgressBar value={serviceAnalytics.delivery_analytics.successful_deliveries} max={serviceAnalytics.delivery_analytics.total_deliveries} color="bg-status-success-500" />
              </div>
              <div className="text-sm">
                <div className="flex justify-between mb-1">
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Failed</span>
                  <span className="text-status-danger-600 dark:text-status-danger-400">{serviceAnalytics.delivery_analytics.failed_deliveries}</span>
                </div>
                <ProgressBar value={serviceAnalytics.delivery_analytics.failed_deliveries} max={serviceAnalytics.delivery_analytics.total_deliveries} color="bg-status-danger-500" />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Items Delivered</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.delivery_analytics.total_items_delivered}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg Items / Delivery</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.delivery_analytics.average_items_per_delivery?.toFixed(1)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Unique Patrons Served</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.delivery_analytics.unique_patrons_served}</span>
              </div>
            </div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Heart className="w-4 h-4 text-lsc-rose" />
              Volunteer Metrics
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Active Volunteers</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.volunteer_analytics.total_active_volunteers}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Hours</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.volunteer_analytics.total_hours_logged}h</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg Hours / Volunteer</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.volunteer_analytics.average_hours_per_volunteer?.toFixed(1)}h</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg Deliveries / Volunteer</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.volunteer_analytics.average_deliveries_per_volunteer?.toFixed(1)}</span>
              </div>
              {Object.keys(serviceAnalytics.volunteer_analytics.hours_by_activity_type).length > 0 && (
                <div>
                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Hours by Activity</p>
                  {Object.entries(serviceAnalytics.volunteer_analytics.hours_by_activity_type).map(([type, hours]) => (
                    <div key={type} className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <span className="capitalize">{type.replace(/_/g, ' ')}</span>
                      <span>{hours}h</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Users className="w-4 h-4 text-lsc-rose" />
              Patron Metrics
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Active Patrons</span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceAnalytics.patron_metrics.active_patrons}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Paused</span>
                <span className="font-medium text-status-warning-600 dark:text-status-warning-400">{serviceAnalytics.patron_metrics.paused_patrons}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">New Enrollments (Period)</span>
                <span className="font-medium text-status-success-600 dark:text-status-success-400">+{serviceAnalytics.patron_metrics.new_enrollments_in_period}</span>
              </div>
            </div>
          </div>

          {applicationPipeline && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <FileText className="w-4 h-4 text-lsc-rose" />
                Application Pipeline
              </h3>
              <div className="space-y-2">
                {Object.entries(applicationPipeline.by_status).map(([status, count]) => (
                  <div key={status} className="flex justify-between text-sm">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{status.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">{count}</span>
                  </div>
                ))}
                {applicationPipeline.average_processing_days !== undefined && (
                  <div className="pt-2 border-t border-lsc-border dark:border-earth-700 flex justify-between text-sm">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg Processing Time</span>
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">{applicationPipeline.average_processing_days?.toFixed(1)} days</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
