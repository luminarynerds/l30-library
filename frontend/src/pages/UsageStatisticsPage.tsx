/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React from 'react'
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Loader2, RefreshCw, Download, Calendar, TrendingUp, Users, BookOpen,
  Monitor, HelpCircle, DoorOpen, Package, BarChart3, FileSpreadsheet,
  FileText, Activity
} from "lucide-react"
import toast from "react-hot-toast"
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from "recharts"
import {
  fetchDashboard,
  fetchMonthOverMonthTrends,
  exportStatistics,
  generateIMLSSurvey,
  fetchReports,
  downloadReport,
  type UsageStatisticsDashboard,
  type MonthOverMonthTrend,
  type StatisticalReport,
  type PeriodType,
  type ExportFormat
} from "../api/usage-statistics-api"
import { useUsageStatisticsColors, useChartTooltipStyle } from "../hooks/useChartColors"
import { useTranslation} from '@/i18n'

export default function UsageStatisticsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isLoading: authLoading, isAuthenticated } = useAuth()
  const [isLoading, setIsLoading] = useState(true)
  const statsColors = useUsageStatisticsColors()
  const tooltipStyle = useChartTooltipStyle()
  const [dashboard, setDashboard] = useState<UsageStatisticsDashboard | null>(null)
  const [trends, setTrends] = useState<MonthOverMonthTrend[]>([])
  const [reports, setReports] = useState<StatisticalReport[]>([])
  const [selectedMetric, setSelectedMetric] = useState("checkouts")

  // Filters
  const [periodStart, setPeriodStart] = useState(() => {
    const date = new Date()
    date.setMonth(date.getMonth() - 1)
    return date.toISOString().split("T")[0] ?? ''
  })
  const [periodEnd, setPeriodEnd] = useState(() => new Date().toISOString().split("T")[0] ?? '')
  const [periodType, setPeriodType] = useState<PeriodType>("monthly")
  const [branchLocation, setBranchLocation] = useState<string>("")

  const [isExporting, setIsExporting] = useState(false)
  const [isGeneratingIMLS, setIsGeneratingIMLS] = useState(false)

  const fetchData = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const [dashboardData, trendsData, reportsData] = await Promise.all([
        fetchDashboard(periodStart, periodEnd, periodType, branchLocation || undefined),
        fetchMonthOverMonthTrends(selectedMetric, 12, branchLocation || undefined),
        fetchReports(undefined, undefined, 10)
      ])
      setDashboard(dashboardData)
      setTrends(trendsData)
      setReports(reportsData)
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      toast.error(t('usageStatistics.failedToLoadUsageStatistics'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, periodStart, periodEnd, periodType, branchLocation, selectedMetric])

  useEffect(() => {
    if (isAuthenticated && token) fetchData()
  }, [isAuthenticated, token, fetchData])

  const handleExport = async (format: ExportFormat) => {
    setIsExporting(true)
    try {
      const report = await exportStatistics(format, periodStart, periodEnd, format === "pdf")
      toast.success(t('toast.usageStatistics.exportStartedReportIdId', { id: report.id }))
      setTimeout(() => fetchData(), 2000) // Refresh reports list
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      toast.error(t('usageStatistics.failedToExportStatistics'))
    } finally {
      setIsExporting(false)
    }
  }

  const handleGenerateIMLS = async () => {
    setIsGeneratingIMLS(true)
    try {
      const currentYear = new Date().getFullYear()
      const report = await generateIMLSSurvey(currentYear, branchLocation || undefined)
      toast.success(t('toast.usageStatistics.imlsSurveyGeneratedReportId', { id: report.id }))
      setTimeout(() => fetchData(), 2000)
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      toast.error(t('usageStatistics.failedToGenerateImlsSurvey'))
    } finally {
      setIsGeneratingIMLS(false)
    }
  }

  const handleDownloadReport = async (reportId: number) => {
    try {
      await downloadReport(reportId)
      toast.success(t('toast.usageStatistics.reportDownloadedSuccessfully'))
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      toast.error(t('usageStatistics.failedToDownloadReport'))
    }
  }

  const formatNumber = (num: number) => num.toLocaleString()

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!isAuthenticated) return <></>

  return (
    <AdminShell title="Usage Statistics">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Usage Statistics
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                IMLS/PLA Reporting and Analytics
              </p>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* Filters */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4">
            <div className="grid md:grid-cols-4 gap-4">
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  <Calendar className="w-4 h-4 text-lsc-rose" />
                  Start Date
                </label>
                <input
                  type="date"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  <Calendar className="w-4 h-4 text-lsc-rose" />
                  End Date
                </label>
                <input
                  type="date"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2 block">
                  Period Type
                </label>
                <select
                  value={periodType}
                  onChange={(e) => setPeriodType(e.target.value as PeriodType)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2 block">
                  Branch
                </label>
                <input
                  type="text"
                  placeholder={t('placeholder.unifiedReports.allBranches')}
                  value={branchLocation}
                  onChange={(e) => setBranchLocation(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
          </div>

          {/* Export Actions */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4">
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => handleExport("csv")}
                disabled={isExporting}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                <FileSpreadsheet className="w-4 h-4" />
                Export CSV
              </button>
              <button
                onClick={() => handleExport("xlsx")}
                disabled={isExporting}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                <FileSpreadsheet className="w-4 h-4" />
                Export Excel
              </button>
              <button
                onClick={() => handleExport("pdf")}
                disabled={isExporting}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                <FileText className="w-4 h-4" />
                Export PDF
              </button>
              <button
                onClick={handleGenerateIMLS}
                disabled={isGeneratingIMLS}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-dark text-lsc-cream rounded-lg hover:bg-lsc-dark/90 transition-colors disabled:opacity-50 ml-auto"
              >
                <Download className="w-4 h-4" />
                Generate IMLS Survey
              </button>
            </div>
          </div>

          {dashboard && (
            <>
              {/* Overview Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  icon={BookOpen}
                  title="Total Checkouts"
                  value={formatNumber(dashboard.circulation.total_checkouts)}
                  color="text-lsc-rose"
                />
                <StatCard
                  icon={Users}
                  title="Registered Patrons"
                  value={formatNumber(dashboard.patron.total_registered)}
                  color="text-lsc-rose dark:text-lsc-rose-light"
                />
                <StatCard
                  icon={Activity}
                  title="Total Programs"
                  value={formatNumber(dashboard.program.total_programs)}
                  color="text-status-success-600"
                />
                <StatCard
                  icon={DoorOpen}
                  title="Library Visits"
                  value={formatNumber(dashboard.visits.total_visits)}
                  color="text-category-600"
                />
              </div>

              {/* Circulation Statistics */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                  <BookOpen className="w-5 h-5 text-lsc-rose" />
                  Circulation Statistics
                </h2>
                <div className="grid md:grid-cols-3 gap-4">
                  <MetricBox label="Total Checkouts" value={formatNumber(dashboard.circulation.total_checkouts)} />
                  <MetricBox label="Total Renewals" value={formatNumber(dashboard.circulation.total_renewals)} />
                  <MetricBox label="Total Returns" value={formatNumber(dashboard.circulation.total_returns)} />
                  <MetricBox label="Physical Checkouts" value={formatNumber(dashboard.circulation.physical_checkouts)} />
                  <MetricBox label="Digital Checkouts" value={formatNumber(dashboard.circulation.digital_checkouts)} />
                  <MetricBox label="Unique Borrowers" value={formatNumber(dashboard.circulation.unique_borrowers)} />
                </div>
              </div>

              {/* Collection Statistics */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                  <Package className="w-5 h-5 text-lsc-rose" />
                  Collection Statistics
                </h2>
                <div className="grid md:grid-cols-3 gap-4">
                  <MetricBox label="Total Physical Items" value={formatNumber(dashboard.collection.total_physical_items)} />
                  <MetricBox label="Total Digital Items" value={formatNumber(dashboard.collection.total_digital_items)} />
                  <MetricBox label="Total Titles" value={formatNumber(dashboard.collection.total_titles)} />
                  <MetricBox label="Physical Titles" value={formatNumber(dashboard.collection.physical_titles)} />
                  <MetricBox label="Digital Titles" value={formatNumber(dashboard.collection.digital_titles)} />
                </div>
              </div>

              {/* Patron Statistics */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                  <Users className="w-5 h-5 text-lsc-rose" />
                  Patron Statistics
                </h2>
                <div className="grid md:grid-cols-3 gap-4">
                  <MetricBox label="Total Registered" value={formatNumber(dashboard.patron.total_registered)} />
                  <MetricBox label="New Registrations" value={formatNumber(dashboard.patron.new_registrations)} />
                  <MetricBox label="Active Borrowers" value={formatNumber(dashboard.patron.active_borrowers)} />
                  <MetricBox label="Renewed Cards" value={formatNumber(dashboard.patron.renewed_cards)} />
                  <MetricBox label="Expired Cards" value={formatNumber(dashboard.patron.expired_cards)} />
                </div>
              </div>

              {/* Program Statistics */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                  <Activity className="w-5 h-5 text-lsc-rose" />
                  Program Statistics
                </h2>
                <div className="grid md:grid-cols-3 gap-4">
                  <MetricBox label="Total Programs" value={formatNumber(dashboard.program.total_programs)} />
                  <MetricBox label="Total Sessions" value={formatNumber(dashboard.program.total_sessions)} />
                  <MetricBox label="Total Attendance" value={formatNumber(dashboard.program.total_attendance)} />
                  <MetricBox label="Unique Attendees" value={formatNumber(dashboard.program.unique_attendees)} />
                  <MetricBox label="Avg Attendance/Session" value={dashboard.program.avg_attendance_per_session.toFixed(1)} />
                </div>
              </div>

              {/* Computer & Technology Usage */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                  <Monitor className="w-5 h-5 text-lsc-rose" />
                  Computer & Technology Usage
                </h2>
                <div className="grid md:grid-cols-4 gap-4">
                  <MetricBox label="Total Sessions" value={formatNumber(dashboard.computer.total_sessions)} />
                  <MetricBox label="Unique Users" value={formatNumber(dashboard.computer.unique_users)} />
                  <MetricBox label="Total Hours Used" value={formatNumber(dashboard.computer.total_hours_used)} />
                  <MetricBox label="Avg Session (min)" value={dashboard.computer.avg_session_length_minutes.toFixed(0)} />
                  <MetricBox label="WiFi Sessions" value={formatNumber(dashboard.computer.wifi_sessions)} />
                  <MetricBox label="WiFi Devices" value={formatNumber(dashboard.computer.wifi_unique_devices)} />
                  <MetricBox label="Print Jobs" value={formatNumber(dashboard.computer.print_jobs)} />
                  <MetricBox label="Pages Printed" value={formatNumber(dashboard.computer.pages_printed)} />
                </div>
              </div>

              {/* Reference & Visits */}
              <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                    <HelpCircle className="w-5 h-5 text-lsc-rose" />
                    Reference Statistics
                  </h2>
                  <div className="space-y-3">
                    <MetricBox label="Total Questions" value={formatNumber(dashboard.reference.total_questions)} />
                    <MetricBox label="Avg Duration (min)" value={dashboard.reference.avg_duration_minutes.toFixed(1)} />
                  </div>
                </div>

                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                    <DoorOpen className="w-5 h-5 text-lsc-rose" />
                    Visit Statistics
                  </h2>
                  <div className="space-y-3">
                    <MetricBox label="Total Visits" value={formatNumber(dashboard.visits.total_visits)} />
                    <MetricBox label="Avg Visits/Day" value={dashboard.visits.avg_visits_per_day.toFixed(1)} />
                    <MetricBox label="Peak Day Visits" value={formatNumber(dashboard.visits.peak_day_visits)} />
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Trends Chart */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-lsc-rose" />
                Month-over-Month Trends
              </h2>
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                aria-label={t('aria.usageStatistics.selectTrendMetric')}
                className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="checkouts">Checkouts</option>
                <option value="visits">Visits</option>
                <option value="registrations">Registrations</option>
                <option value="programs">Programs</option>
                <option value="attendance">Attendance</option>
                <option value="reference">Reference</option>
              </select>
            </div>
            {trends.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke={statsColors.grid} />
                  <XAxis dataKey="period" stroke={statsColors.axis} />
                  <YAxis stroke={statsColors.axis} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Line type="monotone" dataKey="value" stroke={statsColors.primary} strokeWidth={2} name="Value" />
                  <Line type="monotone" dataKey="change_from_previous" stroke={statsColors.secondary} strokeWidth={2} name="Change" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-lsc-dark/70 dark:text-lsc-cream/70">
                No trend data available
              </div>
            )}
          </div>

          {/* Recent Reports */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
              <BarChart3 className="w-5 h-5 text-lsc-rose" />
              Recent Reports
            </h2>
            {reports.length > 0 ? (
              <div className="space-y-2">
                {reports.map((report) => (
                  <div key={report.id} className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                    <div className="flex-1">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{report.report_name}</p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {report.report_type} • {report.file_format.toUpperCase()} • {report.status}
                      </p>
                    </div>
                    {report.status === "COMPLETED" && (
                      <button
                        onClick={() => handleDownloadReport(report.id)}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-rose hover:bg-lsc-rose/10 rounded-lg transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        Download
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">No reports available</p>
            )}
          </div>
    </AdminShell>
  )
}

function StatCard({ icon: Icon, title, value, color }: { icon: React.ComponentType<React.SVGProps<SVGSVGElement>>; title: string; value: string; color: string }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{title}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
        </div>
      </div>
    </div>
  )
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
      <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{value}</p>
    </div>
  )
}
