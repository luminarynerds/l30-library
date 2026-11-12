/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useId } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  Users,
  TrendingUp,
  AlertCircle,
  Download,
  ArrowRight,
  Award,
  Calendar,
  Zap,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'
import { fetchApi } from '@/api/fetchApi'
import PageContainer from '@/components/layout/PageContainer'

interface SchoolBadge {
  id: number
  badge_name: string
  badge_description?: string
  badge_icon_url?: string
  threshold_type: string
  threshold_value: number
  is_active: boolean
  created_at: string
}

interface DashboardData {
  school_id: number
  school_name: string
  active_programs_count: number
  student_registration_count: number
  total_reading_activity: number
  total_minutes_read: number
  total_books_read: number
  school_badges: SchoolBadge[]
  recent_activity_count: number
}

interface ReadingProgram {
  id: number
  name: string
  description?: string
  program_type: string
  curriculum_alignment?: string
  grade_levels: string[]
  reading_levels: string[]
  start_date: string
  end_date: string
  is_active: boolean
}

interface SchoolListEntry {
  id: number
  name: string
}

export default function TeacherReadingDashboardPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const schoolPickerId = useId()
  const isTeacher = user?.role === 'teacher'
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'active' | 'completed'>('all')

  // Staff/admin pick a school; teachers are pinned to their own user.school_id.
  // URL-synced (?school_id=N) so the choice is shareable + survives reloads.
  const [searchParams, setSearchParams] = useSearchParams()
  const urlSchoolIdRaw = searchParams.get('school_id')
  const urlSchoolId =
    urlSchoolIdRaw && /^\d+$/.test(urlSchoolIdRaw) ? Number(urlSchoolIdRaw) : null

  // Fetch the list of schools the user can see. Backend scopes this list
  // (teachers see only their own school; staff/admin see all active partners),
  // so we only need to render the picker for non-teachers.
  const {
    data: schools = [],
    isLoading: schoolsLoading,
  } = useQuery<SchoolListEntry[], Error>({
    queryKey: ['school-partnerships-schools'],
    queryFn: async () => {
      const data = await fetchApi('/school-partnerships/schools')
      // Endpoint can return a bare list OR { schools: [...] }; tolerate both.
      const list = Array.isArray(data)
        ? data
        : ((data as { schools?: SchoolListEntry[] })?.schools ?? [])
      return list as SchoolListEntry[]
    },
    enabled: !!token && !isTeacher,
  })

  // Teachers: pinned to their user.school_id (no picker, no fallback).
  // Staff/admin: ?school_id= -> first school in the list -> null (no fallback to 1).
  const effectiveSchoolId: number | null =
    isTeacher && typeof user?.school_id === 'number'
      ? user.school_id
      : (urlSchoolId ?? schools[0]?.id ?? null)
  const defaultSchoolId = effectiveSchoolId

  const handlePickSchool = (newId: number) => {
    // Preserve any other params already on the URL.
    const next = new URLSearchParams(searchParams)
    next.set('school_id', String(newId))
    setSearchParams(next, { replace: false })
  }

  // All hooks run unconditionally so hook count is stable across renders
  // (rule-of-hooks). The auth gate moved below; the `enabled: !!token`
  // guards keep the queries from firing without a session.
  const {
    data: dashboardData,
    isLoading: dashboardLoading,
    error: dashboardError,
  } = useQuery<DashboardData, Error>({
    queryKey: ['teacher-dashboard', defaultSchoolId],
    queryFn: async () => {
      // fetchApi throws { status, message } on non-ok; 403 surfaces below as
      // a friendly notice rather than an opaque error.
      return (await fetchApi(
        `/school-partnerships/teacher-dashboard/${defaultSchoolId}`,
      )) as DashboardData
    },
    enabled: !!token && !!defaultSchoolId,
    retry: (failureCount, err) => {
      // Don't retry 403s; the school mismatch isn't going to fix itself.
      const status = (err as Error & { status?: number }).status
      return status === 403 ? false : failureCount < 3
    },
  })

  // Fetch school reading programs
  const {
    data: programs = [],
    isLoading: programsLoading,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    error: _programsError,
  } = useQuery({
    queryKey: ['school-programs', defaultSchoolId],
    queryFn: async () => {
      return (await fetchApi(
        `/school-partnerships/schools/${defaultSchoolId}/programs`,
      )) as ReadingProgram[]
    },
    enabled: !!token && !!defaultSchoolId,
  })

  // Fetch school badges
  const {
    data: badges = [],
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    isLoading: _badgesLoading,
  } = useQuery({
    queryKey: ['school-badges', defaultSchoolId],
    queryFn: async () => {
      return (await fetchApi(
        `/school-partnerships/schools/${defaultSchoolId}/badges`,
      )) as SchoolBadge[]
    },
    enabled: !!token && !!defaultSchoolId,
  })

  // Auth gate runs after all hooks (rule-of-hooks).
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <AlertCircle className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" aria-hidden="true" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Authentication Required</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('teacherReadingDashboard.pleaseLogInToAccess')}</p>
        </PageContainer>
      </div>
    )
  }

  // Friendly 403: teacher viewing a school they're not registered with.
  if (dashboardError && (dashboardError as Error & { status?: number }).status === 403) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <AlertCircle className="w-12 h-12 text-lsc-rose mx-auto mb-4" aria-hidden="true" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Dashboard not available
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
            This dashboard is for a school you&apos;re not registered as a teacher at.
            Contact the library if this looks wrong.
          </p>
        </PageContainer>
      </div>
    )
  }

  // Staff/admin: no school selected yet. Either the schools query is in
  // flight, or it resolved to an empty list (no partner schools onboarded).
  if (!isTeacher && !defaultSchoolId) {
    if (schoolsLoading) {
      return (
        <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
          <PageContainer className="text-center">
            <div className="inline-block">
              <div className="w-12 h-12 border-4 border-lsc-dark/20 border-t-lsc-dark dark:border-lsc-cream/20 dark:border-t-lsc-cream rounded-full motion-safe:animate-spin"></div>
            </div>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">Loading schools...</p>
          </PageContainer>
        </div>
      )
    }
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <AlertCircle className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" aria-hidden="true" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            No partner schools yet
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
            Once a school partner is onboarded, you&apos;ll be able to view its reading dashboard here.
          </p>
        </PageContainer>
      </div>
    )
  }

  if (dashboardLoading || programsLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <div className="inline-block">
            <div className="w-12 h-12 border-4 border-lsc-dark/20 border-t-lsc-dark dark:border-lsc-cream/20 dark:border-t-lsc-cream rounded-full motion-safe:animate-spin"></div>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">Loading dashboard...</p>
        </PageContainer>
      </div>
    )
  }

  const handleExportProgress = () => {
    const csvContent = [
      ['School', 'Programs', 'Students', 'Total Minutes', 'Total Books'],
      [
        dashboardData?.school_name || 'N/A',
        dashboardData?.active_programs_count || 0,
        dashboardData?.student_registration_count || 0,
        dashboardData?.total_minutes_read || 0,
        dashboardData?.total_books_read || 0,
      ],
    ]
      .map((row) => row.join(','))
      .join('\n')

    const element = document.createElement('a')
    element.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent))
    element.setAttribute('download', `reading-progress-${dashboardData?.school_id}.csv`)
    element.style.display = 'none'
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    toast.success(t('toast.teacherReadingDashboard.progressReportDownloaded'))
  }

  const filteredPrograms = programs.filter((program) => {
    if (selectedFilter === 'active') return program.is_active
    if (selectedFilter === 'completed') return !program.is_active
    return true
  })

  return (
    <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark">
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-950 border-b border-lsc-dark/10 dark:border-lsc-cream/10 sticky top-0 z-40">
        <PageContainer className="py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-education-primary/10 rounded-lg">
                <BookOpen className="w-8 h-8 text-education-primary" aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  Reading Program Dashboard
                </h1>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                  {dashboardData?.school_name || 'School Reading Programs'}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleExportProgress}
              className="flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-lg bg-education-primary text-white hover:bg-education-primary/90 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-education-primary focus-visible:ring-offset-2"
            >
              <Download className="w-4 h-4" aria-hidden="true" />
              Export Report
            </button>
          </div>
          {/* Staff/admin school picker. Teachers are pinned to their school
              and never see this control. */}
          {!isTeacher && schools.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <label
                htmlFor={schoolPickerId}
                className="text-sm font-medium text-lsc-dark dark:text-lsc-cream"
              >
                School:
              </label>
              <select
                id={schoolPickerId}
                value={defaultSchoolId ?? ''}
                onChange={(e) => handlePickSchool(Number(e.target.value))}
                className="min-h-[44px] px-3 py-2 rounded-lg border border-lsc-dark/20 dark:border-lsc-cream/20 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus-visible:ring-2 focus-visible:ring-education-primary focus-visible:ring-offset-2"
              >
                {schools.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </PageContainer>
      </div>

      <PageContainer className="py-8">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard
            icon={<BookOpen className="w-6 h-6" />}
            label="Active Programs"
            value={dashboardData?.active_programs_count || 0}
          />
          <MetricCard
            icon={<Users className="w-6 h-6" />}
            label="Students Registered"
            value={dashboardData?.student_registration_count || 0}
          />
          <MetricCard
            icon={<TrendingUp className="w-6 h-6" />}
            label="Total Minutes Read"
            value={dashboardData?.total_minutes_read || 0}
            trend="Class aggregate"
          />
          <MetricCard
            icon={<Zap className="w-6 h-6" />}
            label="Total Books Read"
            value={dashboardData?.total_books_read || 0}
            trend="This school year"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Reading Programs Section */}
          <div className="lg:col-span-2 bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-dark/10 dark:border-lsc-cream/10 shadow-sm">
            <div className="p-6 border-b border-lsc-dark/5 dark:border-lsc-cream/5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-education-primary" aria-hidden="true" />
                  Reading Programs
                </h2>
              </div>

              {/* Filter buttons */}
              <div role="group" aria-label="Filter reading programs by status" className="flex gap-2">
                {(['all', 'active', 'completed'] as const).map((filter) => (
                  <button
                    type="button"
                    key={filter}
                    onClick={() => setSelectedFilter(filter)}
                    aria-pressed={selectedFilter === filter}
                    className={`min-h-[44px] px-3 py-2 text-sm rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-education-primary focus-visible:ring-offset-2 ${
                      selectedFilter === filter
                        ? 'bg-education-primary text-white'
                        : 'bg-lsc-dark/5 dark:bg-lsc-cream/5 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-dark/10 dark:hover:bg-lsc-cream/10'
                    }`}
                  >
                    {filter.charAt(0).toUpperCase() + filter.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="divide-y divide-lsc-dark/5 dark:divide-lsc-cream/5">
              {filteredPrograms.length === 0 ? (
                <div className="p-6 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                  <p>{t('teacherReadingDashboard.noReadingProgramsFoundCreate')}</p>
                </div>
              ) : (
                filteredPrograms.map((program) => (
                  <ProgramCard key={program.id} program={program} />
                ))
              )}
            </div>
          </div>

          {/* Sidebar - Badges */}
          <div className="space-y-6">
            {/* School Badges */}
            <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-dark/10 dark:border-lsc-cream/10 shadow-sm p-6">
              <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <Award className="w-5 h-5 text-status-warning-500 dark:text-status-warning-400" aria-hidden="true" />
                School Badges
              </h2>
              <div className="space-y-3">
                {badges.length === 0 ? (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    No badges created yet. Create custom badges for your students!
                  </p>
                ) : (
                  badges.map((badge) => (
                    <div
                      key={badge.id}
                      className="p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-700/30 rounded-lg"
                    >
                      <p className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">
                        {badge.badge_name}
                      </p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {badge.threshold_value} {badge.threshold_type}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Reading Lists Section */}
        <Link
          to="/teacher/reading-lists"
          className="block bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-dark/10 dark:border-lsc-cream/10 shadow-sm hover:border-education-primary/40 transition-colors"
        >
          <div className="p-6 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                Shared Reading Lists
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Browse curated reading lists from librarians and request copies for your classroom.
              </p>
            </div>
            <ArrowRight className="w-5 h-5 text-education-primary flex-shrink-0" aria-hidden="true" />
          </div>
        </Link>
      </PageContainer>
    </div>
  )
}

// Helper Components

function MetricCard({
  icon,
  label,
  value,
  trend,
}: {
  icon: React.ReactNode
  label: string
  value: number | string
  trend?: string
}): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-dark/10 dark:border-lsc-cream/10 p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <span className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium">{label}</span>
        <div className="text-education-primary" aria-hidden="true">{icon}</div>
      </div>
      <div className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mb-1">{value}</div>
      {trend && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{trend}</p>}
    </div>
  )
}

function ProgramCard({ program }: { program: ReadingProgram }): React.ReactElement {
  const isActive = program.is_active
  // Append T00:00:00 so bare YYYY-MM-DD dates parse as local midnight, not UTC.
  // Without this, dates render off-by-one in timezones west of UTC.
  const startDate = new Date(`${program.start_date}T00:00:00`)
  const endDate = new Date(`${program.end_date}T00:00:00`)

  return (
    <div className="p-4 hover:bg-lsc-dark/5 dark:hover:bg-lsc-cream/5 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{program.name}</h3>
        <span
          className={`px-2 py-1 text-xs rounded-full font-medium ${
            isActive
              ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-200'
              : 'bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-earth-200'
          }`}
        >
          {isActive ? 'Active' : 'Completed'}
        </span>
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
        {program.description || 'No description'}
      </p>
      <div className="flex flex-wrap gap-2 mb-3">
        {program.grade_levels.length > 0 && (
          <span className="text-xs px-2 py-1 bg-lsc-dark/10 dark:bg-lsc-cream/10 text-lsc-dark dark:text-lsc-cream rounded">
            Grades: {program.grade_levels.join(', ')}
          </span>
        )}
        {program.curriculum_alignment && (
          <span className="text-xs px-2 py-1 bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light/80 rounded">
            {program.curriculum_alignment}
          </span>
        )}
      </div>
      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        <span>
          {startDate.toLocaleDateString()} - {endDate.toLocaleDateString()}
        </span>
      </div>
    </div>
  )
}

