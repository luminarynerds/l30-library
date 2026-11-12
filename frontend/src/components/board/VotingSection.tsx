/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '@/api/types';
import {
  Plus,
  Trash2,
  Vote,
  Loader2,
  AlertCircle,
  CheckCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import ConfirmDialog from '../ConfirmDialog'
import VotingForm from './VotingForm'
import VotingDetailModal from './VotingDetailModal'
import api from '../../api/api'
import { useTranslation} from '@/i18n'
import type { components } from '@/api/generated/schema'

// Backend-sourced base type (generated from BoardVoteResponse Pydantic schema).
// Refresh with `npm run codegen` after backend schema changes.
type BoardVoteResponse = components['schemas']['BoardVoteResponse']

// VoteItem is a UI view-model. Backend fields (id/title/description/vote_type/
// opens_at/closes_at/quorum_required) are tightened to the generated type;
// the remaining fields are derived in the component (tally counts, user_vote,
// created_date alias, due_date) and stay hand-written.
//
// `status` is narrowed to the three values this component handles. Backend
// BoardVoteResponse types it as `string`; if backend adds a new state, tsc
// won't catch it here — that's deliberate, the component only renders these.
export interface VoteItem
  extends Omit<BoardVoteResponse, 'status'> {
  status: 'open' | 'closed' | 'pending'
  // Derived/UI-only fields
  created_date: string
  due_date?: string
  votes_for?: number
  votes_against?: number
  votes_abstain?: number
  user_vote?: 'FOR' | 'AGAINST' | 'ABSTAIN' | null
}

interface VotingSectionProps {
  token: string | null
  userRole: string
}

export default function VotingSection({
  token,
  userRole,
}: VotingSectionProps): React.ReactElement {
  const { t } = useTranslation()
  const [votes, setVotes] = useState<VoteItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingVote, setEditingVote] = useState<VoteItem | null>(null)
  const [selectedVote, setSelectedVote] = useState<VoteItem | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; title: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [filterStatus, setFilterStatus] = useState<VoteItem['status'] | 'ALL'>('ALL')
  const [pendingVote, setPendingVote] = useState<{ voteId: number; choice: 'yes' | 'no' | 'abstain'; title: string } | null>(null)

  const isAdmin = ['admin', 'super_admin'].includes(userRole)

  const fetchVotes = useCallback(async () => {
    if (!token) return

    try {
      setLoading(true)
      setError(null)
      const data = await api.get(`${API_BASE}/board/votes`)
      if (data && typeof data === 'object') {
        const votes = Array.isArray(data) ? data : (data.votes || [])
        votes.sort((a: { created_date?: string }, b: { created_date?: string }) => new Date(b.created_date ?? '').getTime() - new Date(a.created_date ?? '').getTime())
        setVotes(votes)
      }
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to fetch votes'
      setError(message)
      toast.error(message)
      setVotes([])
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchVotes()
  }, [fetchVotes])

  const handleAddVote = async (formData: unknown) => {
    if (!token) return

    try {
      setSubmitting(true)
      await api.post(`${API_BASE}/board/votes`, formData)
      toast.success(t('components.board.votingSection.voteItemCreatedSuccessfully'))
      setShowForm(false)
      await fetchVotes()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to create vote'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteVote = async () => {
    if (!token || !deleteConfirm) return

    try {
      setSubmitting(true)
      await api.delete(`${API_BASE}/board/votes/${deleteConfirm.id}`)
      toast.success(t('toast.board.voteDeletedSuccessfully'))
      setDeleteConfirm(null)
      await fetchVotes()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to delete vote'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleCastVote = async (voteId: number, choice: 'yes' | 'no' | 'abstain') => {
    if (!token) return

    try {
      await api.post(`${API_BASE}/board/votes/${voteId}/cast`, { choice })
      toast.success(t('components.board.votingSection.yourVoteHasBeenRecorded'))
      await fetchVotes()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to record vote'
      toast.error(message)
    }
  }

  const getStatusColor = (status: VoteItem['status']) => {
    switch (status) {
      case 'open':
        return 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
      case 'closed':
        return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
      case 'pending':
        return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
      default:
        return 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
    }
  }

  const filteredVotes = filterStatus === 'ALL' ? votes : votes.filter((v) => v.status === filterStatus)

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
            Board Voting
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {votes.length} vote items on record
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => {
              setEditingVote(null)
              setShowForm(true)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Vote
          </button>
        )}
      </div>

      {/* Status Filter */}
      <div className="flex flex-wrap gap-2">
        {(['ALL', 'open', 'closed', 'pending'] as const).map((status) => (
          <button
            key={status}
            onClick={() => setFilterStatus(status)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filterStatus === status
                ? 'bg-lsc-rose text-white'
                : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600'
            }`}
          >
            {status.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-900/50 rounded-lg flex gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</p>
        </div>
      )}

      {/* Votes List */}
      <div className="space-y-4">
        {filteredVotes.length === 0 ? (
          <div className="p-8 text-center bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
            <Vote className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {filterStatus !== 'ALL'
                ? `No ${filterStatus.toLowerCase()} votes`
                : 'No voting items'}
            </p>
          </div>
        ) : (
          filteredVotes.map((vote) => {
            const totalVotes = (vote.votes_for || 0) + (vote.votes_against || 0) + (vote.votes_abstain || 0)
            const forPercent = totalVotes > 0 ? ((vote.votes_for || 0) / totalVotes) * 100 : 0
            const againstPercent = totalVotes > 0 ? ((vote.votes_against || 0) / totalVotes) * 100 : 0
            const abstainPercent = totalVotes > 0 ? ((vote.votes_abstain || 0) / totalVotes) * 100 : 0

            return (
              <div
                key={vote.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6"
              >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                        {vote.title}
                      </h3>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                          vote.status
                        )}`}
                      >
                        {vote.status}
                      </span>
                    </div>
                    {vote.description && (
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                        {vote.description}
                      </p>
                    )}
                  </div>

                  {isAdmin && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedVote(vote)}
                        className="px-3 py-1 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600 rounded-lg transition-colors"
                      >
                        Details
                      </button>
                      <button
                        onClick={() =>
                          setDeleteConfirm({
                            id: vote.id,
                            title: vote.title,
                          })
                        }
                        className="p-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                        aria-label={`Delete vote ${vote.title}`}
                      >
                        <Trash2 className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Vote Results */}
                <div className="space-y-3 mb-4">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-status-success-700 dark:text-status-success-300">
                        For ({vote.votes_for || 0})
                      </span>
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {forPercent.toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2">
                      <div
                        className="bg-status-success-600 h-2 rounded-full"
                        style={{ width: `${forPercent}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-status-danger-700 dark:text-status-danger-300">
                        Against ({vote.votes_against || 0})
                      </span>
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {againstPercent.toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2">
                      <div
                        className="bg-status-danger-600 h-2 rounded-full"
                        style={{ width: `${againstPercent}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-status-warning-700 dark:text-status-warning-300">
                        Abstain ({vote.votes_abstain || 0})
                      </span>
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {abstainPercent.toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2">
                      <div
                        className="bg-status-warning-600 h-2 rounded-full"
                        style={{ width: `${abstainPercent}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Vote Buttons */}
                {vote.status === 'open' && !vote.user_vote && (
                  <div className="flex gap-2 pt-4 border-t border-lsc-border dark:border-earth-700">
                    <button
                      onClick={() => setPendingVote({ voteId: vote.id, choice: 'yes', title: vote.title })}
                      aria-label={`Vote for on: ${vote.title}`}
                      className="flex-1 px-3 py-2 bg-status-success-100 hover:bg-status-success-200 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/50 text-status-success-800 dark:text-status-success-300 rounded-lg font-medium transition-colors"
                    >
                      Vote For
                    </button>
                    <button
                      onClick={() => setPendingVote({ voteId: vote.id, choice: 'no', title: vote.title })}
                      aria-label={`Vote against on: ${vote.title}`}
                      className="flex-1 px-3 py-2 bg-status-danger-100 hover:bg-status-danger-200 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/50 text-status-danger-800 dark:text-status-danger-300 rounded-lg font-medium transition-colors"
                    >
                      Vote Against
                    </button>
                    <button
                      onClick={() => setPendingVote({ voteId: vote.id, choice: 'abstain', title: vote.title })}
                      aria-label={`Abstain on: ${vote.title}`}
                      className="flex-1 px-3 py-2 bg-status-warning-100 hover:bg-status-warning-200 dark:bg-status-warning-900/30 dark:hover:bg-status-warning-900/50 text-status-warning-800 dark:text-status-warning-300 rounded-lg font-medium transition-colors"
                    >
                      Abstain
                    </button>
                  </div>
                )}

                {vote.user_vote && (
                  <div role="status" aria-live="polite" className="flex items-center gap-2 pt-4 border-t border-lsc-border dark:border-earth-700 text-sm">
                    <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                      You voted: <span className="font-medium">{vote.user_vote}</span>
                    </span>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* Vote Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!pendingVote}
        title="Confirm Your Vote" confirmText="Cast Vote" confirmVariant="primary"
        message={pendingVote ? `Cast vote "${pendingVote.choice === 'yes' ? 'For' : pendingVote.choice === 'no' ? 'Against' : 'Abstain'}" on "${pendingVote.title}"? This cannot be changed.` : ''}
        onConfirm={async () => {
          if (pendingVote) {
            await handleCastVote(pendingVote.voteId, pendingVote.choice)
            setPendingVote(null)
          }
        }}
        onCancel={() => setPendingVote(null)}
      />

      {/* Voting Detail Modal */}
      {selectedVote && (
        <VotingDetailModal
          vote={selectedVote}
          onClose={() => setSelectedVote(null)}
        />
      )}

      {/* Voting Form */}
      {showForm && isAdmin && (
        <VotingForm
          vote={editingVote}
          onSubmit={handleAddVote}
          onCancel={() => {
            setShowForm(false)
            setEditingVote(null)
          }}
          loading={submitting}
        />
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Vote?"
        message={`Are you sure you want to delete the vote "${deleteConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleDeleteVote}
        onCancel={() => setDeleteConfirm(null)}
        loading={submitting}
      />
    </div>
  )
}