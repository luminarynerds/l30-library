/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import { Modal } from '@/components/ui/Modal'
import { useSearchParams } from 'react-router-dom'
import { API_BASE } from '@/api/types';
import * as Sentry from "@/lib/sentry-lazy"
import {
  MessageSquare,
  AlertCircle,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Mic,
  FileText,
  Filter,
  Settings,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getPendingComments,
  getMeetingComments,
  moderateComment,
  markCommentReadIntoRecord,
  addStaffResponse,
  deleteComment,
  registerSpeaker,
  startSpeaking,
  stopSpeaking,
  getMeetingCommentPeriods,
  createCommentPeriod,
  updateCommentPeriod,
  startCommentPeriod,
  endCommentPeriod,
  deleteCommentPeriod,
  type PublicComment,
  type CommentPeriod,
  type PublicCommentSubmit,
  type CommentPeriodCreate,
} from '../../api/board-public-comments-api'
import api from '@/lib/api-client'
import { useTranslation} from '@/i18n'
import { CommentPeriodsTab } from '../../components/board/CommentPeriodsTab'
import { SpeakersTab } from '../../components/board/SpeakersTab'
import { CommentsListTab } from '../../components/board/CommentsListTab'
import { AdminShell } from '../../components/shells/AdminShell'
import PageContainer from '@/components/layout/PageContainer'

interface BoardMeeting {
  id: number
  title: string
  scheduled_date: string
}

type TabType = 'pending' | 'approved' | 'rejected' | 'speakers' | 'periods'

