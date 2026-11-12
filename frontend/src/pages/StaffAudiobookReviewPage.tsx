/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Audiobook Review Page
 * Review queue for submitted audiobooks with audio playback and approval workflow
 */

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api-client';
import {
  Loader2,
  AlertCircle,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  User,
  FileAudio,
  Volume2,
  Headphones,
} from 'lucide-react'
import toast from 'react-hot-toast'
function formatDurationFriendly(seconds: number): string { const h = Math.floor(seconds / 3600); const m = Math.floor((seconds % 3600) / 60); return h > 0 ? `${h}h ${m}m` : `${m}m`; }
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTranslation} from '@/i18n'
import { formatGenre } from '@/utils/format-utils'
import { AdminShell } from '../components/shells/AdminShell'

async function getAudiobooksForReview() {
  return api.get('/staff/audiobooks/review-queue?status=submitted&limit=20')
}

async function approveAudiobook(audiobook_id: number, notes?: string) {
  return api.post(`/staff/audiobooks/${audiobook_id}/approve`, { notes })
}

async function rejectAudiobook(audiobook_id: number, reason: string, notes?: string) {
  return api.post(`/staff/audiobooks/${audiobook_id}/reject`, { rejection_reason: reason, notes })
}

async function requestRevision(audiobook_id: number, requested_changes: string, notes?: string) {
  return api.post(`/staff/audiobooks/${audiobook_id}/request-revision`, { requested_changes, notes })
}

interface AudiobookReview {
  id: number
  title: string
  author_pen_name: string
  narrator_name: string
  description: string
  genre: string
  content_rating: string
  duration_seconds: number
  file_format: string
  file_size_bytes: number
  submitted_at: string
  stream_url: string
  ai_quality_score: number
}

