/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Star, Package, Heart, Clock, AlertTriangle } from "lucide-react"
import { useTranslation } from "@/i18n"
import { RatingBar } from "./RatingBar"

interface SatisfactionData {
  overall_ratings: {
    overall?: number
    item_satisfaction?: number
    volunteer_rating?: number
    timeliness_rating?: number
    total_responses: number
  }
  rating_distribution: Record<number, number>
  would_recommend_rate?: number
  monthly_trend: { period: string; average_rating?: number }[]
  follow_up_stats: {
    pending_follow_up: number
    completed_follow_up: number
  }
}

interface Props {
  satisfactionData: SatisfactionData | undefined
  satisfactionLoading: boolean
}

export function SatisfactionTab({ satisfactionData, satisfactionLoading }: Props) {
  const { t } = useTranslation()

  if (satisfactionLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!satisfactionData) {
    return <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryReports.noSatisfactionDataAvailable')}</div>
  }

  const metrics = [
    { label: 'Overall Rating', value: satisfactionData.overall_ratings.overall, icon: <Star className="w-5 h-5 text-status-warning-500" /> },
    { label: 'Item Satisfaction', value: satisfactionData.overall_ratings.item_satisfaction, icon: <Package className="w-5 h-5 text-earth-600" /> },
    { label: 'Volunteer Rating', value: satisfactionData.overall_ratings.volunteer_rating, icon: <Heart className="w-5 h-5 text-status-danger-500" /> },
    { label: 'Timeliness', value: satisfactionData.overall_ratings.timeliness_rating, icon: <Clock className="w-5 h-5 text-status-success-500" /> },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 text-center">
            <div className="flex justify-center mb-2">{metric.icon}</div>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
              {metric.value?.toFixed(1) ?? 'N/A'}
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{metric.label}</p>
            {metric.value && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">/ 5.0</p>}
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Rating Distribution</h3>
          <div className="space-y-2">
            {[5, 4, 3, 2, 1].map((star) => (
              <RatingBar
                key={star}
                rating={star}
                count={satisfactionData.rating_distribution[star] ?? 0}
                total={satisfactionData.overall_ratings.total_responses}
              />
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700 flex justify-between text-sm">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Responses</span>
            <span className="font-medium text-lsc-dark dark:text-lsc-cream">{satisfactionData.overall_ratings.total_responses}</span>
          </div>
          {satisfactionData.would_recommend_rate !== undefined && (
            <div className="flex justify-between text-sm mt-1">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Would Recommend</span>
              <span className="font-medium text-status-success-600 dark:text-status-success-400">{satisfactionData.would_recommend_rate?.toFixed(0)}%</span>
            </div>
          )}
        </div>

        {satisfactionData.monthly_trend.length > 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Monthly Trend</h3>
            <div className="space-y-2">
              {satisfactionData.monthly_trend.map((month) => (
                <div key={month.period} className="flex items-center gap-3 text-sm">
                  <span className="w-16 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs">{month.period}</span>
                  {month.average_rating ? (
                    <>
                      <div className="flex-1 bg-lsc-border dark:bg-earth-700 rounded-full h-2">
                        <div className="bg-status-warning-500 h-2 rounded-full" style={{ width: `${(month.average_rating / 5) * 100}%` }} />
                      </div>
                      <span className="w-8 text-right font-medium text-lsc-dark dark:text-lsc-cream">{month.average_rating.toFixed(1)}</span>
                    </>
                  ) : (
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">No data</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-status-warning-500" />
          Follow-up Status
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
            <p className="text-2xl font-bold text-status-warning-700 dark:text-status-warning-400">{satisfactionData.follow_up_stats.pending_follow_up}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Pending Follow-up</p>
          </div>
          <div className="text-center p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
            <p className="text-2xl font-bold text-status-success-700 dark:text-status-success-400">{satisfactionData.follow_up_stats.completed_follow_up}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Completed Follow-up</p>
          </div>
        </div>
      </div>
    </div>
  )
}
