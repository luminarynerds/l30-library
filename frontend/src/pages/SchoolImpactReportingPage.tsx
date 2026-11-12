/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { useTranslation } from '../i18n/I18nContext'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import toast from 'react-hot-toast'
import { API_BASE } from '@/api/types'
import { fetchApi } from '@/api/fetchApi'
import { getAccessToken } from '../utils/tokenStore'
import { AdminShell } from '../components/shells/AdminShell'

function useDarkMode() {
  const [isDark, setIsDark] = useState(() =>
    typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  )
  useEffect(() => {
    const root = document.documentElement
    const observer = new MutationObserver(() => {
      setIsDark(root.classList.contains('dark'))
    })
    observer.observe(root, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])
  return isDark
}

interface SchoolImpactData {
  schoolId: string
  schoolName: string
  readingActivityAggregation: {
    totalMinutes: number
    totalBooks: number
    totalPages: number
    averageReadingMinutes: number
  }
  participationMetrics: {
    totalStudents: number
    activeStudents: number
    participationRate: number
  }
  readingGoals: {
    goalMinutes: number
    achievedMinutes: number
    goalAchievementPercentage: number
  }
  badgeEarnings: {
    totalBadgesEarned: number
    uniqueBadgesEarned: number
    badgesByType: { badgeName: string; count: number }[]
  }
  programMetrics: {
    activePrograms: number
    totalPrograms: number
    averageProgramParticipation: number
  }
  trendData?: Array<{
    month: string
    minutes: number
    books: number
    students: number
  }>
}

interface ComparisonMetrics {
  schools: Array<{
    schoolId: string
    schoolName: string
    readingMinutes: number
    booksRead: number
    studentParticipation: number
    badgesEarned: number
  }>
}

export default function SchoolImpactReportingPage() {
  const { t } = useTranslation()
  const isDark = useDarkMode()
  const [loading, setLoading] = useState(true)
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('')
  const [schools, setSchools] = useState<Array<{ id: string; name: string }>>([])
  const [impactData, setImpactData] = useState<SchoolImpactData | null>(null)
  const [comparisonData, setComparisonData] = useState<ComparisonMetrics | null>(null)
  const [view, setView] = useState<'detail' | 'comparison'>('detail')
  const [exportFormat, setExportFormat] = useState<'pdf' | 'csv'>('pdf')

  const fetchSchools = async () => {
    try {
      const data = await fetchApi('/school-partnerships/schools')
      const schools = Array.isArray(data) ? data : (data.schools || [])
      setSchools(schools)
      if (schools.length > 0) {
        setSelectedSchoolId(String(schools[0].id))
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('errors.failedToLoadSchools') || 'Failed to load schools')
    }
  }


  useEffect(() => {
    fetchSchools()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchImpactReport = async () => {
    if (!selectedSchoolId) return
    setLoading(true)
    try {
      const raw = await fetchApi(`/school-partnerships/reports/school-program-impact/${selectedSchoolId}`)
      // Map backend flat response to frontend SchoolImpactData shape
      const agg = raw.aggregate_metrics || {}
      const mapped: SchoolImpactData = {
        schoolId: String(raw.school_id),
        schoolName: raw.school_name || '',
        readingActivityAggregation: {
          totalMinutes: agg.total_minutes_read || 0,
          totalBooks: agg.total_books_read || 0,
          totalPages: 0,
          averageReadingMinutes: agg.average_minutes_per_student || 0,
        },
        participationMetrics: {
          totalStudents: agg.total_students || 0,
          activeStudents: agg.total_students || 0,
          participationRate: agg.total_students > 0 ? 100 : 0,
        },
        readingGoals: {
          goalMinutes: 0,
          achievedMinutes: agg.total_minutes_read || 0,
          goalAchievementPercentage: 0,
        },
        badgeEarnings: {
          totalBadgesEarned: 0,
          uniqueBadgesEarned: 0,
          badgesByType: [],
        },
        programMetrics: {
          activePrograms: (raw.programs || []).length,
          totalPrograms: (raw.programs || []).length,
          averageProgramParticipation: 0,
        },
      }
      setImpactData(mapped)
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('errors.failedToLoadReport') || 'Failed to load report')
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (selectedSchoolId) {
      fetchImpactReport()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSchoolId])

  const fetchComparisonReport = async () => {
    setLoading(true)
    try {
      const data = await fetchApi('/school-partnerships/reports/school-comparison')
      // Backend returns snake_case rows ({school_name, total_minutes,
      // total_books, ...}); the chart dataKeys are camelCase. Map before
      // storing, mirroring the detail-view mapping above.
      const rows = Array.isArray(data?.schools) ? data.schools : []
      setComparisonData({
        ...data,
        schools: rows.map((s: {
          school_id?: number
          school_name?: string
          total_minutes?: number
          total_books?: number
          student_registrations?: number
        }) => ({
          schoolId: String(s.school_id ?? ''),
          schoolName: s.school_name ?? '',
          readingMinutes: s.total_minutes ?? 0,
          booksRead: s.total_books ?? 0,
          studentParticipation: s.student_registrations ?? 0,
          badgesEarned: 0,
        })),
      })
      setView('comparison')
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('errors.failedToLoadComparison') || 'Failed to load comparison')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    if (!selectedSchoolId) return
    try {
      // Edge case: binary/file download — keep raw fetch with manual Authorization header.
      const token = getAccessToken()
      const endpoint = `${API_BASE}/school-partnerships/reports/school-program-impact/${selectedSchoolId}/export?format=${exportFormat}`
      // eslint-disable-next-line no-restricted-syntax -- School-impact CSV/PDF blob export
      const response = await fetch(endpoint, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `school-impact-report-${selectedSchoolId}.${exportFormat}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        toast.success(t('success.reportExported') || 'Report exported successfully')
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('errors.failedToExport') || 'Failed to export report')
    }
  }

  if (view === 'comparison') {
    return (
      <AdminShell title="School Comparison Report">
        <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
          <div className="max-w-6xl mx-auto">
            <button
              onClick={() => setView('detail')}
              className="mb-6 px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 transition"
            >
              Back to Detail View
            </button>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
              {loading ? (
                <div className="text-center py-12">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading comparison data...</p>
                </div>
              ) : comparisonData ? (
                <div>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={comparisonData.schools}>
                      <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3D3B38' : '#ECEAE8'} />
                      <XAxis dataKey="schoolName" tick={{ fill: isDark ? '#D5D3D0' : '#5D5B57' }} />
                      <YAxis tick={{ fill: isDark ? '#D5D3D0' : '#5D5B57' }} />
                      <Tooltip contentStyle={{ backgroundColor: isDark ? '#2F2E2C' : '#FFFFFF', border: `1px solid ${isDark ? '#3D3B38' : '#ECEAE8'}`, color: isDark ? '#D5D3D0' : '#2D2D2A' }} />
                      <Legend wrapperStyle={{ color: isDark ? '#D5D3D0' : '#5D5B57' }} />
                      <Bar dataKey="readingMinutes" fill="#8B7355" name="Reading Minutes" />
                      <Bar dataKey="booksRead" fill="#D4A574" name="Books Read" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </AdminShell>
    )
  }

  return (

    <AdminShell title="School Comparison Report">    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            School Impact Reporting
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Track and analyze the impact of reading programs across schools
          </p>
        </div>

        {/* Controls */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Select School
              </label>
              <select
                value={selectedSchoolId}
                onChange={(e) => setSelectedSchoolId(e.target.value)}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
              >
                <option value="">-- Choose a school --</option>
                {schools.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Export Format
              </label>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as 'pdf' | 'csv')}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
              >
                <option value="pdf">PDF</option>
                <option value="csv">CSV</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleExport}
                disabled={!selectedSchoolId}
                className="w-full px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 disabled:bg-earth-400 transition"
              >
                Export Report
              </button>
            </div>

            <div className="flex items-end">
              <button
                onClick={fetchComparisonReport}
                className="w-full px-4 py-2 bg-earth-500 text-white rounded-lg hover:bg-earth-600 transition"
              >
                Compare Schools
              </button>
            </div>
          </div>
        </div>

        {/* Impact Report */}
        {loading ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 text-center">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading report...</p>
          </div>
        ) : impactData ? (
          <div className="space-y-8">
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
                <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Total Reading Minutes
                </h3>
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {impactData.readingActivityAggregation.totalMinutes.toLocaleString()}
                </p>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
                <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Books Read
                </h3>
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {impactData.readingActivityAggregation.totalBooks}
                </p>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
                <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Active Students
                </h3>
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {impactData.participationMetrics.activeStudents}
                </p>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
                <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Badges Earned
                </h3>
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {impactData.badgeEarnings.totalBadgesEarned}
                </p>
              </div>
            </div>

            {/* Reading Goals Progress */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
                Reading Goals Achievement
              </h2>
              <div className="mb-4">
                <div className="flex justify-between mb-2">
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {impactData.readingGoals.achievedMinutes} / {impactData.readingGoals.goalMinutes} minutes
                  </span>
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">
                    {impactData.readingGoals.goalAchievementPercentage.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-earth-600 dark:bg-earth-400 h-full transition-all duration-500"
                    style={{
                      width: `${Math.min(impactData.readingGoals.goalAchievementPercentage, 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Participation Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
                  Participation Metrics
                </h2>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Students</span>
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {impactData.participationMetrics.totalStudents}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Active Students</span>
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {impactData.participationMetrics.activeStudents}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Participation Rate</span>
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {impactData.participationMetrics.participationRate.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
                  Program Metrics
                </h2>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Active Programs</span>
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {impactData.programMetrics.activePrograms}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Programs</span>
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {impactData.programMetrics.totalPrograms}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Avg. Participation</span>
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {impactData.programMetrics.averageProgramParticipation.toFixed(0)} students
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Badge Earnings */}
            {impactData.badgeEarnings.badgesByType.length > 0 && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
                  Badge Earnings by Type
                </h2>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={impactData.badgeEarnings.badgesByType}
                      dataKey="count"
                      nameKey="badgeName"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                    >
                      {impactData.badgeEarnings.badgesByType.map((_, index) => {
                        const colors = ['#8B7355', '#D4A574', '#A0826D', '#6F5C47']
                        return <Cell key={`cell-${index}`} fill={colors[index % 4]!} />
                      })}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: isDark ? '#2F2E2C' : '#FFFFFF', border: `1px solid ${isDark ? '#3D3B38' : '#ECEAE8'}`, color: isDark ? '#D5D3D0' : '#2D2D2A' }} />
                    <Legend wrapperStyle={{ color: isDark ? '#D5D3D0' : '#5D5B57' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Trend Data */}
            {impactData.trendData && impactData.trendData.length > 0 && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
                  Reading Trends Over Time
                </h2>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={impactData.trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3D3B38' : '#ECEAE8'} />
                    <XAxis dataKey="month" tick={{ fill: isDark ? '#D5D3D0' : '#5D5B57' }} />
                    <YAxis tick={{ fill: isDark ? '#D5D3D0' : '#5D5B57' }} />
                    <Tooltip contentStyle={{ backgroundColor: isDark ? '#2F2E2C' : '#FFFFFF', border: `1px solid ${isDark ? '#3D3B38' : '#ECEAE8'}`, color: isDark ? '#D5D3D0' : '#2D2D2A' }} />
                    <Legend wrapperStyle={{ color: isDark ? '#D5D3D0' : '#5D5B57' }} />
                    <Line type="monotone" dataKey="minutes" stroke="#8B7355" name="Reading Minutes" />
                    <Line type="monotone" dataKey="books" stroke="#D4A574" name="Books Read" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  </AdminShell>
  )
}