/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { API_BASE } from '@/api/types';
import {
  MessageSquare,
  Calendar,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronLeft,
  Info,
  Send,
} from 'lucide-react'
import api from '../../api/api'
import {
  getMeetingCommentPeriods,
  getActiveCommentPeriods,
  submitPublicComment,
  type CommentPeriod,
} from '../../api/board-public-comments-api'
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
  virtual_meeting_url?: string
  is_cancelled: boolean
  public_comment_enabled: boolean
}


const parseMeetingsResponse = (data: unknown): BoardMeeting[] => {
  if (Array.isArray(data)) return data
  if (data && typeof data === 'object' && 'meetings' in data) {
    return (data as { meetings: BoardMeeting[] }).meetings || []
  }
  return []
}
const meetingTypeLabels: Record<string, string> = {
  regular: 'Regular Meeting',
  special: 'Special Meeting',
  emergency: 'Emergency Meeting',
  committee: 'Committee Meeting',
  workshop: 'Workshop',
  public_hearing: 'Public Hearing',
}


function PublicCommentsLanding() {
  const [meetings, setMeetings] = useState<BoardMeeting[]>([])
  const [activePeriods, setActivePeriods] = useState<CommentPeriod[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [meetingsData, periods] = await Promise.all([
          api.get(`${API_BASE}/board/meetings?limit=100`),
          getActiveCommentPeriods(),
        ])
        const allMeetings = parseMeetingsResponse(meetingsData)
        const commentMeetings = allMeetings.filter(m => !m.is_cancelled && m.public_comment_enabled)
        const upcoming = commentMeetings
          .filter(m => new Date(m.scheduled_date) >= new Date(new Date().toDateString()))
          .sort((a, b) => new Date(a.scheduled_date).getTime() - new Date(b.scheduled_date).getTime())
        setMeetings(upcoming)
        setActivePeriods(periods)
      } catch (err) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    })

  const meetingIdsWithActivePeriods = new Set(activePeriods.map(p => p.meeting_id))

  if (loading) {
    return (
      <PageContainer className="py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-8">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <MessageSquare className="h-7 w-7 text-lsc-rose" />
          <h1 className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">Public Comments</h1>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Members of the public may submit written comments on upcoming board meeting agenda items.
        </p>
      </div>

      {activePeriods.length > 0 && (
        <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle className="h-5 w-5 text-status-success-600 dark:text-status-success-400" />
            <span className="font-semibold text-status-success-800 dark:text-status-success-200">
              {activePeriods.length} open comment {activePeriods.length === 1 ? 'period' : 'periods'}
            </span>
          </div>
          <p className="text-sm text-status-success-700 dark:text-status-success-300 ml-7">
            Select a meeting below to submit your comment.
          </p>
        </div>
      )}

      {meetings.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-earth-200 dark:border-earth-700 p-8 text-center">
          <Calendar className="h-12 w-12 text-earth-600 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">No upcoming meetings with public comments enabled.</p>
          <Link to="/board/meetings" className="text-sm text-lsc-rose hover:underline">
            View all board meetings
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {meetings.map(meeting => {
            const hasActivePeriod = meetingIdsWithActivePeriods.has(meeting.id)
            return (
              <Link
                key={meeting.id}
                to={`/board/public-comments/${meeting.id}`}
                className="block bg-lsc-white dark:bg-earth-800 rounded-xl border border-earth-200 dark:border-earth-700 p-5 hover:border-lsc-rose dark:hover:border-lsc-rose hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-1">{meeting.title}</h2>
                    <div className="flex flex-wrap items-center gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="h-4 w-4" />
                        {formatDate(meeting.scheduled_date)}
                      </span>
                      {meeting.location && (
                        <span className="text-xs">{meeting.location}</span>
                      )}
                      <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded-full text-xs">
                        {meetingTypeLabels[meeting.meeting_type] || meeting.meeting_type}
                      </span>
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    {hasActivePeriod ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 rounded-full text-xs font-medium">
                        <span className="w-2 h-2 bg-status-success-500 rounded-full" />
                        Open
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 rounded-full text-xs font-medium">
                        Upcoming
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}

      <div className="mt-8 bg-earth-50 dark:bg-earth-800/50 rounded-xl border border-earth-200 dark:border-earth-700 p-5">
        <div className="flex items-center gap-2 mb-2">
          <Info className="h-5 w-5 text-lsc-rose" />
          <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream">How Public Comments Work</h2>
        </div>
        <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 ml-7">
          <li>Comments are reviewed by staff before being shared with the board</li>
          <li>Be respectful and constructive in your feedback</li>
          <li>Comments become part of the public record</li>
          <li>You may also attend meetings in person to address the board</li>
        </ul>
      </div>
    </PageContainer>
  )
}

export default function PublicCommentsPage() {
  const { meetingId } = useParams()

  if (!meetingId) {
    return <PublicCommentsLanding />
  }

  return <PublicCommentsMeeting meetingId={meetingId} />
}


function PublicCommentForm({ meetingId }: { meetingId: number }) {
  const [formData, setFormData] = useState({
    commenter_name: '',
    commenter_email: '',
    comment_text: '',
    subject: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.commenter_name.trim() || !formData.comment_text.trim()) return

    try {
      setSubmitting(true)
      setSubmitError(null)
      await submitPublicComment(meetingId, {
        commenter_name: formData.commenter_name.trim(),
        commenter_email: formData.commenter_email.trim() || undefined,
        subject: formData.subject.trim() || undefined,
        comment_text: formData.comment_text.trim(),
      })
      setSubmitted(true)
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      setSubmitError('Unable to submit your comment. Please try again or contact us directly.')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-8 text-center">
        <CheckCircle className="h-12 w-12 text-status-success-600 dark:text-status-success-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-status-success-800 dark:text-status-success-200 mb-2">
          Comment Submitted
        </h3>
        <p className="text-status-success-700 dark:text-status-success-300 text-sm">
          Your comment has been received and will be reviewed by staff before being shared with the board.
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {submitError && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-status-danger-700 dark:text-status-danger-300 text-sm">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{submitError}</span>
          </div>
        </div>
      )}

      <div>
        <label htmlFor="commenter_name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
          Your Name <span className="text-status-danger-600" aria-hidden="true">*</span>
        </label>
        <input
          type="text"
          id="commenter_name"
          name="commenter_name"
          required
          value={formData.commenter_name}
          onChange={handleChange}
          disabled={submitting}
          className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
        />
      </div>

      <div>
        <label htmlFor="commenter_email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
          Email <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">(optional)</span>
        </label>
        <input
          type="email"
          id="commenter_email"
          name="commenter_email"
          value={formData.commenter_email}
          onChange={handleChange}
          disabled={submitting}
          className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
        />
      </div>

      <div>
        <label htmlFor="subject" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
          Subject <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">(optional)</span>
        </label>
        <input
          type="text"
          id="subject"
          name="subject"
          value={formData.subject}
          onChange={handleChange}
          disabled={submitting}
          className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
        />
      </div>

      <div>
        <label htmlFor="comment_text" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
          Your Comment <span className="text-status-danger-600" aria-hidden="true">*</span>
        </label>
        <textarea
          id="comment_text"
          name="comment_text"
          required
          rows={6}
          maxLength={5000}
          value={formData.comment_text}
          onChange={handleChange}
          disabled={submitting}
          className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
        />
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
          {formData.comment_text.length}/5000 characters
        </p>
      </div>

      <button
        type="submit"
        disabled={submitting || !formData.commenter_name.trim() || !formData.comment_text.trim()}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
      >
        {submitting ? (
          <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
        {submitting ? 'Submitting...' : 'Submit Comment'}
      </button>
    </form>
  )
}

function PublicCommentsMeeting({ meetingId }: { meetingId: string }) {
  const [meeting, setMeeting] = useState<BoardMeeting | null>(null)
  const [commentPeriods, setCommentPeriods] = useState<CommentPeriod[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {

      try {
        // Fetch meeting details
        const meetingsData = await api.get(`${API_BASE}/board/meetings?limit=100`)
        const meetings = parseMeetingsResponse(meetingsData)
        const found = meetings.find((m) => m.id === parseInt(meetingId))

        if (!found) {
          setError('Meeting not found')
          setLoading(false)
          return
        }

        setMeeting(found)

        // Fetch comment periods
        const periods = await getMeetingCommentPeriods(parseInt(meetingId), true)
        setCommentPeriods(periods)
      } catch (_err) {
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
        setError('Unable to load meeting information')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [meetingId])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString(getCurrentLocale(), {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }


  if (loading) {
    return (
      <PageContainer className="py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
        </div>
      </PageContainer>
    )
  }

  if (error || !meeting) {
    return (
      <PageContainer className="py-8">
        <Link
          to="/board/meetings"
          className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream mb-4"
        >
          <ChevronLeft className="h-4 w-4" /> Back to Meetings
        </Link>
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-status-danger-600 dark:text-status-danger-400" />
            <p className="text-status-danger-700 dark:text-status-danger-300">{error || 'Meeting not found'}</p>
          </div>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-8">
      <Link
        to="/board/meetings"
        className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream mb-4"
      >
        <ChevronLeft className="h-4 w-4" /> Back to Meetings
      </Link>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Form Section */}
        <div className="lg:col-span-2">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <div className="flex items-center gap-3 mb-6">
              <MessageSquare className="h-6 w-6 text-lsc-rose" />
              <h1 className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                Submit Public Comment
              </h1>
            </div>

            {/* Meeting Info */}
            <div className="bg-lsc-cream/50 dark:bg-earth-900/50 rounded-xl p-4 mb-6">
              <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                {meeting.title}
              </h2>
              <div className="flex flex-wrap gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  {formatDate(meeting.scheduled_date)}
                </div>
                <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded-full text-xs">
                  {meetingTypeLabels[meeting.meeting_type] || meeting.meeting_type}
                </span>
              </div>
            </div>

            {/* Comment Submission Form */}
            <PublicCommentForm meetingId={parseInt(meetingId)} />
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Comment Period Info */}
          {commentPeriods.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="h-5 w-5 text-lsc-rose" />
                <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream">Comment Periods</h2>
              </div>
              <div className="space-y-4">
                {commentPeriods.map((period) => {
                  const now = new Date()
                  const opens = new Date(period.opens_at)
                  const closes = new Date(period.closes_at)
                  const isOpen = period.is_active && now >= opens && now <= closes
                  const isPast = now > closes

                  return (

                    <div
                      key={period.id}
                      className="p-3 rounded-lg bg-lsc-cream/50 dark:bg-earth-900/50"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">
                          {period.title}
                        </h3>
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            isOpen
                              ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
                              : isPast
                              ? 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-300'
                              : 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
                          }`}
                        >
                          {isOpen ? 'Open' : isPast ? 'Closed' : 'Upcoming'}
                        </span>
                      </div>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {formatDateTime(period.opens_at)} - {formatDateTime(period.closes_at)}
                      </p>
                      {period.description && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {period.description}
                        </p>
                      )}
                    </div>

  )
                })}
              </div>
            </div>
          )}

          {/* Guidelines */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <div className="flex items-center gap-2 mb-4">
              <Info className="h-5 w-5 text-lsc-rose" />
              <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream">Guidelines</h2>
            </div>
            <ul className="space-y-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 text-status-success-500 flex-shrink-0 mt-0.5" />
                Comments are reviewed before being shared with the board
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 text-status-success-500 flex-shrink-0 mt-0.5" />
                Be respectful and constructive in your feedback
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 text-status-success-500 flex-shrink-0 mt-0.5" />
                Stay on topic related to library matters
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 text-status-success-500 flex-shrink-0 mt-0.5" />
                Comments become part of the public record
              </li>
            </ul>
          </div>

          {/* Links */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
            <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Resources</h2>
            <div className="space-y-2">
              <Link
                to={`/board/meetings/${meetingId}`}
                className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                View Meeting Details
              </Link>
              <Link
                to="/board/meetings"
                className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                All Board Meetings
              </Link>
              <Link
                to="/board/documents"
                className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                Meeting Documents
              </Link>
              <Link
                to="/board/members"
                className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                Board Members
              </Link>
            </div>
          </div>
        </div>
      </div>
    </PageContainer>
  )
}