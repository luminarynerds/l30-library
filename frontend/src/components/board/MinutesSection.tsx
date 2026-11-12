/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import * as Sentry from "@/lib/sentry-lazy"
import React, { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '@/api/types';
import {
  Plus,
  Edit2,
  Trash2,
  FileText,
  Loader2,
  AlertCircle,
  Eye,
  CheckCircle,
  Clock,
  LayoutList,
  CalendarDays,
} from 'lucide-react'
import toast from 'react-hot-toast'
import ConfirmDialog from '../ConfirmDialog'
import MinutesForm from './MinutesForm'
import MinutesDetailModal from './MinutesDetailModal'
import api from '../../api/api'
import { useTranslation, getCurrentLocale } from '@/i18n'

export interface MinutesSection {
  id?: string
  title?: string
  heading?: string
  content?: string
  body?: string
  notes?: string
}

// The backend stores attendee lists as either plain names or
// {name, title} objects (see BoardMinutes.members_present).
export type MinutesAttendee = string | { name: string; title?: string }

export function attendeeName(a: MinutesAttendee): string {
  return typeof a === 'string' ? a : a?.name ?? ''
}

export interface MeetingMinutes {
  id: number
  meeting_id: number
  status: string
  sections?: MinutesSection[]
  meeting_called_to_order_at?: string
  meeting_adjourned_at?: string
  members_present?: MinutesAttendee[]
  members_absent?: MinutesAttendee[]
  members_excused?: MinutesAttendee[]
  guests_present?: MinutesAttendee[]
  quorum_met?: boolean
  quorum_count?: string
  recording_url?: string
  notes?: string
  plain_language_summary?: string
  approved: boolean
  approved_at?: string
  approved_by_id?: number
  approval_vote_result?: string
  created_at: string
  updated_at?: string
  // Computed/joined fields from meeting
  meeting_title?: string
  meeting_date?: string
}

export interface BoardMeeting {
  id: number
  title: string
  scheduled_date: string
  meeting_type: string
  is_cancelled: boolean
}

export interface MinutesFormData {
  meeting_id: number | string
  status: string
  sections?: MinutesSection[]
  members_present?: string[]
  members_absent?: string[]
  members_excused?: string[]
  guests_present?: string[]
  notes?: string
  plain_language_summary?: string
  quorum_met?: boolean
  quorum_count?: string
}

interface MinutesSectionProps {
  token: string | null
  userRole: string
  /** "h1" when this section is the page's top-level heading (e.g. /board/minutes) */
  headingLevel?: 'h1' | 'h2'
}

export default function MinutesSection({
  token,
  userRole,
  headingLevel = 'h2',
}: MinutesSectionProps): React.ReactElement {
  const HeadingTag = headingLevel
  // Group/card headings sit one and two levels below the section heading.
  const SubheadingTag = headingLevel === 'h1' ? 'h2' : 'h3'
  const CardHeadingTag = headingLevel === 'h1' ? 'h3' : 'h4'
  const { t } = useTranslation()
  const [minutes, setMinutes] = useState<MeetingMinutes[]>([])
  const [meetings, setMeetings] = useState<BoardMeeting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingMinutes, setEditingMinutes] = useState<MeetingMinutes | null>(null)
  const [selectedMinutes, setSelectedMinutes] = useState<MeetingMinutes | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; meeting_id: number; title: string } | null>(null)
  const [approveConfirm, setApproveConfirm] = useState<{ id: number; meeting_id: number; title: string } | null>(null)
  const [voteResult, setVoteResult] = useState('Approved unanimously')
  const [submitting, setSubmitting] = useState(false)
  const [filterStatus, setFilterStatus] = useState<'ALL' | 'draft' | 'approved'>('ALL')
  const [viewMode, setViewMode] = useState<'list' | 'timeline'>('timeline')

  const isAdmin = ['admin', 'super_admin'].includes(userRole)
  const canEdit = ['staff', 'admin', 'super_admin'].includes(userRole)

  const fetchMinutes = useCallback(async () => {
    // Public endpoint - no token required

    try {
      setLoading(true)
      setError(null)

      // Fetch approved minutes from the public endpoint
      const data = await api.get(`${API_BASE}/board/minutes`)
      const minutesList = Array.isArray(data) ? data : (data.minutes || [])

      // Sort by created_at descending
      minutesList.sort(
        (a: MeetingMinutes, b: MeetingMinutes) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
      setMinutes(minutesList)
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to fetch minutes'
      setError(message)
      toast.error(message)
      setMinutes([])
    } finally {
      setLoading(false)
    }
  }, [token])

  const fetchMeetings = useCallback(async () => {
    if (!token) return

    try {
      const data = await api.get(`${API_BASE}/board/meetings`)
      const meetingsList = Array.isArray(data) ? data : (data.meetings || [])
      // Filter out cancelled meetings
      setMeetings(meetingsList.filter((m: BoardMeeting) => !m.is_cancelled))
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
    }
  }, [token])

  useEffect(() => {
    fetchMinutes()
    fetchMeetings()
  }, [fetchMinutes, fetchMeetings])

  const handleAddMinutes = async (formData: MinutesFormData) => {
    if (!token || !formData.meeting_id) {
      toast.error(t('components.board.minutesSection.pleaseSelectAMeeting'))
      return
    }

    try {
      setSubmitting(true)
      await api.post(`${API_BASE}/board/meetings/${formData.meeting_id}/minutes`, {
        meeting_id: formData.meeting_id,
        status: formData.status || 'not_started',
        ...(formData.sections && { sections: formData.sections }),
        ...(formData.members_present && { members_present: formData.members_present }),
        ...(formData.members_absent && { members_absent: formData.members_absent }),
        ...(formData.guests_present && { guests_present: formData.guests_present }),
        ...(formData.notes && { notes: formData.notes }),
        ...(formData.quorum_met !== undefined && { quorum_met: formData.quorum_met }),
        ...(formData.quorum_count && { quorum_count: formData.quorum_count }),
      })
      toast.success(t('components.board.minutesSection.meetingMinutesCreatedSuccessfully'))
      setShowForm(false)
      await fetchMinutes()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create minutes'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpdateMinutes = async (formData: MinutesFormData) => {
    if (!token || !editingMinutes) return

    try {
      setSubmitting(true)
      await api.post(`${API_BASE}/board/meetings/${editingMinutes.meeting_id}/minutes`, {
        meeting_id: editingMinutes.meeting_id,
        status: formData.status,
        ...(formData.sections && { sections: formData.sections }),
        ...(formData.members_present && { members_present: formData.members_present }),
        ...(formData.members_absent && { members_absent: formData.members_absent }),
        ...(formData.guests_present && { guests_present: formData.guests_present }),
        ...(formData.notes && { notes: formData.notes }),
        ...(formData.quorum_met !== undefined && { quorum_met: formData.quorum_met }),
        ...(formData.quorum_count && { quorum_count: formData.quorum_count }),
      })
      toast.success(t('components.board.minutesSection.meetingMinutesUpdatedSuccessfully'))
      setEditingMinutes(null)
      await fetchMinutes()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update minutes'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleApproveMinutes = async () => {
    if (!token || !approveConfirm) return

    try {
      setSubmitting(true)
      // Use meeting-based approve endpoint with vote_result query param
      await api.post(
        `${API_BASE}/board/meetings/${approveConfirm.meeting_id}/minutes/approve?vote_result=${encodeURIComponent(voteResult)}`,
        {}
      )
      toast.success(t('components.board.minutesSection.meetingMinutesApprovedSuccessfully'))
      setApproveConfirm(null)
      setVoteResult('Approved unanimously')
      await fetchMinutes()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to approve minutes'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteMinutes = async () => {
    if (!token || !deleteConfirm) return

    try {
      setSubmitting(true)
      await api.delete(`${API_BASE}/board/meetings/${deleteConfirm.meeting_id}/minutes`)
      toast.success(t('components.board.minutesSection.meetingMinutesDeletedSuccessfully'))
      setDeleteConfirm(null)
      await fetchMinutes()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete minutes'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const getStatusColor = (item: MeetingMinutes) => {
    if (item.approved) {
      return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
    }
    return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
  }

  const getStatusLabel = (item: MeetingMinutes) => {
    if (item.approved) return 'approved'
    return 'draft'
  }

  const filteredMinutes = filterStatus === 'ALL'
    ? minutes
    : minutes.filter((m) => {
        if (filterStatus === 'approved') return m.approved
        if (filterStatus === 'draft') return !m.approved
        return true
      })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <HeadingTag className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
            Meeting Minutes
          </HeadingTag>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {minutes.length} minutes on file
          </p>
        </div>

        {canEdit && (
          <button
            onClick={() => {
              setEditingMinutes(null)
              setShowForm(true)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Minutes
          </button>
        )}
      </div>

      {/* View Toggle + Status Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {(['ALL', 'draft', 'approved'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                filterStatus === status
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600'
              }`}
            >
              {status === 'ALL' ? 'All' : status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 bg-lsc-cream dark:bg-earth-700 rounded-lg p-1">
          <button
            onClick={() => setViewMode('list')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              viewMode === 'list'
                ? 'bg-lsc-white dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream shadow-sm'
                : 'text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream'
            }`}
            aria-label="List view"
          >
            <LayoutList className="w-4 h-4" />
            List
          </button>
          <button
            onClick={() => setViewMode('timeline')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              viewMode === 'timeline'
                ? 'bg-lsc-white dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream shadow-sm'
                : 'text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream'
            }`}
            aria-label="Timeline view"
          >
            <CalendarDays className="w-4 h-4" />
            Timeline
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-900/50 rounded-lg flex gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</p>
        </div>
      )}

      {/* Minutes Display */}
      {filteredMinutes.length === 0 ? (
        <div className="p-8 text-center bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <FileText className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {filterStatus !== 'ALL'
              ? `No ${filterStatus.toLowerCase()} minutes`
              : 'No meeting minutes'}
          </p>
        </div>
      ) : viewMode === 'list' ? (
        /* List View */
        <div className="space-y-4">
          {filteredMinutes.map((minutesItem) => (
            <div
              key={minutesItem.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <SubheadingTag className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                      Meeting #{minutesItem.meeting_id} Minutes
                    </SubheadingTag>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(minutesItem)}`}
                    >
                      {getStatusLabel(minutesItem)}
                    </span>
                  </div>

                  {minutesItem.meeting_title && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                      Meeting: {minutesItem.meeting_title}
                    </p>
                  )}

                  {minutesItem.notes && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2" title={minutesItem.notes}>
                      {minutesItem.notes}
                    </p>
                  )}

                  {minutesItem.members_present && minutesItem.members_present.length > 0 && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                      {minutesItem.members_present.length} members present
                    </p>
                  )}

                  <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {new Date(minutesItem.created_at).toLocaleDateString()}
                    </div>
                    {minutesItem.approved && minutesItem.approval_vote_result && (
                      <span className="text-status-success-600 dark:text-status-success-400">
                        {minutesItem.approval_vote_result}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedMinutes(minutesItem)}
                    className="px-3 py-1 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Eye className="w-4 h-4" />
                    View
                  </button>

                  {isAdmin && !minutesItem.approved && (
                    <button
                      onClick={() =>
                        setApproveConfirm({
                          id: minutesItem.id,
                          meeting_id: minutesItem.meeting_id,
                          title: `Meeting #${minutesItem.meeting_id}`,
                        })
                      }
                      className="px-3 py-1 text-sm bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 hover:bg-status-success-200 dark:hover:bg-status-success-900/50 rounded-lg transition-colors flex items-center gap-2"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Approve
                    </button>
                  )}

                  {canEdit && !minutesItem.approved && (
                    <>
                      <button
                        onClick={() => setEditingMinutes(minutesItem)}
                        className="p-2 hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 rounded-lg transition-colors"
                        aria-label={t('aria.board.editMinutes')}
                      >
                        <Edit2 className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() =>
                          setDeleteConfirm({
                            id: minutesItem.id,
                            meeting_id: minutesItem.meeting_id,
                            title: `Meeting #${minutesItem.meeting_id}`,
                          })
                        }
                        className="p-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                        aria-label={t('aria.board.deleteMinutes')}
                      >
                        <Trash2 className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Timeline View */
        <div className="space-y-8">
          {(() => {
            const grouped: Record<string, { label: string; items: MeetingMinutes[] }> = {}
            filteredMinutes.forEach((item) => {
              const monthKey = (item.meeting_date || item.created_at || '').substring(0, 7)
              const monthLabel = new Date(item.meeting_date || item.created_at).toLocaleDateString(getCurrentLocale(), { year: 'numeric', month: 'long' })
              if (!grouped[monthKey]) grouped[monthKey] = { label: monthLabel, items: [] }
              grouped[monthKey].items.push(item)
            })
            return Object.entries(grouped).map(([, { label: monthYear, items }]) => (
              <div key={monthYear}>
                <SubheadingTag className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                  {monthYear}
                </SubheadingTag>
                <div className="relative border-l-2 border-lsc-rose/30 ml-4 space-y-6">
                  {items.map((minutesItem) => (
                    <div key={minutesItem.id} className="relative pl-8">
                      {/* Timeline dot */}
                      <div className="absolute left-[-7px] top-3 w-3 h-3 rounded-full bg-lsc-rose" />
                      {/* Card */}
                      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 hover:shadow-md transition-shadow">
                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-1">
                              <CardHeadingTag className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                                {minutesItem.meeting_title || `Meeting #${minutesItem.meeting_id}`}
                              </CardHeadingTag>
                              <span
                                className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(minutesItem)}`}
                              >
                                {getStatusLabel(minutesItem)}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                              <span>
                                {new Date(minutesItem.meeting_date || minutesItem.created_at).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })}
                              </span>
                              {minutesItem.approved && minutesItem.approved_at && (
                                <span className="text-status-success-600 dark:text-status-success-400">
                                  Approved {new Date(minutesItem.approved_at).toLocaleDateString()}
                                </span>
                              )}
                              {minutesItem.approval_vote_result && (
                                <span className="text-status-success-600 dark:text-status-success-400">
                                  {minutesItem.approval_vote_result}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setSelectedMinutes(minutesItem)}
                              className="px-3 py-1 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600 rounded-lg transition-colors flex items-center gap-2"
                            >
                              <Eye className="w-4 h-4" />
                              View
                            </button>
                            {isAdmin && !minutesItem.approved && (
                              <button
                                onClick={() =>
                                  setApproveConfirm({
                                    id: minutesItem.id,
                                    meeting_id: minutesItem.meeting_id,
                                    title: minutesItem.meeting_title || `Meeting #${minutesItem.meeting_id}`,
                                  })
                                }
                                className="px-3 py-1 text-sm bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 hover:bg-status-success-200 dark:hover:bg-status-success-900/50 rounded-lg transition-colors flex items-center gap-2"
                              >
                                <CheckCircle className="w-4 h-4" />
                                Approve
                              </button>
                            )}
                            {canEdit && !minutesItem.approved && (
                              <>
                                <button
                                  onClick={() => setEditingMinutes(minutesItem)}
                                  className="p-2 hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 rounded-lg transition-colors"
                                  aria-label={t('aria.board.editMinutes')}
                                >
                                  <Edit2 className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                                </button>
                                <button
                                  onClick={() =>
                                    setDeleteConfirm({
                                      id: minutesItem.id,
                                      meeting_id: minutesItem.meeting_id,
                                      title: minutesItem.meeting_title || `Meeting #${minutesItem.meeting_id}`,
                                    })
                                  }
                                  className="p-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                                  aria-label={t('aria.board.deleteMinutes')}
                                >
                                  <Trash2 className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          })()}
        </div>
      )}

      {/* Minutes Detail Modal */}
      {selectedMinutes && (
        <MinutesDetailModal
          minutes={selectedMinutes}
          onClose={() => setSelectedMinutes(null)}
        />
      )}

      {/* Minutes Form */}
      {(showForm || editingMinutes) && canEdit && (
        <MinutesForm
          minutes={editingMinutes}
          meetings={meetings}
          onSubmit={editingMinutes ? handleUpdateMinutes : handleAddMinutes}
          onCancel={() => {
            setShowForm(false)
            setEditingMinutes(null)
          }}
          loading={submitting}
        />
      )}

      {/* Approve Confirmation */}
      {approveConfirm && (
        <ModalBackdrop onClose={() => { setApproveConfirm(null); setVoteResult('Approved unanimously'); }} title="Approve Minutes?">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6">
            <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              Approve Minutes?
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Approve the minutes for "{approveConfirm.title}"? Approved minutes cannot be edited.
            </p>
            <div className="mb-4">
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Vote Result
              </label>
              <input
                type="text"
                value={voteResult}
                onChange={(e) => setVoteResult(e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.board.egApproved50')}
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setApproveConfirm(null)
                  setVoteResult('Approved unanimously')
                }}
                disabled={submitting}
                className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveMinutes}
                disabled={submitting || !voteResult.trim()}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {submitting && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                Approve
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Minutes?"
        message={`Are you sure you want to delete the minutes for "${deleteConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleDeleteMinutes}
        onCancel={() => setDeleteConfirm(null)}
        loading={submitting}
      />
    </div>
  )
}