/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Loader2, BarChart3, Users, CheckCircle, TrendingUp, TrendingDown } from 'lucide-react'
import { getMarketingAnalytics } from '@/api/marketing-api'
import { useTranslation } from '@/i18n'
import { StatCard } from './StatCard'

export function AnalyticsTab({ token }: { token: string }): React.ReactElement {
  const { t } = useTranslation()
  const [dateRange, setDateRange] = useState<number>(30)

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['marketing-analytics', dateRange],
    queryFn: () => getMarketingAnalytics(token, { days: dateRange }),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!analytics) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center">
        <BarChart3 className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('marketingCampaigns.noAnalyticsDataAvailable')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <select
          value={dateRange}
          onChange={(e) => setDateRange(Number(e.target.value))}
          className="px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Subscribers"
          value={analytics.total_subscribers.toLocaleString()}
          icon={Users}
          color="accent"
        />
        <StatCard
          title="Active Subscribers"
          value={analytics.active_subscribers.toLocaleString()}
          icon={CheckCircle}
          color="success"
        />
        <StatCard
          title="New This Month"
          value={`+${analytics.new_subscribers_this_month}`}
          icon={TrendingUp}
          color="warning"
          trend={analytics.subscriber_growth_rate}
        />
        <StatCard
          title="Unsubscribed"
          value={analytics.unsubscribed_this_month}
          icon={TrendingDown}
          color="danger"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">Email Performance</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Average Open Rate</span>
              <span className="text-xl font-bold text-status-success-600 dark:text-status-success-400">
                {analytics.average_open_rate.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-lsc-cream dark:bg-lsc-brown rounded-full h-2">
              <div
                className="bg-status-success-500 h-2 rounded-full"
                style={{ width: `${Math.min(100, analytics.average_open_rate)}%` }}
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Average Click Rate</span>
              <span className="text-xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {analytics.average_click_rate.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-lsc-cream dark:bg-lsc-brown rounded-full h-2">
              <div
                className="bg-earth-500 h-2 rounded-full"
                style={{ width: `${Math.min(100, analytics.average_click_rate * 5)}%` }}
              />
            </div>
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">Subscribers by Frequency</h3>
          <div className="space-y-3">
            {Object.entries(analytics.subscribers_by_frequency).map(([freq, count]) => (
              <div key={freq} className="flex items-center justify-between">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{freq}</span>
                <div className="flex items-center gap-3">
                  <div className="w-24 bg-lsc-cream dark:bg-lsc-brown rounded-full h-2">
                    <div
                      className="bg-lsc-rose h-2 rounded-full"
                      style={{
                        width: `${(count / analytics.active_subscribers) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream w-12 text-right">
                    {count.toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">Subscribers by Interest</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {analytics.subscribers_by_interest.map((item, _index) => (
            <div key={item.interest} className="text-center p-4 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl">
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {item.count.toLocaleString()}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.interest}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">Subscriber Growth Trend</h3>
        <div className="h-48 flex items-end gap-1">
          {analytics.subscriber_trend.slice(-30).map((point, _index) => {
            const maxCount = Math.max(...analytics.subscriber_trend.map((p) => p.count))
            const minCount = Math.min(...analytics.subscriber_trend.map((p) => p.count))
            const range = maxCount - minCount || 1
            const height = ((point.count - minCount) / range) * 100 + 20
            return (
              <div
                key={point.date}
                className="flex-1 bg-lsc-rose/70 hover:bg-lsc-rose rounded-t transition-colors"
                style={{ height: `${height}%` }}
                title={`${point.date}: ${point.count.toLocaleString()} subscribers`}
              />
            )
          })}
        </div>
        <div className="flex justify-between mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <span>30 days ago</span>
          <span>Today</span>
        </div>
      </div>
    </div>
  )
}
