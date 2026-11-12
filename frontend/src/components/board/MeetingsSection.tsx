/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '@/api/types';
import {
  Plus,
  Edit2,
  Trash2,
  Calendar,
  Clock,
  MapPin,
  Users,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import ConfirmDialog from '../ConfirmDialog'
import MeetingForm from './MeetingForm'
import type { MeetingFormData } from './MeetingForm'
import MeetingDetailModal from './MeetingDetailModal'
import api from '../../api/api'

export interface BoardMeeting {
  id: number
  title: string
  description?: string
  scheduled_date: string
  start_time: string
  end_time?: string
  location?: string
  agenda?: string
  attendees?: number
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'cancelled'
  meeting_minutes_id?: number
}

interface MeetingsSectionProps {
  token: string | null
  userRole: string
}

export default function MeetingsSection({
  token,
  userRole,
}: MeetingsSectionProps): React.ReactElement {
  const { t } = useTranslation()
  const [meetings, setMeetings] = useState<BoardMeeting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingMeeting, setEditingMeeting] = useState<BoardMeeting | null>(null)
  const [selectedMeeting, setSelectedMeeting] = useState<BoardMeeting | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; title: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [filterStatus, setFilterStatus] = useState<BoardMeeting['status'] | 'ALL'>('ALL')

  const isAdmin = ['admin', 'super_admin'].includes(userRole)

  const fetchMeetings = useCallback(async () => {
    if (!token) return

    try {
      setLoading(true)
      setError(null)
      const data = await api.get(`${API_BASE}/board/meetings`)
      if (data && typeof data === 'object') {
        const meetings = Array.isArray(data) ? data : (data.meetings || [])
        // Sort by scheduled_date descending
        meetings.sort(
          (a: { scheduled_date?: string }, b: { scheduled_date?: string }) =>
            new Date(b.scheduled_date ?? '').getTime() - new Date(a.scheduled_date ?? '').getTime()
        )
        setMeetings(meetings)
      }
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to load meetings. Please try again.'
      setError(message)
      toast.error(message)
      setMeetings([])
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchMeetings()
  }, [fetchMeetings])

  const handleAddMeeting = async (formData: MeetingFormData) => {
    if (!token) return

    try {
      setSubmitting(true)
      await api.post(`${API_BASE}/board/meetings`, formData)
      toast.success(t('toast.meetingScheduled'))
      setShowForm(false)
      await fetchMeetings()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to schedule meeting. Please try again.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpdateMeeting = async (formData: MeetingFormData) => {
    if (!token || !editingMeeting) return

    try {
      setSubmitting(true)
      await api.put(`${API_BASE}/board/meetings/${editingMeeting.id}`, formData)
      toast.success(t('toast.meetingUpdated'))
      setEditingMeeting(null)
      await fetchMeetings()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to update meeting. Please try again.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteMeeting = async () => {
    if (!token || !deleteConfirm) return

    try {
      setSubmitting(true)
      await api.delete(`${API_BASE}/board/meetings/${deleteConfirm.id}`)
      toast.success(t('toast.meetingDeleted'))
      setDeleteConfirm(null)
      await fetchMeetings()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to delete meeting. Please try again.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const getStatusColor = (status: BoardMeeting['status']) => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
      case 'IN_PROGRESS':
        return 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
      case 'SCHEDULED':
        return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
      case 'cancelled':
        return 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
      default:
        return 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
    }
  }

  const filteredMeetings =
    filterStatus === 'ALL' ? meetings : meetings.filter((m) => m.status === filterStatus)

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
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
            Board Meetings
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {meetings.length} meetings on record
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => {
              setEditingMeeting(null)
              setShowForm(true)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Schedule Meeting
          </button>
        )}
      </div>

      {/* Status Filter */}
      <div className="flex flex-wrap gap-2">
        {(['ALL', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'cancelled'] as const).map(
          (status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                filterStatus === status
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600'
              }`}
            >
              {status === 'ALL' ? 'All' : status.toLowerCase().replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </button>
          )
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-900/50 rounded-lg flex gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</p>
        </div>
      )}

      {/* Meetings List */}
      <div className="space-y-4">
        {filteredMeetings.length === 0 ? (
          <div className="p-8 text-center bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
            <Calendar className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {filterStatus !== 'ALL'
                ? `No ${filterStatus.toLowerCase().replace('_', ' ')} meetings`
                : 'No meetings scheduled'}
            </p>
          </div>
        ) : (
          filteredMeetings.map((meeting) => (
            <div
              key={meeting.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                      {meeting.title}
                    </h3>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        meeting.status
                      )}`}
                    >
                      {meeting.status?.toLowerCase().replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()) ?? 'Unknown'}
                    </span>
                  </div>

                  {meeting.description && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-3">
                      {meeting.description}
                    </p>
                  )}

                  <div className="flex flex-wrap gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      {new Date(meeting.scheduled_date).toLocaleDateString()}
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      {meeting.start_time}
                      {meeting.end_time && ` - ${meeting.end_time}`}
                    </div>
                    {meeting.location && (
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        {meeting.location}
                      </div>
                    )}
                    {meeting.attendees && (
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        {meeting.attendees} attendees
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedMeeting(meeting)}
                    className="px-3 py-1 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600 rounded-lg transition-colors"
                  >
                    Details
                  </button>

                  {isAdmin && (
                    <>
                      <button
                        onClick={() => setEditingMeeting(meeting)}
                        className="p-2 hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 rounded-lg transition-colors"
                        aria-label={`Edit meeting ${meeting.title}`}
                      >
                        <Edit2 className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() =>
                          setDeleteConfirm({
                            id: meeting.id,
                            title: meeting.title,
                          })
                        }
                        className="p-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                        aria-label={`Delete meeting ${meeting.title}`}
                      >
                        <Trash2 className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Meeting Detail Modal */}
      {selectedMeeting && (
        <MeetingDetailModal
          meeting={selectedMeeting}
          onClose={() => setSelectedMeeting(null)}
          onEdit={() => {
            setEditingMeeting(selectedMeeting)
            setSelectedMeeting(null)
          }}
          userRole={userRole}
        />
      )}

      {/* Meeting Form */}
      {(showForm || editingMeeting) && isAdmin && (
        <MeetingForm
          meeting={editingMeeting}
          onSubmit={editingMeeting ? handleUpdateMeeting : handleAddMeeting}
          onCancel={() => {
            setShowForm(false)
            setEditingMeeting(null)
          }}
          loading={submitting}
        />
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Meeting?"
        message={`Are you sure you want to delete the meeting "${deleteConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleDeleteMeeting}
        onCancel={() => setDeleteConfirm(null)}
        loading={submitting}
      />
    </div>
  )
}