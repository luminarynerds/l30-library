/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Sparkles,
  Users,
  MousePointerClick,
  BookOpen,
  TrendingUp,
  AlertCircle,
  BarChart3,
  Loader2,
} from 'lucide-react'
import type { RecommendationStats } from '../../api/recommendations-api'

interface StatCardProps {
  title: string
  value: string
  icon: React.ElementType
  color: 'warning' | 'accent' | 'success' | 'category'
}

function StatCard({ title, value, icon: Icon, color }: StatCardProps): React.ReactElement {
  const colorClasses = {
    warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-lsc-rose',
    accent: 'bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light',
    success: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-600 dark:text-status-success-400',
    category: 'bg-category-50 dark:bg-category-900/20 text-category-600 dark:text-category-400',
  }

  return (

    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{title}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
        </div>
      </div>
    </div>
  )
}

interface StatisticsTabProps {
  stats: RecommendationStats
  isLoading: boolean
  hasError: boolean
}

export function StatisticsTab({ stats, isLoading, hasError }: StatisticsTabProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  if (hasError) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-earth-300 dark:text-earth-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">Statistics Not Available</h3>
        <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
          The statistics API endpoint is not available. Statistics will be shown when the recommendation
          system is fully configured.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Recommendations Served"
          value={stats.total_recommendations_served.toLocaleString()}
          icon={Sparkles}
          color="warning"
        />
        <StatCard
          title="Unique Users"
          value={stats.unique_users_served.toLocaleString()}
          icon={Users}
          color="accent"
        />
        <StatCard
          title="Click-Through Rate"
          value={`${(stats.click_through_rate * 100).toFixed(1)}%`}
          icon={MousePointerClick}
          color="success"
        />
        <StatCard
          title="Avg Items Shown"
          value={stats.average_items_shown.toFixed(1)}
          icon={BookOpen}
          color="category"
        />
      </div>

      {/* Algorithm Performance */}
      {stats.algorithm_performance.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-lsc-rose" />
            Algorithm Performance
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700">
                  <th className="text-left py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Algorithm
                  </th>
                  <th className="text-right py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Recommendations
                  </th>
                  <th className="text-right py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    CTR
                  </th>
                  <th className="text-right py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Avg Position
                  </th>
                </tr>
              </thead>
              <tbody>
                {stats.algorithm_performance.map((perf) => (
                  <tr
                    key={perf.algorithm}
                    className="border-b border-earth-100 dark:border-earth-700/50"
                  >
                    <td className="py-3 text-lsc-dark dark:text-lsc-cream">{perf.algorithm}</td>
                    <td className="py-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                      {perf.recommendations_count.toLocaleString()}
                    </td>
                    <td className="py-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                      {(perf.click_through_rate * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                      {perf.avg_position.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Most Recommended Items */}
      {stats.most_recommended_items.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-lsc-rose" />
            Most Recommended Items
          </h3>
          <div className="space-y-3">
            {stats.most_recommended_items.slice(0, 10).map((item, index) => (
              <div
                key={item.item_id}
                className="flex items-center justify-between p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-lsc-dark/70 dark:text-lsc-cream/70 w-6">
                    {index + 1}
                  </span>
                  <span className="font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</span>
                </div>
                <div className="text-right">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {item.times_recommended} recs
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {(item.ctr * 100).toFixed(1)}% CTR
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {stats.total_recommendations_served === 0 && (
        <div className="text-center py-12">
          <BarChart3 className="h-12 w-12 text-earth-300 dark:text-earth-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">No Statistics Yet</h3>
          <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            Statistics will appear here once the recommendation system starts serving recommendations.
          </p>
        </div>
      )}
    </div>
  )
}
