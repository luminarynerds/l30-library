/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'
import { useTranslation} from '@/i18n'
import { useAuth } from '../contexts/AuthContext'
import {
  getCollectionDevelopmentReport,
  CollectionDevelopmentReport,
  formatServiceName,
  formatContentType,
  type StreamingService,
  type StreamingContentType,
} from '../api/streaming-api'
import {
  FileText,
  TrendingUp,
  DollarSign,
  Users,
  Film,
  Headphones,
  BookOpen,
  Download,
  Loader2,
  BarChart3,
  PieChart,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells/AdminShell'
import PageContainer from '@/components/layout/PageContainer'

export default function StreamingReportsPage() {
  const { t } = useTranslation()
  const { token, user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [report, setReport] = useState<CollectionDevelopmentReport | null>(null)
  const [startDate, setStartDate] = useState(() => {
    const date = new Date()
    date.setMonth(date.getMonth() - 3)
    return date.toISOString().split('T')[0] ?? ''
  })
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split('T')[0] ?? ''
  })

  const fetchReport = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const data = await getCollectionDevelopmentReport(token, startDate, endDate)
      setReport(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(error instanceof Error ? error.message : t('toast.streamingReports.failedToLoadReport'))
    } finally {
      setLoading(false)
    }
  }, [token, startDate, endDate, t])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  const handleExport = () => {
    if (!report) return

    const csvContent = generateCSV(report)
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `streaming-report-${startDate}-to-${endDate}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    toast.success(t('toast.lostDamagedReports.reportExportedSuccessfully'))
  }

  if (!user || !['staff', 'admin', 'super_admin'].includes(user.role)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('streamingReports.youDonTHavePermission')}</p>
      </div>
    )
  }

  return (
    <AdminShell title="Collection Development Report">
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b">
        <PageContainer width="wide" className="py-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div></div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">From:</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm dark:bg-earth-800 dark:text-earth-100 dark:border-earth-600"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">To:</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm dark:bg-earth-800 dark:text-earth-100 dark:border-earth-600"
                />
              </div>
              <button
                onClick={fetchReport}
                disabled={loading}
                className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose-dark disabled:opacity-50 flex items-center gap-2"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
                Generate
              </button>
              {report && (
                <button
                  onClick={handleExport}
                  className="px-4 py-2 border rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 flex items-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Export CSV
                </button>
              )}
            </div>
          </div>
        </PageContainer>
      </div>

      {/* Content */}
      <PageContainer width="wide" className="py-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : report ? (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <SummaryCard
                icon={DollarSign}
                label="Total Cost"
                value={`$${parseFloat(report.total_cost).toLocaleString()}`}
                color="success"
              />
              <SummaryCard
                icon={Users}
                label="Unique Patrons"
                value={report.total_unique_patrons.toLocaleString()}
                color="accent"
              />
              <SummaryCard
                icon={TrendingUp}
                label="Repeat User Rate"
                value={`${(report.repeat_user_rate * 100).toFixed(1)}%`}
                color="category"
              />
              <SummaryCard
                icon={BarChart3}
                label="Report Period"
                value={`${daysBetween(startDate, endDate)} days`}
                color="warning"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Most Watched Titles */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <Film className="w-5 h-5 text-status-info-600" />
                  Most Watched Titles
                </h3>
                <div className="space-y-3">
                  {report.most_watched_titles.slice(0, 10).map((title, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-2 border-b last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 w-6">#{index + 1}</span>
                        <div>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">{title.title}</p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {title.service && formatServiceName(title.service as StreamingService)} •{' '}
                            {title.content_type && formatContentType(title.content_type as StreamingContentType)}
                          </p>
                        </div>
                      </div>
                      <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{title.checkouts}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cost by Service */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-status-success-600" />
                  Cost Analysis by Service
                </h3>
                <div className="space-y-4">
                  {Object.entries(report.cost_by_service).map(([service, cost]) => {
                    const percentage =
                      parseFloat(report.total_cost) > 0
                        ? (cost / parseFloat(report.total_cost)) * 100
                        : 0
                    const costPerCheckout = report.cost_per_checkout_by_service[service] || 0

                    return (
                      <div key={service} className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {formatServiceName(service as StreamingService)}
                          </span>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">${cost.toLocaleString()}</span>
                        </div>
                        <div className="h-2 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              service === 'palace' ? 'bg-status-success-500' : 'bg-status-info-500'
                            }`}
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <span>{percentage.toFixed(1)}% of total</span>
                          <span>${costPerCheckout.toFixed(2)} per checkout</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Most Watched Genres */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <Headphones className="w-5 h-5 text-category-600" />
                  Popular Genres
                </h3>
                <div className="space-y-3">
                  {report.most_watched_genres.slice(0, 8).map((genre, index) => {
                    const maxCheckouts = report.most_watched_genres[0]?.checkouts || 1
                    const percentage = (genre.checkouts / maxCheckouts) * 100

                    return (
                      <div key={index} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">{genre.genre}</span>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{genre.checkouts}</span>
                        </div>
                        <div className="h-2 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-category-500 rounded-full"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Content Type Breakdown */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-status-warning-600" />
                  Content Type Distribution
                </h3>
                <div className="space-y-4">
                  {report.most_active_content_types.map((type) => {
                    const totalCheckouts = report.most_active_content_types.reduce(
                      (sum, t) => sum + t.checkouts,
                      0
                    )
                    const percentage =
                      totalCheckouts > 0 ? (type.checkouts / totalCheckouts) * 100 : 0
                    const cost = report.cost_by_content_type[type.content_type] || 0

                    return (
                      <div key={type.content_type} className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {formatContentType(type.content_type as StreamingContentType)}
                          </span>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{type.checkouts} checkouts</span>
                        </div>
                        <div className="h-2 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-status-warning-500 rounded-full"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <span>{percentage.toFixed(1)}%</span>
                          <span>${cost.toFixed(2)} total</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Patron Engagement */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-status-info-600" />
                Patron Engagement by Service
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Object.entries(report.patron_engagement_by_service).map(([service, patrons]) => (
                  <div
                    key={service}
                    className="bg-earth-50 dark:bg-earth-900 rounded-lg p-4 flex items-center justify-between"
                  >
                    <div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {formatServiceName(service as StreamingService)}
                      </p>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{patrons}</p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">unique patrons</p>
                    </div>
                    <div
                      className={`w-16 h-16 rounded-full flex items-center justify-center ${
                        service === 'palace' ? 'bg-status-success-100 dark:bg-status-success-900/30' : 'bg-status-info-100 dark:bg-status-info-900/30'
                      }`}
                    >
                      <Users
                        className={`w-8 h-8 ${
                          service === 'palace' ? 'text-status-success-600' : 'text-status-info-600'
                        }`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Insights */}
            <div className="bg-status-info-50 dark:bg-status-info-900/20 rounded-lg p-6">
              <h3 className="font-serif font-semibold text-status-info-900 dark:text-status-info-200 mb-4">Collection Development Insights</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-status-info-800 dark:text-status-info-300">
                <div className="flex items-start gap-2">
                  <TrendingUp className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium">Top Performing Content</p>
                    <p>
                      {report.most_active_content_types[0]?.content_type
                        ? formatContentType(report.most_active_content_types[0].content_type as StreamingContentType)
                        : 'N/A'}{' '}
                      content is your most popular category with{' '}
                      {report.most_active_content_types[0]?.checkouts || 0} checkouts.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <DollarSign className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium">Cost Efficiency</p>
                    <p>
                      Average cost per checkout is $
                      {(
                        parseFloat(report.total_cost) /
                        report.most_active_content_types.reduce((sum, t) => sum + t.checkouts, 0) ||
                        1
                      ).toFixed(2)}
                      . Consider this when budgeting for next period.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Users className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium">User Retention</p>
                    <p>
                      {(report.repeat_user_rate * 100).toFixed(1)}% of patrons are repeat users,
                      indicating{' '}
                      {report.repeat_user_rate > 0.5 ? 'strong' : 'room for improvement in'} service
                      engagement.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <BarChart3 className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium">Genre Focus</p>
                    <p>
                      Consider expanding {report.most_watched_genres[0]?.genre || 'popular'} content
                      as it's your most requested genre.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-8 text-center">
            <FileText className="w-12 h-12 mx-auto mb-4 text-earth-300" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('streamingReports.noDataAvailableForThe')}</p>
          </div>
        )}
      </PageContainer>
    </div>
    </AdminShell>
  )
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string
  color: 'accent' | 'success' | 'category' | 'warning'
}) {
  const colors = {
    accent: 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-600',
    success: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-600',
    category: 'bg-category-100 dark:bg-category-900/30 text-category-600',
    warning: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-600',
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
        </div>
      </div>
    </div>
  )
}

function daysBetween(start: string, end: string): number {
  const startDate = new Date(start)
  const endDate = new Date(end)
  const diffTime = Math.abs(endDate.getTime() - startDate.getTime())
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
}

function generateCSV(report: CollectionDevelopmentReport): string {
  const lines: string[] = []

  // Header
  lines.push('Collection Development Report')
  lines.push(
    `Period: ${new Date(report.report_period_start).toLocaleDateString()} - ${new Date(report.report_period_end).toLocaleDateString()}`
  )
  lines.push('')

  // Summary
  lines.push('Summary')
  lines.push(`Total Cost,$${parseFloat(report.total_cost).toFixed(2)}`)
  lines.push(`Unique Patrons,${report.total_unique_patrons}`)
  lines.push(`Repeat User Rate,${(report.repeat_user_rate * 100).toFixed(1)}%`)
  lines.push('')

  // Most Watched Titles
  lines.push('Most Watched Titles')
  lines.push('Rank,Title,Service,Content Type,Checkouts')
  report.most_watched_titles.forEach((title, index) => {
    lines.push(
      `${index + 1},"${title.title}",${title.service || ''},${title.content_type || ''},${title.checkouts}`
    )
  })
  lines.push('')

  // Cost by Service
  lines.push('Cost by Service')
  lines.push('Service,Cost,Cost per Checkout')
  Object.entries(report.cost_by_service).forEach(([service, cost]) => {
    const cpc = report.cost_per_checkout_by_service[service] || 0
    lines.push(`${service},$${cost.toFixed(2)},$${cpc.toFixed(2)}`)
  })
  lines.push('')

  // Content Types
  lines.push('Content Types')
  lines.push('Content Type,Checkouts,Cost')
  report.most_active_content_types.forEach((type) => {
    const cost = report.cost_by_content_type[type.content_type] || 0
    lines.push(`${type.content_type},${type.checkouts},$${cost.toFixed(2)}`)
  })

  return lines.join('\n')
}