function ReviewCard({ audiobook, onAction }: {
  audiobook: AudiobookReview
  onAction: (action: 'approve' | 'reject' | 'revision', notes?: string) => void
}) {
  const { t } = useTranslation()
  const [isPlaying, setIsPlaying] = useState(false)
  const [showActions, setShowActions] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')
  const [revisionNotes, setRevisionNotes] = useState('')
  const [approvalNotes, setApprovalNotes] = useState('')

  const fileSizeMB = (audiobook.file_size_bytes / 1024 / 1024).toFixed(2)
  const qualityBadge = audiobook.ai_quality_score > 0.8 ? 'High' : audiobook.ai_quality_score > 0.6 ? 'Good' : 'Low'
  const qualityColor = audiobook.ai_quality_score > 0.8 ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-200' : audiobook.ai_quality_score > 0.6 ? 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light/80' : 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-200'

  return (
    <Card className="mb-4">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lsc-dark dark:text-lsc-cream">{audiobook.title}</CardTitle>
            <div className="flex items-center gap-3 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <User className="w-4 h-4" />
              <span>{audiobook.author_pen_name}</span>
              {audiobook.narrator_name && (
                <>
                  <Headphones className="w-4 h-4" />
                  <span>Narrated by {audiobook.narrator_name}</span>
                </>
              )}
            </div>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${qualityColor}`}>
            Quality: {qualityBadge}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Description Preview */}
        <div>
          <h4 className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm mb-2">Description</h4>
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 line-clamp-2" title={audiobook.description}>
            {audiobook.description}
          </p>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-3 bg-lsc-cream dark:bg-earth-800 rounded-lg">
          <div>
            <div className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Genre</div>
            <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{formatGenre(audiobook.genre)}</div>
          </div>
          <div>
            <div className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Duration</div>
            <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
              {formatDurationFriendly(audiobook.duration_seconds)}
            </div>
          </div>
          <div>
            <div className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Format</div>
            <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{audiobook.file_format}</div>
          </div>
          <div>
            <div className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Size</div>
            <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{fileSizeMB}MB</div>
          </div>
          <div>
            <div className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Rating</div>
            <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{audiobook.content_rating}</div>
          </div>
        </div>

        {/* Audio Player Preview */}
        <div className="bg-lsc-dark/5 dark:bg-earth-700 p-4 rounded-lg flex items-center gap-4">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            aria-label={isPlaying ? t('aria.staffAudiobookReview.pausePreview', 'Pause preview') : t('aria.staffAudiobookReview.playPreview', 'Play preview')}
            aria-pressed={isPlaying}
            className="p-3 bg-lsc-rose text-white rounded-full hover:bg-lsc-rose/90 transition-colors"
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          </button>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Preview audio quality</p>
            <div className="h-1 bg-lsc-dark/10 dark:bg-earth-700 rounded-full mt-2 overflow-hidden">
              <div className="h-full w-1/4 bg-lsc-rose"></div>
            </div>
          </div>
          <Volume2 className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
        </div>

        {/* Submission Info */}
        <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <Clock className="w-4 h-4" />
          <span>Submitted {new Date(audiobook.submitted_at).toLocaleDateString()}</span>
        </div>

        {/* Action Section */}
        <div className="space-y-3 pt-4 border-t border-lsc-border dark:border-earth-700">
          {!showActions ? (
            <Button
              onClick={() => setShowActions(true)}
              className="w-full bg-lsc-rose hover:bg-lsc-rose/90 text-white"
            >
              Review This Audiobook
            </Button>
          ) : (
            <div className="space-y-3">
              {/* Approval Section */}
              <div className="bg-status-success-50 dark:bg-status-success-900/20 p-3 rounded-lg border border-status-success-200 dark:border-status-success-800">
                <h4 className="font-medium text-status-success-800 dark:text-status-success-200 text-sm mb-2 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  Approve
                </h4>
                <textarea
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder={t('placeholder.staffAudiobookReview.optionalApprovalNotes')}
                  aria-label={t('aria.staffAudiobookReview.approvalNotes', 'Approval notes')}
                  className="w-full text-sm p-2 border border-status-success-200 dark:border-status-success-800 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 mb-2 h-16"
                />
                <Button
                  onClick={() => onAction('approve')}
                  variant="outline"
                  className="w-full text-status-success-700 dark:text-status-success-200 border-status-success-200 dark:border-status-success-800 hover:bg-status-success-50 dark:bg-status-success-900/20 dark:hover:bg-status-success-900/30 text-sm"
                >
                  Approve Audiobook
                </Button>
              </div>

              {/* Revision Section */}
              <div className="bg-status-warning-50 dark:bg-status-warning-900/20 p-3 rounded-lg border border-status-warning-200 dark:border-status-warning-800">
                <h4 className="font-medium text-status-warning-800 dark:text-status-warning-200 text-sm mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Request Revision
                </h4>
                <textarea
                  value={revisionNotes}
                  onChange={(e) => setRevisionNotes(e.target.value)}
                  placeholder={t('staffAudiobookReview.whatNeedsToBeRevised')}
                  aria-label={t('aria.staffAudiobookReview.requestedChanges', 'Requested changes')}
                  className="w-full text-sm p-2 border border-status-warning-200 dark:border-status-warning-800 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 mb-2 h-16"
                />
                <Button
                  onClick={() => onAction('revision')}
                  variant="outline"
                  className="w-full text-status-warning-700 dark:text-status-warning-200 border-status-warning-200 dark:border-status-warning-800 hover:bg-status-warning-50 dark:bg-status-warning-900/20 dark:hover:bg-status-warning-900/30 text-sm"
                  disabled={!revisionNotes.trim()}
                >
                  Request Revision
                </Button>
              </div>

              {/* Rejection Section */}
              <div className="bg-status-danger-50 dark:bg-status-danger-900/20 p-3 rounded-lg border border-status-danger-200 dark:border-status-danger-800">
                <h4 className="font-medium text-status-danger-800 dark:text-status-danger-200 text-sm mb-2 flex items-center gap-2">
                  <XCircle className="w-4 h-4" />
                  Reject
                </h4>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder={t('staffAudiobookReview.whyIsThisAudiobookBeing')}
                  aria-label={t('aria.staffAudiobookReview.rejectionReason', 'Rejection reason')}
                  className="w-full text-sm p-2 border border-status-danger-200 dark:border-status-danger-800 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 mb-2 h-16"
                />
                <Button
                  onClick={() => onAction('reject')}
                  variant="outline"
                  className="w-full text-status-danger-700 dark:text-status-danger-200 border-status-danger-200 dark:border-status-danger-800 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/30 text-sm"
                  disabled={!rejectionReason.trim()}
                >
                  Reject Audiobook
                </Button>
              </div>

              <Button
                onClick={() => setShowActions(false)}
                variant="outline"
                className="w-full"
              >
                Cancel
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function StaffAudiobookReviewPage() {
  const { t } = useTranslation()
  const { data: audiobooks, isLoading, error, refetch } = useQuery({
    queryKey: ['audiobooks-review-queue'],
    queryFn: getAudiobooksForReview,
  })

  const approveMutation = useMutation({
    mutationFn: (data: { audiobook_id: number; notes?: string }) =>
      approveAudiobook(data.audiobook_id, data.notes),
    onSuccess: () => {
      toast.success(t('toast.staffAudiobookReview.audiobookApproved'))
      refetch()
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.staffAudiobookReview.failedToApprove'))
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (data: { audiobook_id: number; reason: string; notes?: string }) =>
      rejectAudiobook(data.audiobook_id, data.reason, data.notes),
    onSuccess: () => {
      toast.success(t('toast.staffAudiobookReview.audiobookRejected'))
      refetch()
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.staffAudiobookReview.failedToReject'))
    },
  })

  const revisionMutation = useMutation({
    mutationFn: (data: { audiobook_id: number; changes: string; notes?: string }) =>
      requestRevision(data.audiobook_id, data.changes, data.notes),
    onSuccess: () => {
      toast.success(t('toast.staffAudiobookReview.revisionRequested'))
      refetch()
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.staffAudiobookReview.failedToRequestRevision'))
    },
  })

  const handleAction = (audiobook_id: number, action: 'approve' | 'reject' | 'revision', notes: string) => {
    if (action === 'approve') {
      approveMutation.mutate({ audiobook_id, notes })
    } else if (action === 'reject') {
      rejectMutation.mutate({ audiobook_id, reason: notes })
    } else if (action === 'revision') {
      revisionMutation.mutate({ audiobook_id, changes: notes })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-6 flex gap-4">
        <AlertCircle className="w-6 h-6 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
        <div>
          <h2 className="font-serif font-semibold text-status-danger-800 dark:text-status-danger-200">{t('staffAudiobookReview.errorLoadingReviewQueue')}</h2>
          <p className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
        </div>
      </div>
    )
  }

  return (

    <AdminShell title="Audiobook Review Queue">    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Audiobook Review Queue
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {audiobooks?.length || 0} audiobook{audiobooks?.length !== 1 ? 's' : ''} awaiting review
        </p>
      </div>

      {/* Review Queue */}
      {audiobooks && audiobooks.length > 0 ? (
        <div>
          {audiobooks.map((audiobook: AudiobookReview) => (
            <ReviewCard
              key={audiobook.id}
              audiobook={audiobook}
              onAction={(action: 'approve' | 'reject' | 'revision', notes?: string) => handleAction(audiobook.id, action, notes || '')}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12">
            <FileAudio className="w-16 h-16 mx-auto mb-4 text-lsc-dark/20 dark:text-lsc-cream/20" />
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              No audiobooks to review
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              All audiobooks have been reviewed! Great work.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  </AdminShell>
  )
}