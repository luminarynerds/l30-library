/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  Calendar,
  Clock,
  Users,
  FileText,
  Gavel,
  MessageSquare,
  FolderOpen,
  CheckCircle2,
  XCircle,
  Pause,
  ArrowRight,
} from "lucide-react"
import api from "../../api/api"
import { API_BASE } from "@/api/types"
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'
import { getCurrentLocale } from '@/i18n'

interface BoardMeeting {
  id: number
  meeting_type: string
  title: string
  description?: string
  scheduled_date: string
  start_time?: string
  end_time?: string
  location?: string
  is_virtual: boolean
  is_cancelled: boolean
}

interface BoardMotion {
  id: number
  meeting_id: number
  motion_number: string
  title: string
  status: string
  created_at: string
}

interface CommentPeriod {
  id: number
  meeting_id: number
  title: string
  description?: string
  opens_at: string
  closes_at: string
  is_active: boolean
}


interface MeetingsResponse {
  meetings?: BoardMeeting[]
  results?: BoardMeeting[]
}
const statusConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  passed: {
    label: "Passed",
    icon: <CheckCircle2 className="h-4 w-4" />,
    color: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400",
  },
  failed: {
    label: "Failed",
    icon: <XCircle className="h-4 w-4" />,
    color: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400",
  },
  tabled: {
    label: "Tabled",
    icon: <Pause className="h-4 w-4" />,
    color: "bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-300",
  },
  referred: {
    label: "Referred",
    icon: <ArrowRight className="h-4 w-4" />,
    color: "bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light",
  },
  under_discussion: {
    label: "In Discussion",
    icon: <MessageSquare className="h-4 w-4" />,
    color: "bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-400",
  },
  pending: {
    label: "Pending",
    icon: <Clock className="h-4 w-4" />,
    color: "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400",
  },
}

const quickLinks = [
  { to: "/board/members", icon: Users, label: "Members" },
  { to: "/board/meetings", icon: Calendar, label: "Meetings" },
  { to: "/board/minutes", icon: FileText, label: "Minutes" },
  { to: "/board/motions", icon: Gavel, label: "Motions" },
  { to: "/board/committees", icon: Users, label: "Committees" },
  { to: "/board/documents", icon: FolderOpen, label: "Documents" },
  { to: "/board/public-comments", icon: MessageSquare, label: "Public Comments" },
]

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  })
}

function formatTime(timeString?: string): string | null {
  if (!timeString) return null
  return new Date(timeString).toLocaleTimeString(getCurrentLocale(), {
    hour: "numeric",
    minute: "2-digit",
  })
}

