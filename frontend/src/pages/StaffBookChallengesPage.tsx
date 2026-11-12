/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, Filter, ChevronLeft, ChevronRight, Loader2,
  Eye, Edit, MessageSquare, BarChart3, BookOpen, AlertTriangle
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import {
  getChallenges,
  getChallenge,
  createChallenge,
  updateChallenge,
  addChallengeNote,
  getChallengeStats,
  CHALLENGE_STATUS_LABELS,
  CHALLENGE_OUTCOME_LABELS,
  CHALLENGE_REASON_LABELS,
  type BookChallenge,
  type BookChallengeDetail,
  type BookChallengeCreate,
  type BookChallengeUpdate,
  type ChallengeStatus,
  type ChallengeOutcome,
  type ChallengeReason,
} from '../api/api'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { formatEnumLabel } from '@/utils/format-utils'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { ChallengeRationaleViewer } from '@/components/challenges/ChallengeRationaleViewer'
import PageContainer from '@/components/layout/PageContainer'

const STATUS_OPTIONS: ChallengeStatus[] = [
  'received', 'under_review', 'committee_review', 'board_review',
  'resolved_retained', 'resolved_restricted', 'resolved_removed', 'withdrawn'
]

const OUTCOME_OPTIONS: ChallengeOutcome[] = [
  'pending', 'retained', 'retained_with_changes', 'restricted', 'removed', 'withdrawn'
]

const REASON_OPTIONS: ChallengeReason[] = [
  'sexual_content', 'lgbtq_content', 'violence', 'language',
  'religious_viewpoint', 'political_viewpoint', 'age_inappropriate',
  'racism', 'drugs_alcohol', 'anti_family', 'occult_supernatural', 'other'
]