export default function BoardPublicCommentsAdminPage(): React.ReactElement {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const meetingIdParam = searchParams.get('meeting')

  const [activeTab, setActiveTab] = useState<TabType>('pending')
  const [comments, setComments] = useState<PublicComment[]>([])
  const [commentPeriods, setCommentPeriods] = useState<CommentPeriod[]>([])
  const [meetings, setMeetings] = useState<BoardMeeting[]>([])
  const [selectedMeetingId, setSelectedMeetingId] = useState<number | null>(
    meetingIdParam ? parseInt(meetingIdParam) : null
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [selectedComment, setSelectedComment] = useState<PublicComment | null>(null)
  const [moderationAction, setModerationAction] = useState<{
    type: 'approve' | 'reject' | 'read' | 'delete'
    comment: PublicComment
  } | null>(null)
  const [moderationNotes, setModerationNotes] = useState('')
  const [rejectionReason, setRejectionReason] = useState('')

  const [respondingTo, setRespondingTo] = useState<PublicComment | null>(null)
  const [staffResponse, setStaffResponse] = useState('')

  const [showSpeakerForm, setShowSpeakerForm] = useState(false)
  const [speakerForm, setSpeakerForm] = useState<PublicCommentSubmit & { type: 'in_person' | 'virtual' }>({
    commenter_name: '',
    commenter_email: '',
    commenter_phone: '',
    organization: '',
    is_resident: true,
    subject: '',
    comment_text: '',
    type: 'in_person',
  })

  const [activeSpeaker, setActiveSpeaker] = useState<number | null>(null)

  const [showPeriodForm, setShowPeriodForm] = useState(false)
  const [editingPeriod, setEditingPeriod] = useState<CommentPeriod | null>(null)
  const [periodForm, setPeriodForm] = useState<CommentPeriodCreate>({
    title: '',
    description: '',
    opens_at: '',
    closes_at: '',
    is_active: true,
    allow_written: true,
    allow_in_person: true,
    allow_virtual: true,
    max_comment_length: 2000,
    speaker_time_limit_seconds: 180,
  })
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingDeletePeriodId, setPendingDeletePeriodId] = useState<number | null>(null)

  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        const data = await api.get(`${API_BASE}/board/meetings?limit=50`) as { meetings?: BoardMeeting[] } | BoardMeeting[]
        const meetingsList = Array.isArray(data) ? data : (data.meetings || [])
        setMeetings(meetingsList)
      } catch {
        Sentry.captureMessage('Failed to fetch meetings', 'error')
      }
    }
    fetchMeetings()
  }, [])

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      if (selectedMeetingId) {
        const [commentsData, periodsData] = await Promise.all([
          getMeetingComments(selectedMeetingId),
          getMeetingCommentPeriods(selectedMeetingId, false),
        ])
        setComments(commentsData)
        setCommentPeriods(periodsData)
      } else {
        const pendingData = await getPendingComments(100)
        setComments(pendingData)
        setCommentPeriods([])
      }
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to load data. Please try again.'
      setError(message)
      toast.error(message)
      setComments([])
      setCommentPeriods([])
    } finally {
      setLoading(false)
    }
  }, [selectedMeetingId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleMeetingChange = (meetingId: string) => {
    const id = meetingId ? parseInt(meetingId) : null
    setSelectedMeetingId(id)
    if (id) {
      setSearchParams({ meeting: String(id) })
    } else {
      setSearchParams({})
    }
  }

  const handleModerateComment = async () => {
    if (!moderationAction) return

    try {
      setSubmitting(true)

      if (moderationAction.type === 'delete') {
        await deleteComment(moderationAction.comment.id)
        toast.success(t('toast.boardPublicCommentsAdmin.commentDeleted'))
      } else if (moderationAction.type === 'read') {
        await markCommentReadIntoRecord(moderationAction.comment.id, {
          ...(moderationNotes && { reading_notes: moderationNotes }),
        })
        toast.success(t('boardPublicCommentsAdmin.commentMarkedAsReadInto'))
      } else {
        await moderateComment(moderationAction.comment.id, {
          status: moderationAction.type === 'approve' ? 'approved' : 'rejected',
          ...(moderationNotes && { moderation_notes: moderationNotes }),
          ...(moderationAction.type === 'reject' && rejectionReason && { rejection_reason: rejectionReason }),
        })
        toast.success(t('toast.boardPublicCommentsAdmin.commentTypeapproveapprovedrejected', { typeapproveapprovedrejected: moderationAction.type === 'approve' ? 'approved' : 'rejected' }))
      }

      setModerationAction(null)
      setModerationNotes('')
      setRejectionReason('')
      await fetchData()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Action failed. Please try again.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleStaffResponse = async () => {
    if (!respondingTo || !staffResponse.trim()) return

    try {
      setSubmitting(true)
      await addStaffResponse(respondingTo.id, { staff_response: staffResponse.trim() })
      toast.success(t('toast.boardPublicCommentsAdmin.staffResponseAdded'))
      setRespondingTo(null)
      setStaffResponse('')
      await fetchData()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to add response.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleRegisterSpeaker = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedMeetingId || !speakerForm.commenter_name.trim()) return

    try {
      setSubmitting(true)
      await registerSpeaker(selectedMeetingId, {
        commenter_name: speakerForm.commenter_name.trim(),
        ...(speakerForm.commenter_email?.trim() && { commenter_email: speakerForm.commenter_email.trim() }),
        ...(speakerForm.commenter_phone?.trim() && { commenter_phone: speakerForm.commenter_phone.trim() }),
        ...(speakerForm.organization?.trim() && { organization: speakerForm.organization.trim() }),
        ...(typeof speakerForm.is_resident === 'boolean' && { is_resident: speakerForm.is_resident }),
        ...(speakerForm.subject?.trim() && { subject: speakerForm.subject.trim() }),
        comment_text: speakerForm.comment_text?.trim() || '',
      }, speakerForm.type)

      toast.success(t('toast.boardPublicCommentsAdmin.speakerRegistered'))
      setShowSpeakerForm(false)
      setSpeakerForm({
        commenter_name: '',
        commenter_email: '',
        commenter_phone: '',
        organization: '',
        is_resident: true,
        subject: '',
        comment_text: '',
        type: 'in_person',
      })
      await fetchData()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to register speaker.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleStartSpeaking = async (commentId: number) => {
    try {
      await startSpeaking(commentId)
      setActiveSpeaker(commentId)
      toast.success(t('toast.boardPublicCommentsAdmin.speakerStarted'))
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to start speaker.'
      toast.error(message)
    }
  }

  const handleStopSpeaking = async (commentId: number) => {
    try {
      const result = await stopSpeaking(commentId)
      setActiveSpeaker(null)
      toast.success(t('toast.boardPublicCommentsAdmin.speakerFinishedDurationseconds60Min', { durationseconds60: Math.round(result.duration_seconds / 60) }))
      await fetchData()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to stop speaker.'
      toast.error(message)
    }
  }

  const handleCreatePeriod = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedMeetingId) return

    try {
      setSubmitting(true)
      if (editingPeriod) {
        await updateCommentPeriod(editingPeriod.id, periodForm)
        toast.success(t('toast.boardPublicCommentsAdmin.commentPeriodUpdated'))
      } else {
        await createCommentPeriod(selectedMeetingId, periodForm)
        toast.success(t('toast.boardPublicCommentsAdmin.commentPeriodCreated'))
      }
      setShowPeriodForm(false)
      setEditingPeriod(null)
      setPeriodForm({
        title: '',
        description: '',
        opens_at: '',
        closes_at: '',
        is_active: true,
        allow_written: true,
        allow_in_person: true,
        allow_virtual: true,
        max_comment_length: 2000,
        speaker_time_limit_seconds: 180,
      })
      await fetchData()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to save comment period.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleStartPeriod = async (periodId: number) => {
    try {
      await startCommentPeriod(periodId)
      toast.success(t('toast.boardPublicCommentsAdmin.commentPeriodStarted'))
      await fetchData()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to start period.'
      toast.error(message)
    }
  }

  const handleEndPeriod = async (periodId: number) => {
    try {
      await endCommentPeriod(periodId)
      toast.success(t('toast.boardPublicCommentsAdmin.commentPeriodEnded'))
      await fetchData()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to end period.'
      toast.error(message)
    }
  }

  const handleDeletePeriod = (periodId: number) => {
    setPendingDeletePeriodId(periodId)
    setConfirmOpen(true)
  }

  const handleDeletePeriodConfirm = async () => {
    if (pendingDeletePeriodId === null) return
    setConfirmOpen(false)
    try {
      await deleteCommentPeriod(pendingDeletePeriodId)
      toast.success(t('toast.boardPublicCommentsAdmin.commentPeriodDeleted'))
      await fetchData()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to delete period.'
      toast.error(message)
    } finally {
      setPendingDeletePeriodId(null)
    }
  }

  const getStatusColor = (status: PublicComment['status']) => {
    switch (status) {
      case 'approved':
        return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
      case 'rejected':
        return 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
      case 'read_into_record':
        return 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
      case 'pending':
      default:
        return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    }
  }

  const getStatusIcon = (status: PublicComment['status']) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="w-4 h-4" />
      case 'rejected':
        return <XCircle className="w-4 h-4" />
      case 'read_into_record':
        return <FileText className="w-4 h-4" />
      case 'pending':
      default:
        return <Clock className="w-4 h-4" />
    }
  }

  const getCommentTypeIcon = (type: PublicComment['comment_type']) => {
    switch (type) {
      case 'in_person':
        return <Mic className="w-4 h-4" />
      case 'virtual':
        return <FileText className="w-4 h-4" />
      case 'written':
      default:
        return <MessageSquare className="w-4 h-4" />
    }
  }

  const pendingComments = comments.filter((c) => c.status === 'pending')
  const approvedComments = comments.filter((c) => c.status === 'approved' || c.status === 'read_into_record')
  const rejectedComments = comments.filter((c) => c.status === 'rejected')
  const speakerComments = comments.filter((c) => c.comment_type === 'in_person' || c.comment_type === 'virtual')

  const displayComments =
    activeTab === 'pending' ? pendingComments :
    activeTab === 'approved' ? approvedComments :
    activeTab === 'rejected' ? rejectedComments :
    activeTab === 'speakers' ? speakerComments : []

  if (loading) {
    return (
      <AdminShell title="Public Comments Management">
        <PageContainer className="py-8">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
          </div>
        </PageContainer>
      </AdminShell>
    )
  }

  return (
    <AdminShell title="Public Comments Management">
    <PageContainer className="py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
            Public Comments Management
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Review, moderate, and manage public comments for board meetings
          </p>
        </div>
      </div>

      {/* Meeting Filter */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <label htmlFor="meeting-filter" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              Filter by Meeting:
            </label>
          </div>
          <select
            id="meeting-filter"
            value={selectedMeetingId || ''}
            onChange={(e) => handleMeetingChange(e.target.value)}
            className="flex-1 max-w-md px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">{t('boardPublicCommentsAdmin.allMeetingsPendingOnly')}</option>
            {meetings.map((meeting) => (
              <option key={meeting.id} value={meeting.id}>
                {meeting.title} ({new Date(meeting.scheduled_date).toLocaleDateString()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-lsc-border dark:border-earth-700 overflow-x-auto mb-6">
        <button
          onClick={() => setActiveTab('pending')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'pending'
              ? 'border-lsc-rose text-lsc-rose'
              : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
          }`}
        >
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Pending ({pendingComments.length})
          </div>
        </button>
        <button
          onClick={() => setActiveTab('approved')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'approved'
              ? 'border-lsc-rose text-lsc-rose'
              : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
          }`}
        >
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            Approved ({approvedComments.length})
          </div>
        </button>
        <button
          onClick={() => setActiveTab('rejected')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'rejected'
              ? 'border-lsc-rose text-lsc-rose'
              : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
          }`}
        >
          <div className="flex items-center gap-2">
            <XCircle className="w-4 h-4" />
            Rejected ({rejectedComments.length})
          </div>
        </button>
        {selectedMeetingId && (
          <>
            <button
              onClick={() => setActiveTab('speakers')}
              className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'speakers'
                  ? 'border-lsc-rose text-lsc-rose'
                  : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
              }`}
            >
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4" />
                Speakers ({speakerComments.length})
              </div>
            </button>
            <button
              onClick={() => setActiveTab('periods')}
              className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'periods'
                  ? 'border-lsc-rose text-lsc-rose'
                  : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
              }`}
            >
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Comment Periods ({commentPeriods.length})
              </div>
            </button>
          </>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-900/50 rounded-lg flex gap-3 mb-6">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</p>
        </div>
      )}

      {/* Tab Content */}
      {activeTab === 'periods' && selectedMeetingId && (
        <CommentPeriodsTab
          commentPeriods={commentPeriods}
          showPeriodForm={showPeriodForm}
          setShowPeriodForm={setShowPeriodForm}
          editingPeriod={editingPeriod}
          setEditingPeriod={setEditingPeriod}
          periodForm={periodForm}
          setPeriodForm={setPeriodForm}
          submitting={submitting}
          confirmOpen={confirmOpen}
          setConfirmOpen={setConfirmOpen}
          setPendingDeletePeriodId={setPendingDeletePeriodId}
          onCreatePeriod={handleCreatePeriod}
          onStartPeriod={handleStartPeriod}
          onEndPeriod={handleEndPeriod}
          onDeletePeriod={handleDeletePeriod}
          onDeletePeriodConfirm={handleDeletePeriodConfirm}
        />
      )}

      {activeTab === 'speakers' && selectedMeetingId && (
        <SpeakersTab
          speakerComments={speakerComments}
          showSpeakerForm={showSpeakerForm}
          setShowSpeakerForm={setShowSpeakerForm}
          speakerForm={speakerForm}
          setSpeakerForm={setSpeakerForm}
          submitting={submitting}
          activeSpeaker={activeSpeaker}
          getStatusColor={getStatusColor}
          getCommentTypeIcon={getCommentTypeIcon}
          onRegisterSpeaker={handleRegisterSpeaker}
          onStartSpeaking={handleStartSpeaking}
          onStopSpeaking={handleStopSpeaking}
        />
      )}

      {activeTab !== 'periods' && activeTab !== 'speakers' && (
        <CommentsListTab
          activeTab={activeTab as 'pending' | 'approved' | 'rejected'}
          displayComments={displayComments}
          selectedComment={selectedComment}
          setSelectedComment={setSelectedComment}
          getStatusColor={getStatusColor}
          getStatusIcon={getStatusIcon}
          getCommentTypeIcon={getCommentTypeIcon}
          onModerateAction={(type, comment) => setModerationAction({ type, comment })}
          onRespond={setRespondingTo}
        />
      )}

      {/* Moderation Dialog */}
      <Modal
        isOpen={!!moderationAction}
        onClose={() => {
          setModerationAction(null)
          setModerationNotes('')
          setRejectionReason('')
        }}
        title={
          moderationAction?.type === 'approve' ? 'Approve Comment?' :
          moderationAction?.type === 'reject' ? 'Reject Comment?' :
          moderationAction?.type === 'read' ? 'Mark as Read into Record?' :
          'Delete Comment?'
        }
        size="md"
      >
      {moderationAction && (
        <>
            <p className="mb-4 text-lsc-dark/70 dark:text-lsc-cream/70">
              {moderationAction.type === 'approve'
                ? 'This comment will be approved and may be displayed publicly.'
                : moderationAction.type === 'reject'
                ? 'This comment will be rejected and will not be displayed.'
                : moderationAction.type === 'read'
                ? 'This comment will be marked as having been read into the official record.'
                : 'This comment will be permanently deleted. This action cannot be undone.'}
            </p>
            {moderationAction.type !== 'delete' && (
              <div className="mb-4">
                <label htmlFor="moderation-notes" className="block text-sm font-medium mb-2 text-lsc-dark dark:text-lsc-cream">
                  {moderationAction.type === 'reject' ? 'Rejection Reason' : 'Notes'} (optional)
                </label>
                {moderationAction.type === 'reject' && (
                  <input
                    id="rejection-reason"
                    type="text"
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm mb-2"
                    placeholder={t('boardPublicCommentsAdmin.briefReasonForRejection')}
                  />
                )}
                <textarea
                  id="moderation-notes"
                  value={moderationNotes}
                  onChange={(e) => setModerationNotes(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
                  placeholder={t('boardPublicCommentsAdmin.addAnyNotesAboutThis')}
                />
              </div>
            )}
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setModerationAction(null)
                  setModerationNotes('')
                  setRejectionReason('')
                }}
                disabled={submitting}
                className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleModerateComment}
                disabled={submitting}
                className={`px-4 py-2 rounded-lg text-white disabled:opacity-50 ${
                  moderationAction.type === 'reject' || moderationAction.type === 'delete'
                    ? 'bg-status-danger-600 hover:bg-status-danger-700'
                    : 'bg-lsc-rose hover:bg-lsc-rose/90'
                }`}
              >
                {submitting ? 'Processing...' : (
                  moderationAction.type === 'approve' ? 'Approve' :
                  moderationAction.type === 'reject' ? 'Reject' :
                  moderationAction.type === 'read' ? 'Mark as Read' :
                  'Delete'
                )}
              </button>
            </div>
        </>
      )}
      </Modal>

      {/* Staff Response Dialog */}
      <Modal
        isOpen={!!respondingTo}
        onClose={() => {
          setRespondingTo(null)
          setStaffResponse('')
        }}
        title="Add Staff Response"
        size="md"
      >
      {respondingTo && (
        <>
            <p className="mb-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Add an official staff response to this comment. This may be shared with the commenter and/or included in meeting records.
            </p>
            <textarea
              id="staff-response"
              aria-label="Staff response"
              value={staffResponse}
              onChange={(e) => setStaffResponse(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm mb-4"
              placeholder={t('placeholder.boardPublicCommentsAdmin.enterYourResponse')}
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setRespondingTo(null)
                  setStaffResponse('')
                }}
                disabled={submitting}
                className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleStaffResponse}
                disabled={submitting}
                className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Submit Response'}
              </button>
            </div>
        </>
      )}
      </Modal>
    </PageContainer>
    </AdminShell>
  )
}