function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export default function BoardDashboardPage() {
  const branding = useBranding()
  const [nextMeeting, setNextMeeting] = useState<BoardMeeting | null>(null)
  const [recentMotions, setRecentMotions] = useState<BoardMotion[]>([])
  const [openPeriods, setOpenPeriods] = useState<CommentPeriod[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchRecentMotions = async (meetingsList: BoardMeeting[]): Promise<BoardMotion[]> => {
      try {
        const motionResults = await Promise.all(
          meetingsList.slice(0, 5).map((m) =>
            api
              .get(`${API_BASE}/board/meetings/${m.id}/motions`)
              .then((data: unknown) => Array.isArray(data) ? (data as BoardMotion[]) : [])
              .catch(() => [] as BoardMotion[])
          )
        )
        return motionResults
          .flat()
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .slice(0, 5)
      } catch {
        return []
      }
    }

    const fetchData = async () => {
      try {
        const meetingsRes = await api.get(`${API_BASE}/board/meetings?limit=20`)

        // Find next upcoming meeting
        const meetings: BoardMeeting[] = Array.isArray(meetingsRes)
          ? meetingsRes
          : (meetingsRes as MeetingsResponse).meetings || (meetingsRes as MeetingsResponse).results || []
        const now = new Date()
        const upcoming = meetings
          .filter((m) => new Date(m.scheduled_date) >= now && !m.is_cancelled)
          .sort((a, b) => new Date(a.scheduled_date).getTime() - new Date(b.scheduled_date).getTime())
        setNextMeeting(upcoming[0] || null)

        const motionsData = await fetchRecentMotions(meetings)
        setRecentMotions(motionsData)

        // Fetch comment periods from upcoming meetings
        if (upcoming.length > 0) {
          const periodsResults = await Promise.all(
            upcoming.slice(0, 5).map((m) =>
              api
                .get(`${API_BASE}/board/meetings/${m.id}/comment-periods?active_only=true`)
                .catch(() => [])
            )
          )
          const allPeriods = (periodsResults.flat() as CommentPeriod[]).filter((p) => {
            const closes = new Date(p.closes_at)
            return p.is_active && closes >= now
          })
          setOpenPeriods(allPeriods)
        }
      } catch (err) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <>
        <PageContainer className="py-8">
          <div className="motion-safe:animate-pulse space-y-6">
            <div className="h-8 bg-earth-200 dark:bg-earth-600 rounded w-1/3"></div>
            <div className="h-48 bg-earth-200 dark:bg-earth-600 rounded-xl"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="h-64 bg-earth-200 dark:bg-earth-600 rounded-xl"></div>
              <div className="h-64 bg-earth-200 dark:bg-earth-600 rounded-xl"></div>
            </div>
          </div>
        </PageContainer>
      </>
    )
  }

  return (
    <>
      <PageContainer className="py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Board of Trustees
          </h1>
          <p className="text-earth-600 dark:text-earth-200 mt-2">
            Governance, meetings, and public participation for the {branding.library_name}.
          </p>
        </div>

        {/* Next Meeting Hero */}
        <section className="mb-8" aria-label="Next meeting">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md border border-lsc-border dark:border-earth-700 p-6">
            {nextMeeting ? (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-lsc-rose uppercase tracking-wide mb-1">
                    Next Meeting
                  </p>
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {nextMeeting.title}
                  </h2>
                  <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-earth-600 dark:text-earth-200">
                    <span className="flex items-center gap-1.5">
                      <Calendar className="h-4 w-4" />
                      {formatDate(nextMeeting.scheduled_date)}
                    </span>
                    {nextMeeting.start_time && (
                      <span className="flex items-center gap-1.5">
                        <Clock className="h-4 w-4" />
                        {formatTime(nextMeeting.start_time)}
                      </span>
                    )}
                  </div>
                  {nextMeeting.location && (
                    <p className="text-sm text-earth-600 dark:text-earth-200 mt-1">
                      {nextMeeting.location}
                    </p>
                  )}
                </div>
                <Link
                  to={`/board/meetings/${nextMeeting.id}`}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors text-sm font-medium self-start"
                >
                  View Details
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            ) : (
              <div className="text-center py-4">
                <Calendar className="h-8 w-8 text-earth-600 mx-auto mb-2" />
                <p className="text-earth-600 dark:text-earth-200">
                  No upcoming meetings scheduled.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Two-column: Motions + Comment Periods */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Recent Motions */}
          <section aria-label="Recent motions">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md border border-lsc-border dark:border-earth-700 p-6 h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <Gavel className="h-5 w-5 text-lsc-rose" />
                  Recent Motions
                </h2>
                <Link
                  to="/board/motions"
                  className="text-sm text-lsc-rose hover:underline"
                >
                  View all
                </Link>
              </div>
              {recentMotions.length === 0 ? (
                <p className="text-sm text-earth-600 dark:text-earth-200">
                  No motions recorded yet.
                </p>
              ) : (
                <ul className="space-y-3">
                  {recentMotions.map((motion) => {
                    const config = statusConfig[motion.status] || {
                      label: motion.status,
                      icon: <FileText className="h-4 w-4" />,
                      color: "bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-300",
                    }
                    return (
                      <li key={motion.id}>
                        <Link
                          to={`/board/motions/${motion.id}`}
                          className="flex items-start justify-between gap-3 group"
                        >
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose truncate">
                              {motion.title}
                            </p>
                            <p className="text-xs text-earth-600 dark:text-earth-400 mt-0.5">
                              {motion.motion_number}
                            </p>
                          </div>
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${config.color}`}
                          >
                            {config.icon}
                            {config.label}
                          </span>
                        </Link>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </section>

          {/* Open Comment Periods */}
          <section aria-label="Public comment periods">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md border border-lsc-border dark:border-earth-700 p-6 h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-lsc-rose" />
                  Public Comment Periods
                </h2>
              </div>
              {openPeriods.length === 0 ? (
                <p className="text-sm text-earth-600 dark:text-earth-200">
                  No open comment periods at this time.
                </p>
              ) : (
                <ul className="space-y-3">
                  {openPeriods.map((period) => (
                    <li
                      key={period.id}
                      className="p-3 rounded-lg bg-lsc-cream/50 dark:bg-earth-900/50"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                          {period.title}
                        </h3>
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300">
                          Open
                        </span>
                      </div>
                      <p className="text-xs text-earth-600 dark:text-earth-400">
                        Closes {formatDateTime(period.closes_at)}
                      </p>
                      {period.description && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {period.description}
                        </p>
                      )}
                      <Link
                        to="/board/public-comments"
                        className="inline-block mt-2 text-xs text-lsc-rose hover:underline"
                      >
                        Submit a comment
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </div>

        {/* Quick Links */}
        <section aria-label="Board sections">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Board Sections
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {quickLinks.map(({ to, icon: Icon, label }) => (
              <Link
                key={to}
                to={to}
                className="flex flex-col items-center gap-2 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 shadow-sm hover:shadow-md hover:border-lsc-rose/50 transition-all text-center group"
              >
                <Icon className="h-6 w-6 text-earth-600 dark:text-earth-300 group-hover:text-lsc-rose transition-colors" />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {label}
                </span>
              </Link>
            ))}
          </div>
        </section>
      </PageContainer>
    </>
  )
}