export default function StaffBookChallengesPage() {
  const { t } = useTranslation()
  const { accessToken } = useAuth()
  const queryClient = useQueryClient()

  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<ChallengeStatus | ''>('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [selectedChallenge, setSelectedChallenge] = useState<BookChallengeDetail | null>(null)
  const [newNote, setNewNote] = useState('')

  const perPage = 20

  // Fetch challenges
  const { data: challengesData, isLoading } = useQuery({
    queryKey: ['staffChallenges', page, statusFilter],
    queryFn: () => getChallenges(accessToken!, clean({ page, perPage, status: statusFilter || undefined })),
    enabled: !!accessToken,
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['staffChallengeStats'],
    queryFn: () => getChallengeStats(accessToken!),
    enabled: !!accessToken,
  })

  // Create challenge mutation
  const createMutation = useMutation({
    mutationFn: (data: BookChallengeCreate) => createChallenge(accessToken!, data),
    onSuccess: () => {
      toast.success(t('toast.staffBookChallenges.challengeCreated'))
      queryClient.invalidateQueries({ queryKey: ['staffChallenges'] })
      queryClient.invalidateQueries({ queryKey: ['staffChallengeStats'] })
      setShowCreateModal(false)
    },
    onError: () => toast.error(t('staffBookChallenges.failedToCreateChallenge')),
  })

  // Update challenge mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: BookChallengeUpdate }) =>
      updateChallenge(accessToken!, id, data),
    onSuccess: () => {
      toast.success(t('toast.staffBookChallenges.challengeUpdated'))
      queryClient.invalidateQueries({ queryKey: ['staffChallenges'] })
      queryClient.invalidateQueries({ queryKey: ['staffChallengeStats'] })
      if (selectedChallenge) {
        loadChallengeDetail(selectedChallenge.id)
      }
    },
    onError: () => toast.error(t('staffBookChallenges.failedToUpdateChallenge')),
  })

  // Add note mutation
  const addNoteMutation = useMutation({
    mutationFn: ({ challengeId, note }: { challengeId: number; note: string }) =>
      addChallengeNote(accessToken!, challengeId, note, true),
    onSuccess: () => {
      toast.success(t('toast.staffBookChallenges.noteAdded'))
      setNewNote('')
      if (selectedChallenge) {
        loadChallengeDetail(selectedChallenge.id)
      }
    },
    onError: () => toast.error(t('staffBookChallenges.failedToAddNote')),
  })

  const loadChallengeDetail = useCallback(async (id: number) => {
    try {
      const detail = await getChallenge(accessToken!, id)
      setSelectedChallenge(detail)
      setShowDetailModal(true)
    } catch {
      toast.error(t('staffBookChallenges.failedToLoadChallengeDetails'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken])

  const getStatusColor = (status: ChallengeStatus) => {
    if (status.startsWith('RESOLVED')) return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
    if (status === 'withdrawn') return 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
    if (status === 'board_review') return 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
    if (status === 'committee_review') return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    return 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
  }

  return (
    <PageContainer width="wide" className="py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
            <AlertTriangle className="w-8 h-8 text-lsc-rose" />
            Book Challenge Tracking
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Manage and track formal challenges to library materials
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Challenge
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-5 h-5 text-lsc-rose" />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total</span>
            </div>
            <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {stats.total_challenges}
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-2 mb-2">
              <Loader2 className="w-5 h-5 text-earth-600" />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Pending</span>
            </div>
            <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
              {stats.pending_challenges}
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-5 h-5 text-status-success-500" />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Retained</span>
            </div>
            <div className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
              {(stats.outcomes?.RETAINED || 0) + (stats.outcomes?.RETAINED_WITH_CHANGES || 0)}
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-5 h-5 text-status-warning-500" />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">This Year</span>
            </div>
            <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {stats.resolved_this_year}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Filter:</span>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as ChallengeStatus | '')
              setPage(1)
            }}
            aria-label={t('staffBookChallenges.filterByChallengeStatus')}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Statuses</option>
            {STATUS_OPTIONS.map(status => (
              <option key={status} value={status}>{CHALLENGE_STATUS_LABELS[status]}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Challenges Table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : challengesData && challengesData.items.length > 0 ? (
          <>
            <table className="w-full">
              <thead className="bg-lsc-cream dark:bg-earth-700">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-lsc-dark dark:text-lsc-cream">Title</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-lsc-dark dark:text-lsc-cream">Author</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-lsc-dark dark:text-lsc-cream">Reason</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-lsc-dark dark:text-lsc-cream">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-lsc-dark dark:text-lsc-cream">Date</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-lsc-dark dark:text-lsc-cream">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {challengesData.items.map((challenge: BookChallenge) => (
                  <tr key={challenge.id} className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {challenge.title}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {challenge.author || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-earth-700 rounded">
                        {(() => {
                          const k = formatEnumLabel(challenge.primary_reason) as ChallengeReason
                          return CHALLENGE_REASON_LABELS[k] || k
                        })()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {(() => {
                        const k = formatEnumLabel(challenge.status) as ChallengeStatus
                        return (
                          <span className={`text-xs px-2 py-1 rounded-full font-medium ${getStatusColor(k)}`}>
                            {CHALLENGE_STATUS_LABELS[k] || k}
                          </span>
                        )
                      })()}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {new Date(challenge.date_received).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => loadChallengeDetail(challenge.id)}
                        className="p-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-lsc-border dark:border-earth-700">
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Showing {((page - 1) * perPage) + 1} - {Math.min(page * perPage, challengesData.total)} of {challengesData.total}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Page {page} of {challengesData.pages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(challengesData.pages, p + 1))}
                  disabled={page >= challengesData.pages}
                  className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="p-12 text-center">
            <AlertTriangle className="w-12 h-12 text-lsc-rose/50 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              No Challenges Found
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              {statusFilter ? 'No challenges match this filter.' : 'No challenges have been recorded yet.'}
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
            >
              <Plus className="w-5 h-5" />
              Record First Challenge
            </button>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <CreateChallengeModal
          onClose={() => setShowCreateModal(false)}
          onCreate={(data) => createMutation.mutate(data)}
          isLoading={createMutation.isPending}
        />
      )}

      {/* Detail Modal */}
      {showDetailModal && selectedChallenge && (
        <ChallengeDetailModal
          challenge={selectedChallenge}
          onClose={() => {
            setShowDetailModal(false)
            setSelectedChallenge(null)
          }}
          onUpdate={(data) => updateMutation.mutate({ id: selectedChallenge.id, data })}
          onAddNote={(note) => addNoteMutation.mutate({ challengeId: selectedChallenge.id, note })}
          newNote={newNote}
          setNewNote={setNewNote}
          isUpdating={updateMutation.isPending}
          isAddingNote={addNoteMutation.isPending}
        />
      )}
    </PageContainer>
  )
}

// Create Challenge Modal
function CreateChallengeModal({
  onClose,
  onCreate,
  isLoading,
}: {
  onClose: () => void
  onCreate: (data: BookChallengeCreate) => void
  isLoading: boolean
}) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState<BookChallengeCreate>({
    title: '',
    author: '',
    isbn: '',
    primary_reason: 'other',
    challenger_complaint: '',
    challenger_name: '',
    challenger_is_patron: true,
    challenger_contact: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onCreate(formData)
  }

  return (
    <ModalBackdrop onClose={onClose} title="Record New Challenge">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Record New Challenge
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="challenge-form-title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Book Title *
              </label>
              <input
                id="challenge-form-title"
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="challenge-form-author" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Author
              </label>
              <input
                id="challenge-form-author"
                type="text"
                value={formData.author || ''}
                onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </div>

          <div>
            <label htmlFor="challenge-form-reason" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Primary Reason for Challenge *
            </label>
            <select
              id="challenge-form-reason"
              required
              value={formData.primary_reason}
              onChange={(e) => setFormData({ ...formData, primary_reason: e.target.value as ChallengeReason })}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            >
              {REASON_OPTIONS.map(reason => (
                <option key={reason} value={reason}>{CHALLENGE_REASON_LABELS[reason]}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="challenge-form-complaint" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Challenger's Complaint
            </label>
            <textarea
              id="challenge-form-complaint"
              rows={3}
              value={formData.challenger_complaint || ''}
              onChange={(e) => setFormData({ ...formData, challenger_complaint: e.target.value })}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('staffBookChallenges.summaryOfTheChallengerS')}
            />
          </div>

          <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">
              Challenger Information (Optional)
            </h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="challenge-form-challenger-name" className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Name
                </label>
                <input
                  id="challenge-form-challenger-name"
                  type="text"
                  value={formData.challenger_name || ''}
                  onChange={(e) => setFormData({ ...formData, challenger_name: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label htmlFor="challenge-form-challenger-contact" className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Contact
                </label>
                <input
                  id="challenge-form-challenger-contact"
                  type="text"
                  value={formData.challenger_contact || ''}
                  onChange={(e) => setFormData({ ...formData, challenger_contact: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('placeholder.staffBookChallenges.emailOrPhone')}
                />
              </div>
            </div>
            <label className="flex items-center gap-2 mt-3">
              <input
                type="checkbox"
                checked={formData.challenger_is_patron}
                onChange={(e) => setFormData({ ...formData, challenger_is_patron: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Challenger is a library patron
              </span>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Create Challenge
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}

// Challenge Detail Modal
function ChallengeDetailModal({
  challenge,
  onClose,
  onUpdate,
  onAddNote,
  newNote,
  setNewNote,
  isUpdating,
  isAddingNote,
}: {
  challenge: BookChallengeDetail
  onClose: () => void
  onUpdate: (data: BookChallengeUpdate) => void
  onAddNote: (note: string) => void
  newNote: string
  setNewNote: (note: string) => void
  isUpdating: boolean
  isAddingNote: boolean
}) {
  const [editMode, setEditMode] = useState(false)
  const [editData, setEditData] = useState<BookChallengeUpdate>({
    status: challenge.status,
    outcome: challenge.outcome,
    resolution_summary: challenge.resolution_summary,
    is_public: challenge.is_public,
    public_title: challenge.public_title,
    public_summary: challenge.public_summary,
    lessons_learned: challenge.lessons_learned,
  })

  const handleSave = () => {
    onUpdate(editData)
    setEditMode(false)
  }

  return (
    <ModalBackdrop onClose={onClose} title="Challenge Details">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <div>
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {challenge.title}
            </h2>
            {challenge.author && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">by {challenge.author}</p>
            )}
          </div>
          <button
            onClick={() => setEditMode(!editMode)}
            className="p-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <Edit className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Status & Outcome */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="challenge-detail-status" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Status
              </label>
              {editMode ? (
                <select
                  id="challenge-detail-status"
                  value={editData.status || challenge.status}
                  onChange={(e) => setEditData({ ...editData, status: e.target.value as ChallengeStatus })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                >
                  {STATUS_OPTIONS.map(status => (
                    <option key={status} value={status}>{CHALLENGE_STATUS_LABELS[status]}</option>
                  ))}
                </select>
              ) : (
                <span className="text-lsc-dark dark:text-lsc-cream">
                  {(() => {
                    const k = formatEnumLabel(challenge.status) as ChallengeStatus
                    return CHALLENGE_STATUS_LABELS[k] || k
                  })()}
                </span>
              )}
            </div>
            <div>
              <label htmlFor="challenge-detail-outcome" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Outcome
              </label>
              {editMode ? (
                <select
                  id="challenge-detail-outcome"
                  value={editData.outcome || challenge.outcome}
                  onChange={(e) => setEditData({ ...editData, outcome: e.target.value as ChallengeOutcome })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                >
                  {OUTCOME_OPTIONS.map(outcome => (
                    <option key={outcome} value={outcome}>{CHALLENGE_OUTCOME_LABELS[outcome]}</option>
                  ))}
                </select>
              ) : (
                <span className="text-lsc-dark dark:text-lsc-cream">
                  {(() => {
                    const k = formatEnumLabel(challenge.outcome) as ChallengeOutcome
                    return CHALLENGE_OUTCOME_LABELS[k] || k
                  })()}
                </span>
              )}
            </div>
          </div>

          {/* Challenge Details */}
          <div>
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Challenge Details
            </h3>
            <div className="bg-lsc-cream dark:bg-earth-700 rounded-lg p-4 space-y-2 text-sm">
              <div><strong>Reason:</strong> {(() => {
                const k = formatEnumLabel(challenge.primary_reason) as ChallengeReason
                return CHALLENGE_REASON_LABELS[k] || k
              })()}</div>
              <div><strong>Date Received:</strong> {new Date(challenge.date_received).toLocaleDateString()}</div>
              {challenge.date_resolved && (
                <div><strong>Date Resolved:</strong> {new Date(challenge.date_resolved).toLocaleDateString()}</div>
              )}
              {challenge.challenger_complaint && (
                <div><strong>Complaint:</strong> {challenge.challenger_complaint}</div>
              )}
            </div>
          </div>

          {/* M3: Acquisition rationale (anti-banning defense surface) */}
          <div className="bg-lsc-cream dark:bg-earth-700 rounded-lg p-4 text-sm">
            <ChallengeRationaleViewer
              rationale={challenge.acquisition_rationale}
              challengeReason={challenge.primary_reason as ChallengeReason}
            />
          </div>

          {/* Resolution Summary */}
          <div>
            <label htmlFor="challenge-detail-resolution-summary" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Resolution Summary
            </label>
            {editMode ? (
              <textarea
                id="challenge-detail-resolution-summary"
                rows={3}
                value={editData.resolution_summary || ''}
                onChange={(e) => setEditData({ ...editData, resolution_summary: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            ) : (
              <p className="text-lsc-dark/80 dark:text-lsc-cream/90">
                {challenge.resolution_summary || 'No resolution summary yet.'}
              </p>
            )}
          </div>

          {/* Public Story Settings */}
          {editMode && (
            <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
              <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">
                Public Story (for Banned Books page)
              </h3>
              <label className="flex items-center gap-2 mb-3">
                <input
                  type="checkbox"
                  checked={editData.is_public}
                  onChange={(e) => setEditData({ ...editData, is_public: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Make this challenge story public
                </span>
              </label>
              {editData.is_public && (
                <div className="space-y-3">
                  <div>
                    <label htmlFor="challenge-detail-public-title" className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Public Title (optional, defaults to book title)
                    </label>
                    <input
                      id="challenge-detail-public-title"
                      type="text"
                      value={editData.public_title || ''}
                      onChange={(e) => setEditData({ ...editData, public_title: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label htmlFor="challenge-detail-public-summary" className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Public Summary
                    </label>
                    <textarea
                      id="challenge-detail-public-summary"
                      rows={2}
                      value={editData.public_summary || ''}
                      onChange={(e) => setEditData({ ...editData, public_summary: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label htmlFor="challenge-detail-lessons-learned" className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Lessons Learned
                    </label>
                    <textarea
                      id="challenge-detail-lessons-learned"
                      rows={2}
                      value={editData.lessons_learned || ''}
                      onChange={(e) => setEditData({ ...editData, lessons_learned: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Notes Section */}
          <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Notes & Timeline
            </h3>
            <div className="space-y-3 mb-4">
              {challenge.notes && challenge.notes.length > 0 ? (
                challenge.notes.map((note) => (
                  <div key={note.id} className="bg-lsc-cream dark:bg-earth-700 rounded-lg p-3">
                    <p className="text-sm text-lsc-dark dark:text-lsc-cream">{note.note}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {note.created_at ? new Date(note.created_at).toLocaleString() : 'Just now'}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No notes yet.</p>
              )}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder={t('placeholder.staffBookChallenges.addANote')}
                aria-label={t('aria.staffBookChallenges.addANote', 'Add a note')}
                className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
              <button
                onClick={() => newNote && onAddNote(newNote)}
                disabled={!newNote || isAddingNote}
                className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                {isAddingNote ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : 'Add'}
              </button>
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            Close
          </button>
          {editMode && (
            <button
              onClick={handleSave}
              disabled={isUpdating}
              className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2"
            >
              {isUpdating && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Save Changes
            </button>
          )}
        </div>
      </div>
    </ModalBackdrop>

  )
}
