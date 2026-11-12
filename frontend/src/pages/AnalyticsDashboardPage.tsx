/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BarChart3,
  BookOpen,
  Users,
  TrendingUp,
  AlertTriangle,
  DollarSign,
  Clock,
  Award,
  RefreshCw,
} from 'lucide-react'
import {
  getCirculationAnalytics,
  getCollectionHealth,
  getDriftingItems,
  getPatronEngagement,
  getTopReaders,
  getReadingAnalytics,
  getFineAnalytics,
  getPopularItems,
} from '@/api/api'
import { StatCard } from '@/components/ui/StatCard'
import { StatGrid } from '@/components/ui/StatGrid'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import PageContainer from '@/components/layout/PageContainer'

function SectionHeader({ title, icon: Icon }: { title: string; icon: React.ElementType }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon className="w-5 h-5 text-lsc-rose" />
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h2>
    </div>
  )
}

// eslint-disable-next-line complexity
export default function AnalyticsDashboardPage(): React.ReactElement {
  const { t } = useTranslation()
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d' | 'year'>('30d')
  const [activeTab, setActiveTab] = useState<'overview' | 'circulation' | 'collection' | 'patrons' | 'reading' | 'fines'>('overview')

  const daysParams = {
    '7d': { days: 7 },
    '30d': { days: 30 },
    '90d': { days: 90 },
    'year': { days: 365 },
  }

  const { data: circulation, isLoading: loadingCirculation } = useQuery({
    queryKey: ['analytics', 'circulation', dateRange],
    queryFn: () => getCirculationAnalytics(daysParams[dateRange]),
  })

  const { data: collectionHealth, isLoading: loadingCollection } = useQuery({
    queryKey: ['analytics', 'collection-health'],
    queryFn: () => getCollectionHealth(),
  })

  const { data: driftingItems } = useQuery({
    queryKey: ['analytics', 'drifting-items'],
    queryFn: () => getDriftingItems({ limit: 10 }),
  })

  const { data: patronEngagement, isLoading: loadingPatrons } = useQuery({
    queryKey: ['analytics', 'patron-engagement', dateRange],
    queryFn: () => getPatronEngagement(daysParams[dateRange]),
  })

  const { data: topReaders } = useQuery({
    queryKey: ['analytics', 'top-readers'],
    queryFn: () => getTopReaders({ limit: 10 }),
  })

  const { data: readingAnalytics, isLoading: loadingReading } = useQuery({
    queryKey: ['analytics', 'reading', dateRange],
    queryFn: () => getReadingAnalytics(daysParams[dateRange]),
  })

  const { data: fineAnalytics, isLoading: loadingFines } = useQuery({
    queryKey: ['analytics', 'fines', dateRange],
    queryFn: () => getFineAnalytics(daysParams[dateRange]),
  })

  const { data: popularItems } = useQuery({
    queryKey: ['analytics', 'popular-items'],
    queryFn: () => getPopularItems({ limit: 10 }),
  })

  const queryClient = useQueryClient()
  const isLoading = loadingCirculation || loadingCollection || loadingPatrons || loadingReading || loadingFines

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'circulation', label: 'Circulation', icon: BookOpen },
    { id: 'collection', label: 'Collection', icon: BookOpen },
    { id: 'patrons', label: 'Patrons', icon: Users },
    { id: 'reading', label: 'Reading', icon: Clock },
    { id: 'fines', label: 'Fines', icon: DollarSign },
  ] as const

  return (

    <AdminShell title="Analytics Dashboard" subtitle={t('analyticsDashboard.comprehensiveLibraryMetricsAndInsights')}>    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer width="wide" className="py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div></div>
          <div className="flex items-center gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value as typeof dateRange)}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="year">Last year</option>
            </select>
            <button
              onClick={() => queryClient.invalidateQueries({ queryKey: ['analytics'] })}
              aria-label={t('aria.analyticsDashboard.refreshDashboard')}
              className="p-2 rounded-lg bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose"></div>
          </div>
        ) : (
          <>
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div className="space-y-8">
                {/* Key Metrics */}
                <StatGrid columns={4}>
                  <StatCard
                    title="Total Checkouts"
                    value={circulation?.total_checkouts?.toLocaleString() ?? 0}
                    icon={BookOpen}
                    color="accent"
                  />
                  <StatCard
                    title="Active Patrons"
                    value={patronEngagement?.active_patrons?.toLocaleString() ?? 0}
                    icon={Users}
                    color="success"
                  />
                  <StatCard
                    title="Collection Size"
                    value={collectionHealth?.total_items?.toLocaleString() ?? 0}
                    icon={BarChart3}
                    color="category"
                  />
                  <StatCard
                    title="Reading Minutes"
                    value={readingAnalytics?.total_minutes_read?.toLocaleString() ?? 0}
                    icon={Clock}
                    color="warning"
                  />
                </StatGrid>

                {/* Alerts & Popular Items */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Alerts */}
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Attention Required" icon={AlertTriangle} />
                    <div className="space-y-3">
                      {(circulation?.overdue_count ?? 0) > 0 && (
                        <div className="flex items-center justify-between p-3 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg">
                          <span className="text-status-danger-700 dark:text-status-danger-400">Overdue Items</span>
                          <span className="font-bold text-status-danger-700 dark:text-status-danger-400">{circulation?.overdue_count}</span>
                        </div>
                      )}
                      {(collectionHealth?.damaged_items ?? 0) > 0 && (
                        <div className="flex items-center justify-between p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
                          <span className="text-status-warning-700 dark:text-status-warning-400">Damaged Items</span>
                          <span className="font-bold text-status-warning-700 dark:text-status-warning-400">{collectionHealth?.damaged_items}</span>
                        </div>
                      )}
                      {(driftingItems?.items?.length ?? 0) > 0 && (
                        <div className="flex items-center justify-between p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
                          <span className="text-status-warning-700 dark:text-status-warning-400">Drifting Items (90+ days)</span>
                          <span className="font-bold text-status-warning-700 dark:text-status-warning-400">{driftingItems?.total_drifting}</span>
                        </div>
                      )}
                      {(fineAnalytics?.outstanding_total ?? 0) > 0 && (
                        <div className="flex items-center justify-between p-3 bg-earth-50 dark:bg-earth-800/20 rounded-lg">
                          <span className="text-lsc-rose dark:text-lsc-rose-light">Outstanding Fines</span>
                          <span className="font-bold text-lsc-rose dark:text-lsc-rose-light">${(fineAnalytics?.outstanding_total ?? 0).toFixed(2)}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Popular Items */}
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Popular Items" icon={TrendingUp} />
                    <div className="space-y-3">
                      {popularItems?.items?.slice(0, 5).map((item, index) => (
                        <div key={item.catalog_item_id} className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="w-6 h-6 rounded-full bg-lsc-rose/20 text-lsc-rose text-sm flex items-center justify-center font-medium">
                              {index + 1}
                            </span>
                            <div>
                              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream line-clamp-1" title={item.title}>{item.title}</p>
                              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{item.author ?? 'Unknown'}</p>
                            </div>
                          </div>
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.checkout_count} checkouts</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Top Readers */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                  <SectionHeader title="Top Readers" icon={Award} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                    {topReaders?.readers?.slice(0, 5).map((reader, index) => (
                      <div key={reader.user_id} className="text-center p-4 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                        <div className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center text-white font-bold ${
                          index === 0 ? 'bg-status-warning-500' : index === 1 ? 'bg-earth-400' : index === 2 ? 'bg-status-warning-600' : 'bg-earth-400'
                        }`}>
                          {index + 1}
                        </div>
                        <p className="mt-2 font-medium text-lsc-dark dark:text-lsc-cream text-sm">{reader.user_name}</p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{reader.total_minutes.toLocaleString()} min</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Circulation Tab */}
            {activeTab === 'circulation' && circulation && (
              <div className="space-y-6">
                <StatGrid columns={4}>
                  <StatCard title="Total Checkouts" value={circulation.total_checkouts} icon={BookOpen} color="accent" />
                  <StatCard title="Returns Today" value={circulation.returns_today} icon={BookOpen} color="success" />
                  <StatCard title="Active Checkouts" value={circulation.active_checkouts} icon={Clock} color="warning" />
                  <StatCard title="Overdue Items" value={circulation.overdue_count} icon={AlertTriangle} color="danger" />
                </StatGrid>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Circulation Metrics" icon={BarChart3} />
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Checkouts Today</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{circulation.checkouts_today}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Unique Patrons</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{circulation.unique_patrons}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg Daily Checkouts</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{(circulation.avg_daily_checkouts ?? 0).toFixed(1)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Turnover Rate</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{(circulation.turnover_rate ?? 0).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Trends" icon={TrendingUp} />
                    <div className="space-y-4">
                      {circulation.checkout_trend && (
                        <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Checkout Trend</span>
                            <span className={`font-medium ${
                              circulation.checkout_trend.direction === 'up' ? 'text-status-success-600' :
                              circulation.checkout_trend.direction === 'down' ? 'text-status-danger-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                            }`}>
                              {circulation.checkout_trend.direction === 'up' ? '↑' : circulation.checkout_trend.direction === 'down' ? '↓' : '→'} {(circulation.checkout_trend?.change_percentage ?? 0).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                      {circulation.overdue_trend && (
                        <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Overdue Trend</span>
                            <span className={`font-medium ${
                              circulation.overdue_trend.direction === 'down' ? 'text-status-success-600' :
                              circulation.overdue_trend.direction === 'up' ? 'text-status-danger-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                            }`}>
                              {circulation.overdue_trend.direction === 'up' ? '↑' : circulation.overdue_trend.direction === 'down' ? '↓' : '→'} {(circulation.overdue_trend?.change_percentage ?? 0).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Collection Tab */}
            {activeTab === 'collection' && collectionHealth && (
              <div className="space-y-6">
                <StatGrid columns={4}>
                  <StatCard title="Total Items" value={collectionHealth.total_items} icon={BookOpen} color="accent" />
                  <StatCard title="Available" value={collectionHealth.total_available} icon={BookOpen} color="success" />
                  <StatCard title="Checked Out" value={collectionHealth.total_items - collectionHealth.total_available} icon={Clock} color="warning" />
                  <StatCard title="Damaged" value={collectionHealth.damaged_items} icon={AlertTriangle} color="danger" />
                </StatGrid>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Collection Status" icon={BarChart3} />
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Never Checked Out</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{collectionHealth.never_checked_out}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Missing Items</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{collectionHealth.missing_items}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Utilization Rate</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{(collectionHealth.utilization_rate ?? 0).toFixed(1)}%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg Checkouts/Item</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{(collectionHealth.avg_checkouts_per_item ?? 0).toFixed(1)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Dormancy Breakdown" icon={BarChart3} />
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Active (&lt;90 days)</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{collectionHealth.dormancy.active_count} ({(collectionHealth.dormancy?.active_percentage ?? 0).toFixed(1)}%)</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Drifting (90-180 days)</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{collectionHealth.dormancy.drifting_count} ({(collectionHealth.dormancy?.drifting_percentage ?? 0).toFixed(1)}%)</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Dormant (180+ days)</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{collectionHealth.dormancy.dormant_count} ({collectionHealth.dormancy.dormant_percentage.toFixed(1)}%)</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Drifting Items */}
                {driftingItems && driftingItems.items.length > 0 && (
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title={t('analyticsDashboard.driftingItemsDaysSinceCheckout')} icon={AlertTriangle} />
                    <div className="overflow-x-auto">
                      <table className="w-full" aria-label={t('analyticsDashboard.driftingItemsToDaysSince')}>
                        <thead>
                          <tr className="border-b border-lsc-border dark:border-earth-700">
                            <th scope="col" className="text-left py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Title</th>
                            <th scope="col" className="text-left py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Author</th>
                            <th className="text-right py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Days Since Checkout</th>
                            <th className="text-right py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Copies</th>
                          </tr>
                        </thead>
                        <tbody>
                          {driftingItems.items.map((item) => (
                            <tr key={item.catalog_item_id} className="border-b border-earth-100 dark:border-earth-700/50">
                              <td className="py-2 text-sm text-lsc-dark dark:text-lsc-cream">{item.title}</td>
                              <td className="py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.author ?? '-'}</td>
                              <td className="py-2 text-sm text-right text-lsc-dark dark:text-lsc-cream">{item.days_since_checkout}</td>
                              <td className="py-2 text-sm text-right text-lsc-dark dark:text-lsc-cream">{item.copy_count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Patrons Tab */}
            {activeTab === 'patrons' && patronEngagement && (
              <div className="space-y-6">
                <StatGrid columns={4}>
                  <StatCard title="Active Patrons" value={patronEngagement.active_patrons} icon={Users} color="accent" />
                  <StatCard title="New Patrons" value={patronEngagement.new_patrons} icon={Users} color="success" />
                  <StatCard title="Dormant Patrons" value={patronEngagement.dormant_patrons} icon={Clock} color="warning" />
                  <StatCard title="Avg Checkouts/Patron" value={patronEngagement.avg_checkouts_per_patron.toFixed(1)} icon={TrendingUp} color="category" />
                </StatGrid>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Patron Metrics" icon={BarChart3} />
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Patrons</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{patronEngagement.total_patrons.toLocaleString()}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Engagement Rate</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{patronEngagement.engagement_rate.toFixed(1)}%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Retention Rate</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{patronEngagement.retention_rate.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Trends" icon={TrendingUp} />
                    <div className="space-y-4">
                      {patronEngagement.engagement_trend && (
                        <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Engagement Trend</span>
                            <span className={`font-medium ${
                              patronEngagement.engagement_trend.direction === 'up' ? 'text-status-success-600' :
                              patronEngagement.engagement_trend.direction === 'down' ? 'text-status-danger-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                            }`}>
                              {patronEngagement.engagement_trend.direction === 'up' ? '↑' : patronEngagement.engagement_trend.direction === 'down' ? '↓' : '→'} {patronEngagement.engagement_trend.change_percentage.toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                      {patronEngagement.new_patrons_trend && (
                        <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">New Patrons Trend</span>
                            <span className={`font-medium ${
                              patronEngagement.new_patrons_trend.direction === 'up' ? 'text-status-success-600' :
                              patronEngagement.new_patrons_trend.direction === 'down' ? 'text-status-danger-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                            }`}>
                              {patronEngagement.new_patrons_trend.direction === 'up' ? '↑' : patronEngagement.new_patrons_trend.direction === 'down' ? '↓' : '→'} {patronEngagement.new_patrons_trend.change_percentage.toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Reading Tab */}
            {activeTab === 'reading' && readingAnalytics && (
              <div className="space-y-6">
                <StatGrid columns={4}>
                  <StatCard title="Total Minutes" value={readingAnalytics.total_minutes_read.toLocaleString()} icon={Clock} color="accent" />
                  <StatCard title="Books Completed" value={readingAnalytics.total_books_completed} icon={BookOpen} color="success" />
                  <StatCard title="Total Participants" value={readingAnalytics.total_participants} icon={Users} color="warning" />
                  <StatCard title="Avg Min/Session" value={readingAnalytics.avg_minutes_per_session.toFixed(0)} icon={TrendingUp} color="category" />
                </StatGrid>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Reading Metrics" icon={BarChart3} />
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Pages Read</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{readingAnalytics.total_pages_read.toLocaleString()}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg Pages/Session</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{readingAnalytics.avg_pages_per_session.toFixed(1)}</span>
                      </div>
                      {readingAnalytics.avg_rating && (
                        <div className="flex items-center justify-between">
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg Rating</span>
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">{readingAnalytics.avg_rating.toFixed(1)} / 5</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Trends" icon={TrendingUp} />
                    <div className="space-y-4">
                      {readingAnalytics.minutes_trend && (
                        <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Minutes Trend</span>
                            <span className={`font-medium ${
                              readingAnalytics.minutes_trend.direction === 'up' ? 'text-status-success-600' :
                              readingAnalytics.minutes_trend.direction === 'down' ? 'text-status-danger-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                            }`}>
                              {readingAnalytics.minutes_trend.direction === 'up' ? '↑' : readingAnalytics.minutes_trend.direction === 'down' ? '↓' : '→'} {readingAnalytics.minutes_trend.change_percentage.toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                      {readingAnalytics.books_trend && (
                        <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Books Completed Trend</span>
                            <span className={`font-medium ${
                              readingAnalytics.books_trend.direction === 'up' ? 'text-status-success-600' :
                              readingAnalytics.books_trend.direction === 'down' ? 'text-status-danger-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                            }`}>
                              {readingAnalytics.books_trend.direction === 'up' ? '↑' : readingAnalytics.books_trend.direction === 'down' ? '↓' : '→'} {readingAnalytics.books_trend.change_percentage.toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Fines Tab */}
            {activeTab === 'fines' && fineAnalytics && (
              <div className="space-y-6">
                <StatGrid columns={4}>
                  <StatCard title="Outstanding" value={`$${fineAnalytics.outstanding_total.toFixed(2)}`} icon={DollarSign} color="danger" />
                  <StatCard title="Paid This Month" value={`$${fineAnalytics.paid_this_month.toFixed(2)}`} icon={DollarSign} color="success" />
                  <StatCard title="Waived This Month" value={`$${fineAnalytics.waived_this_month.toFixed(2)}`} icon={DollarSign} color="warning" />
                  <StatCard title="Patrons with Fines" value={fineAnalytics.patrons_with_fines} icon={Users} color="accent" />
                </StatGrid>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Collection Rate" icon={TrendingUp} />
                    <div className="flex items-center justify-center h-48">
                      <div className="text-center">
                        <div className="text-5xl font-bold text-lsc-rose">{(fineAnalytics.collection_rate * 100).toFixed(1)}%</div>
                        <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">of fines collected</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
                    <SectionHeader title="Outstanding Trend" icon={TrendingUp} />
                    <div className="space-y-4">
                      {fineAnalytics.outstanding_trend ? (
                        <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Outstanding Fines</span>
                            <span className={`font-medium ${
                              fineAnalytics.outstanding_trend.direction === 'down' ? 'text-status-success-600' :
                              fineAnalytics.outstanding_trend.direction === 'up' ? 'text-status-danger-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                            }`}>
                              {fineAnalytics.outstanding_trend.direction === 'up' ? '↑' : fineAnalytics.outstanding_trend.direction === 'down' ? '↓' : '→'} {fineAnalytics.outstanding_trend.change_percentage.toFixed(1)}%
                            </span>
                          </div>
                          <div className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            Previous: ${fineAnalytics.outstanding_trend.previous_value.toFixed(2)} → Current: ${fineAnalytics.outstanding_trend.current_value.toFixed(2)}
                          </div>
                        </div>
                      ) : (
                        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">{t('analyticsDashboard.noTrendDataAvailable')}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </PageContainer>
    </div>
  </AdminShell>
  )
}
